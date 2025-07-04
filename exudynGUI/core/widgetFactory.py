# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: core/widgetFactory.py
#
# Description:
#     handles special-case fields like inertia, graphics, and user functions
#
# Authors:  Michael Pieber
# Date:     2025-05-12
#
# License:  BSD-3 license
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
from exudynGUI.core.qtImports import *

def buildIndexSelectorWidget(fieldName, default, meta, structure, parent=None):
    itemType = inferDependencyTypeFromField(fieldName)
    container = QComboBox()
    items = structure.get(itemType + "s", [])  # e.g., 'nodes', 'objects', ...
    for item in items:
        label = f"[{itemType} {item['index']}] {item.get('name', '')}"
        container.addItem(label, item['index'])
    container.setCurrentIndex(container.findData(default))
    container.fieldType = f"{itemType}Index"
    return container


def inferDependencyTypeFromField(fieldName):
    lname = fieldName.lower()
    if "node" in lname:
        return "node"
    if "object" in lname or "body" in lname:
        return "object"
    if "marker" in lname:
        return "marker"
    if "sensor" in lname:
        return "sensor"
    if "load" in lname:
        return "load"
    return "unknown"

