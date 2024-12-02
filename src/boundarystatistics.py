from PyQt5.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (QWidget, QListWidget, QListWidgetItem,
                                QLabel, QLineEdit, QGridLayout, QMenu,
                                QAction, QCheckBox)
import os, inspect
from processing.gui.wrappers import WidgetWrapper
from qgis.core import (QgsProcessing,
                        QgsProcessingAlgorithm,
                        QgsProcessingParameterFeatureSource,
                        QgsProcessingParameterFileDestination,
                        QgsProcessingParameterEnum,
                        QgsProcessingParameterNumber,
                        QgsProcessingParameterString,
                        QgsProcessingException,
                        QgsProcessingParameterVectorLayer,
                        QgsProcessingParameterMatrix,
                        QgsMapLayerProxyModel)
from qgis.gui import (QgsMapLayerComboBox, QgsFieldComboBox)

# https://gis.stackexchange.com/questions/465952/how-to-chose-a-vector-layer-chose-a-field-then-chose-values-using-parameterase


class BoundaryStatsAlgorithm(QgsProcessingAlgorithm):
    INPUT_PARAMS = 'INPUT_PARAMS'
    
    # OUTPUT = 'OUTPUT NAME'
    # INPUT = 'INPUT LAYER'
    # START_YEAR = 'STARTING YEAR'
    # END_YEAR = 'ENDING YEAR'
    # SPAN = 'SPAN'
    # PARAMETER = 'PARAMETER'
    # SPATIALSTAT = 'SPATIAL REDUCER'
    # TEMPORALSTAT = 'TEMPORAL REDUCER'
    # TEMPORALSTEP = 'TEMPORAL STEP'
    # COLNAME = 'UNIQUE FIELD'

    # STEPOPTIONS = ['Monthly','Yearly']
    # SPANOPTIONS = ['Calendar Year','Hydrological Year']
    # REDUCERS = ['Mean', 'Median', 'Max', 'Min', 'Mode', 'Total']
    # DATASETS = ['IMD Rainfall',
    #         'IMD Max Temperature',
    #         'IMD Min Temperature',
    #         'ETa SSEBop'
    #             ]
    
    def initAlgorithm(self, config=None):
        param = QgsProcessingParameterMatrix(self.INPUT_PARAMS, self.INPUT_PARAMS.title())
        param.setMetadata({'widget_wrapper': {'class': BoundaryStatsWidget}})
        self.addParameter(param)
        
    def processAlgorithm(self, parameters, context, feedback):
        user_options = self.parameterAsMatrix(parameters, self.INPUT_PARAMS, context)
        input_vector_layer, selected_features, unique_field = user_options
        
        return {'INPUT_LAYER': input_vector_layer,
                'SELECTED_FEATURES': selected_features,
                'INPUT_FIELD': unique_field}
    
    # def initAlgorithm(self, config=None):
    #     # input of Polygon Layer
    #     self.addParameter(
    #         QgsProcessingParameterFeatureSource(
    #             self.INPUT,
    #             self.tr(self.INPUT.title()),
    #             [QgsProcessing.TypeVectorPolygon, QgsProcessing.TypeVectorPoint]
    #         )
    #     )

    #     self.addParameter(
    #         QgsProcessingParameterNumber(
    #             self.START_YEAR,
    #             self.tr(self.START_YEAR.title()),
    #             type=QgsProcessingParameterNumber.Integer,
    #             defaultValue=2020,
    #             optional=False,
    #             minValue=1994)
    #     )

    #     self.addParameter(
    #         QgsProcessingParameterNumber(
    #             self.END_YEAR,
    #             self.tr(self.END_YEAR.title()),
    #             type=QgsProcessingParameterNumber.Integer,
    #             defaultValue=2020,
    #             optional=False,
    #             minValue=1994)
    #     )

    #     self.addParameter(
    #         QgsProcessingParameterEnum(
    #             self.SPAN,
    #             self.tr(self.SPAN.title()),
    #             options=[self.tr(item) for item in self.SPANOPTIONS],
    #             defaultValue=0,
    #             optional=False
    #         )
    #     )

    #     self.addParameter(
    #         QgsProcessingParameterEnum(
    #             self.PARAMETER,
    #             self.tr(self.PARAMETER.title()),
    #             options=[self.tr(item) for item in self.DATASETS],
    #             defaultValue=0,
    #             optional=False
    #         )
    #     )

    #     self.addParameter(
    #         QgsProcessingParameterEnum(
    #             self.TEMPORALSTEP,
    #             self.tr(self.TEMPORALSTEP.title()),
    #             options = [self.tr(item) for item in self.STEPOPTIONS],
    #             defaultValue = 0,
    #             optional = False
    #         )
    #     )

    #     self.addParameter(
    #         QgsProcessingParameterEnum(
    #             self.TEMPORALSTAT,
    #             self.tr(self.TEMPORALSTAT.title()),
    #             options = [self.tr(item) for item in self.REDUCERS],
    #             defaultValue = 0,
    #             optional = False
    #         )
    #     )

    #     self.addParameter(
    #         QgsProcessingParameterEnum(
    #             self.SPATIALSTAT,
    #             self.tr(self.SPATIALSTAT.title()),
    #             options=[self.tr(item) for item in self.REDUCERS],
    #             defaultValue = 0,
    #             optional = False
    #         )
    #     )

    #     self.addParameter(
    #         QgsProcessingParameterString(
    #             self.COLNAME,
    #             self.tr(self.COLNAME.title()),
    #             optional = False
    #         )
    #     )

    #     # file output of type CSV.
    #     self.addParameter(
    #         QgsProcessingParameterFileDestination(
    #             self.OUTPUT,
    #             self.tr(self.OUTPUT.title()),
    #             'CSV files (*.csv)',
    #         )
    #     )

    # def set_feedback(self, feedback, perc):
    #     if feedback.isCanceled():
    #         raise QgsProcessingException('Processing Canceled.')
    #     feedback.setProgress(int(perc))

    # def processAlgorithm(self, parameters, context, feedback):
    #     source_lyr = self.parameterAsVectorLayer(parameters, self.INPUT, context)
    #     print(source_lyr)
    #     year = self.parameterAsInt(parameters, self.YEAR, context)
    #     yr_span = self.parameterAsInt(parameters,self.SPAN,context)
    #     param = self.parameterAsInt(parameters, self.PARAMETER, context)
    #     step = self.parameterAsInt(parameters, self.TEMPORALSTEP, context)
    #     temp_reducer = self.parameterAsInt(parameters, self.TEMPORALSTAT, context)
    #     spat_reducer = self.parameterAsInt(parameters, self.SPATIALSTAT, context)
    #     col_name = self.parameterAsString(parameters, self.COLNAME, context)
    #     out_csv = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

    #     step = self.STEPOPTIONS[step]
    #     yr_span = self.SPANOPTIONS[yr_span]
    #     temp_reducer = self.REDUCERS[temp_reducer]
    #     spat_reducer = self.REDUCERS[spat_reducer]
    #     param = self.DATASETS[param]
        
    #     if col_name not in [field.name() for field in source_lyr.fields()]:
    #         raise QgsProcessingException('Unique Field Heading not available.')
        
    #     from .boundarystatisticscore import BoundaryWiseStats
    #     from ..utils import get_feature_collection
        
    #     self.set_feedback(feedback,1)
    #     f_col = get_feature_collection(source_lyr)
    #     self.set_feedback(feedback,15)
    #     bws = BoundaryWiseStats(f_col,param,year,spat_reducer,temp_reducer,step)
    #     bws.set_image_coll()
    #     self.set_feedback(feedback,20)
    #     bws.make_date_range_list(yr_span)
    #     self.set_feedback(feedback,25)
    #     bws.filter_image_coll()
    #     self.set_feedback(feedback,30)
    #     bws.set_temporal_reducer()
    #     bws.set_spatial_reducer()
    #     self.set_feedback(feedback,35)
    #     bws.temp_reduce_image_coll()
    #     self.set_feedback(feedback,45)
    #     bws.get_boundarywisestats()
    #     self.set_feedback(feedback,60)
    #     bws.get_out_dict(col_name,(feedback,self.set_feedback,60,38))
    #     self.set_feedback(feedback,98)
    #     bws.export_csv(out_csv)
    #     self.set_feedback(feedback,100)
    #     return {self.OUTPUT: out_csv}

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

