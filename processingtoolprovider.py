from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
import os, inspect
from .boundarystatistics.boundarystatistics import BoundaryStatsAlgorithm
from .dwlulcstatistics.dwlulcstatistics import LulcStatsAlgorithm
from .coeffofvariation.coeffofvariation import CoeffVariationAlgorithm


class ToolProvider(QgsProcessingProvider):

    def __init__(self):
        QgsProcessingProvider.__init__(self)

    def unload(self):
        pass

    def loadAlgorithms(self):
        self.addAlgorithm(BoundaryStatsAlgorithm())
        self.addAlgorithm(LulcStatsAlgorithm())
        self.addAlgorithm(CoeffVariationAlgorithm())
        # add additional algorithms here
        # self.addAlgorithm(MyOtherAlgorithm())

    def id(self):
        return 'geocogs'

    def name(self):
        return self.tr('GeoCogs')

    def icon(self):
        cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]
        return QIcon(os.path.join(os.path.join(cmd_folder, 'icon.png')))

    def longName(self):
        return self.name()