import inspect
import os
import sys
import webbrowser

from PyQt5 import QtCore
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (QApplication, QDialog, QLabel, QPushButton,
                             QVBoxLayout)


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

        github_btn = QPushButton('GitHub', self)
        github_btn.setToolTip("GeoCogs' GitHub Page")
        github_btn.clicked.connect(lambda: webbrowser.open(
            'https://github.com/balakumaran247/geocogs'))

        self.layout().addWidget(logo_label)
        self.layout().addWidget(tool_name)
        self.layout().addWidget(github_btn)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AboutPlugin()
    window.show()
    sys.exit(app.exec_())
