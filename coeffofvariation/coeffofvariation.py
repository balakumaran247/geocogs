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

class CoeffVariationAlgorithm(QgsProcessingAlgorithm):
    OUTPUT = 'OUTPUT'
    INPUT = 'INPUT'
    START_YEAR = 'START YEAR'
    END_YEAR = 'END YEAR'
    START_MONTH = 'START MONTH'
    END_MONTH = 'END MONTH'
    PARAMETER = 'PARAMETER'
    COLNAME = 'COLNAME'
    DATASETS = ['Precipitation']

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input layer'),
                [QgsProcessing.TypeVectorPolygon, QgsProcessing.TypeVectorPoint]
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.START_YEAR,
                self.tr('Start Year'),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=2020,
                optional=False,
                minValue=1994)
        )
        
        self.addParameter(
            QgsProcessingParameterNumber(
                self.END_YEAR,
                self.tr('End Year'),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=2020,
                optional=False,
                minValue=1994)
        )
        
        self.addParameter(
            QgsProcessingParameterNumber(
                self.START_MONTH,
                self.tr('Start Month'),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=6,
                optional=False,
                minValue=1,
                maxValue=12)
        )
        
        self.addParameter(
            QgsProcessingParameterNumber(
                self.END_MONTH,
                self.tr('End Month'),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=9,
                optional=False,
                minValue=1,
                maxValue=12)
        )
        
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PARAMETER,
                self.tr('Parameter'),
                options=[self.tr(item) for item in self.DATASETS],
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
        
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                self.tr('Output File'),
                'CSV files (*.csv)',
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source_lyr = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        start_year = self.parameterAsInt(parameters, self.START_YEAR, context)
        end_year = self.parameterAsInt(parameters, self.END_YEAR, context)
        start_month = self.parameterAsInt(parameters, self.START_MONTH, context)
        end_month = self.parameterAsInt(parameters, self.END_MONTH, context)
        param = self.parameterAsInt(parameters, self.PARAMETER, context)
        col_name = self.parameterAsString(parameters, self.COLNAME, context)
        out_csv = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        param = self.DATASETS[param]

        if col_name not in [field.name() for field in source_lyr.fields()]:
            raise QgsProcessingException('Unique Field Heading not available.')
        
        from .coeffofvariationcore import CoeffVariation
        from ..utils import get_feature_collection, set_progressbar_perc, month_days, logger

        set_progressbar_perc(feedback,1,'Converting Layer to ee.FeatureCollection')
        f_col = get_feature_collection(source_lyr)
        set_progressbar_perc(feedback,10,'Fetch ee.ImageCollection')
        cv = CoeffVariation(
            featureCol = f_col,
            dataset = param,
            start_year = start_year,
            end_year = end_year,
            start_month = start_month,
            end_month = end_month,
            col_name = col_name,
            feedback = feedback
        )
        cv.set_image_coll()
        set_progressbar_perc(feedback,12,'Fetch ee.DateRange')
        date_range = cv.get_date_range(
            year = start_year,
            end_year = end_year,
            start_month = start_month,
            end_month = end_month,
            start_date = 1,
            end_date = month_days(end_year, end_month),
            extend = True
        )
        set_progressbar_perc(feedback,14,'Set projection and scale')
        cv.generate_proj_scale()
        set_progressbar_perc(feedback,15,'Filter ee.ImageCollection')
        iColl_filtered = cv.filter_image_coll(date_range=date_range)
        set_progressbar_perc(feedback,20,'Calculate Area Weighted Average')
        awa_dict = cv.get_area_weighted_average(iColl_filtered, 20, 60)
        set_progressbar_perc(feedback,80,'Save Area Weighted Average as CSV')
        awa_df = cv.get_awa_df(awa_dict)
        awa_csv_path = out_csv.replace('.csv','_awa.csv')
        out_log = {'AWA CSV': awa_csv_path}
        cv.save_awa_df(awa_df, awa_csv_path)
        set_progressbar_perc(feedback,85,'Calculate Std.Dev, Mean and CV')
        std_df = cv.calc_std_dev(awa_df)
        mean_df = cv.calc_mean(awa_df)
        joined_df = cv.join_dfs(std_df, mean_df)
        set_progressbar_perc(feedback, 95,'Save CV as CSV')
        cv_df = cv.calc_cv(joined_df)
        cv.save_cv_df(cv_df, out_csv)
        set_progressbar_perc(feedback,100,'Completed!')
        out_log[self.OUTPUT] = out_csv
        return out_log

    def name(self):
        return 'coeff_var'

    def displayName(self):
        return self.tr('Coeff of Variation')

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
        return CoeffVariationAlgorithm()