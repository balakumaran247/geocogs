from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from time import perf_counter
from typing import Any, Optional

import ee
from qgis.core import QgsProcessingFeedback

from .helper import Assistant

ee.Initialize()


class ImageCollections:
    TIMESTAMP_LABEL = 'system:time_start'
    CALENDAR_START_MONTH = 1
    CALENDAR_END_MONTH = 12
    HYDROLOGICAL_START_MONTH = Assistant.read_preferences()['dateTime']['hydrologicalYearStartMonth']
    HYDROLOGICAL_END_MONTH = HYDROLOGICAL_START_MONTH - 1

    def __init__(self, parameter: str) -> None:
        """
        Initializes the ImageCollections class with a parameter.

        Args:
            parameter (str): The parameter for the image collection.
        """
        self.parameter = parameter

    @property
    def band(self) -> str:
        """
        Returns the band name for the image collection.
        """
        return {
            'IMD Rainfall': 'b1',
            'IMD Max Temperature': 'b1',
            'IMD Min Temperature': 'b1',
            'ETa SSEBop': 'b1',
            'Dynamic World V1': 'label'
        }[self.parameter]

    @property
    def ee_object(self) -> ee.ImageCollection:
        """
        Returns the Earth Engine ImageCollection object.
        """
        return ee.ImageCollection(Assistant.read_json().get(self.parameter).get('id'))

    def __call__(self) -> ee.ImageCollection:
        """
        Returns the Earth Engine ImageCollection object.
        """
        return self.ee_object

    @staticmethod
    def _get_date(asset: Any, start_date: ee.Date, advance_count: int) -> datetime:
        """
        Recursively finds the date based on the asset and advance count.

        Args:
            asset (Any): The Earth Engine asset.
            start_date (ee.Date): The start date.
            advance_count (int): The number of months to advance.

        Returns:
            datetime: The calculated date.
        """
        end_date = start_date.advance(advance_count, 'month')
        filtered = asset.filterDate(start_date.advance(
            abs(advance_count)*-1, 'month'), start_date.advance(abs(advance_count), 'month'))
        adv_filtered = asset.filterDate(
            start_date, end_date) if advance_count > 0 else asset.filterDate(end_date, start_date)
        if adv_filtered.size().getInfo():
            return ImageCollections._get_date(asset, end_date, advance_count)
        try:
            date = filtered.aggregate_max(ImageCollections.TIMESTAMP_LABEL).getInfo(
            ) if advance_count > 0 else filtered.aggregate_min(ImageCollections.TIMESTAMP_LABEL).getInfo()
        except Exception as e:
            raise ValueError(
                f'Failed to get date for {asset.get("system:id").getInfo()}') from e
        return datetime.fromtimestamp(date/1000.0)

    @staticmethod
    def _fetch_properties(label: str, data: dict) -> dict:
        """
        Fetches properties for a given label and data.

        If the label is 'last_update', it returns a dictionary with the label and data.
        Otherwise, it fetches the start and end dates from the Earth Engine ImageCollection
        and returns a dictionary with the updated date properties.

        Args:
            label (str): The label for the properties to fetch.
            data (dict): The data containing the properties to fetch. It should include
                         'id', 'start_year', 'start_month', 'start_day', 'end_year', 
                         'end_month', and 'end_day'.

        Returns:
            dict: A dictionary containing the label and the fetched properties.
        """
        asset = ee.ImageCollection(data.get('id'))
        current_start_date = ee.Date.fromYMD(
            data.get('start_year'), data.get('start_month'), data.get('start_day'))
        current_end_date = ee.Date.fromYMD(data.get('end_year'),
                                           data.get('end_month'), data.get('end_day'))
        with ThreadPoolExecutor() as ex:
            futures = [
                ex.submit(ImageCollections._get_date,
                          asset, current_start_date, -3),
                ex.submit(ImageCollections._get_date,
                          asset, current_end_date, 3)
            ]
        min_date = futures[0].result()
        max_date = futures[1].result()
        dates_dict = {
            'start_year': int(f'{min_date:%Y}'),
            'start_month': int(f'{min_date:%m}'),
            'start_day': int(f'{min_date:%d}'),
            'end_year': int(f'{max_date:%Y}'),
            'end_month': int(f'{max_date:%m}'),
            'end_day': int(f'{max_date:%d}')
        }
        return {label: data | dates_dict}

    @staticmethod
    def _compute_year_step(data: dict) -> dict:
        """
        Computes the adjusted start and end years for calendar and hydrological years based on the given data.
        Args:
            data (dict): A dictionary where keys are labels and values are dictionaries containing 
                         'start_month', 'end_month', 'start_year', and 'end_year'.
        Returns:
            dict: A dictionary with the same keys as the input, but with values updated to include 
                  'calendar_start', 'hydrological_start', 'calendar_end', and 'hydrological_end' years.
        """
        for label, properties in data.items():
            start_month = properties.get('start_month')
            end_month = properties.get('end_month')
            start_year = properties.get('start_year')
            end_year = properties.get('end_year')
            data[label] |= {
                'calendar_start': start_year if start_month == ImageCollections.CALENDAR_START_MONTH else start_year + 1,
                'hydrological_start': start_year if start_month < ImageCollections.HYDROLOGICAL_START_MONTH else start_year + 1,
                'calendar_end': end_year if end_month == ImageCollections.CALENDAR_END_MONTH else end_year - 1,
                'hydrological_end': end_year - 1 if end_month > ImageCollections.HYDROLOGICAL_END_MONTH else end_year - 2
            }
        return data

    @staticmethod
    def update_metadata(date: str, feedback: Optional[QgsProcessingFeedback] = None) -> None:
        """
        Updates the metadata by fetching properties for each item in the image collections JSON.

        This function reads the existing metadata from a JSON file, checks if the 'last_update' key
        matches the provided date, and if not, it fetches updated properties for each item in the
        image collections. The updated metadata is then written back to the JSON file.

        Args:
            date (str): The date string to compare with the 'last_update' key in the metadata.

        Raises:
            KeyError: If the 'last_update' key is not found in the image collections JSON.
        """
        data = Assistant.read_json()
        if last_update := data.get('last_update') != date:
            start_time = perf_counter()
            if not last_update:
                raise KeyError(
                    'last_update key not found in the imagecollections JSON')
            data.pop('last_update', None)
            out_dict = {}
            with ThreadPoolExecutor() as ex:
                futures = [ex.submit(ImageCollections._fetch_properties, k, v)
                           for k, v in data.items()]
            for future in as_completed(futures):
                out = future.result()
                # if feedback: Assistant.logger(
                #     feedback,
                #     f'Updated metadata for {list(out.keys())[0]}',
                #     True
                # )
                out_dict |= out
            out_dict = ImageCollections._compute_year_step(out_dict)
            out_dict['last_update'] = date
            Assistant.write_json(out_dict)
            end_time = perf_counter()
            if feedback: Assistant.logger(
                feedback,
                f"metadata updated in {end_time - start_time:.2f} seconds",
                True
            )
        if feedback: Assistant.logger(feedback, 'Metadata is up to date', True)


@dataclass
class Reducers:
    """
    A class to manage and retrieve Google Earth Engine (GEE) reducers.
    Attributes:
        reducer (str): The name of the reducer to retrieve.
    Methods:
        ee_object() -> ee.Reducer:
            Returns the GEE Reducer object corresponding to the specified reducer name.
        __call__() -> ee.Reducer:
            Returns the GEE Reducer object corresponding to the specified reducer name.
    """
    reducer: str

    @property
    def ee_object(self) -> ee.Reducer:
        """
        Returns the Earth Engine Reducer object.
        """
        return {
            'sum': ee.Reducer.sum(),
            'mean': ee.Reducer.mean(),
            'median': ee.Reducer.median(),
            'max': ee.Reducer.max(),
            'min': ee.Reducer.min(),
            'mode': ee.Reducer.mode()
        }[self.reducer.lower()]
    
    def __call__(self) -> ee.Reducer:
        return self.ee_object
