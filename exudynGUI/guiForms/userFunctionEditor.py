# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/userFunctionEditor.py
#
# Description:
#     Dialog for editing user-defined UF* functions in userFunctions.py.
#
#     Features:
#       - Full text editor for userFunctions.py with undo/redo support
#       - Load, edit, save, and reload Python user function definitions
#       - Live module reloading for immediate availability of changes
#       - Detects unsaved changes and supports reset-to-file state
#       - Integrates with specialWidgets debug logging
#
# Authors:  Michael Pieber
# Date:     2025-07-03
#
# License:  BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from exudynGUI.core.qtImports import *
import os
from pathlib import Path
filePath = Path(__file__).resolve().parent.parent / 'functions' / 'userFunctions.py'

class UserFunctionEditorDialog(QDialog):
    def __init__(self, path=filePath, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit userFunctions.py")
        self.resize(700, 500)
        self.path = path

        layout = QVBoxLayout(self)

        self.textEdit = QTextEdit()
        layout.addWidget(self.textEdit)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel | QDialogButtonBox.Reset)
        layout.addWidget(self.buttonBox)

        self.loadFile()

        self.buttonBox.accepted.connect(self.saveFile)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QDialogButtonBox.Reset).clicked.connect(self.loadFile)
        
    def loadFile(self):
        """Load the file content into the editor."""
        try:
            with open(str(self.path), 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Clear any undo/redo history and set new content
            self.textEdit.document().clearUndoRedoStacks()
            self.textEdit.setPlainText(content)
            
            from exudynGUI.guiForms.specialWidgets import debugLog
            debugLog(f"UserFunctionEditor: Loaded {len(content)} characters from {self.path}")
        except Exception as e:
            error_content = f"# Error loading file: {e}"
            self.textEdit.setPlainText(error_content)
            from exudynGUI.guiForms.specialWidgets import debugLog
            debugLog(f"UserFunctionEditor: Error loading file: {e}")
    
    def hasUnsavedChanges(self):
        """Check if the editor has unsaved changes compared to the file."""
        try:
            with open(str(self.path), 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            editor_content = self.textEdit.toPlainText()
            return editor_content.strip() != file_content.strip()
        except Exception:
            return False  # If we can't read the file, assume no changes
    
    def forceRefresh(self):
        """Force refresh of the editor content from file."""
        from exudynGUI.guiForms.specialWidgets import debugLog
        debugLog("UserFunctionEditor: Forcing refresh from file...")
        self.loadFile()
        self.textEdit.update()
        self.textEdit.repaint()
        return True
    
    def saveFile(self):
        try:
            with open(str(self.path), 'w') as f:
                f.write(self.textEdit.toPlainText())
    
            # 🔁 Force reload of the updated module
            import importlib
            import exudynGUI.functions.userFunctions as userFunctions
            importlib.reload(userFunctions)
    
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))
