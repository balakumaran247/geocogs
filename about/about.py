from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QApplication, QPushButton
from PyQt5 import QtCore
from PyQt5.QtGui import QFont, QPixmap
import sys
import os
import inspect
import pandas as pd
import webbrowser


class AboutPlugin(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setLayout(QVBoxLayout())
        self.setFixedSize(640, 480)

        logo_label = QLabel(self)
        cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]
        l_path = os.path.join(os.path.join(
            os.path.dirname(cmd_folder), 'icon.png'))
        pixmap = QPixmap(l_path)
        logo_label.setPixmap(pixmap)
        logo_label.resize(pixmap.width(), pixmap.height())
        logo_label.setAlignment(QtCore.Qt.AlignCenter)

        tool_name = QLabel()
        tool_name.setText('GeoCogs')
        tool_name.setAlignment(QtCore.Qt.AlignCenter)
        tool_name.setFont(QFont('Times', 24))

        self.cversion = float(self.get_version())
        version_label = QLabel()
        version_label.setText(f'Current Version: {self.cversion}')
        version_label.setAlignment(QtCore.Qt.AlignCenter)
        version_label.setFont(QFont('Times', 16))

        self.update_label = QLabel()
        self.update_label.setText('Check if update available')
        self.update_label.setAlignment(QtCore.Qt.AlignCenter)
        self.update_label.setFont(QFont('Times', 14))

        check_update_btn = QPushButton('Check for update', self)
        check_update_btn.clicked.connect(self.set_update_label)

        github_btn = QPushButton('GitHub', self)
        github_btn.setToolTip("GeoCogs' GitHub Page")
        github_btn.clicked.connect(lambda: webbrowser.open(
            'https://github.com/balakumaran247/geocogs'))

        self.layout().addWidget(logo_label)
        self.layout().addWidget(tool_name)
        self.layout().addWidget(version_label)
        self.layout().addWidget(self.update_label)
        self.layout().addWidget(check_update_btn)
        self.layout().addWidget(github_btn)

    def get_version(self):
        path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        df = pd.read_csv(os.path.join(path, 'version.csv'))
        return df['version'][0]

    def set_update_label(self):
        self.update_label.setText('Checking....')
        self.update_label.setText(f'{self.check_update()}')

    def check_update(self):
        try:
            df = pd.read_csv(
                r'https://raw.githubusercontent.com/balakumaran247/geocogs/main/version.csv')
            uversion = float(df['version'][0])
        except TimeoutError:
            return "Failed to Check"
        if uversion > self.cversion:
            return "new version available"
        elif self.cversion > uversion:
            return "dev version in use"
        else:
            return "version upto date"


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AboutPlugin()
    window.show()
    sys.exit(app.exec_())
