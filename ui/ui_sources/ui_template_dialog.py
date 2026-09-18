# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'template_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QSpacerItem, QTextEdit,
    QVBoxLayout, QWidget)

class Ui_TemplateDialog(object):
    def setupUi(self, TemplateDialog):
        if not TemplateDialog.objectName():
            TemplateDialog.setObjectName(u"TemplateDialog")
        TemplateDialog.resize(600, 500)
        TemplateDialog.setStyleSheet(u"/* Modern Dark Theme */\n"
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
"QLineEdit {\n"
"    background-color: rgba(255, 255, 255, 0.05);\n"
"    color: #E8E9EA;\n"
"    border: 1px solid rgba(255, 255, 255, 0.1);\n"
"    border-radius: 6px;\n"
"    padding: 8px 12px;\n"
"    font-size: 13px;\n"
"    font-weight: 400;\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    background-color: rgba(255, 255, 255, 0.08);\n"
"    border: 1px solid #0078D4;\n"
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
"    background-color: rgba(255, 255, 25"
                        "5, 0.1);\n"
"}\n"
"\n"
"QTextEdit {\n"
"    background-color: rgba(255, 255, 255, 0.05);\n"
"    color: #E8E9EA;\n"
"    border: 1px solid rgba(255, 255, 255, 0.1);\n"
"    border-radius: 6px;\n"
"    padding: 8px;\n"
"    font-size: 13px;\n"
"}\n"
"\n"
"QComboBox {\n"
"    background-color: rgba(255, 255, 255, 0.05);\n"
"    color: #E8E9EA;\n"
"    border: 1px solid rgba(255, 255, 255, 0.1);\n"
"    border-radius: 6px;\n"
"    padding: 6px 12px;\n"
"    font-size: 13px;\n"
"}\n"
"\n"
"QComboBox:focus {\n"
"    border: 1px solid #0078D4;\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    border: none;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    image: none;\n"
"    border-left: 5px solid transparent;\n"
"    border-right: 5px solid transparent;\n"
"    border-top: 5px solid #E8E9EA;\n"
"    margin-right: 8px;\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    background-color: #2D2E32;\n"
"    color: #E8E9EA;\n"
"    border: 1px solid rgba(255, 255, 255, 0.2);\n"
"    border-radius: 6px;\n"
"    selection-back"
                        "ground-color: #0078D4;\n"
"}")
        self.verticalLayout = QVBoxLayout(TemplateDialog)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(20, 20, 20, 20)
        self.titleLabel = QLabel(TemplateDialog)
        self.titleLabel.setObjectName(u"titleLabel")
        self.titleLabel.setStyleSheet(u"font-size: 18px; font-weight: 600; color: #FFFFFF; margin-bottom: 10px;")

        self.verticalLayout.addWidget(self.titleLabel)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(10)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.templateList = QListWidget(TemplateDialog)
        self.templateList.setObjectName(u"templateList")
        self.templateList.setMinimumSize(QSize(200, 0))
        self.templateList.setMaximumSize(QSize(250, 16777215))

        self.horizontalLayout.addWidget(self.templateList)

        self.templateDetailsLayout = QVBoxLayout()
        self.templateDetailsLayout.setSpacing(10)
        self.templateDetailsLayout.setObjectName(u"templateDetailsLayout")
        self.templateNameLabel = QLabel(TemplateDialog)
        self.templateNameLabel.setObjectName(u"templateNameLabel")
        self.templateNameLabel.setStyleSheet(u"font-size: 16px; font-weight: 600; color: #FFFFFF;")

        self.templateDetailsLayout.addWidget(self.templateNameLabel)

        self.templateDescription = QTextEdit(TemplateDialog)
        self.templateDescription.setObjectName(u"templateDescription")
        self.templateDescription.setMaximumSize(QSize(16777215, 100))
        self.templateDescription.setReadOnly(True)

        self.templateDetailsLayout.addWidget(self.templateDescription)

        self.modNameLabel = QLabel(TemplateDialog)
        self.modNameLabel.setObjectName(u"modNameLabel")

        self.templateDetailsLayout.addWidget(self.modNameLabel)

        self.modNameEdit = QLineEdit(TemplateDialog)
        self.modNameEdit.setObjectName(u"modNameEdit")

        self.templateDetailsLayout.addWidget(self.modNameEdit)

        self.authorLabel = QLabel(TemplateDialog)
        self.authorLabel.setObjectName(u"authorLabel")

        self.templateDetailsLayout.addWidget(self.authorLabel)

        self.authorEdit = QLineEdit(TemplateDialog)
        self.authorEdit.setObjectName(u"authorEdit")

        self.templateDetailsLayout.addWidget(self.authorEdit)

        self.categoryLabel = QLabel(TemplateDialog)
        self.categoryLabel.setObjectName(u"categoryLabel")

        self.templateDetailsLayout.addWidget(self.categoryLabel)

        self.categoryCombo = QComboBox(TemplateDialog)
        self.categoryCombo.setObjectName(u"categoryCombo")

        self.templateDetailsLayout.addWidget(self.categoryCombo)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.templateDetailsLayout.addItem(self.verticalSpacer)


        self.horizontalLayout.addLayout(self.templateDetailsLayout)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setSpacing(10)
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.horizontalSpacer)

        self.createButton = QPushButton(TemplateDialog)
        self.createButton.setObjectName(u"createButton")

        self.buttonLayout.addWidget(self.createButton)

        self.cancelButton = QPushButton(TemplateDialog)
        self.cancelButton.setObjectName(u"cancelButton")

        self.buttonLayout.addWidget(self.cancelButton)


        self.verticalLayout.addLayout(self.buttonLayout)


        self.retranslateUi(TemplateDialog)

        self.createButton.setDefault(True)


        QMetaObject.connectSlotsByName(TemplateDialog)
    # setupUi

    def retranslateUi(self, TemplateDialog):
        TemplateDialog.setWindowTitle(QCoreApplication.translate("TemplateDialog", u"Mod Templates", None))
        self.titleLabel.setText(QCoreApplication.translate("TemplateDialog", u"Create Mod from Template", None))
        self.templateNameLabel.setText(QCoreApplication.translate("TemplateDialog", u"Template Name", None))
        self.modNameLabel.setText(QCoreApplication.translate("TemplateDialog", u"Mod Name:", None))
        self.modNameEdit.setPlaceholderText(QCoreApplication.translate("TemplateDialog", u"Enter mod name...", None))
        self.authorLabel.setText(QCoreApplication.translate("TemplateDialog", u"Author:", None))
        self.authorEdit.setPlaceholderText(QCoreApplication.translate("TemplateDialog", u"Enter author name...", None))
        self.categoryLabel.setText(QCoreApplication.translate("TemplateDialog", u"Category Filter:", None))
        self.categoryCombo.setPlaceholderText(QCoreApplication.translate("TemplateDialog", u"All Categories", None))
        self.createButton.setText(QCoreApplication.translate("TemplateDialog", u"Create Mod", None))
        self.cancelButton.setText(QCoreApplication.translate("TemplateDialog", u"Cancel", None))
    # retranslateUi

