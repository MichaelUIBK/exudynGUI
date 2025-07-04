# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/flexibleBodyDialog.py
#
# Description:
#     Dialog for defining parameters of a flexible body (FEM/FFRF) to be used
#     in the Exudyn model. Parameters include geometry, material properties,
#     and FEM mesh resolution.
#
#     Features:
#       - Input fields for width/height, length, mesh size, density, Young’s modulus, etc.
#       - Spin boxes with validation for physical units and practical limits
#       - Modal dialog returns all parameters as a dictionary via get_params()
#
# Authors:  Michael Pieber
# Date:     2025-07-03
#
# License:  BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from core.qtImports import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDoubleSpinBox, QSpinBox
from PyQt5.QtWidgets import QMessageBox

class FlexibleBodyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Flexible Body (FEM/FFRF)")
        self.setMinimumWidth(350)
        layout = QVBoxLayout(self)

        # Parameter fields
        self.param_fields = {}
        params = [
            ("a (width/height)", 0.025),
            ("L (length)", 1.0),
            ("h (maxh mesh)", 0.0125),
            ("nModes", 8),
            ("rho (density)", 1000),
            ("Emodulus", 1e8),
            ("nu (Poisson)", 0.3),
            ("meshOrder", 1),
        ]
        for label, default in params:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            if isinstance(default, int):
                field = QSpinBox()
                field.setValue(default)
                if label == "meshOrder":
                    field.setMinimum(1)
                    field.setMaximum(2)
                else:
                    field.setMinimum(1)
                    field.setMaximum(100)
            else:
                field = QDoubleSpinBox()
                field.setDecimals(5)
                field.setValue(default)
                field.setMinimum(0.0)
                field.setMaximum(1e6)
            row.addWidget(field)
            layout.addLayout(row)
            self.param_fields[label] = field

        # OK/Cancel buttons
        btns = QHBoxLayout()
        self.okBtn = QPushButton("Create Flexible Body")
        self.cancelBtn = QPushButton("Cancel")
        btns.addWidget(self.okBtn)
        btns.addWidget(self.cancelBtn)
        layout.addLayout(btns)

        self.okBtn.clicked.connect(self.accept)
        self.cancelBtn.clicked.connect(self.reject)

    def get_params(self):
        return {
            'a': self.param_fields["a (width/height)"].value(),
            'L': self.param_fields["L (length)"].value(),
            'h': self.param_fields["h (maxh mesh)"].value(),
            'nModes': self.param_fields["nModes"].value(),
            'rho': self.param_fields["rho (density)"].value(),
            'Emodulus': self.param_fields["Emodulus"].value(),
            'nu': self.param_fields["nu (Poisson)"].value(),
            'meshOrder': self.param_fields["meshOrder"].value(),
        }
