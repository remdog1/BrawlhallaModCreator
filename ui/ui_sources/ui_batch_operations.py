# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'batch_operations.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDialog,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QProgressBar, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_BatchOperationsDialog(object):
    def setupUi(self, BatchOperationsDialog):
        if not BatchOperationsDialog.objectName():
            BatchOperationsDialog.setObjectName(u"BatchOperationsDialog")
        BatchOperationsDialog.resize(500, 400)
        BatchOperationsDialog.setStyleSheet(u"/* Modern Dark Theme */\n"
"QDialog {\n"
"    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, \n"
"                               stop:0 #2D2E32, stop:1 #1E1F23);\n"
"    border-radius: 8px;\n"
"}\n"
"\n"
"QLabel {\n"
"    color: #E8E9EA;\n"
"    font-family: \"Segoe UI\", \"Roboto\", sans-serif;\n"
"    font-size: 13px;\n"
"    font-weight: 500;\n"
"}\n"
"\n"
"QPushButton {\n"
"    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, \n"
"                               stop:0 #0078D4, stop:1 #106EBE);\n"
"    color: #FFFFFF;\n"
"    border: none;\n"
"    border-radius: 6px;\n"
"    padding: 8px 16px;\n"
"    font-size: 13px;\n"
"    font-weight: 500;\n"
"    min-height: 20px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, \n"
"                               stop:0 #106EBE, stop:1 #005A9E);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, \n"
"                               stop:0 #005A9E, stop:1 #004578);\n"
"}\n"
""
                        "\n"
"QPushButton:disabled {\n"
"    background: rgba(255, 255, 255, 0.1);\n"
"    color: rgba(255, 255, 255, 0.4);\n"
"}\n"
"\n"
"QListWidget {\n"
"    background-color: rgba(255, 255, 255, 0.03);\n"
"    color: #E8E9EA;\n"
"    border: 1px solid rgba(255, 255, 255, 0.08);\n"
"    border-radius: 6px;\n"
"    padding: 4px;\n"
"    font-size: 13px;\n"
"}\n"
"\n"
"QListWidget::item {\n"
"    padding: 8px;\n"
"    border-radius: 4px;\n"
"    margin: 2px;\n"
"}\n"
"\n"
"QListWidget::item:selected {\n"
"    background-color: #0078D4;\n"
"    color: #FFFFFF;\n"
"}\n"
"\n"
"QListWidget::item:hover {\n"
"    background-color: rgba(255, 255, 255, 0.1);\n"
"}\n"
"\n"
"QCheckBox {\n"
"    color: #E8E9EA;\n"
"    font-size: 13px;\n"
"    spacing: 8px;\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    width: 16px;\n"
"    height: 16px;\n"
"    border-radius: 3px;\n"
"    border: 1px solid rgba(255, 255, 255, 0.3);\n"
"    background-color: rgba(255, 255, 255, 0.05);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    backgrou"
                        "nd-color: #0078D4;\n"
"    border: 1px solid #0078D4;\n"
"}\n"
"\n"
"QCheckBox::indicator:checked:after {\n"
"    content: \"\u2713\";\n"
"    color: white;\n"
"    font-weight: bold;\n"
"}\n"
"\n"
"QProgressBar {\n"
"    border: 1px solid rgba(255, 255, 255, 0.1);\n"
"    border-radius: 6px;\n"
"    background-color: rgba(255, 255, 255, 0.05);\n"
"    text-align: center;\n"
"    color: #E8E9EA;\n"
"    font-size: 12px;\n"
"}\n"
"\n"
"QProgressBar::chunk {\n"
"    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, \n"
"                               stop:0 #0078D4, stop:1 #106EBE);\n"
"    border-radius: 5px;\n"
"}")
        self.verticalLayout = QVBoxLayout(BatchOperationsDialog)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(20, 20, 20, 20)
        self.titleLabel = QLabel(BatchOperationsDialog)
        self.titleLabel.setObjectName(u"titleLabel")
        self.titleLabel.setStyleSheet(u"font-size: 18px; font-weight: 600; color: #FFFFFF; margin-bottom: 10px;")

        self.verticalLayout.addWidget(self.titleLabel)

        self.descriptionLabel = QLabel(BatchOperationsDialog)
        self.descriptionLabel.setObjectName(u"descriptionLabel")

        self.verticalLayout.addWidget(self.descriptionLabel)

        self.modsList = QListWidget(BatchOperationsDialog)
        self.modsList.setObjectName(u"modsList")
        self.modsList.setSelectionMode(QAbstractItemView.MultiSelection)

        self.verticalLayout.addWidget(self.modsList)

        self.operationsLayout = QHBoxLayout()
        self.operationsLayout.setSpacing(10)
        self.operationsLayout.setObjectName(u"operationsLayout")
        self.buildCheckBox = QCheckBox(BatchOperationsDialog)
        self.buildCheckBox.setObjectName(u"buildCheckBox")

        self.operationsLayout.addWidget(self.buildCheckBox)

        self.installCheckBox = QCheckBox(BatchOperationsDialog)
        self.installCheckBox.setObjectName(u"installCheckBox")

        self.operationsLayout.addWidget(self.installCheckBox)

        self.uninstallCheckBox = QCheckBox(BatchOperationsDialog)
        self.uninstallCheckBox.setObjectName(u"uninstallCheckBox")

        self.operationsLayout.addWidget(self.uninstallCheckBox)

        self.deleteCheckBox = QCheckBox(BatchOperationsDialog)
        self.deleteCheckBox.setObjectName(u"deleteCheckBox")

        self.operationsLayout.addWidget(self.deleteCheckBox)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.operationsLayout.addItem(self.horizontalSpacer)


        self.verticalLayout.addLayout(self.operationsLayout)

        self.progressBar = QProgressBar(BatchOperationsDialog)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(True)

        self.verticalLayout.addWidget(self.progressBar)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setSpacing(10)
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.horizontalSpacer2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacer2)

        self.executeButton = QPushButton(BatchOperationsDialog)
        self.executeButton.setObjectName(u"executeButton")

        self.buttonLayout.addWidget(self.executeButton)

        self.cancelButton = QPushButton(BatchOperationsDialog)
        self.cancelButton.setObjectName(u"cancelButton")

        self.buttonLayout.addWidget(self.cancelButton)


        self.verticalLayout.addLayout(self.buttonLayout)


        self.retranslateUi(BatchOperationsDialog)

        self.executeButton.setDefault(True)


        QMetaObject.connectSlotsByName(BatchOperationsDialog)
    # setupUi

    def retranslateUi(self, BatchOperationsDialog):
        BatchOperationsDialog.setWindowTitle(QCoreApplication.translate("BatchOperationsDialog", u"Batch Operations", None))
        self.titleLabel.setText(QCoreApplication.translate("BatchOperationsDialog", u"Batch Operations", None))
        self.descriptionLabel.setText(QCoreApplication.translate("BatchOperationsDialog", u"Select mods and choose an operation to perform:", None))
        self.buildCheckBox.setText(QCoreApplication.translate("BatchOperationsDialog", u"Build", None))
        self.installCheckBox.setText(QCoreApplication.translate("BatchOperationsDialog", u"Install", None))
        self.uninstallCheckBox.setText(QCoreApplication.translate("BatchOperationsDialog", u"Uninstall", None))
        self.deleteCheckBox.setText(QCoreApplication.translate("BatchOperationsDialog", u"Delete", None))
        self.executeButton.setText(QCoreApplication.translate("BatchOperationsDialog", u"Execute", None))
        self.cancelButton.setText(QCoreApplication.translate("BatchOperationsDialog", u"Cancel", None))
    # retranslateUi

