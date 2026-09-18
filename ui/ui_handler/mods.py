from typing import List, Dict
import os
import shutil

from PySide6.QtWidgets import QWidget, QFileDialog, QFrame, QVBoxLayout, QApplication, QMessageBox
from PySide6.QtGui import QPaintEvent, QPixmap, QColor, QDragEnterEvent, QDropEvent
from PySide6.QtCore import QEvent, Qt, QTimer, QSize, QMimeData

from .modclass import ModClass
from .modbutton import ModButton
from .template_dialog import TemplateDialog
from .batch_operations import BatchOperationsDialog

from ..ui_sources.ui_mods import Ui_Mods
from ..ui_sources.ui_mod_build_actions import Ui_ModsBuildActions
from ..ui_sources.ui_mod_body import Ui_ModCreator
from ..ui_sources.ui_preview_editor import Ui_SetPreviewWidget

from ..utils.layout import AddToFrame, ClearFrame
from ..utils.textformater import TextFormatter


def SelectImageDialog():
    dlg = QFileDialog()
    dlg.setFileMode(QFileDialog.AnyFile)
    dlg.setNameFilter("Image files (*.jpg *.png)")

    if dlg.exec_():
        filenames = dlg.selectedFiles()
        if filenames:
            return filenames[0]

    return None


