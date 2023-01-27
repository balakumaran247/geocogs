from PyQt5.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
import os, inspect
from qgis.core import (QgsProcessing,
                        QgsProcessingAlgorithm,
                        QgsProcessingParameterFeatureSource,
                        QgsProcessingParameterFileDestination,
                        QgsProcessingParameterEnum,
                        QgsProcessingParameterNumber,
                        QgsProcessingParameterString,
                        QgsProcessingException)

class LulcStatsAlgorithm(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    YEAR = 'YEAR'
    SPAN = 'SPAN'
    COLNAME = 'COLNAME'
    SPANOPTIONS = ['calendar year','hydrological year']

    def initAlgorithm(self, config=None):
        # input of Polygon Layer
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input layer'),
                [QgsProcessing.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.YEAR,
                self.tr('Year'),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=2020,
                optional=False,
                minValue=1994)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.SPAN,
                self.tr('Year Span'),
                options=[self.tr(item) for item in self.SPANOPTIONS],
                defaultValue=0,
                optional=False
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.COLNAME,
                self.tr('Unique Field'),
                optional = False
            )
        )
        # file output of type CSV.
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                self.tr('Output File'),
                'CSV files (*.csv)',
            )
        )

    def set_feedback(self, feedback, perc):
        if feedback.isCanceled():
            raise QgsProcessingException('Processing Canceled.')
        feedback.setProgress(int(perc))


    def processAlgorithm(self, parameters, context, feedback):
        source_lyr = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        year = self.parameterAsInt(parameters, self.YEAR, context)
        yr_span = self.parameterAsInt(parameters,self.SPAN,context)
        col_name = self.parameterAsString(parameters, self.COLNAME, context)
        out_csv = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        yr_span = self.SPANOPTIONS[yr_span]

        if col_name not in [field.name() for field in source_lyr.fields()]:
            raise QgsProcessingException('Unique Field Heading not available.')
        
        from .dwlulcstatisticscore import DWStats
        from ..utils import get_feature_collection

        self.set_feedback(feedback,5)
        f_col = get_feature_collection(source_lyr)
        self.set_feedback(feedback,15)
        lulc = DWStats(year, yr_span, f_col, col_name)
        self.set_feedback(feedback,20)
        dwMode = lulc.filter_col()
        self.set_feedback(feedback,25)
        area_stat = lulc.get_area_stat((feedback, self.set_feedback,25,60))
        self.set_feedback(feedback,85)
        df_dict = lulc.get_df((feedback, self.set_feedback,85,10))
        self.set_feedback(feedback,95)
        lulc.export_csv(out_csv)
        self.set_feedback(feedback,100)
        return {self.OUTPUT: out_csv}
    
    def name(self):
        return 'lulc_stats'

    def displayName(self):
        return self.tr('LULC Statistics')

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return ''

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def icon(self):
        cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]
        return QIcon(os.path.join(os.path.join(os.path.dirname(cmd_folder), 'icon.png')))

    def createInstance(self):
        return LulcStatsAlgorithm()