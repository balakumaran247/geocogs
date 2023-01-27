import ee
ee.Initialize()

image_col = {
    'Precipitation' : ee.ImageCollection("users/jaltol/IMD/rain"),
    'Min Temp' : ee.ImageCollection("users/jaltol/IMD/minTemp"),
    'Max Temp' : ee.ImageCollection("users/jaltol/IMD/maxTemp"),
    'ETa(SSEBop)' : ee.ImageCollection("users/jaltol/ET_new/etSSEBop"),
    'soil moisture' : ee.ImageCollection("NASA_USDA/HSL/SMAP10KM_soil_moisture"),
    'groundwater' : ee.ImageCollection("users/jaltol/GW/IndiaWRIS"),
    'dynamicworld': ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1"),
    'co-efficient of variation(rain)': ee.ImageCollection("users/jaltol/realwater/cvRainfall"),
    'S2': ee.ImageCollection("COPERNICUS/S2"),
}

feature_col = {
    'dist2011' : ee.FeatureCollection('users/jaltol/FeatureCol/District_Map_2011'),
    'hydrosheds': ee.FeatureCollection('users/jaltol/FeatureCol/Hydroshds_Jaltol'),
}

stat_dict = {
    'total':ee.Reducer.sum(),
    'mean':ee.Reducer.mean(),
    'median':ee.Reducer.median(),
    'max':ee.Reducer.max(),
    'min':ee.Reducer.min(),
    'mode':ee.Reducer.mode()
}

expression_dict = {
    'NDVI': lambda x: x.normalizedDifference(['B8', 'B4']).rename('NDVI').copyProperties(x, ['system:time_start', 'system:time_end']),
}

def mask_s2_clouds(image):
    qa = image.select('QA60')
    cloudBitMask = 1 << 10
    cirrusBitMask = 1 << 11
    mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))
    return image.updateMask(mask)