class BoundaryStatsWidget(WidgetWrapper):

    def createWidget(self):
        self.custom_widget = customParametersWidget()
        return self.custom_widget

    def value(self):
        source_layer = self.custom_widget.get_layer()
        selected_features = self.custom_widget.onlyselected_cb.isChecked()
        source_field = self.custom_widget.get_field()
        params = [source_layer, selected_features, source_field]
        return params
    
class customParametersWidget(QWidget):
    def __init__(self):
        super(customParametersWidget, self).__init__()
        
        self.lyr_lbl = QLabel('Input Vector Layer:')
        self.lyr_cb = QgsMapLayerComboBox(self)
        self.lyr_cb.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.lyr_cb.layerChanged.connect(self.layer_changed)
        self.onlyselected_cb = QCheckBox('Only Selected Features', self)
        self.fld_lbl = QLabel('Select Unique Field:')
        self.fld_cb = QgsFieldComboBox(self)
        self.fld_cb.setLayer(self.lyr_cb.currentLayer())
        # self.fld_cb.fieldChanged.connect(self.populate_list_widget)
        
        self.layout = QGridLayout()
        self.layout.addWidget(self.lyr_lbl, 0, 0, 1, 1)
        self.layout.addWidget(self.lyr_cb, 0, 1, 1, 3)
        self.layout.addWidget(self.onlyselected_cb, 1, 1, 1, 3)
        self.layout.addWidget(self.fld_lbl, 2, 0, 1, 1)
        self.layout.addWidget(self.fld_cb, 2, 1, 1, 3)
        
        self.setLayout(self.layout)
    
    def layer_changed(self, lyr):
        self.fld_cb.setLayer(lyr)
    
    def get_layer(self):
        return self.lyr_cb.currentLayer()
        
    def get_field(self):
        return self.fld_cb.currentField()