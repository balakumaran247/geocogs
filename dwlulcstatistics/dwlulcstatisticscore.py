from ..geeassets import image_col, stat_dict
from ..utils import dw_class_ordered
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import ee
ee.Initialize()


class DWStats:
    def __init__(self, year, span, fcol, col_name) -> None:
        self.year = year
        self.span = span
        self.feature_col = fcol
        self.col_name = col_name
        self.dw_col = image_col['dynamicworld']

    def filter_col(self):
        if self.span == "hydrological year":
            start = ee.Date.fromYMD(self.year, 6, 1)
            end = ee.Date.fromYMD(self.year+1, 6, 1)
        else:
            start = ee.Date.fromYMD(self.year, 1, 1)
            end = ee.Date.fromYMD(self.year+1, 1, 1)
        filtered = self.dw_col.filterDate(start, end).filterBounds(
            self.feature_col).select('label')
        self.dwMode = filtered.reduce(stat_dict['mode'])
        self.area_image = ee.Image.pixelArea().divide(1e4).addBands(self.dwMode)
        return self.dwMode

    def calc_area(self, feature, name):
        params = {
            'reducer': ee.Reducer.sum().group(1, 'group'), 
            'geometry': feature.geometry(), 
        }
        additional = ({'scale': 10, 'maxPixels': 1e12},
                    {'scale': 10, 'maxPixels': 1e12, 'bestEffort': True},
                    {'scale': 30, 'maxPixels': 1e12, 'bestEffort': True},
                    {'scale': 100, 'maxPixels': 1e12, 'bestEffort': True},
                    {'scale': 100, 'maxPixels': 1e12, 'bestEffort': True, 'tileScale': 2})
        for ix, p in enumerate(additional):
            try:
                params.update(p)
                result = self.area_image.reduceRegion(**params).getInfo()
                break
            except Exception:
                result = None
                print(f'{name}: parameter choice {ix} failed, moving to next parameter choice')
        if not result:
            raise IOError(f'{name} GEE Computation Timeout.')
        return result

    # def classify(self, feature):
    #     area_classified = self.calc_area(feature)
    #     f_area = ee.Number(feature.area()).divide(1e4)
    #     return feature.set('area_classified', area_classified).set('f_area', f_area)
    
    def calc_info(self, feature):
        name = feature.getInfo()['properties'][self.col_name]
        f_area = ee.Number(feature.area()).divide(1e4).getInfo()
        area_classified = self.calc_area(feature, name)
        return (name, f_area, area_classified)

    # method to calculate area and set as property in single GEE native computation
    # def get_area_stat(self):
    #     self.final = self.feature_col.map(self.classify).getInfo()
    #     return self.final
    
    def get_area_stat(self, progressbar=None):
        self.fc_size = self.feature_col.size().getInfo()
        if progressbar:
            feedback, func, current, pextent= progressbar
            pstep = (pextent)/self.fc_size
        self.fc_list = self.feature_col.toList(self.fc_size)
        # self.final = [self.classify(ee.Feature(self.fc_list.get(num))) for num in range(self.fc_size)]
        self.final = []
        with ThreadPoolExecutor() as ex:
            futures = [ex.submit(self.calc_info, ee.Feature(self.fc_list.get(num))) for num in range(self.fc_size)]
        # for num in range(self.fc_size):
            # self.final.append(self.calc_info(ee.Feature(self.fc_list.get(num))))
        for future in as_completed(futures):
            self.final.append(future.result())
            if progressbar:
                current += pstep
                func(feedback,current)
        return self.final
    
    def get_df(self, progressbar=None):
        if progressbar:
            feedback, func, current, pextent= progressbar
            pstep = (pextent)/self.fc_size
        self.out_dict = {}
        for f in self.final:
            # feature = f.getInfo()
            # name = feature['properties'][self.col_name]
            # f_area = feature['properties']['f_area']
            # classified = feature['properties']['area_classified']['groups']
            name, f_area, classified = f
            self.out_dict[name] = {'feature(Ha)': f_area}
            for claz in classified['groups']:
                lulc_class = dw_class_ordered[claz['group']]
                self.out_dict[name][f"{lulc_class}(Ha)"] = claz['sum']
                self.out_dict[name][f"{lulc_class}(%)"] = (claz['sum']/f_area)*100
            if progressbar:
                current += pstep
                func(feedback,current)
        return self.out_dict

    # single GEE native computation DataFrame method
    # def get_df(self):
    #     self.out_dict = {}
    #     for feature in self.final['features']:
    #         distr = feature['properties']['DISTRICT']
    #         f_area = feature['properties']['f_area']
    #         classified = feature['properties']['area_classified']['groups']
    #         self.out_dict[distr] = {'feature(Ha)': f_area}
    #         for claz in classified:
    #             lulc_class = dw_class_ordered[claz['group']]
    #             self.out_dict[distr][f"{lulc_class}(Ha)"] = claz['sum']
    #             self.out_dict[distr][f"{lulc_class}(%)"] = (claz['sum']/f_area)*100
    #     return self.out_dict
    
    def export_csv(self, path):
        df = pd.DataFrame(self.out_dict).T
        df.to_csv(path)