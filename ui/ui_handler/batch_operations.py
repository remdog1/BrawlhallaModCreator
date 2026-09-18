"""
Batch Operations Dialog for Mod Creator
Handles batch operations on multiple mods
"""

import os
from typing import List, Dict, Any, Callable
from PySide6.QtWidgets import QDialog, QMessageBox, QListWidgetItem, QApplication
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont

from ..ui_sources.ui_batch_operations import Ui_BatchOperationsDialog


class BatchOperationWorker(QThread):
    """Worker thread for batch operations"""
    
    progress_updated = Signal(int, str)  # progress, status
    operation_completed = Signal(str, bool)  # mod_name, success
    finished = Signal()
    
    def __init__(self, mods: List[Dict], operations: List[str], 
                 build_func: Callable = None, install_func: Callable = None,
                 uninstall_func: Callable = None, delete_func: Callable = None):
        super().__init__()
        self.mods = mods
        self.operations = operations
        self.build_func = build_func
        self.install_func = install_func
        self.uninstall_func = uninstall_func
        self.delete_func = delete_func
        self.should_stop = False
    
    def run(self):
        """Execute batch operations"""
        total_mods = len(self.mods)
        
        for i, mod in enumerate(self.mods):
            if self.should_stop:
                break
                
            mod_name = mod.get('name', 'Unknown')
            self.progress_updated.emit(int((i / total_mods) * 100), f"Processing {mod_name}...")
            
            success = True
            for operation in self.operations:
                if self.should_stop:
                    break
                    
                try:
                    if operation == 'build' and self.build_func:
                        result = self.build_func(mod)
                        if not result:
                            success = False
                            break
                    elif operation == 'install' and self.install_func:
                        result = self.install_func(mod)
                        if not result:
                            success = False
                            break
                    elif operation == 'uninstall' and self.uninstall_func:
                        result = self.uninstall_func(mod)
                        if not result:
                            success = False
                            break
                    elif operation == 'delete' and self.delete_func:
                        result = self.delete_func(mod)
                        if not result:
                            success = False
                            break
                except Exception as e:
                    print(f"Error in batch operation {operation} for {mod_name}: {e}")
                    success = False
                    break
            
            self.operation_completed.emit(mod_name, success)
        
        self.progress_updated.emit(100, "Batch operations completed")
        self.finished.emit()
    
    def stop(self):
        """Stop the worker thread"""
        self.should_stop = True


