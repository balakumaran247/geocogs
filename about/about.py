from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QApplication
from PyQt5 import QtCore
from PyQt5.QtGui import QFont
import sys, os
import pandas as pd


class AboutPlugin(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setLayout(QVBoxLayout())
        self.setFixedSize(640, 480)
        tool_name = QLabel()
        tool_name.setText('GeoCogs')
        tool_name.setAlignment(QtCore.Qt.AlignCenter)
        tool_name.setFont(QFont('Times', 24))
        version_label = QLabel()
        version_label.setText(f'Current Version: {self.get_version()}')
        version_label.setAlignment(QtCore.Qt.AlignCenter)
        version_label.setFont(QFont('Times', 16))
        self.layout().addWidget(tool_name)
        self.layout().addWidget(version_label)
    
    def get_version(self):
        path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        df = pd.read_csv(os.path.join(path, 'version.csv'))
        return df['version'][0]


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AboutPlugin()
    window.show()
    sys.exit(app.exec_())