class SetPreview(QWidget):
    cachedPreviews = {}

    def __init__(self):
        super().__init__()
        self.ui = Ui_SetPreviewWidget()
        self.ui.setupUi(self)

        self.preview = None

        self.ui.add.clicked.connect(self.addClick)
        self.ui.deletePreview.clicked.connect(self.deleteClick)
        self.ui.change.clicked.connect(self.changeClick)

        self.previewAdded = lambda path: None
        self.previewChanged = lambda path: None
        self.previewDeleted = lambda path: None

    def resizeEvent(self, event):
        if event is not None:
            super().resizeEvent(event)

        self.ui.buttons.setGeometry(0, 0, self.width(), self.height())

        pixmap: QPixmap = self.ui.preview.pixmap()
        size = pixmap.size()
        if size != QSize(0, 0):
            w = size.width()
            h = size.height()
            pw = self.ui.main.width()
            ph = self.ui.main.height()

            c = h / w

            w = ph / c
            if w <= pw:
                h = ph
            else:
                w = pw
                h = pw * c

            self.ui.preview.setGeometry((pw//2)-(w//2), (ph//2)-(h//2), w, h)

        else:
            self.ui.preview.setGeometry(0, 0, self.ui.main.width(), self.ui.main.height())

    def setPreview(self, path: str):
        if path not in self.cachedPreviews:
            pixmap = QPixmap(path)
            self.cachedPreviews[path] = pixmap
        else:
            pixmap = self.cachedPreviews[path]

        self.preview = path
        self.ui.preview.setPixmap(pixmap)

        self.updateButtons()
        self.resizeEvent(None)

    def clearPreview(self):
        self.preview = None
        self.ui.preview.setPixmap(QPixmap())
        self.updateButtons()
        self.resizeEvent(None)

    def updateButtons(self):
        layout: QVBoxLayout = self.ui.buttons.layout()

        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
                layout.removeWidget(child.widget())

        if self.preview is None:
            AddToFrame(self.ui.buttons, self.ui.add)
        else:
            AddToFrame(self.ui.buttons, self.ui.deletePreview)
            AddToFrame(self.ui.buttons, self.ui.change)

    def setHeight(self, h: int):
        self.setMinimumHeight(h)

    def addClick(self):
        preview = SelectImageDialog()
        if preview is not None:
            self.setPreview(preview)
            self.previewAdded(preview)

    def deleteClick(self):
        preview = self.preview
        self.clearPreview()
        self.previewDeleted(preview)

    def changeClick(self):
        preview = SelectImageDialog()
        if preview is not None:
            self.setPreview(preview)
            self.previewChanged(preview)


class Mods(QWidget):
    previewSetters: List[SetPreview] = []

    descriptionOriginalFont = None
    descriptionOriginalColor = None

    selectedModButton: ModButton = None
    modsButtons: List[ModButton] = []
    modsSources: Dict[str, ModClass] = {}

    currentGameVersion = ""

    def __init__(self, saveMethod, installMethod, uninstallMethod, deleteMethod, buildMethod, createMethod,
                 reloadMethod, openFolderMethod):
        super().__init__()

        self.ui = Ui_Mods()
        self.ui.setupUi(self)

        bodyWidget = QWidget()
        self.body = Ui_ModCreator()
        self.body.setupUi(bodyWidget)
        self.ui.scrollBody.setWidget(bodyWidget)

        actionsWidget = QWidget()
        self.actions = Ui_ModsBuildActions()
        self.actions.setupUi(actionsWidget)

        self.actions.uninstall.setParent(None)

        self.ui.createModFrame.setMaximumHeight(30)
        self.ui.modsBuildActions.setMaximumHeight(95)
        self.ui.modsBuildActions.setMinimumHeight(95)
        AddToFrame(self.ui.modsBuildActions, actionsWidget)

        # Filling previews grid
        for r in range(2):
            for c in range(3):
                previewSetter = SetPreview()
                previewSetter.previewAdded = self.previewSelected
                previewSetter.previewChanged = self.previewSelected
                previewSetter.previewDeleted = self.previewSelected
                previewSetter.setParent(self.body.previews)
                self.body.previews.layout().addWidget(previewSetter, r, c)
                self.previewSetters.append(previewSetter)

        self.body.description.textChanged.connect(self.descriptionChanged)
        self.descriptionOriginalFont = self.body.description.currentFont()
        self.descriptionOriginalColor = self.body.description.textColor()
        self.body.description.installEventFilter(self)

        self.body.author.installEventFilter(self)
        self.body.gameVersion.installEventFilter(self)
        self.body.version.installEventFilter(self)
        self.body.tags.installEventFilter(self)
        self.body.source.textChanged.connect(self.featuresChanged)
        self.body.source.installEventFilter(self)
        self.ui.modBody.installEventFilter(self)
        
        # Enable drag and drop for the mod body
        self.ui.modBody.setAcceptDrops(True)
        self.ui.modBody.dragEnterEvent = self.dragEnterEvent
        self.ui.modBody.dropEvent = self.dropEvent

        modsListFrame = QFrame()
        layout = QVBoxLayout(modsListFrame)
        layout.setSpacing(0)
        layout.setContentsMargins(2, 5, 2, 5)
        self.modsList = QFrame()
        self.modsList.setMaximumWidth(self.ui.modsList.maximumWidth())
        layout2 = QVBoxLayout(self.modsList)
        layout2.setSpacing(1)
        layout2.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.modsList, 0, Qt.AlignTop)
        self.ui.scrollModsList.setWidget(modsListFrame)

        self.resizeEvent = self.onResize
        self.origScrollModsListResizeEvent = self.ui.scrollModsList.resizeEvent
        self.ui.scrollModsList.resizeEvent = self.onModsListResize

        self.saveTimer = QTimer()
        self.saveTimer.setSingleShot(True)
        #self.saveTimer.start(3000)  # Save every 5 seconds

        self.saveTimer.timeout.connect(saveMethod)
        self.actions.install.clicked.connect(installMethod)
        self.actions.uninstall.clicked.connect(uninstallMethod)
        self.actions.deleteMod.clicked.connect(deleteMethod)
        self.actions.build.clicked.connect(buildMethod)
        self.ui.createMod.clicked.connect(createMethod)
        self.ui.reloadModsList.clicked.connect(reloadMethod)
        self.ui.openModsFolderButton.clicked.connect(openFolderMethod)
        # expose save for drops/edits that adjust features silently
        self.saveMethod = saveMethod
        
        # Add template button if it exists
        if hasattr(self.ui, 'createFromTemplate'):
            self.ui.createFromTemplate.clicked.connect(self.show_template_dialog)
        
        # Add batch operations button if it exists
        if hasattr(self.ui, 'batchOperations'):
            self.ui.batchOperations.clicked.connect(self.show_batch_operations)

        self.ui.searchArea.textChanged.connect(self.searchEvent)

        self.oldSize = (0, 0)

    def onResize(self, event):
        size = self.ui.modBody.size()
        if size == self.oldSize:
            return
        else:
            self.oldSize = size

        previewsWidth = self.body.previews.width()
        previewWidth = (previewsWidth - self.body.previews.layout().spacing() * 2) // 3
        previewHeight = int(previewWidth * 0.5625)

        for previewSetter in self.previewSetters:
            previewSetter.setHeight(previewHeight)

    def eventFilter(self, qobject, event):
        if self.selectedModButton is not None:
            if qobject == self.body.author:
                if event.type() == QEvent.Type.FocusIn:
                    self.body.author.setText(self.selectedModButton.modClass.author or " ")
                elif event.type() == QEvent.Type.FocusOut:
                    self.updateAuthor()

            elif qobject == self.body.gameVersion:
                if event.type() == QEvent.Type.FocusIn:
                    self.body.gameVersion.setText(self.selectedModButton.modClass.gameVersion or " ")
                elif event.type() == QEvent.Type.FocusOut:
                    self.updateGameVersion()

            elif qobject == self.body.version:
                if event.type() == QEvent.Type.FocusIn:
                    self.body.version.setText(self.selectedModButton.modClass.version or " ")
                elif event.type() == QEvent.Type.FocusOut:
                    self.updateVersion()

            elif qobject == self.body.tags:
                if event.type() == QEvent.Type.FocusIn:
                    self.body.tags.setText(", ".join(self.selectedModButton.modClass.tags) or " ")
                elif event.type() == QEvent.Type.FocusOut:
                    self.updateTags()

            elif qobject == self.body.source:
                if event.type() == QEvent.Type.FocusIn:
                    features = getattr(self.selectedModButton.modClass, 'features', [])
                    self.body.source.setText(", ".join(features) or " ")
                elif event.type() == QEvent.Type.FocusOut:
                    self.updateFeatures()

            elif qobject == self.body.description:
                if event.type() == QEvent.Type.FocusIn:
                    self.body.description.setPlainText(self.selectedModButton.modClass.description)
                elif event.type() == QEvent.Type.FocusOut:
                    self.updateDescription()

        if isinstance(event, QPaintEvent):
            self.onResize(event)

        return False

    def updateButtons(self):
        QApplication.processEvents()

        if self.selectedModButton is None:
            return

        layout = self.actions.topButtons.layout()
        modSource = self.selectedModButton.modClass

        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
                layout.removeWidget(child.widget())

        if modSource.installed:
            AddToFrame(self.actions.topButtons, self.actions.uninstall)
        elif modSource.modFileExist:
            AddToFrame(self.actions.topButtons, self.actions.install)

        AddToFrame(self.actions.topButtons, self.actions.deleteMod)

    def onModsListResize(self, event):
        for n in range(self.modsList.layout().count()):
            w = self.modsList.layout().takeAt(0).widget()
            w.onParentResize()
            self.modsList.layout().addWidget(w)

        self.origScrollModsListResizeEvent(event)

    def searchEvent(self, text):
        if not text:
            displayModButtons = self.modsButtons

        else:
            text = text.casefold()

            if len(text.split(" ")) == 1:
                text = f" {text}"

            displayModButtons = [
                modButton
                for modButton in self.modsButtons
                if any([
                    text in f" {modButton.modClass.name.lower()}",
                    text in f" {modButton.modClass.author.lower()}",
                    modButton.modClass.gameVersion.startswith(text.strip()),
                    any([tag.casefold().lower().startswith(text.strip()) for tag in modButton.modClass.tags])
                ])
            ]

        for modButton in self.modsButtons:
            modButton.remove()

        for modButton in displayModButtons:
            modButton.restore(self.modsList)

    # Changed
    def nameChanged(self, text):
        self.saveTimer.stop()
        self.saveTimer.start(500)

        if self.selectedModButton is not None:
            self.selectedModButton.modClass.name = text.strip()
            self.selectedModButton.updateData()

    def authorChanged(self, text):
        self.saveTimer.stop()
        self.saveTimer.start(500)

        if self.selectedModButton is not None:
            self.selectedModButton.modClass.author = text.strip()
            self.selectedModButton.updateData()

    def gameVersionChanged(self, text):
        self.saveTimer.stop()
        self.saveTimer.start(500)

        if self.selectedModButton is not None:
            gameVersion = text.strip()
            self.selectedModButton.modClass.gameVersion = gameVersion
            if gameVersion == self.currentGameVersion:
                self.selectedModButton.modClass.currentVersion = True
            else:
                self.selectedModButton.modClass.currentVersion = False
            self.selectedModButton.updateData()

    def modVersionChanged(self, text):
        self.saveTimer.stop()
        self.saveTimer.start(500)

        if self.selectedModButton is not None:
            self.selectedModButton.modClass.version = text.strip()

    def tagsChanged(self, text):
        self.saveTimer.stop()
        self.saveTimer.start(500)

        if self.selectedModButton is not None:
            # Handle empty text properly
            if text.strip():
                self.selectedModButton.modClass.tags = [t.strip() for t in text.strip().split(",") if t.strip()]
            else:
                self.selectedModButton.modClass.tags = []

    def featuresChanged(self, text):
        print(f"DEBUG: featuresChanged called with: '{text}'")
        self.saveTimer.stop()
        self.saveTimer.start(500)

        if self.selectedModButton is not None:
            # Remove placeholder text before parsing, just like tags
            placeholder = self.body.source.placeholderText()
            if text.startswith(placeholder):
                text = text[len(placeholder):].strip()
            
            # Handle empty text properly like tags
            if text.strip():
                features = [f.strip() for f in text.strip().split(",") if f.strip()]
                print(f"DEBUG: Setting features to: {features}")
                self.selectedModButton.modClass.features = features
            else:
                print("DEBUG: Setting features to empty list")
                self.selectedModButton.modClass.features = []
            self.selectedModButton.updateData()
        else:
            print("DEBUG: No selected mod button")
            # Persist empty state too
            try:
                self.saveMethod()
            except Exception:
                pass

    def descriptionChanged(self):
        self.saveTimer.stop()
        self.saveTimer.start(500)

        self.body.descriptionFrame.setMinimumHeight(self.body.description.document().size().height() +
                                                    self.body.description.minimumHeight())

        if self.body.description.currentFont() != self.descriptionOriginalFont:
            self.body.description.setCurrentFont(self.descriptionOriginalFont)

        if self.body.description.textColor() != self.descriptionOriginalColor:
            self.descriptionOriginalColor = QColor("#eeeeee")
            self.body.description.setTextColor(self.descriptionOriginalColor)

        if self.selectedModButton is not None:
            self.selectedModButton.modClass.description = self.body.description.toPlainText()

    def previewSelected(self, previewPath):
        self.saveTimer.stop()
        self.saveTimer.start(500)

        previews = []
        for previewSetter in self.previewSetters:
            preview = previewSetter.preview
            if preview:
                previews.append(preview)

        if self.selectedModButton is not None:
            self.selectedModButton.modClass.previewsPaths = previews

    # Update ui
    def updateName(self):
        try:
            self.body.name.textChanged.disconnect()
        except RuntimeError:
            pass
        self.body.name.setText(self.selectedModButton.modClass.name)
        self.body.name.textChanged.connect(self.nameChanged)

    def updateAuthor(self):
        try:
            self.body.author.textChanged.disconnect()
        except RuntimeError:
            pass
        self.body.author.setText(f"{self.body.author.placeholderText()} {self.selectedModButton.modClass.author}")
        self.body.author.textChanged.connect(self.authorChanged)

    def updateGameVersion(self):
        try:
            self.body.gameVersion.textChanged.disconnect()
        except RuntimeError:
            pass
        self.body.gameVersion.setText(f"{self.body.gameVersion.placeholderText()} "
                                      f"{self.selectedModButton.modClass.gameVersion}")
        self.body.gameVersion.textChanged.connect(self.gameVersionChanged)

    def updateVersion(self):
        try:
            self.body.version.textChanged.disconnect()
        except RuntimeError:
            pass
        self.body.version.setText(f"{self.body.version.placeholderText()} {self.selectedModButton.modClass.version}")
        self.body.version.textChanged.connect(self.modVersionChanged)

    def updateTags(self):
        try:
            self.body.tags.textChanged.disconnect()
        except RuntimeError:
            pass
        self.body.tags.setText(f"{self.body.tags.placeholderText()} {', '.join(self.selectedModButton.modClass.tags)}")
        self.body.tags.textChanged.connect(self.tagsChanged)

    def updateFeatures(self):
        try:
            self.body.source.textChanged.disconnect()
        except RuntimeError:
            pass
        features = getattr(self.selectedModButton.modClass, 'features', [])
        self.body.source.setText(f"{self.body.source.placeholderText()} {', '.join(features)}")
        self.body.source.textChanged.connect(self.featuresChanged)

    def updateModSourcesPath(self):
        self.body.modSourcesPath.setText(f"{self.body.modSourcesPath.placeholderText()} "
                                         f"{self.selectedModButton.modClass.modSourcesPath}")

    def updateDescription(self):
        try:
            self.body.description.textChanged.disconnect()
        except RuntimeError:
            pass
        self.body.description.setText(TextFormatter.format(self.selectedModButton.modClass.description))
        self.body.descriptionFrame.setMinimumHeight(self.body.description.document().size().height() +
                                                    self.body.description.minimumHeight())
        self.body.description.textChanged.connect(self.descriptionChanged)

    def updatePreviews(self):
        for n, previewSetter in enumerate(self.previewSetters):
            if len(self.selectedModButton.modClass.previewsPaths) >= n + 1:
                preview = self.selectedModButton.modClass.previewsPaths[n]
                previewSetter.setPreview(preview)
            else:
                previewSetter.clearPreview()

    def updateAll(self):
        if self.selectedModButton is not None:
            self.updateName()
            self.updateAuthor()
            self.updateGameVersion()
            self.updateVersion()
            self.updateTags()
            self.updateFeatures()
            self.updateDescription()
            self.updatePreviews()
            self.updateModSourcesPath()

            for modButton in self.modsButtons:
                modButton.updateData()

            self.updateButtons()

    # Actions
    def selectMod(self, modClass: ModClass):
        for modButton in self.modsButtons:
            if modButton.modClass == modClass:
                self.selectedModButton = modButton

        self.updateAll()

    def addModButton(self, modClass: ModClass):
        modButton = ModButton(modClass=modClass,
                              method=self.selectMod)
        self.modsButtons.append(modButton)
        self.modsList.layout().addWidget(modButton)

        if not self.selectedModButton:
            modButton.select()
            self.saveTimer.start(3000)

    def addMod(self,
               gameVersion: str,
               name: str,
               author: str,
               version: str,
               description: str,
               tags: List[str],
               features: List[str],
               previewsPaths: List[str],
               hash: str,
               platform: str,
               #installed: bool,
               currentVersion: bool,
               #modFileExist: bool
               modSourcesPath: str):

        modSources = ModClass(gameVersion=gameVersion,
                              name=name,
                              author=author,
                              version=version,
                              description=description,
                              tags=tags,
                              previewsPaths=previewsPaths,
                              hash=hash,
                              platform=platform,
                              installed=False,
                              currentVersion=currentVersion,
                              modFileExist=False,
                              modSourcesPath=modSourcesPath)

        # Ensure features from controller are reflected in UI model
        try:
            modSources.features = features or []
        except Exception:
            modSources.features = []

        self.modsSources[hash] = modSources
        self.addModButton(modSources)

    def updateMod(self,
                  hash: str,
                  installed: bool,
                  modFileExist: bool):

        modSources = self.modsSources.get(hash, None)

        if modSources is not None:
            modSources.installed = installed
            modSources.modFileExist = modFileExist

    def removeAllMods(self):
        ClearFrame(self.modsList)

        self.selectedModButton = None
        for modButton in self.modsButtons:
            modButton.__del__()
            del modButton
        self.modsButtons.clear()

        for modSource in self.modsSources.values():
            del modSource
        self.modsSources.clear()

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events for file drops"""
        if event.mimeData().hasUrls():
            # Check if any of the dropped files are valid mod files
            urls = event.mimeData().urls()
            valid_files = []
            
            for url in urls:
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    # Check for valid mod file extensions
                    if (file_path.lower().endswith(('.swf', '.bnk', '.wem', '.txt', '.png', '.jpg', '.jpeg')) or
                        file_path.lower().endswith('.bmod')):
                        valid_files.append(file_path)
            
            if valid_files:
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handle drop events for file drops"""
        if not self.selectedModButton:
            QMessageBox.warning(self, "No Mod Selected", 
                              "Please select a mod first before dropping files.")
            return
            
        urls = event.mimeData().urls()
        mod_path = self.selectedModButton.modClass.modSourcesPath
        
        if not os.path.exists(mod_path):
            QMessageBox.warning(self, "Mod Path Not Found", 
                              f"Mod path not found: {mod_path}")
            return
        
        copied_files = []
        failed_files = []
        
        for url in urls:
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                try:
                    # Determine destination based on file type
                    filename = os.path.basename(file_path)
                    dest_path = self._get_destination_path(mod_path, filename, file_path)
                    
                    # Create destination directory if it doesn't exist
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    
                    # Copy the file
                    shutil.copy2(file_path, dest_path)
                    copied_files.append(filename)
                    
                except Exception as e:
                    failed_files.append(f"{filename}: {str(e)}")
        
        # Show results
        if copied_files:
            message = f"Successfully copied {len(copied_files)} file(s):\n" + "\n".join(copied_files)
            if failed_files:
                message += f"\n\nFailed to copy {len(failed_files)} file(s):\n" + "\n".join(failed_files)
            
            QMessageBox.information(self, "Files Copied", message)
            
            # Refresh the mod to show new files
            if hasattr(self, 'reloadMethod'):
                self.reloadMethod()
        else:
            QMessageBox.warning(self, "No Files Copied", 
                              "No valid files were copied. Please check file types and permissions.")
        
        event.acceptProposedAction()

    def _get_destination_path(self, mod_path: str, filename: str, source_path: str) -> str:
        """Determine the destination path for a dropped file based on its type"""
        filename_lower = filename.lower()
        
        # SWF files go to root
        if filename_lower.endswith('.swf'):
            return os.path.join(mod_path, filename)
        
        # BNK files go to Sound folder
        elif filename_lower.endswith('.bnk'):
            return os.path.join(mod_path, "Sound", filename)
        
        # WEM files go to Sound folder (in appropriate BNK subfolder)
        elif filename_lower.endswith('.wem'):
            # Try to determine BNK folder based on filename patterns
            if 'announcer' in filename_lower or 'vox' in filename_lower:
                return os.path.join(mod_path, "Sound", "VOX_Announcer.bnk", filename)
            elif 'spc' in filename_lower or 'character' in filename_lower:
                return os.path.join(mod_path, "Sound", "SPC_Character.bnk", filename)
            else:
                return os.path.join(mod_path, "Sound", filename)
        
        # Language files go to languages folder
        elif filename_lower.endswith('.txt') and 'language' in filename_lower:
            return os.path.join(mod_path, "languages", filename)
        
        # Image files go to _previews folder
        elif filename_lower.endswith(('.png', '.jpg', '.jpeg')):
            return os.path.join(mod_path, "_previews", filename)
        
        # Default: put in root
        else:
            return os.path.join(mod_path, filename)

    def show_template_dialog(self):
        """Show the template selection dialog"""
        from core.core.worker.variables import MODS_SOURCES_PATH
        
        if not MODS_SOURCES_PATH:
            QMessageBox.warning(self, "No Mods Sources Path", 
                              "Mods sources path is not configured.")
            return
        
        dialog = TemplateDialog(self, MODS_SOURCES_PATH[0])
        dialog.mod_created.connect(self.on_template_mod_created)
        
        if dialog.exec() == QDialog.Accepted:
            # Dialog was accepted, mod creation handled by signal
            pass
    
    def on_template_mod_created(self, template_id: str, mod_path: str):
        """Handle mod creation from template"""
        # Reload the mods list to show the new mod
        if hasattr(self, 'reloadMethod'):
            self.reloadMethod()
        
        # Find and select the newly created mod
        mod_name = os.path.basename(mod_path)
        for mod_button in self.modsButtons:
            if mod_button.modClass.folderName == mod_name:
                self.selectMod(mod_button)
                break

    def show_batch_operations(self):
        """Show the batch operations dialog"""
        # Prepare mod data for batch operations
        mods_data = []
        for mod_button in self.modsButtons:
            mod_data = {
                'name': mod_button.modClass.name,
                'path': mod_button.modClass.modSourcesPath,
                'mod_button': mod_button
            }
            mods_data.append(mod_data)
        
        if not mods_data:
            QMessageBox.information(self, "No Mods", "No mods available for batch operations.")
            return
        
        dialog = BatchOperationsDialog(self, mods_data)
        
        # Set up operation functions
        dialog.set_operation_functions(
            build_func=self._batch_build_mod,
            install_func=self._batch_install_mod,
            uninstall_func=self._batch_uninstall_mod,
            delete_func=self._batch_delete_mod
        )
        
        dialog.operations_completed.connect(self.on_batch_operations_completed)
        
        if dialog.exec() == QDialog.Accepted:
            # Operations completed successfully
            pass
    
    def _batch_build_mod(self, mod_data: Dict) -> bool:
        """Build a single mod (for batch operations)"""
        try:
            mod_button = mod_data['mod_button']
            if hasattr(self, 'buildMethod'):
                self.buildMethod(mod_button)
            return True
        except Exception as e:
            print(f"Error building mod {mod_data['name']}: {e}")
            return False
    
    def _batch_install_mod(self, mod_data: Dict) -> bool:
        """Install a single mod (for batch operations)"""
        try:
            mod_button = mod_data['mod_button']
            if hasattr(self, 'installMethod'):
                self.installMethod(mod_button)
            return True
        except Exception as e:
            print(f"Error installing mod {mod_data['name']}: {e}")
            return False
    
    def _batch_uninstall_mod(self, mod_data: Dict) -> bool:
        """Uninstall a single mod (for batch operations)"""
        try:
            mod_button = mod_data['mod_button']
            if hasattr(self, 'uninstallMethod'):
                self.uninstallMethod(mod_button)
            return True
        except Exception as e:
            print(f"Error uninstalling mod {mod_data['name']}: {e}")
            return False
    
    def _batch_delete_mod(self, mod_data: Dict) -> bool:
        """Delete a single mod (for batch operations)"""
        try:
            mod_button = mod_data['mod_button']
            if hasattr(self, 'deleteMethod'):
                self.deleteMethod(mod_button)
            return True
        except Exception as e:
            print(f"Error deleting mod {mod_data['name']}: {e}")
            return False
    
    def on_batch_operations_completed(self):
        """Handle completion of batch operations"""
        # Reload the mods list to reflect changes
        if hasattr(self, 'reloadMethod'):
            self.reloadMethod()

        self.saveTimer.stop()
