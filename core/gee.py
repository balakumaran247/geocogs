from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import ee

from .helper import read_json, write_json

ee.Initialize()


class ImageCollections:
    TIMESTAMP_LABEL = 'system:time_start'

    def __init__(self, parameter: str) -> None:
        """
        Initializes the ImageCollections class with a parameter.

        Args:
            parameter (str): The parameter for the image collection.
        """
        self.parameter = parameter

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
        print(ee.Date(start_date).format('y-M-d').getInfo())
        end_date = start_date.advance(advance_count, 'month')
        print(ee.Date(end_date).format('y-M-d').getInfo())
        filtered = asset.filterDate(start_date.advance(
            abs(advance_count)*-1, 'month'), start_date.advance(abs(advance_count), 'month'))
        print(filtered.size().getInfo())
        adv_filtered = asset.filterDate(
            start_date, end_date) if advance_count > 0 else asset.filterDate(end_date, start_date)
        if adv_filtered.size().getInfo():
            return ImageCollections._get_date(asset, end_date, advance_count)
        date = filtered.aggregate_max(ImageCollections.TIMESTAMP_LABEL).getInfo(
        ) if advance_count > 0 else filtered.aggregate_min(ImageCollections.TIMESTAMP_LABEL).getInfo()
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
        if label == 'last_update':
            return {label: data}
        asset = ee.ImageCollection(data.get('id'))
        current_start_date = ee.Date.fromYMD(int(data.get('start_year')), int(
            data.get('start_month')), int(data.get('start_day')))
        current_end_date = ee.Date.fromYMD(int(data.get('end_year')), int(
            data.get('end_month')), int(data.get('end_day')))
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
            'start_year': f'{min_date:%Y}',
            'start_month': f'{min_date:%m}',
            'start_day': f'{min_date:%d}',
            'end_year': f'{max_date:%Y}',
            'end_month': f'{max_date:%m}',
            'end_day': f'{max_date:%d}'
        }
        return {label: data | dates_dict}

    @staticmethod
    def update_metadata(date: str) -> None:
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
        data = read_json()
        if last_update := data.get('last_update') != date:
            if not last_update:
                raise KeyError(
                    'last_update key not found in the imagecollections JSON')
            out_dict = {}
            with ThreadPoolExecutor() as ex:
                futures = [ex.submit(ImageCollections._fetch_properties, k, v)
                           for k, v in data.items()]
            for future in as_completed(futures):
                out = future.result()
                out_dict |= out
            out_dict['last_update'] = date
            write_json(out_dict)


@dataclass
class Reducers:
    """
    A class to manage and retrieve Google Earth Engine (GEE) reducers.
    Attributes:
        reducer (str): The name of the reducer to retrieve.
        _reducers (dict[str, ee.Reducer]): A dictionary mapping reducer names to their corresponding GEE Reducer objects.
    Methods:
        __call__() -> ee.Reducer:
            Returns the GEE Reducer object corresponding to the specified reducer name.
    """
    reducer: str
    _reducers: dict[str, ee.Reducer] = field(default_factory=lambda: {
        'total': ee.Reducer.sum(),
        'mean': ee.Reducer.mean(),
        'median': ee.Reducer.median(),
        'max': ee.Reducer.max(),
        'min': ee.Reducer.min(),
        'mode': ee.Reducer.mode()
    }, init=False, repr=False, hash=True, compare=False)

    def __call__(self) -> ee.Reducer:
        return self._reducers.get(self.reducer.lower())
