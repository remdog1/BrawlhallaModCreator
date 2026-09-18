"""
Template Dialog for Mod Creator
Handles template selection and mod creation from templates
"""

import os
from typing import Optional, Dict, Any

from PySide6.QtWidgets import QDialog, QMessageBox, QListWidgetItem
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ..ui_sources.ui_template_dialog import Ui_TemplateDialog
from core.core.worker.templates import ModTemplateManager, ModTemplate


class TemplateDialog(QDialog):
    """Dialog for selecting and creating mods from templates"""
    
    mod_created = Signal(str, str)  # Signal emitted when mod is created (template_id, mod_path)
    
    def __init__(self, parent=None, mods_sources_path: str = None):
        super().__init__(parent)
        self.ui = Ui_TemplateDialog()
        self.ui.setupUi(self)
        
        self.mods_sources_path = mods_sources_path
        self.template_manager = ModTemplateManager()
        self.selected_template: Optional[ModTemplate] = None
        
        self.setup_ui()
        self.connect_signals()
        self.load_templates()
    
    def setup_ui(self):
        """Setup the UI components"""
        # Set window properties
        self.setModal(True)
        self.setWindowTitle("Create Mod from Template")
        
        # Set default values
        self.ui.modNameEdit.setText("")
        self.ui.authorEdit.setText("")
        
        # Load categories
        categories = self.template_manager.get_template_categories()
        self.ui.categoryCombo.addItem("All Categories")
        for category in categories:
            self.ui.categoryCombo.addItem(category)
    
    def connect_signals(self):
        """Connect UI signals to handlers"""
        self.ui.templateList.currentItemChanged.connect(self.on_template_selected)
        self.ui.categoryCombo.currentTextChanged.connect(self.filter_templates)
        self.ui.createButton.clicked.connect(self.create_mod)
        self.ui.cancelButton.clicked.connect(self.reject)
        self.ui.modNameEdit.textChanged.connect(self.validate_inputs)
        self.ui.authorEdit.textChanged.connect(self.validate_inputs)
    
    def load_templates(self):
        """Load all available templates into the list"""
        self.ui.templateList.clear()
        templates = self.template_manager.get_all_templates()
        
        for template_id, template in templates.items():
            item = QListWidgetItem(template.name)
            item.setData(Qt.UserRole, template_id)
            item.setToolTip(f"{template.description}\n\nCategory: {template.category}")
            self.ui.templateList.addItem(item)
        
        # Select first item if available
        if self.ui.templateList.count() > 0:
            self.ui.templateList.setCurrentRow(0)
    
    def filter_templates(self, category: str):
        """Filter templates by category"""
        self.ui.templateList.clear()
        
        if category == "All Categories":
            templates = self.template_manager.get_all_templates()
        else:
            templates = self.template_manager.get_templates_by_category(category)
        
        for template_id, template in templates.items():
            item = QListWidgetItem(template.name)
            item.setData(Qt.UserRole, template_id)
            item.setToolTip(f"{template.description}\n\nCategory: {template.category}")
            self.ui.templateList.addItem(item)
        
        # Select first item if available
        if self.ui.templateList.count() > 0:
            self.ui.templateList.setCurrentRow(0)
    
    def on_template_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Handle template selection"""
        if not current:
            return
        
        template_id = current.data(Qt.UserRole)
        template = self.template_manager.get_template(template_id)
        
        if template:
            self.selected_template = template
            self.ui.templateNameLabel.setText(template.name)
            self.ui.templateDescription.setText(template.description)
            
            # Set default mod name if empty
            if not self.ui.modNameEdit.text():
                self.ui.modNameEdit.setText(template.metadata.get("name", ""))
            
            # Set default author if empty
            if not self.ui.authorEdit.text():
                self.ui.authorEdit.setText(template.metadata.get("author", ""))
            
            self.validate_inputs()
    
    def validate_inputs(self):
        """Validate input fields and enable/disable create button"""
        has_template = self.selected_template is not None
        has_name = bool(self.ui.modNameEdit.text().strip())
        has_author = bool(self.ui.authorEdit.text().strip())
        
        self.ui.createButton.setEnabled(has_template and has_name and has_author)
    
    def create_mod(self):
        """Create a new mod from the selected template"""
        if not self.selected_template:
            QMessageBox.warning(self, "No Template Selected", "Please select a template first.")
            return
        
        mod_name = self.ui.modNameEdit.text().strip()
        author_name = self.ui.authorEdit.text().strip()
        
        if not mod_name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a mod name.")
            return
        
        if not author_name:
            QMessageBox.warning(self, "Invalid Input", "Please enter an author name.")
            return
        
        # Check if mods sources path is available
        if not self.mods_sources_path or not os.path.exists(self.mods_sources_path):
            QMessageBox.warning(self, "Invalid Path", "Mods sources path is not available.")
            return
        
        # Create mod path
        safe_mod_name = "".join(c for c in mod_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        mod_path = os.path.join(self.mods_sources_path, safe_mod_name)
        
        # Check if mod already exists
        if os.path.exists(mod_path):
            reply = QMessageBox.question(
                self, "Mod Exists", 
                f"A mod with the name '{safe_mod_name}' already exists. Do you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # Prepare custom metadata
        custom_metadata = {
            "author": author_name,
            "name": mod_name
        }
        
        # Create mod from template
        success = self.template_manager.create_mod_from_template(
            self.ui.templateList.currentItem().data(Qt.UserRole),
            mod_name,
            mod_path,
            custom_metadata
        )
        
        if success:
            QMessageBox.information(
                self, "Mod Created", 
                f"Mod '{mod_name}' has been created successfully from the '{self.selected_template.name}' template."
            )
            self.mod_created.emit(
                self.ui.templateList.currentItem().data(Qt.UserRole),
                mod_path
            )
            self.accept()
        else:
            QMessageBox.critical(
                self, "Creation Failed", 
                "Failed to create mod from template. Please check the error logs."
            )
    
    def get_selected_template(self) -> Optional[ModTemplate]:
        """Get the currently selected template"""
        return self.selected_template
    
    def get_mod_name(self) -> str:
        """Get the entered mod name"""
        return self.ui.modNameEdit.text().strip()
    
    def get_author_name(self) -> str:
        """Get the entered author name"""
        return self.ui.authorEdit.text().strip()
