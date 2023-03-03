from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QApplication, QPushButton
from PyQt5 import QtCore
from PyQt5.QtGui import QFont
import sys, os
import pandas as pd
import webbrowser


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
        update_label = QLabel()
        update_label.setText(f'{self.check_update()}')
        update_label.setAlignment(QtCore.Qt.AlignCenter)
        update_label.setFont(QFont('Times', 14))
        github_btn = QPushButton('GitHub', self)
        github_btn.setToolTip("GeoCogs' GitHub Page")
        github_btn.clicked.connect(lambda: webbrowser.open('https://github.com/balakumaran247/geocogs'))
        self.layout().addWidget(tool_name)
        self.layout().addWidget(version_label)
        self.layout().addWidget(update_label)
        self.layout().addWidget(github_btn)
    
    def get_version(self):
        path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        df = pd.read_csv(os.path.join(path, 'version.csv'))
        return df['version'][0]
    
    def check_update(self):
        df = pd.read_csv(r'https://raw.githubusercontent.com/balakumaran247/geocogs/main/version.csv')
        uversion = float(df['version'][0])
        cversion = float(self.get_version())
        if uversion > cversion:
            return "new version available"
        elif cversion > uversion:
            return "dev version in use"
        else:
            return "version upto date"


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AboutPlugin()
    window.show()
    sys.exit(app.exec_())
