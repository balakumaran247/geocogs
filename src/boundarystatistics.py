import inspect
import os
from datetime import datetime

from processing.gui.wrappers import WidgetWrapper
from PyQt5.QtCore import QCoreApplication
from qgis.core import (QgsMapLayerProxyModel, QgsProcessing,
                       QgsProcessingAlgorithm, QgsProcessingException,
                       QgsProcessingOutputFile, QgsProcessingParameterEnum,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterMatrix,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterString,
                       QgsProcessingParameterVectorLayer)
from qgis.gui import (QgsExternalStorageFileWidget, QgsFieldComboBox,
                      QgsMapLayerComboBox)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (QAction, QButtonGroup, QCheckBox, QComboBox,
                                 QFileDialog, QGridLayout, QLabel, QLineEdit,
                                 QListWidget, QListWidgetItem, QMenu,
                                 QPushButton, QRadioButton, QSpinBox, QWidget)

import ee
from ..core.gee import ImageCollections, Reducers
from ..core.helper import Assistant
from ..core.process import GeoCogs
# https://gis.stackexchange.com/questions/465952/how-to-chose-a-vector-layer-chose-a-field-then-chose-values-using-parameterase


class BoundaryStatsAlgorithm(QgsProcessingAlgorithm, ImageCollections, Reducers, GeoCogs):
    INPUT_PARAMS = 'INPUT_PARAMS'

    def initAlgorithm(self, config=None):
        param = QgsProcessingParameterMatrix(
            self.INPUT_PARAMS, 'Boundary Statistics')
        param.setMetadata({'widget_wrapper': {'class': BoundaryStatsWidget}})
        self.addParameter(param)

    def processAlgorithm(self, parameters, context, feedback):
        user_options = self.parameterAsMatrix(
            parameters, self.INPUT_PARAMS, context)
        keys = ('INPUT_LAYER', 'SELECTED_FEATURES', 'INPUT_FIELD', 'PARAMETER', 'SPAN',
                'TEMPORALSTEP', 'START_YEAR', 'END_YEAR', 'SPATIALSTAT', 'TEMPORALSTAT',
                'SCALE', 'TILESCALE', 'EXPORT_TO', 'EXPORT_PATH')
        kwargs = dict(zip(keys, user_options))

        ee.Initialize()
        
        self.set_parameter(kwargs['PARAMETER'])
        params = {
            'select_band': self.band,
            'temp_reducer': self.ee_reducer(kwargs['TEMPORALSTAT']),
            'spat_reducer': self.ee_reducer(kwargs['SPATIALSTAT']),
            'scale': kwargs['SCALE'],
            'tileScale': kwargs['TILESCALE'],
            'crs': None,
            'bands': None,
            'bandsRename': None,
            'imgProps': None,
            'imgPropsRename': None,
            'datetimeName': 'date',
            'datetimeFormat': 'YYYY-MM'
        }

        self.update_metadata(f'{datetime.now():%Y-%m-%d}', feedback)

        self.set_params(params)
        self.layer2ee(kwargs['INPUT_LAYER'], kwargs['SELECTED_FEATURES'], feedback)
        ic_reduced = self.reduce2imagecollection(self.ee_imagecollection, self.ee_featurecollection, kwargs['START_YEAR'], kwargs['END_YEAR'], kwargs['SPAN'], kwargs['TEMPORALSTEP'])
        get_stats = self.zonal_stats(ic_reduced, self.ee_featurecollection)
        if kwargs['EXPORT_TO'] == 'local':
            stats = get_stats.getInfo()
            Assistant.export2csv(stats, kwargs['EXPORT_PATH'], kwargs['SPATIALSTAT'], kwargs['INPUT_FIELD'], params['datetimeName'])
            summary = {'Output': kwargs['EXPORT_PATH']}
        return summary


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
        source_layer = self.custom_widget.lyr_cb.currentLayer()  # get_layer()
        selected_features = self.custom_widget.onlyselected_cb.isChecked()
        source_field = self.custom_widget.fld_cb.currentField()  # get_field()
        parameter = self.custom_widget.parm_cb.currentText()
        span = self.custom_widget.span_cb.currentText()
        step = self.custom_widget.step_cb.currentText()
        start_year = self.custom_widget.start_year_int.value()
        end_year = self.custom_widget.end_year_int.value()
        spatial_reducer = self.custom_widget.spatial_cb.currentText()
        temporal_reducer = self.custom_widget.temporal_cb.currentText()
        scale = self.custom_widget.scale_int.value()
        tilescale = int(self.custom_widget.tilescale_cb.currentText())
        export_to = self.custom_widget.export_option
        export_path = self.custom_widget.export_ln.text()
        return [
            source_layer, selected_features, source_field, parameter, span, step,
            start_year, end_year, spatial_reducer, temporal_reducer, scale,
            tilescale, export_to, export_path
        ]


