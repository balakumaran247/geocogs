import inspect
import os
from datetime import datetime

import ee
from processing.gui.wrappers import WidgetWrapper
from PyQt5.QtCore import QCoreApplication
from qgis.core import (QgsMapLayerProxyModel, QgsProcessingAlgorithm,
                       QgsProcessingException, QgsProcessingParameterMatrix,
                       QgsVectorLayer)
from qgis.gui import QgsFieldComboBox, QgsMapLayerComboBox
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (QButtonGroup, QCheckBox, QComboBox,
                                 QFileDialog, QGridLayout, QLabel, QLineEdit,
                                 QPushButton, QRadioButton, QSpinBox, QWidget)

from ..core.gee import ImageCollections, Reducers
from ..core.helper import Assistant
from ..core.process import GeoCogs


class LulcStatsAlgorithm(QgsProcessingAlgorithm, ImageCollections, Reducers, GeoCogs):
    INPUT_PARAMS = 'INPUT_PARAMS'

    def initAlgorithm(self, config=None):
        param = QgsProcessingParameterMatrix(
            self.INPUT_PARAMS, 'LULC Statistics')
        param.setMetadata({'widget_wrapper': {'class': LulcStatsWidget}})
        self.addParameter(param)

    def processAlgorithm(self, parameters, context, feedback):
        user_options = self.parameterAsMatrix(
            parameters, self.INPUT_PARAMS, context)
        keys = ('INPUT_LAYER', 'SELECTED_FEATURES', 'INPUT_FIELD', 'PARAMETER', 'SPAN',
                'START_YEAR', 'SCALE', 'TILESCALE', 'EXPORT_TO', 'EXPORT_PATH')
        kwargs = dict(zip(keys, user_options))

        return kwargs

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


class LulcStatsWidget(WidgetWrapper):
    """
    A widget wrapper class for LULC statistics.
    Methods
    -------
    createWidget():
        Creates and returns a custom parameters widget.
    value():
        Retrieves and returns the current values from the custom widget.
    """

    def createWidget(self):
        self.custom_widget = customParametersWidget()
        return self.custom_widget

    def value(self):
        source_layer = self.custom_widget.lyr_cb.currentLayer()
        selected_features = self.custom_widget.onlyselected_cb.isChecked()
        source_field = self.custom_widget.fld_cb.currentField()
        parameter = self.custom_widget.parm_cb.currentText()
        span = self.custom_widget.span_cb.currentText()
        start_year = self.custom_widget.start_year_int.value()
        scale = self.custom_widget.scale_int.value()
        tilescale = int(self.custom_widget.tilescale_cb.currentText())
        export_to = self.custom_widget.export_option
        export_path = self.custom_widget.export_ln.text()
        return [
            source_layer, selected_features, source_field, parameter, span,
            start_year, scale, tilescale, export_to, export_path
        ]


