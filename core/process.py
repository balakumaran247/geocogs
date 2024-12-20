import ee
import json
from qgis.core import QgsJsonExporter

from .helper import Assistant

ee.Initialize()


class GeoCogs:
    def __init__(self, params = None) -> None:
        self.params = params
        self._params = {
            'spat_reducer': ee.Reducer.mean(),
            'scale': None,
            'tileScale': 1,
            'crs': None,
            'bands': None,
            'bandsRename': None,
            'imgProps': None,
            'imgPropsRename': None,
            'datetimeName': 'date',#time',
            'datetimeFormat': 'YYYY-MM-dd'# HH:mm:ss'
        }

    def layer2ee(self, active_lyr, selected: bool = False):
        def convert2ee(active_lyr, features):
            lyr = QgsJsonExporter(active_lyr)
            gs = lyr.exportFeatures(features)
            gj = json.loads(gs)
            for feature in gj["features"]:
                feature["id"] = f'{feature["id"]:04d}'
            return ee.FeatureCollection(gj)
        selected_count = active_lyr.selectedFeatureCount()
        if selected:
            print(f'selected features: {selected_count}')
            return convert2ee(active_lyr, active_lyr.selectedFeatures())
        else:
            return convert2ee(active_lyr, active_lyr.getFeatures())
    
    def zonal_stats(self, ic, fc):
        if self.params:
            for param in self.params:
                self._params[param] = self.params.get(param, self._params[param])

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

        def _get_stats(img):
            img = ee.Image(img.select(self._params['bands'], self._params['bandsRename'])) \
                .set(self._params['datetimeName'], img.date().format(self._params['datetimeFormat'])) \
                .set('timestamp', img.get('system:time_start'))

            props_from = ee.List(self._params['imgProps']).cat(ee.List([self._params['datetimeName'], 'timestamp']))
            props_to = ee.List(self._params['imgPropsRename']).cat(ee.List([self._params['datetimeName'], 'timestamp']))
            img_props = img.toDictionary(props_from).rename(props_from, props_to)

            return img.reduceRegions(
                collection=fc,
                reducer=self._params['spat_reducer'],
                scale=self._params['scale'],
                crs=self._params['crs'],
                tileScale=self._params['tileScale']
            ).map(lambda f: f.set(img_props))

        results = ic.map(_get_stats).flatten().filter(ee.Filter.notNull(self._params['bandsRename']))

        return results
