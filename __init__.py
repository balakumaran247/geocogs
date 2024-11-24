from .src.geocogs import GeoCogsPlugin

def classFactory(iface):
    return GeoCogsPlugin(iface)