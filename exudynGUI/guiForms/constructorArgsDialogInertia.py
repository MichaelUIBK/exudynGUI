# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/constructorArgsDialogInertia.py
#
# Description:
#     Dialog for selecting and configuring inertia constructors from
#     exudyn.utilities (e.g., InertiaCuboid, InertiaSphere).
#
#     Features:
#       - Dropdown to choose an Inertia* constructor
#       - Auto-generated argument fields using Python introspection
#       - Validates argument syntax before submission
#       - Emits constructor name and argument string for integration
#
# Authors:  Michael Pieber
# Date:     2025-05-22
#
# License:  BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from exudynGUI.core.qtImports import *
from PyQt5.QtWidgets import QWidget, QFormLayout, QLineEdit, QLabel, QMessageBox, QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QCheckBox

import exudyn.utilities as exuutils
import inspect
import ast
import numpy as np
        
class ConstructorArgsDialog(QDialog):
    def __init__(self, constructorName="", argsString="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Inertia Constructor")
        self.resize(500, 300)

        self.result = {"name": constructorName, "args": argsString}

        layout = QVBoxLayout(self)

        # Dropdown for constructor
        self.combo = QComboBox()
        self.constructors = [k for k in dir(exuutils) 
                            if callable(getattr(exuutils, k)) 
                            and (k.startswith("Inertia") or 
                                 k.endswith("Inertia") or 
                                 "Inertia" in k)]
        self.combo.addItems(self.constructors)
        if constructorName in self.constructors:
            self.combo.setCurrentText(constructorName)
        layout.addWidget(QLabel("Graphics Function"))
        layout.addWidget(self.combo)

        # Dynamic argument fields
        self.argsWidget = QWidget()
        self.argsLayout = QFormLayout(self.argsWidget)
        layout.addWidget(self.argsWidget)
        self.argFields = {}  # name: widget

        self.combo.currentIndexChanged.connect(self.updateArgsFromConstructor)
        self.updateArgsFromConstructor(argsString)

        # OK/Cancel
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accepted)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def updateArgsFromConstructor(self, argsString=None):
        from exudynGUI.guiForms.specialWidgets import buildMatrix3x3Widget, buildVec3Widget
        # Helper functions to robustly check for 3x3 matrix and 3-vector
        def is_matrix3x3(candidate):
            if isinstance(candidate, np.ndarray):
                return candidate.shape == (3, 3)
            if isinstance(candidate, (list, tuple)) and len(candidate) == 3:
                return all(isinstance(row, (list, tuple, np.ndarray)) and len(row) == 3 for row in candidate)
            return False
        def is_vector3(candidate):
            if isinstance(candidate, np.ndarray):
                return candidate.shape == (3,)
            if isinstance(candidate, (list, tuple)) and len(candidate) == 3:
                return all(isinstance(x, (int, float, np.integer, np.floating)) for x in candidate)
            return False
        # Remove old fields
        while self.argsLayout.rowCount():
            self.argsLayout.removeRow(0)
        self.argFields.clear()
        funcName = self.combo.currentText()
        try:
            func = getattr(exuutils, funcName)
            sig = inspect.signature(func)
            # Parse provided argsString if present and is a string
            argValues = {}
            if argsString and isinstance(argsString, str):
                for arg in argsString.split(','):
                    if '=' in arg:
                        k, v = arg.split('=', 1)
                        argValues[k.strip()] = v.strip()
            for name, param in sig.parameters.items():
                if name == 'kwargs' or name.startswith('**'):
                    continue
                default = param.default if param.default is not inspect.Parameter.empty else ''
                val = argValues.get(name, default)
                # Convert numpy arrays to lists for robust type checks
                if isinstance(val, np.ndarray):
                    val = val.tolist()
                if isinstance(default, np.ndarray):
                    default = default.tolist()
                widget = None
                # Check if parameter is boolean
                if isinstance(default, bool) or (isinstance(val, str) and val.lower() in ['true', 'false']):
                    widget = QCheckBox()
                    # Convert string 'True'/'False' to bool if needed
                    if isinstance(val, str):
                        val = val.lower() == 'true'
                    widget.setChecked(bool(val))
                elif name.lower() in ["inertiatensor"] or is_matrix3x3(val) or is_matrix3x3(default):
                    widget = buildMatrix3x3Widget(name, value=val, parent=self)
                elif name.lower() in ["com", "centerofmass"] or is_vector3(val) or is_vector3(default):
                    widget = buildVec3Widget(name, value=val, parent=self)
                else:
                    widget = QLineEdit(str(val))
                self.argsLayout.addRow(QLabel(name), widget)
                self.argFields[name] = widget
        except Exception as e:
            self.argsLayout.addRow(QLabel("Error"), QLabel(str(e)))

    def accepted(self):
        import numpy as np
        funcName = self.combo.currentText()
        argsList = []
        for name, field in self.argFields.items():
            # Handle different widget types
            if isinstance(field, QCheckBox):
                val = str(field.isChecked())  # Convert bool to 'True' or 'False'
            elif hasattr(field, "getValue"):
                val = field.getValue()
            else:
                val = field.text().strip()
            # Convert lists to np.array for specific fields
            if name.lower() in ["inertiatensor", "com", "centerofmass"]:
                if isinstance(val, list):
                    val = f"np.array({val})"
            if isinstance(val, (list, tuple)):
                val = str(val)
            if val != '' and val is not None:
                argsList.append(f"{name}={val}")
        # Validate syntax
        fullExpr = f"exuutils.{funcName}({', '.join(argsList)})"
        try:
            ast.parse(fullExpr, mode="eval")
        except Exception as e:
            QMessageBox.warning(self, "Syntax Error", f"Invalid input:\n{e}")
            return
        self.result = {
            "name": funcName,
            "args": ', '.join(argsList)
        }
        self.accept()

    def getName(self):
        return self.combo.currentText()

    def getArgs(self):
        return self.result.get("args", "")

    def getResult(self):
        return self.result