class customParametersWidget(QWidget):
    """
    A custom widget for selecting parameters and options for LULC statistics in QGIS.
    Attributes:
        PARAMETERS (list): List of available parameters for selection.
        SPANOPTIONS (list): List of span options for selection.
        TILESCALE (list): List of tile scale options.
        DEFAULT_PATH (str): Default path for exporting data.
        IMAGECOLLECTION_JSON (dict): JSON data containing image collection information.
    Methods:
        __init__(): Initializes the customParametersWidget with various UI components.
        export_type(): Handles the export type selection and updates UI accordingly.
        _export_type_behaviour(arg0, arg1): Updates the export option and visibility of export path components.
        set_min_max_dates(): Sets the minimum and maximum dates based on the selected parameter and span.
        browse(): Opens a file dialog to select the export path.
        layer_changed(lyr): Updates the field combo box based on the selected layer.
    """
    PARAMETERS = [
        'Dynamic World V1'
    ]
    SPANOPTIONS = ['Calendar Year', 'Hydrological Year']
    TILESCALE = ["1", "2", "4"]
    DEFAULT_PATH = Assistant.default_path()
    IMAGECOLLECTION_JSON = Assistant.read_json()

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
        self.parm_cb.currentIndexChanged.connect(self.set_min_max_dates)

        self.span_lb1 = QLabel('Select Span:')
        self.span_cb = QComboBox(self)
        self.span_cb.addItems(self.SPANOPTIONS)
        self.span_cb.currentIndexChanged.connect(self.set_min_max_dates)

        self.fld_lbl = QLabel('Select Unique Field:')
        self.fld_cb = QgsFieldComboBox(self)
        self.fld_cb.setLayer(self.lyr_cb.currentLayer())

        self.start_year_lb1 = QLabel('Year:')
        self.start_year_int = QSpinBox(self)
        self.start_year_int.setSingleStep(1)
        self.start_year_int.setWrapping(True)
        self.start_year_int.valueChanged.connect(self.set_min_max_dates)

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
        self.export_ln = QLineEdit(self.DEFAULT_PATH, self)

        self.layout = QGridLayout()
        self.layout.addWidget(self.lyr_lbl, 0, 0, 1, 1)
        self.layout.addWidget(self.lyr_cb, 0, 1, 1, 2)
        self.layout.addWidget(self.onlyselected_cb, 0, 3, 1, 1)
        self.layout.addWidget(self.fld_lbl, 1, 0, 1, 1)
        self.layout.addWidget(self.fld_cb, 1, 1, 1, 2)
        self.layout.addWidget(self.parm_lbl, 2, 0, 1, 1)
        self.layout.addWidget(self.parm_cb, 2, 1, 1, 1)
        self.layout.addWidget(self.span_lb1, 3, 0, 1, 1)
        self.layout.addWidget(self.span_cb, 3, 1, 1, 1)
        self.layout.addWidget(self.start_year_lb1, 3, 2, 1, 1)
        self.layout.addWidget(self.start_year_int, 3, 3, 1, 1)
        self.layout.addWidget(self.scale_lb1, 4, 0, 1, 1)
        self.layout.addWidget(self.scale_int, 4, 1, 1, 1)
        self.layout.addWidget(self.tilescale_lb1, 4, 2, 1, 1)
        self.layout.addWidget(self.tilescale_cb, 4, 3, 1, 1)
        self.layout.addWidget(self.export_lb1, 5, 0, 1, 1)
        self.layout.addWidget(self.export_rb1, 5, 1, 1, 1)
        self.layout.addWidget(self.export_rb2, 5, 2, 1, 1)
        self.layout.addWidget(self.export_ln, 6, 0, 1, 3)
        self.layout.addWidget(self.export_btn, 6, 3, 1, 1)

        self.setLayout(self.layout)

    def export_type(self) -> None:
        """
        Determines the export type based on the state of the radio buttons and 
        calls the appropriate export type behavior.
        If the first radio button (export_rb1) is checked, it sets the export type 
        to 'local' and enables the corresponding behavior. Otherwise, it sets the 
        export type to 'drive' and disables the corresponding behavior.
        """
        if self.export_rb1.isChecked():
            self._export_type_behaviour('local', True)
        else:
            self._export_type_behaviour('drive', False)

    def _export_type_behaviour(self, arg0: str, arg1: bool) -> None:
        """
        Sets the export option and controls the visibility of export-related UI elements.
        Args:
            arg0 (str): The export option to be set.
            arg1 (bool): A flag indicating whether the export-related UI elements should be visible.
        """
        self.export_option = arg0
        self.export_ln.setVisible(arg1)
        self.export_btn.setVisible(arg1)

    def set_min_max_dates(self) -> None:
        """
        Sets the minimum and maximum dates for the start and end year input fields
        based on the selected parameter and span.
        The method retrieves the selected parameter from the parameter combo box
        and the selected span from the span combo box. Depending on whether the
        span is 'Calendar Year' or not, it fetches the corresponding start and end
        dates from the IMAGECOLLECTION_JSON dictionary. It then sets these dates
        as the minimum and maximum values for the start and end year input fields.
        """
        parameter = self.parm_cb.currentText()
        span = self.span_cb.currentText()
        if span == 'Calendar Year':
            start = self.IMAGECOLLECTION_JSON[parameter]['calendar_start']
            end = self.IMAGECOLLECTION_JSON[parameter]['calendar_end']
        else:
            start = self.IMAGECOLLECTION_JSON[parameter]['hydrological_start']
            end = self.IMAGECOLLECTION_JSON[parameter]['hydrological_end']
        self.start_year_int.setMinimum(start)
        self.start_year_int.setMaximum(end)

    def browse(self) -> None:
        """
        Opens a file dialog to select a location and name for saving a CSV file.
        This method uses QFileDialog to open a 'Save As' dialog, allowing the user to specify
        the path and filename for exporting a CSV file. The selected path is then set to the
        export_path attribute and displayed in the export_ln widget.
        Returns:
            None
        """
        self.export_path = QFileDialog.getSaveFileName(
            None, self.tr("Save As"), None, self.tr("CSV files (*.csv)"))
        self.export_ln.setText(self.export_path[0])

    def layer_changed(self, lyr: QgsVectorLayer) -> None:
        """
        Updates the field combo box with the given vector layer.
        This method is called when the layer is changed. It sets the new layer
        to the field combo box.
        Args:
            lyr (QgsVectorLayer): The new vector layer to be set.
        """
        self.fld_cb.setLayer(lyr)
