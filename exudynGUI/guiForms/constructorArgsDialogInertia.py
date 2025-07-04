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
from PyQt5.QtWidgets import QWidget, QFormLayout, QLineEdit, QLabel, QMessageBox, QDialog, QVBoxLayout, QComboBox, QDialogButtonBox

import exudyn.utilities as exuutils
import inspect
import ast
        
class ConstructorArgsDialog(QDialog):
    def __init__(self, constructorName="", argsString="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Inertia Constructor")
        self.resize(500, 300)

        self.result = {"name": constructorName, "args": argsString}

        layout = QVBoxLayout(self)

        # Dropdown for constructor
        self.combo = QComboBox()
        self.constructors = [k for k in dir(exuutils) if callable(getattr(exuutils, k)) and k.startswith("Inertia")]
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
                field = QLineEdit(str(val))
                self.argsLayout.addRow(QLabel(name), field)
                self.argFields[name] = field
        except Exception as e:
            self.argsLayout.addRow(QLabel("Error"), QLabel(str(e)))

    def accepted(self):
        funcName = self.combo.currentText()
        argsList = []
        for name, field in self.argFields.items():
            val = field.text().strip()
            if val != '':
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
