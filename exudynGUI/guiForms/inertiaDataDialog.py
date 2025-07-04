# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/inertiaDataDialog.py
#
# Description:
#     Dialog and widget for editing 'inertia' field using visual presets.
#     Features:
#       - Uses constructor-based definitions for inertia shapes (e.g. Sphere, Cuboid)
#       - Integrates with inertiaRegistry for default options
#       - Allows adding, editing, and validating inertia metadata
#       - Returns inertia entry as {'name': ..., 'args': ...}
#
# Authors:  Michael Pieber
# Date:     2025-07-03
#
# License:  BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from exudynGUI.core.qtImports import *
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QDialogButtonBox, QWidget
import exudyn.utilities as exuutils
import numpy as np
import inspect
import exudyn.graphics as gfx
from exudynGUI.guiForms.constructorArgsDialogInertia import ConstructorArgsDialog # assumes you created this
from exudynGUI.core.debug import debugLog
from exudynGUI.functions import inertiaDefinitions as idf  # <-- add this import

# If GDTL is used, import or define it (assuming it's exudyn.graphics.GraphicsDataTriangleList)
try:
    from exudyn.graphics import GraphicsDataTriangleList as GDTL
except ImportError:
    GDTL = None  # fallback if not available

def createGraphicsEntry(callStr):
    try:
        obj = eval(f"gfx.{callStr}", {"gfx": gfx})
        if isinstance(obj, dict):
            # wrap in valid graphicsData container
            obj = GDTL(points=obj['points'], triangles=obj['triangles'])
        setattr(obj, '__guiMetadata__', {'call': callStr})
        return {'call': callStr, 'object': obj}
    except Exception as e:
        debugLog(f"[createGraphicsEntry] ❌ Failed to evaluate gfx.{callStr}: {e}", origin="InertiaDataDialog")
        return {'call': callStr, 'object': None}

    
class InertiaDataDialog(QDialog):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Inertia List")
        self.resize(600, 400)

        # Use inertiaRegistry for default options
        self.inertiaRegistry = getattr(idf, 'inertiaRegistry', {})

        self.entries = []
        for entry in (data or []):
            if isinstance(entry, dict) and 'name' in entry and 'args' in entry:
                self.entries.append(entry)
            elif isinstance(entry, str):  # fallback: try to split string
                name, args = self.splitCall(entry)
                self.entries.append({'name': name, 'args': args})

        layout = QVBoxLayout(self)

        self.listWidget = QListWidget()
        layout.addWidget(self.listWidget)

        btnLayout = QHBoxLayout()
        for text, handler in [
            ("Add", self.addEntry),
            ("Edit", self.editEntry),
            ("Remove", self.removeEntry)
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btnLayout.addWidget(btn)
        layout.addLayout(btnLayout)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

        self.refreshList()

    def refreshList(self):
        self.listWidget.clear()
        for entry in self.entries:
            if isinstance(entry, dict) and 'name' in entry and 'args' in entry:
                callStr = f"{entry['name'].removeprefix('GraphicsData')}({entry['args']})"
            else:
                callStr = str(entry)
            self.listWidget.addItem(callStr)

    def addEntry(self):
        name, args = self.promptEntry()
        if name:
            self.entries.append({'name': name, 'args': args})  # ✅ correct
            self.refreshList()

    def editEntry(self):
        row = self.listWidget.currentRow()
        if row < 0:
            return
        old = self.entries[row]
        name = old['name'].removeprefix("GraphicsData")
        args = old['args']
        newName, newArgs = self.promptEntry(name, args)
        if newName:
            self.entries[row] = {'name': f"{newName}", 'args': newArgs}  # ✅ FIXED
            self.refreshList()


    def removeEntry(self):
        row = self.listWidget.currentRow()
        if row >= 0:
            del self.entries[row]
            self.refreshList()

    def promptEntry(self, defaultName='', defaultArgs=''):
        # Use inertiaRegistry to provide default options
        if not defaultName and self.inertiaRegistry:
            # Pick the first inertia definition as default
            firstKey = next(iter(self.inertiaRegistry))
            defaultName = self.inertiaRegistry[firstKey]['name']
            defaultArgs = self.inertiaRegistry[firstKey]['args']
        dlg = ConstructorArgsDialog(defaultName, defaultArgs, parent=self)
        if dlg.exec_():
            return dlg.getName(), dlg.getArgs()
        return '', ''

    def splitCall(self, callStr):
        """Split call string into name and args"""
        if "(" not in callStr or not callStr.endswith(")"):
            return callStr, ""
        name = callStr[:callStr.index("(")]
        args = callStr[callStr.index("(")+1:-1]
        return name, args

    def getInertiaDataList(self):
        """Returns pure call strings"""
        return self.entries

    def getData(self):
        result = []
        for entry in self.entries:
            if isinstance(entry, dict) and 'name' in entry and 'args' in entry:
                result.append(entry)
            elif isinstance(entry, str):  # fallback if needed
                name, args = self.splitCall(entry)
                result.append({'name': f"{name}", 'args': args})
        debugLog(f"[InertiaDataDialog] Returning {len(result)} graphics entries", origin="InertiaDataDialog")
        return result

    def getValue(self):
        # For inertia, we only expect a single entry:
        if len(self.entries) == 1:
            return self.entries[0]
        elif len(self.entries) == 0:
            return None
        else:
            debugLog("[InertiaDataDialog] ⚠️ Multiple inertia entries found — expected only one!", origin="InertiaDataDialog")
            return self.entries[0]  # fallback: return first
    
def buildInertiaWidget(fieldName, default, meta, parent=None, structure=None):
    container = QWidget(parent)
    container.data = []  # Ensure .data always exists to avoid AttributeError
    layout = QHBoxLayout(container)
    container.setLayout(layout)

    label = QLabel("Inertia:")
    layout.addWidget(label)

    button = QPushButton("Edit...")
    layout.addWidget(button)

    # Add status/preview label
    statusLabel = QLabel()
    layout.addWidget(statusLabel)

    def updateStatus():
        if hasattr(container, 'data') and isinstance(container.data, list) and container.data:
            entry = container.data[0]
            if isinstance(entry, dict) and 'name' in entry:
                statusLabel.setText(f"<b>{entry['name']}</b>")
                statusLabel.setStyleSheet("color: green;")
            else:
                statusLabel.setText(str(entry))
                statusLabel.setStyleSheet("color: green;")
        else:
            statusLabel.setText("< required to choose inertia >")
            statusLabel.setStyleSheet("color: orange;")    # --- Prefill with existing data when editing an object ---
    if isinstance(default, dict) and 'name' in default:
        # Existing inertia data from saved object: {'name': 'InertiaSphere', 'args': 'mass=1.0, radius=0.1'}
        container.data = [dict(default)]
    elif isinstance(default, str) and default in getattr(idf, 'inertiaRegistry', {}):
        # Template from inertiaRegistry
        template = idf.inertiaRegistry[default]
        container.data = [dict(template)]
    elif isinstance(default, list) and default:
        # Already a list of inertia entries
        container.data = list(default)

    def onEdit():
        dialog = InertiaDataDialog(data=container.data, parent=parent)
        if dialog.exec_():
            container.data = dialog.getData()
            updateStatus()

    button.clicked.connect(onEdit)
    updateStatus()

    # Always return a single dict (or None) for inertia field
    container.fieldType = "inertia"
    container.getValue = lambda: container.data[0] if container.data and isinstance(container.data, list) else None
    return container