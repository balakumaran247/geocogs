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

class BoundaryStatsAlgorithm(QgsProcessingAlgorithm):
    OUTPUT = 'OUTPUT'
    INPUT = 'INPUT'
    YEAR = 'YEAR'
    SPAN = 'SPAN'
    PARAMETER = 'PARAMETER'
    SPATIALSTAT = 'SPATIALSTAT'
    TEMPORALSTAT = 'TEMPORALSTAT'
    TEMPORALSTEP = 'TEMPORALSTEP'
    COLNAME = 'COLNAME'
    STEPOPTIONS = ['Monthly','Yearly']
    SPANOPTIONS = ['calendar year','hydrological year']
    REDUCERS = ['mean','median','total','min','max']
    DATASETS = ['Precipitation',
                'Min Temp',
                'Max Temp',
                'ETa(SSEBop)',
                'soil moisture',
                'groundwater',
                'co-efficient of variation(rain)',
                'NDVI',
                'ET(IITB)']
    
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
            QgsProcessingParameterEnum(
                self.PARAMETER,
                self.tr('Parameter'),
                options=[self.tr(item) for item in self.DATASETS],
                defaultValue=0,
                optional=False
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.TEMPORALSTEP,
                self.tr('Temporal Step'),
                options = [self.tr(item) for item in self.STEPOPTIONS],
                defaultValue = 0,
                optional = False
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.TEMPORALSTAT,
                self.tr('Temporal Reducer'),
                options = [self.tr(item) for item in self.REDUCERS],
                defaultValue = 0,
                optional = False
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.SPATIALSTAT,
                self.tr('Spatial Reducer'),
                options=[self.tr(item) for item in self.REDUCERS],
                defaultValue = 0,
                optional = False
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
        param = self.parameterAsInt(parameters, self.PARAMETER, context)
        step = self.parameterAsInt(parameters, self.TEMPORALSTEP, context)
        temp_reducer = self.parameterAsInt(parameters, self.TEMPORALSTAT, context)
        spat_reducer = self.parameterAsInt(parameters, self.SPATIALSTAT, context)
        col_name = self.parameterAsString(parameters, self.COLNAME, context)
        out_csv = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        step = self.STEPOPTIONS[step]
        yr_span = self.SPANOPTIONS[yr_span]
        temp_reducer = self.REDUCERS[temp_reducer]
        spat_reducer = self.REDUCERS[spat_reducer]
        param = self.DATASETS[param]
        
        if col_name not in [field.name() for field in source_lyr.fields()]:
            raise QgsProcessingException('Unique Field Heading not available.')
        
        from .boundarystatisticscore import BoundaryWiseStats
        from ..utils import get_feature_collection
        
        self.set_feedback(feedback,1)
        f_col = get_feature_collection(source_lyr)
        self.set_feedback(feedback,15)
        bws = BoundaryWiseStats(f_col,param,year,spat_reducer,temp_reducer,step)
        bws.set_image_coll()
        self.set_feedback(feedback,20)
        bws.make_date_range_list(yr_span)
        self.set_feedback(feedback,25)
        bws.filter_image_coll()
        self.set_feedback(feedback,30)
        bws.set_temporal_reducer()
        bws.set_spatial_reducer()
        self.set_feedback(feedback,35)
        bws.temp_reduce_image_coll()
        self.set_feedback(feedback,45)
        bws.get_boundarywisestats()
        self.set_feedback(feedback,60)
        bws.get_out_dict(col_name,(feedback,self.set_feedback,60,38))
        self.set_feedback(feedback,98)
        bws.export_csv(out_csv)
        self.set_feedback(feedback,100)
        return {self.OUTPUT: out_csv}

    def name(self):
        return 'boundary_stats'

    def displayName(self):
        return self.tr('Boundary Statistics')

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
        return BoundaryStatsAlgorithm()