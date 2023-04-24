from qgis.core import (
    QgsJsonExporter,
    QgsVectorLayer,
    QgsProcessingException,
    QgsFeedback
)
import json
import ee
ee.Initialize()
from .geeassets import feature_col, image_col, stat_dict
from typing import Tuple, Optional

dw_class_ordered = ('water',
    'trees',
    'grass',
    'flooded_vegetation',
    'crops',
    'shrub_and_scrub',
    'built',
    'bare',
    'snow_and_ice')

def get_feature_collection(active_lyr: QgsVectorLayer) -> ee.FeatureCollection:
    """convert the input QGIS Vector layer to ee.Feature Collection

    Args:
        active_lyr (QgsVectorLayer): active layer from the iface

    Returns:
        ee.FeatureCollection: Earth Engine Feature Collection object of the layer
    """
    lyr = QgsJsonExporter(active_lyr)
    gs = lyr.exportFeatures(active_lyr.getFeatures())
    gj = json.loads(gs)
    for feature in gj['features']:
        feature['id'] = f'{feature["id"]:04d}'
    return ee.FeatureCollection(gj)

def get_admin_info(feature: ee.Feature) -> Tuple[str, str]:
    """Get State and District Name from Dist2011 FC for the input feature
    based on Proximity analysis of the centroid

    Args:
        feature (ee.Feature): Input Feature

    Returns:
        Tuple[str,str]: State Name and District Name
    """
    geom = ee.Feature(feature)
    geometry_centroid = geom.centroid()
    dist_boundary = feature_col['dist2011']
    filtered = dist_boundary.filterBounds(geom.geometry())
    def calc_dist(poly):
        dist = geometry_centroid.distance(poly.centroid())
        return poly.set('mindist',dist)
    dist_fc = filtered.map(calc_dist)
    min_dist = dist_fc.sort('mindist', True).first().getInfo()
    return (min_dist['properties']['ST_NM'], min_dist['properties']['DISTRICT'])

def set_progressbar_perc(feedback: QgsFeedback, perc: int) -> None:
    """Set the feedback percentage in Progess bar

    Args:
        feedback (QgsFeedback): feadback object
        perc (int): progressbar percentage to set

    Raises:
        QgsProcessingException: Cancel button clicked
    """
    if feedback.isCanceled():
        raise QgsProcessingException('Processing Canceled.')
    feedback.setProgress(perc)

class GeoCogsBase:
    def __init__(self, **kwargs) -> None:
        '''
        featureCol,
        dataset,
        year,
        start_year,
        end_year,
        start_month,
        end_month,
        spatial_stat,
        temporal_stat,
        temporal_step,
        col_name
        '''
        self.geocogs = kwargs
    
    def set_image_coll(self, dataset: Optional[str] = None) -> ee.ImageCollection:
        self.iColl = image_col[dataset] if dataset else image_col[self.geocogs['dataset']]
        return self.iColl
    
    def get_date_range(self, **kwargs) -> ee.DateRange:
        '''
        start_year: int,
        end_year: Optional[int] = None,
        start_month: int = 6,
        end_month: int = 6,
        start_date: int = 1,
        end_date: int = 1
        '''
        iargs = {
            'start_year': kwargs.get('start_year', self.geocogs['year']),
            'end_year': kwargs.get('end_year', self.geocogs['year'] + 1),
            'start_month': kwargs.get('start_month', 6),
            'end_month': kwargs.get('end_month', 6),
            'start_date': kwargs.get('start_date', 1),
            'end_date': kwargs.get('end_date', 1),
        }
        start = ee.Date.fromYMD(iargs['start_year'], iargs['start_month'], iargs['start_date'])
        end = ee.Date.fromYMD(iargs['end_year'], iargs['end_month'], iargs['end_date'])
        return ee.DateRange(start,end)
    
    def generate_proj_scale(
        self,
        iColl: Optional[ee.ImageCollection] = None,
        band_id: int = 0,
        epsg_value: Optional[int] = None,
        scale: Optional[int] = None) -> None:
        if iColl is None:
            iColl = self.iColl
        sample_image = iColl.first().select(band_id)
        if epsg_value:
            self.proj = ee.Projection(f'EPSG:{epsg_value}')
        else:
            self.proj = sample_image.projection()
        self.scale = scale or self.proj.nominalScale()
    
    def filter_image_coll(self, **kwargs) -> ee.ImageCollection:
        '''
        date_range (ee.DateRange)
        --------OR-------------
        start_ee_date (ee.Date)
        end_ee_date (ee.Date)
        '''
        iColl = kwargs.get('iColl', self.iColl)
        if 'date_range' in kwargs:
            return iColl.filterDate(kwargs['date_range'])
        else:
            return iColl.filter(ee.Filter.date(kwargs['start_ee_date'], kwargs['end_ee_date']))
    
    def spatial_reduce(self, image: ee.Image, reducer_str: str, boundary: Optional[ee.Geometry] = None) -> ee.FeatureCollection:
        if boundary is None:
            boundary = self.geocogs['featureCol']
        return image.reduceRegions(
                collection= boundary,
                reducer= stat_dict[reducer_str],
                scale= self.scale,
                crs= self.proj
            ).set(
                "year",
                ee.Date(ee.Image(image).get("system:time_start")).get('year')
                ).set(
                "month",
                ee.Date(ee.Image(image).get("system:time_start")).get('month')
                ).set(
                "day",
                ee.Date(ee.Image(image).get("system:time_start")).get('day')
                )