class BatchOperationsDialog(QDialog):
    """Dialog for batch operations on multiple mods"""
    
    operations_completed = Signal()  # Signal emitted when all operations are completed
    
    def __init__(self, parent=None, mods: List[Dict] = None):
        super().__init__(parent)
        self.ui = Ui_BatchOperationsDialog()
        self.ui.setupUi(self)
        
        self.mods = mods or []
        self.worker = None
        
        # Store operation functions
        self.build_func = None
        self.install_func = None
        self.uninstall_func = None
        self.delete_func = None
        
        self.setup_ui()
        self.connect_signals()
        self.load_mods()
    
    def setup_ui(self):
        """Setup the UI components"""
        self.setModal(True)
        self.setWindowTitle("Batch Operations")
        
        # Set initial state
        self.ui.progressBar.setValue(0)
        self.ui.progressBar.setVisible(False)
        self.ui.executeButton.setEnabled(False)
    
    def connect_signals(self):
        """Connect UI signals to handlers"""
        self.ui.executeButton.clicked.connect(self.execute_operations)
        self.ui.cancelButton.clicked.connect(self.reject)
        
        # Connect checkboxes to enable/disable execute button
        self.ui.buildCheckBox.toggled.connect(self.validate_operations)
        self.ui.installCheckBox.toggled.connect(self.validate_operations)
        self.ui.uninstallCheckBox.toggled.connect(self.validate_operations)
        self.ui.deleteCheckBox.toggled.connect(self.validate_operations)
    
    def load_mods(self):
        """Load mods into the list"""
        self.ui.modsList.clear()
        
        for mod in self.mods:
            item = QListWidgetItem(mod.get('name', 'Unknown Mod'))
            item.setData(Qt.UserRole, mod)
            item.setCheckState(Qt.Unchecked)
            self.ui.modsList.addItem(item)
    
    def validate_operations(self):
        """Validate that at least one operation is selected"""
        has_operation = (self.ui.buildCheckBox.isChecked() or 
                        self.ui.installCheckBox.isChecked() or
                        self.ui.uninstallCheckBox.isChecked() or
                        self.ui.deleteCheckBox.isChecked())
        
        has_selected_mods = any(item.checkState() == Qt.Checked 
                              for i in range(self.ui.modsList.count())
                              for item in [self.ui.modsList.item(i)])
        
        self.ui.executeButton.setEnabled(has_operation and has_selected_mods)
    
    def get_selected_mods(self) -> List[Dict]:
        """Get list of selected mods"""
        selected_mods = []
        for i in range(self.ui.modsList.count()):
            item = self.ui.modsList.item(i)
            if item.checkState() == Qt.Checked:
                mod_data = item.data(Qt.UserRole)
                selected_mods.append(mod_data)
        return selected_mods
    
    def get_selected_operations(self) -> List[str]:
        """Get list of selected operations"""
        operations = []
        if self.ui.buildCheckBox.isChecked():
            operations.append('build')
        if self.ui.installCheckBox.isChecked():
            operations.append('install')
        if self.ui.uninstallCheckBox.isChecked():
            operations.append('uninstall')
        if self.ui.deleteCheckBox.isChecked():
            operations.append('delete')
        return operations
    
    def execute_operations(self):
        """Execute the selected operations on selected mods"""
        selected_mods = self.get_selected_mods()
        selected_operations = self.get_selected_operations()
        
        if not selected_mods:
            QMessageBox.warning(self, "No Mods Selected", "Please select at least one mod.")
            return
        
        if not selected_operations:
            QMessageBox.warning(self, "No Operations Selected", "Please select at least one operation.")
            return
        
        # Confirm the operations
        mod_names = [mod.get('name', 'Unknown') for mod in selected_mods]
        operation_names = [op.title() for op in selected_operations]
        
        reply = QMessageBox.question(
            self, "Confirm Batch Operations",
            f"Are you sure you want to {', '.join(operation_names).lower()} the following mods?\n\n" +
            "\n".join(mod_names),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Start the worker thread
        self.ui.progressBar.setVisible(True)
        self.ui.progressBar.setValue(0)
        self.ui.executeButton.setEnabled(False)
        self.ui.cancelButton.setText("Stop")
        
        self.worker = BatchOperationWorker(
            selected_mods, selected_operations,
            self.build_func, self.install_func,
            self.uninstall_func, self.delete_func
        )
        
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.operation_completed.connect(self.on_operation_completed)
        self.worker.finished.connect(self.on_operations_finished)
        
        self.worker.start()
    
    def update_progress(self, progress: int, status: str):
        """Update progress bar and status"""
        self.ui.progressBar.setValue(progress)
        self.ui.progressBar.setFormat(f"{status} ({progress}%)")
    
    def on_operation_completed(self, mod_name: str, success: bool):
        """Handle completion of a single operation"""
        status = "✓" if success else "✗"
        print(f"{status} {mod_name}")
    
    def on_operations_finished(self):
        """Handle completion of all operations"""
        self.ui.progressBar.setValue(100)
        self.ui.progressBar.setFormat("Batch operations completed (100%)")
        
        QMessageBox.information(
            self, "Batch Operations Complete",
            "All batch operations have been completed."
        )
        
        self.operations_completed.emit()
        self.accept()
    
    def set_operation_functions(self, build_func: Callable = None, 
                               install_func: Callable = None,
                               uninstall_func: Callable = None,
                               delete_func: Callable = None):
        """Set the operation functions"""
        self.build_func = build_func
        self.install_func = install_func
        self.uninstall_func = uninstall_func
        self.delete_func = delete_func
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Stop Operations",
                "Operations are still running. Do you want to stop them?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.worker.stop()
                self.worker.wait(3000)  # Wait up to 3 seconds
            else:
                event.ignore()
                return
        
        event.accept()

































