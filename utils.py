from qgis.core import QgsJsonExporter
import json
import ee
ee.Initialize()
from .geeassets import feature_col

def get_feature_collection(active_lyr):
    """convert the input layer to ee.Feature Collection

    Args:
        active_lyr (vector_layer): active layer from the iface

    Returns:
        ee.FeatureCollection: Earth Engine Feature Collection object of the layer
    """
    lyr = QgsJsonExporter(active_lyr)
    gs = lyr.exportFeatures(active_lyr.getFeatures())
    gj = json.loads(gs)
    for feature in gj['features']:
        feature['id'] = f'{feature["id"]:04d}'
    return ee.FeatureCollection(gj)

def get_admin_info(feature):
    # KA_command = feature_col['hydrosheds']
    # wshed = KA_command.filter(ee.Filter.eq('Shape_Area',0.0145969763252)).filter(
        # ee.Filter.eq('Shape_Leng',0.54712339639)).first().geometry()
    geom = ee.Feature(feature)
    geometry_centroid = geom.centroid()
    ###################
    dist_boundary = feature_col['dist2011']
    filtered = dist_boundary.filterBounds(geom.geometry())
    def calc_dist(poly):
        dist = geometry_centroid.distance(poly.centroid())
        return poly.set('mindist',dist)
    dist_fc = filtered.map(calc_dist)
    min_dist = dist_fc.sort('mindist', True).first().getInfo()
    return (min_dist['properties']['ST_NM'], min_dist['properties']['DISTRICT'])

dw_class_ordered = ('water',
    'trees',
    'grass',
    'flooded_vegetation',
    'crops',
    'shrub_and_scrub',
    'built',
    'bare',
    'snow_and_ice')