from ..geeassets import image_col, stat_dict, expression_dict, mask_s2_clouds
from .boundarystatisticsutils import get_IITB_dr
import pandas as pd
import numpy as np
import ee
ee.Initialize()
from qgis.core import QgsProcessingException

class BoundaryWiseStats:
    """
    class to handle an image collection , 
    aggregate it as required, monthly/yearly etc
    then return stats for a feature collection's polygons
    """

    def __init__(self,featureCol,dataset,year,spatial_stat,temporal_stat,temporal_step):
        self.boundaries = featureCol
        self.spatial_stat = spatial_stat
        self.temporal_stat = temporal_stat
        self.temporal_step = temporal_step
        self.dataset = dataset
        self.year = year
        self.S2_indices = ['NDVI']

    def set_image_coll(self):
        if self.dataset in self.S2_indices:
            self.iColl = image_col['S2']
        else:
            self.iColl = image_col[self.dataset]

    def make_date_range_list(self, span): 
        if self.temporal_step == 'Monthly' and span == 'hydrological year':
            if self.dataset == 'ET(IITB)':
                self.drl = get_IITB_dr(self.year, 'hyd_month')
            else:
                # list of months in hydro year - [6,..,12,1,..,5]
                months1 = ee.List.sequence(6,12)
                months2 = ee.List.sequence(1,5)
                dr1 = months1.map(
                    lambda m: ee.Date.fromYMD(self.year,m,1).getRange('month'))
                dr2 = months2.map(
                    lambda m: ee.Date.fromYMD(self.year+1,m,1).getRange('month'))
                self.drl = dr1.cat(dr2)
        elif self.temporal_step == 'Yearly' and span == 'hydrological year':
            if self.dataset == 'ET(IITB)':
                self.drl = get_IITB_dr(self.year, 'hyd_year')
            else:
                start = ee.Date.fromYMD(self.year,6,1)
                end = ee.Date.fromYMD(self.year+1,6,1)
                self.drl = ee.List([ee.DateRange(start,end)])
        elif self.temporal_step == 'Yearly' and span == 'calendar year':
            if self.dataset == 'ET(IITB)':
                self.drl = get_IITB_dr(self.year, 'cal_year')
            else:
                start = ee.Date.fromYMD(self.year,1,1)
                end = ee.Date.fromYMD(self.year+1,1,1)
                self.drl = ee.List([ee.DateRange(start,end)])
        elif self.temporal_step == 'Monthly' and span == 'calendar year':
            if self.dataset == 'ET(IITB)':
                self.drl = get_IITB_dr(self.year, 'cal_month')
            else:
                months = ee.List.sequence(1,12)
                self.drl = months.map(
                    lambda m: ee.Date.fromYMD(self.year,m,1).getRange('month'))
        else:
            raise QgsProcessingException('DateRange could not be acquired')
    
    def filter_image_coll(self):
        start = ee.Date.fromYMD(self.year,1,1)
        end = ee.Date.fromYMD(self.year+1,12,31)
        self.iColl_filtered = self.iColl.filterDate(start,end)
        
        if self.dataset in self.S2_indices:
            self.sample_image = self.iColl_filtered.first().select(3)
            self.proj = ee.Projection('EPSG:4326')
            self.scale = 10
        else:
            self.sample_image = self.iColl_filtered.first().select(0)
            self.proj = self.sample_image.projection()
            self.scale = self.proj.nominalScale()
    
    def set_temporal_reducer(self):
        self.tempReducer = stat_dict.get(self.temporal_stat)
        
    def set_spatial_reducer(self):
        self.spatialReducer = stat_dict.get(self.spatial_stat)

    def temp_reduce_image_coll(self):
        def temp_reduce_image(dr):
            start = ee.DateRange(dr).start()
            end = ee.DateRange(dr).end()
            if self.dataset in self.S2_indices:
                mimages = self.iColl_filtered.filter(ee.Filter.date(
                    start,end)).map(mask_s2_clouds).map(
                    expression_dict[self.dataset]).select(0)
            else:
                mimages = self.iColl_filtered.filter(ee.Filter.date(start,end)).select(0)
            mimages_reduced = mimages.reduce(self.tempReducer)
            mimages_reduced = ee.Image(mimages_reduced.set(
                'system:time_start', start.millis()).set(
                'system:time_end', end.millis()))
            return ee.Image(mimages_reduced.updateMask(mimages_reduced.gte(0)))
        def temp_reduce_IITBET(dr):
            IC_comb = ee.ImageCollection([])
            timestamp = None
            for ix, ele in enumerate(dr):
                start, end, coeff = ele
                mimages = self.iColl_filtered.filter(ee.Filter.date(start, end)).select(0)
                if ix == 1:
                    timestamp = ee.Image(mimages.first()).get('system:time_start')
                mimages = mimages.map(
                    lambda x: (x.multiply(coeff)).updateMask(x.multiply(coeff).gte(0))
                )
                IC_comb = IC_comb.merge(mimages)
            mimages_reduced = IC_comb.reduce(self.tempReducer)
            mimages_reduced = ee.Image(mimages_reduced.set('system:time_start', timestamp))
            return ee.Image(mimages_reduced.updateMask(mimages_reduced.gte(0)))
        if self.dataset == 'ET(IITB)':
            self.iColl_reduced = ee.List(list(map(temp_reduce_IITBET, self.drl)))
        else:
            self.iColl_reduced = self.drl.map(temp_reduce_image)
        
    def get_boundarywisestats(self):
        self.bws = self.iColl_reduced.map(
            lambda image:
                ee.Image(image).reduceRegions(
                collection= self.boundaries,
                reducer= self.spatialReducer,
                scale= self.scale,
                crs= self.proj
            ).set(
                "year",ee.Date(ee.Image(image).get("system:time_start")).get('year'))
            .set(
                "month",ee.Date(ee.Image(image).get("system:time_start")).get('month'))
        )
    
    def get_out_dict(self, col_name, progressbar=None):
        if progressbar:
            feedback, func, current, pextent= progressbar
        self.out_dict = {}
        self.bws_size = self.bws.size().getInfo()
        if progressbar:
            current += 2
            func(feedback,current)
        self.fc_size = self.boundaries.size().getInfo()
        if progressbar:
            current += 2
            func(feedback,current)
        ptotal = self.bws_size * self.fc_size
        if progressbar:
            pstep = (pextent-4)/ptotal
        for period in range(self.bws_size):
            month = self.bws.get(period).getInfo()
            col = f"{month['properties']['year']}{month['properties']['month']:02d}"
            self.out_dict[col] = {}
            for feature in month['features']:
                distr = feature['properties'][col_name]
                if self.spatial_stat in feature['properties'].keys():
                    valu = feature['properties'][self.spatial_stat]
                else:
                    valu = np.nan
                self.out_dict[col][distr] = valu
                if progressbar:
                    current += pstep
                    func(feedback,current)

    def export_csv(self, path):
        df = pd.DataFrame(self.out_dict)
        df.to_csv(path)
