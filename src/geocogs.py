import inspect
import os

import processing
from PyQt5.QtWidgets import QAction
from qgis.core import QgsApplication
from qgis.PyQt.QtGui import QIcon

from .about.about import AboutPlugin
from .processingtoolprovider import ToolProvider


class GeoCogsPlugin:
    def __init__(self, iface):
        self.cmd_folder = os.path.split(
            inspect.getfile(inspect.currentframe()))[0]
        self.icon = os.path.join(os.path.join(self.cmd_folder, 'icon.png'))
        self.provider = None
        self.iface = iface

    def processing_provider_init(self):
        self.provider = ToolProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def processing_provider_unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)

    def about_init(self):
        self.about_action = QAction(
            QIcon(self.icon), 'About', self.iface.mainWindow())
        self.about_obj = AboutPlugin()
        self.about_action.triggered.connect(self.about_obj.show)
        self.iface.addPluginToMenu('&GeoCogs', self.about_action)

    def about_unload(self):
        self.iface.removePluginMenu('&GeoCogs', self.about_action)
        del self.about_obj
        del self.about_action

    def boundarystats_init(self):
        self.boundarystats_action = QAction(
            QIcon(self.icon), "Boundary Statistics", self.iface.mainWindow())
        self.boundarystats_action.triggered.connect(self.boundarystats_run)
        self.iface.addPluginToMenu(u"&GeoCogs", self.boundarystats_action)

    def boundarystats_unload(self):
        self.iface.removePluginMenu("&GeoCogs", self.boundarystats_action)

    def boundarystats_run(self):
        processing.execAlgorithmDialog("geocogs:boundary_stats")

    def lulcstats_init(self):
        self.lulcstats_action = QAction(
            QIcon(self.icon), "LULC Statistics", self.iface.mainWindow())
        self.lulcstats_action.triggered.connect(self.lulcstats_run)
        self.iface.addPluginToMenu(u"&GeoCogs", self.lulcstats_action)

    def lulcstats_unload(self):
        self.iface.removePluginMenu("&GeoCogs", self.lulcstats_action)

    def lulcstats_run(self):
        processing.execAlgorithmDialog("geocogs:lulc_stats")

    def initGui(self):
        self.processing_provider_init()
        self.about_init()
        self.boundarystats_init()
        self.lulcstats_init()

    def unload(self):
        self.processing_provider_unload()
        self.about_unload()
        self.boundarystats_unload()
        self.lulcstats_unload()
