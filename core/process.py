import ee
import json
from qgis.core import QgsJsonExporter, QgsProcessingFeedback, QgsVectorLayer
from typing import Optional

from .helper import Assistant

class GeoCogs:
    PREFERENCES = Assistant.read_preferences()
    
    def set_params(self, params = None) -> None:
        self.params = params
        self._params = {
            'select_band': None,
            'temp_reducer': ee.Reducer.mean(),
            'spat_reducer': ee.Reducer.mean(),
            'scale': self.PREFERENCES['defaults']['defaultScale'],
            'tileScale': 1,
            'crs': None,
            'bands': None,
            'bandsRename': None,
            'imgProps': None,
            'imgPropsRename': None,
            'datetimeName': 'date',
            'datetimeFormat': 'YYYY-MM-dd'
        }
        if self.params:
            for param in self.params:
                self._params[param] = self.params.get(param, self._params[param])

    def layer2ee(self, active_lyr: QgsVectorLayer, selected: bool = False, feedback: Optional[QgsProcessingFeedback] = None) -> None:
        def convert2ee(active_lyr, features):
            lyr = QgsJsonExporter(active_lyr)
            gs = lyr.exportFeatures(features)
            gj = json.loads(gs)
            for feature in gj["features"]:
                feature["id"] = f'{feature["id"]:04d}'
            return ee.FeatureCollection(gj)
        selected_count = active_lyr.selectedFeatureCount()
        if selected:
            if feedback: Assistant.logger(feedback, f'selected features: {selected_count}')
            self.ee_featurecollection = convert2ee(active_lyr, active_lyr.selectedFeatures())
        else:
            self.ee_featurecollection = convert2ee(active_lyr, active_lyr.getFeatures())
    
    def reduce2imagecollection(self, ic: ee.ImageCollection, fc: ee.FeatureCollection, start_year: int, end_year: int, span: str, step: str) -> ee.ImageCollection:
        years_range = range(start_year, end_year+1)
        if step == 'Monthly':
            unit = 'month'
            if span == 'Calendar Year':
                months_range = range(1, 13)
                date_range = [f'{year}-{month:02d}-01' for year in years_range for month in months_range]
            else:
                hyd_month = self.PREFERENCES['dateTime']['hydrologicalYearStartMonth']
                date_range = [f'{year}-{month:02d}-01' for year in years_range for month in range(hyd_month, 13)]
                date_range += [f'{year+1}-{month:02d}-01' for year in years_range for month in range(1, hyd_month)]
        else:
            unit = 'year'
            if span == 'Calendar Year':
                date_range = [f'{year}-01-01' for year in years_range]
            else:
                date_range = [f'{year}-{self.PREFERENCES["dateTime"]["hydrologicalYearStartMonth"]:02d}-01' for year in years_range]
        return ee.ImageCollection.fromImages(ee.List(date_range).map(lambda x: self._composite(x, ic, fc, unit)))
    
    def zonal_stats(self, ic: ee.ImageCollection, fc: ee.FeatureCollection) -> ee.FeatureCollection:
        img_rep = ic.first()
        non_system_img_props = ee.Feature(None).copyProperties(img_rep).propertyNames()
        if not self._params['bands']:
            self._params['bands'] = img_rep.bandNames()
        if not self._params['bandsRename']:
            self._params['bandsRename'] = self._params['bands']
        if not self._params['imgProps']:
            self._params['imgProps'] = non_system_img_props
        if not self._params['imgPropsRename']:
            self._params['imgPropsRename'] = self._params['imgProps']

        def _get_stats(img: ee.Image) -> ee.FeatureCollection:
            # img = ee.Image(img.select(self._params['bands'], self._params['bandsRename'])) \
            #     .set(self._params['datetimeName'], img.date().format(self._params['datetimeFormat'])) \
            #     .set('timestamp', img.get('system:time_start'))

            # props_from = ee.List(self._params['imgProps']).cat(ee.List([self._params['datetimeName'], 'timestamp']))
            # props_to = ee.List(self._params['imgPropsRename']).cat(ee.List([self._params['datetimeName'], 'timestamp']))
            # img_props = img.toDictionary(props_from).rename(props_from, props_to)

            img = ee.Image(img.set(self._params['datetimeName'], img.date().format(self._params['datetimeFormat'])).set('timestamp', img.get('system:time_start')))
            props = ee.List([self._params['datetimeName'], 'timestamp'])
            img_props = img.toDictionary(props)
            return img.reduceRegions(
                collection=fc,
                reducer=self._params['spat_reducer'],
                scale=self._params['scale'],
                crs=self._params['crs'],
                tileScale=self._params['tileScale']
            ).map(lambda f: f.set(img_props))

        results = ic.map(_get_stats).flatten()#.filter(ee.Filter.notNull(self._params['bandsRename']))

        return results

    def _composite(self, date: str, ic: ee.ImageCollection, fc: ee.FeatureCollection, unit: str) -> ee.Image:
        start_date = ee.Date(date)
        end_date = start_date.advance(1, unit)
        return ee.Image(ic.filterDate(
            start_date, end_date
            ).filterBounds(fc).select([self._params.get('select_band')]).reduce(
                self._params.get('temp_reducer')
                ).rename(self._params.get('select_band')).set('system:time_start', start_date.millis()))
