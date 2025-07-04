# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/variableEditor.py
#
# Description:
#     Editor widget for user-defined symbolic variables (userVariables.py).
#
#     Features:
#       - Editable QTextEdit for defining variables like m = 2.0
#       - Save/reload functionality and undo/redo support
#       - Automatic file sync checking and debug logging
#       - Programmatic updates from variable dictionaries
#       - Force refresh with sync verification
#
# Authors:  Michael Pieber
# Date:     2025-07-03
#
# License:  BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


from exudynGUI.core.qtImports import *
import os
from pathlib import Path
filePath = Path(__file__).resolve().parent.parent / 'functions' / 'userVariables.py'

class VariableEditor(QWidget):
    def __init__(self, path=None, parent=None):
        super().__init__(parent)

        if path is None:
            path = (Path(__file__).resolve().parent.parent 
                    / 'functions' / 'userVariables.py')
        self.path = str(path)

        self.editor = QTextEdit()
        self.editor.setFont(QFont("Courier", 10))

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Edit user-defined variables (e.g., m = 2.0):"))
        layout.addWidget(self.editor)

        btnLayout = QHBoxLayout()
        self.saveButton = QPushButton("Save")
        self.reloadButton = QPushButton("Reload")
        btnLayout.addWidget(self.saveButton)
        btnLayout.addWidget(self.reloadButton)
        layout.addLayout(btnLayout)
        self.setLayout(layout)

        self.saveButton.clicked.connect(self.saveFile)
        self.reloadButton.clicked.connect(self.loadFile)        # start by loading the file
        self.loadFile()

    def loadFile(self):
        """Load the entire contents of userVariables.py into the editor."""
        if os.path.exists(self.path):
            with open(self.path, 'r', encoding='utf-8') as f:
                contents = f.read()
            
            # Clear editor state before loading new content
            self.editor.document().clearUndoRedoStacks()
            self.editor.setPlainText(contents)
            
            # Move cursor to beginning
            cursor = self.editor.textCursor()
            cursor.movePosition(cursor.Start)
            self.editor.setTextCursor(cursor)
            
            from exudynGUI.guiForms.specialWidgets import debugLog
            debugLog(f"VariableEditor: Loaded {len(contents)} characters from {self.path}")
        else:
            default_content = "# Define symbolic variables here, e.g.:\nm = 2.0\nk = 100"
            self.editor.setPlainText(default_content)
            from exudynGUI.guiForms.specialWidgets import debugLog
            debugLog(f"VariableEditor: File not found, using default content")
    
    def forceRefresh(self):
        """Force a complete refresh of the editor content and display."""
        from exudynGUI.guiForms.specialWidgets import debugLog
        debugLog("VariableEditor: Forcing complete refresh...")
        
        # Clear any cached state
        self.editor.document().clearUndoRedoStacks()
        
        # Reload from file
        self.loadFile()
          # Force visual update
        self.editor.update()
        self.editor.repaint()
        
        # Verify content matches file
        editor_content = self.editor.toPlainText()
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            if editor_content.strip() == file_content.strip():
                from exudynGUI.guiForms.specialWidgets import debugLog
                debugLog("VariableEditor: ✓ Editor and file are in sync after refresh")
            else:
                from exudynGUI.guiForms.specialWidgets import debugLog
                debugLog("VariableEditor: ⚠️ Editor and file still out of sync after refresh!")
                from exudynGUI.guiForms.specialWidgets import debugLog
                debugLog(f"Editor: {repr(editor_content[:100])}")
                from exudynGUI.guiForms.specialWidgets import debugLog
                debugLog(f"File: {repr(file_content[:100])}")
        except Exception as e:
            from exudynGUI.guiForms.specialWidgets import debugLog
            debugLog(f"VariableEditor: Could not verify sync: {e}")
        
        return True

    def saveFile(self):
        text = self.editor.toPlainText()
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(text)
        # QMessageBox.information(self, "Saved", f"Variables saved to:\n{self.path}")

    def updateFromVariables(self, variables=None):
        """Update the editor content from the variables or variables file. Called when loading projects."""
        from exudynGUI.guiForms.specialWidgets import debugLog
        debugLog(f"VariableEditor: updateFromVariables called with variables: {variables}")
        
        if variables is not None:
            # Convert variables dict to Python code format
            variable_lines = []
            for key, value in variables.items():
                if isinstance(value, str):
                    variable_lines.append(f"{key} = '{value}'")
                else:
                    variable_lines.append(f"{key} = {value}")
            
            variable_content = "\n".join(variable_lines)
            
            # Write to file and update editor
            try:
                with open(self.path, 'w', encoding='utf-8') as f:
                    f.write(variable_content)
                self.editor.setPlainText(variable_content)
                from exudynGUI.guiForms.specialWidgets import debugLog
                debugLog(f"VariableEditor: Updated with {len(variables)} variables")
            except Exception as e:
                from exudynGUI.guiForms.specialWidgets import debugLog
                debugLog(f"VariableEditor: Error updating variables: {e}")
                self.loadFile()  # Fallback to loading from file
        else:
            # No variables provided, load from file
            self.loadFile()
        
        return True



