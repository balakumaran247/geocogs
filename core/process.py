import json
from typing import Dict, Optional

import ee
from qgis.core import (QgsJsonExporter, QgsProcessingException,
                       QgsProcessingFeedback, QgsVectorLayer)

from .helper import Assistant


class GeoCogs:
    PREFERENCES = Assistant.read_preferences()

    def set_params(self, params: Optional[Dict] = None) -> None:
        """
        Sets the parameters for the GeoCogs class.

        Args:
            params (Optional[Dict]): A dictionary of parameters to set. If None, default parameters will be used.
        """
        self.params = params
        self._params = {
            'select_band': None,
            'temp_reducer': ee.Reducer.mean(),
            'spat_reducer': ee.Reducer.mean(),
            'scale': self.PREFERENCES['defaults']['defaultScale'],
            'tileScale': 1,
            'crs': 'EPSG:4326',
            'datetimeName': 'date',
            'datetimeFormat': 'YYYY-MM-dd'
        }
        if self.params:
            for param in self._params:
                self._params[param] = self.params.get(
                    param, self._params[param])

    def layer2ee(self, active_lyr: QgsVectorLayer, selected: bool = False, feedback: Optional[QgsProcessingFeedback] = None) -> None:
        """
        Converts a QGIS vector layer to an Earth Engine object.

        Args:
            active_lyr (QgsVectorLayer): The active QGIS vector layer to convert.
            selected (bool): If True, only selected features will be converted. Defaults to False.
            feedback (Optional[QgsProcessingFeedback]): Feedback object for processing messages. Defaults to None.
        """
        def convert2ee(active_lyr, features):
            lyr = QgsJsonExporter(active_lyr)
            gs = lyr.exportFeatures(features)
            gj = json.loads(gs)
            for feature in gj["features"]:
                feature["id"] = f'{feature["id"]:04d}'
            return ee.FeatureCollection(gj)
        selected_count = active_lyr.selectedFeatureCount()
        self.layer_name = active_lyr.name()
        try:
            if selected:
                if feedback:
                    Assistant.logger(
                        feedback,
                        f'selected features: {selected_count}'
                    )
                self.ee_featurecollection = convert2ee(
                    active_lyr, active_lyr.selectedFeatures())
            else:
                self.ee_featurecollection = convert2ee(
                    active_lyr, active_lyr.getFeatures())
        except Exception as e:
            raise QgsProcessingException(
                'Error converting layer to ee.FeatureCollection')

    def reduce2imagecollection(self, ic: ee.ImageCollection, fc: ee.FeatureCollection, start_year: int, end_year: int, span: str, step: str) -> ee.ImageCollection:
        """
        Reduces an Earth Engine ImageCollection to a new ImageCollection based on specified temporal parameters.
        Args:
            ic (ee.ImageCollection): The input ImageCollection to be reduced.
            fc (ee.FeatureCollection): The FeatureCollection used for reduction.
            start_year (int): The starting year for the reduction.
            end_year (int): The ending year for the reduction.
            span (str): The span of the reduction, either 'Calendar Year' or another span.
            step (str): The step of the reduction, either 'Monthly' or 'Yearly'.
        Returns:
            ee.ImageCollection: The reduced ImageCollection based on the specified temporal parameters.
        """
        years_range = range(start_year, end_year+1)
        if step == 'Monthly':
            unit = 'month'
            if span == 'Calendar Year':
                months_range = range(1, 13)
                date_range = [
                    f'{year}-{month:02d}-01' for year in years_range for month in months_range]
            else:
                hyd_month = self.PREFERENCES['dateTime']['hydrologicalYearStartMonth']
                date_range = [
                    f'{year}-{month:02d}-01' for year in years_range for month in range(hyd_month, 13)]
                date_range += [
                    f'{year+1}-{month:02d}-01'
                    for year in years_range
                    for month in range(1, hyd_month)
                ]
        else:
            unit = 'year'
            if span == 'Calendar Year':
                date_range = [f'{year}-01-01' for year in years_range]
            else:
                date_range = [
                    f'{year}-\
                    {self.PREFERENCES["dateTime"]["hydrologicalYearStartMonth"]:02d}\
                    -01'
                    for year in years_range
                ]
        return ee.ImageCollection.fromImages(ee.List(date_range).map(lambda x: self._composite(x, ic, fc, unit)))

    def zonal_stats(self, ic: ee.ImageCollection, fc: ee.FeatureCollection) -> ee.FeatureCollection:
        """
        Computes zonal statistics for an Earth Engine ImageCollection over a given FeatureCollection.
        Args:
            ic (ee.ImageCollection): The input ImageCollection for which to compute zonal statistics.
            fc (ee.FeatureCollection): The FeatureCollection defining the zones over which to compute statistics.
        Returns:
            ee.FeatureCollection: A FeatureCollection containing the computed statistics for each zone.
        """
        def _get_stats(img: ee.Image) -> ee.FeatureCollection:
            img = ee.Image(img.set(self._params['datetimeName'], img.date().format(
                self._params['datetimeFormat'])).set('timestamp', img.get('system:time_start')))
            props = ee.List([self._params['datetimeName'], 'timestamp'])
            img_props = img.toDictionary(props)
            return img.reduceRegions(
                collection=fc,
                reducer=self._params['spat_reducer'],
                scale=self._params['scale'],
                crs=self._params['crs'],
                tileScale=self._params['tileScale']
            ).map(lambda f: f.set(img_props))

        results = ic.map(_get_stats).flatten()

        return results

    def class2area(self, image: ee.Image) -> ee.FeatureCollection:
        """
        Computes the area of each class in an Earth Engine Image.
        Args:
            image (ee.Image): The input Image for which to compute class areas.
        Returns:
            ee.FeatureCollection: A FeatureCollection containing the computed areas for each class.
        """
        image = image.select(self._params.get('select_band'))
        area_image = ee.Image.pixelArea().rename("area").addBands(image)
        return area_image.reduceRegions(
            collection=self.ee_featurecollection,
            reducer=ee.Reducer.sum().group(1, 'lulc_class'),
            scale=self._params['scale'],
            crs=self._params['crs']
        )

    def export2drive(self, data: ee.FeatureCollection, filename: str) -> None:
        """
        Exports a given Earth Engine FeatureCollection to Google Drive as a CSV file.
        Args:
            data (ee.FeatureCollection): The Earth Engine FeatureCollection to export.
            filename (str): The name of the file to be created in Google Drive.
        Returns:
            None
        """
        task = ee.batch.Export.table.toDrive(
            collection=data,
            description=filename,
            fileFormat='CSV',
            fileNamePrefix=filename
        )
        task.start()

    def _composite(self, date: str, ic: ee.ImageCollection, fc: ee.FeatureCollection, unit: str) -> ee.Image:
        """
        Generates a composite image from an Earth Engine ImageCollection within a specified date range and region.
        Args:
            date (str): The start date for the composite in 'YYYY-MM-DD' format.
            ic (ee.ImageCollection): The Earth Engine ImageCollection to composite.
            fc (ee.FeatureCollection): The Earth Engine FeatureCollection defining the region of interest.
            unit (str): The time unit for the date range (e.g., 'day', 'month', 'year').
        Returns:
            ee.Image: The composite image for the specified date range and region.
        """
        start_date = ee.Date(date)
        end_date = start_date.advance(1, unit)
        return ee.Image(ic.filterDate(
            start_date, end_date
        ).filterBounds(fc).select([self._params.get('select_band')]).reduce(
            self._params.get('temp_reducer')
        ).rename(self._params.get('select_band')).set('system:time_start', start_date.millis()))
