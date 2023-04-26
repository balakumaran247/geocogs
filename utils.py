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
from typing import Tuple, Optional, Callable
import calendar

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

def month_days(year: int, month: int) -> int:
    """get the no. of days in a month

    Args:
        year (int): input year
        month (int): input month

    Returns:
        int: no. of days in the month
    """
    return calendar.monthrange(year, month)[1]
class GeoCogsBase:
    def __init__(
        self,
        featureCol,
        dataset,
        year = None,
        start_year = None,
        end_year = None,
        start_month = None,
        end_month = None,
        spatial_stat = None,
        temporal_stat = None,
        temporal_step = None,
        col_name = None
        ) -> None:
        self.featureCol = featureCol
        self.dataset = dataset
        self.year = year
        self.start_year = start_year
        self.end_year = end_year
        self.start_month = start_month
        self.end_month = end_month
        self.spatial_stat = spatial_stat
        self.temporal_stat = temporal_stat
        self.temporal_step = temporal_step
        self.col_name = col_name
        if self.year is None and (self.start_year is None or self.end_year is None):
            raise(ValueError("Start and End Years or Year expected."))
    
    def set_image_coll(self, dataset: Optional[str] = None) -> ee.ImageCollection:
        self.iColl = image_col[dataset] if dataset else image_col[self.dataset]
        return self.iColl
    
    def get_date_range(
        self,
        year: int,
        end_year: Optional[int] = None,
        start_month: int = 6,
        end_month: int = 6,
        start_date: int = 1,
        end_date: int = 1,
        extend: bool = False
        ) -> ee.DateRange:
        if end_year is None:
            end_year = year
        start = ee.Date.fromYMD(year, start_month, start_date)
        end = ee.Date.fromYMD(end_year, end_month, end_date)
        if extend:
            end = end.advance(1, 'day')
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
    
    def filter_image_coll(
        self,
        iColl: Optional[ee.ImageCollection] = None,
        date_range: Optional[ee.DateRange] = None,
        start_ee_date: Optional[ee.Date] = None,
        end_ee_date: Optional[ee.Date] = None) -> ee.ImageCollection:
        if iColl is None:
            try:
                iColl = self.iColl
            except NameError as e:
                raise (NameError('Image Collection is not found.')).with_traceback(
                    e.__traceback__
                ) from e
        if date_range is None and (start_ee_date is None or end_ee_date is None):
            raise(ValueError("Start and End Dates or Date Range expected."))
        if date_range:
            return iColl.filterDate(date_range)
        else:
            return iColl.filter(ee.Filter.date(start_ee_date, end_ee_date))
    
    def spatial_reduce_setup(self, reducer_str: str, boundary: Optional[ee.Geometry] = None) -> Callable:
        if boundary is None:
            boundary = self.featureCol
        def spatial_reduce(image: ee.Image) -> ee.FeatureCollection:
            return ee.Image(image).reduceRegions(
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
        return spatial_reduce