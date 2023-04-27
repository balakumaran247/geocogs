from qgis.core import (
    QgsJsonExporter,
    QgsVectorLayer,
    QgsProcessingException,
    QgsProcessingFeedback
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

def set_progressbar_perc(
    feedback: QgsProcessingFeedback,
    perc: int,
    text: Optional[str] = None) -> None:
    """Set the feedback percentage in Progess bar

    Args:
        feedback (QgsProcessingFeedback): feadback object
        perc (int): progressbar percentage to set
        text (Optional[str]): progress text to set

    Raises:
        QgsProcessingException: Cancel button clicked
    """
    if feedback.isCanceled():
        raise QgsProcessingException('Processing Canceled.')
    feedback.setProgress(perc)
    if text:
        feedback.setProgressText(text)

def month_days(year: int, month: int) -> int:
    """get the no. of days in a month

    Args:
        year (int): input year
        month (int): input month

    Returns:
        int: no. of days in the month
    """
    return calendar.monthrange(year, month)[1]

def logger(feedback: QgsProcessingFeedback, msg: str, console: bool = False) -> None:
    """Log Informations. console used to report the output from executing an 
    external command or subprocess.

    Args:
        feedback (QgsProcessingFeedback): feedback object
        msg (str): text to log
        console (bool, optional): True for ConsoleInfo. Defaults to False.
    """
    if console:
        feedback.pushConsoleInfo(msg)
    else:
        feedback.pushInfo(msg)

class GeoCogsBase:
    """Base Class for the GeoCogs tool with common methods for processing
    """
    def __init__(
        self,
        featureCol: ee.FeatureCollection,
        dataset: str,
        year: Optional[int] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        start_month: Optional[int] = None,
        end_month: Optional[int] = None,
        spatial_stat: Optional[str] = None,
        temporal_stat: Optional[str] = None,
        temporal_step: Optional[str] = None,
        col_name: Optional[str] = None,
        **kwargs) -> None:
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
        self.kwargs = kwargs
        if self.year is None and (self.start_year is None or self.end_year is None):
            raise(ValueError("Start and End Years or Year expected."))
    
    def set_image_coll(self, dataset: Optional[str] = None) -> ee.ImageCollection:
        """Set the Image Collection to be used based on the dataset argument

        Args:
            dataset (Optional[str], optional): dataset to use. Defaults to None.

        Returns:
            ee.ImageCollection: Image Collection related to the dataset
        """
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
        """Get the Date Range ee object for the input range. extend arg can be
        used to extend the day by 1 (DateRange in filtering the last day is 
        exclusive).

        Args:
            year (int): year or start year
            end_year (Optional[int], optional): end year if different. Defaults to None.
            start_month (int, optional): start month. Defaults to 6.
            end_month (int, optional): end month. Defaults to 6.
            start_date (int, optional): Start day. Defaults to 1.
            end_date (int, optional): end day. Defaults to 1.
            extend (bool, optional): extend by one day if True. Defaults to False.

        Returns:
            ee.DateRange: DateRange ee Object
        """
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
        """generate the projection and scale arguments for the Image collection

        Args:
            iColl (Optional[ee.ImageCollection], optional): Image Collection. Defaults to None.
            band_id (int, optional): id for band of image. Defaults to 0.
            epsg_value (Optional[int], optional): EPSG value for projection. Defaults to None.
            scale (Optional[int], optional): scale value. Defaults to None.
        """
        if iColl is None:
            iColl = self.iColl
        sample_image = iColl.first().select(band_id)
        if epsg_value:
            self.proj = ee.Projection(f'EPSG:{epsg_value}')
        else:
            self.proj = sample_image.projection()
        self.scale = scale if scale else self.proj.nominalScale()
    
    def filter_image_coll(
        self,
        iColl: Optional[ee.ImageCollection] = None,
        date_range: Optional[ee.DateRange] = None,
        start_ee_date: Optional[ee.Date] = None,
        end_ee_date: Optional[ee.Date] = None) -> ee.ImageCollection:
        """filter image collection based on date range or start and end dates.

        Args:
            iColl (Optional[ee.ImageCollection], optional): Image Collection. Defaults to None.
            date_range (Optional[ee.DateRange], optional): Date range ee object. Defaults to None.
            start_ee_date (Optional[ee.Date], optional): start date ee object. Defaults to None.
            end_ee_date (Optional[ee.Date], optional): end date ee object. Defaults to None.

        Returns:
            ee.ImageCollection: Filtered Image Collection
        """
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
    
    def spatial_reduce_setup(self, spatial_stat: Optional[str] = None, boundary: Optional[ee.FeatureCollection] = None) -> Callable:
        """setup to spatially Reduce image based on the spatial stat reducer
        for the boundary to get a statistical output

        Args:
            spatial_stat (Optional[str], optional): spatial reducer. Defaults to None.
            boundary (Optional[ee.FeatureCollection], optional): boundary. Defaults to None.

        Returns:
            Callable: function to spatial reduce images
        """
        if boundary is None:
            boundary = self.featureCol
        if spatial_stat is None:
            spatial_stat = self.spatial_stat
        def spatial_reduce(image: ee.Image) -> ee.FeatureCollection:
            """spatially reduce the input images

            Args:
                image (ee.Image): image to reduce

            Returns:
                ee.FeatureCollection: Reduced result as feature collection
            """
            return ee.Image(image).reduceRegions(
                collection= boundary,
                reducer= stat_dict[spatial_stat],
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