class customParametersWidget(QWidget):
    PARAMETERS = [
        'IMD Rainfall',
        'IMD Max Temperature',
        'IMD Min Temperature',
        'ETa SSEBop'
    ]
    SPANOPTIONS = ['Calendar Year', 'Hydrological Year']
    STEPOPTIONS = ['Monthly', 'Yearly']
    REDUCERS = ['Mean', 'Median', 'Max', 'Min', 'Mode', 'Sum']
    TILESCALE = ["1", "2", "4"]

    def __init__(self):
        super(customParametersWidget, self).__init__()

        self.lyr_lbl = QLabel('Input Vector Layer:')
        self.lyr_cb = QgsMapLayerComboBox(self)
        self.lyr_cb.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.lyr_cb.layerChanged.connect(self.layer_changed)

        self.onlyselected_cb = QCheckBox('Only Selected Features', self)

        self.parm_lbl = QLabel('Select Parameter:')
        self.parm_cb = QComboBox(self)
        self.parm_cb.addItems(self.PARAMETERS)

        self.span_lb1 = QLabel('Select Span:')
        self.span_cb = QComboBox(self)
        self.span_cb.addItems(self.SPANOPTIONS)

        self.step_lb1 = QLabel('Select Step:')
        self.step_cb = QComboBox(self)
        self.step_cb.addItems(self.STEPOPTIONS)

        self.fld_lbl = QLabel('Select Unique Field:')
        self.fld_cb = QgsFieldComboBox(self)
        self.fld_cb.setLayer(self.lyr_cb.currentLayer())

        self.start_year_lb1 = QLabel('Start Year:')
        self.start_year_int = QSpinBox(self)
        self.start_year_int.setMinimum(1994)
        self.start_year_int.setMaximum(2021)
        self.start_year_int.setValue(2020)
        self.start_year_int.setSingleStep(1)
        self.start_year_int.setWrapping(True)

        self.end_year_lb1 = QLabel('End Year:')
        self.end_year_int = QSpinBox(self)
        self.end_year_int.setMinimum(1994)
        self.end_year_int.setMaximum(2021)
        self.end_year_int.setValue(2020)
        self.end_year_int.setSingleStep(1)
        self.end_year_int.setWrapping(True)

        self.spatial_lb1 = QLabel('Spatial Reducer:')
        self.spatial_cb = QComboBox(self)
        self.spatial_cb.addItems(self.REDUCERS)

        self.temporal_lb1 = QLabel('Temporal Reducer:')
        self.temporal_cb = QComboBox(self)
        self.temporal_cb.addItems(self.REDUCERS)

        self.scale_lb1 = QLabel('Scale (optional):')
        self.scale_int = QSpinBox(self)
        self.scale_int.setMinimum(10)
        self.scale_int.setMaximum(1000)
        self.scale_int.setValue(100)
        self.scale_int.setSingleStep(10)
        self.scale_int.setWrapping(True)

        self.tilescale_lb1 = QLabel('tileScale (optional):')
        self.tilescale_cb = QComboBox(self)
        self.tilescale_cb.addItems(self.TILESCALE)

        self.export_lb1 = QLabel('Export to:')
        self.rbgroup = QButtonGroup()
        self.export_rb1 = QRadioButton("Local (Light Computation)")
        self.export_rb2 = QRadioButton("Google Drive (Heavy Computation)")
        self.export_rb1.setChecked(True)
        self.export_rb1.toggled.connect(self.export_type)
        self.export_option = 'local'

        self.export_btn = QPushButton('Browse')
        self.export_btn.clicked.connect(self.browse)
        self.export_ln = QLineEdit(os.path.join(os.path.expanduser("~"), 'Desktop', 'GeoCogs_Output.csv'), self)

        self.layout = QGridLayout()
        self.layout.addWidget(self.lyr_lbl, 0, 0, 1, 1)
        self.layout.addWidget(self.lyr_cb, 0, 1, 1, 2)
        self.layout.addWidget(self.onlyselected_cb, 0, 3, 1, 1)
        self.layout.addWidget(self.fld_lbl, 1, 0, 1, 1)
        self.layout.addWidget(self.fld_cb, 1, 1, 1, 1)
        self.layout.addWidget(self.parm_lbl, 1, 2, 1, 1)
        self.layout.addWidget(self.parm_cb, 1, 3, 1, 1)
        self.layout.addWidget(self.span_lb1, 2, 0, 1, 1)
        self.layout.addWidget(self.span_cb, 2, 1, 1, 1)
        self.layout.addWidget(self.step_lb1, 2, 2, 1, 1)
        self.layout.addWidget(self.step_cb, 2, 3, 1, 1)
        self.layout.addWidget(self.start_year_lb1, 3, 0, 1, 1)
        self.layout.addWidget(self.start_year_int, 3, 1, 1, 1)
        self.layout.addWidget(self.end_year_lb1, 3, 2, 1, 1)
        self.layout.addWidget(self.end_year_int, 3, 3, 1, 1)
        self.layout.addWidget(self.spatial_lb1, 4, 0, 1, 1)
        self.layout.addWidget(self.spatial_cb, 4, 1, 1, 1)
        self.layout.addWidget(self.temporal_lb1, 4, 2, 1, 1)
        self.layout.addWidget(self.temporal_cb, 4, 3, 1, 1)
        self.layout.addWidget(self.scale_lb1, 5, 0, 1, 1)
        self.layout.addWidget(self.scale_int, 5, 1, 1, 1)
        self.layout.addWidget(self.tilescale_lb1, 5, 2, 1, 1)
        self.layout.addWidget(self.tilescale_cb, 5, 3, 1, 1)
        self.layout.addWidget(self.export_lb1, 6, 0, 1, 1)
        self.layout.addWidget(self.export_rb1, 6, 1, 1, 1)
        self.layout.addWidget(self.export_rb2, 6, 2, 1, 1)
        self.layout.addWidget(self.export_ln, 7, 0, 1, 3)
        self.layout.addWidget(self.export_btn, 7, 3, 1, 1)

        self.setLayout(self.layout)

    def export_type(self):
        if self.export_rb1.isChecked():
            self._export_type_behaviour('local', True)
        else:
            self._export_type_behaviour('drive', False)

    def _export_type_behaviour(self, arg0, arg1):
        self.export_option = arg0
        self.export_ln.setVisible(arg1)
        self.export_btn.setVisible(arg1)

    def browse(self):
        self.export_path = QFileDialog.getSaveFileName(
            None, self.tr("Save As"), None, self.tr("CSV files (*.csv)"))
        self.export_ln.setText(self.export_path[0])

    def layer_changed(self, lyr):
        self.fld_cb.setLayer(lyr)
