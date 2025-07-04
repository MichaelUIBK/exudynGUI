# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: model/modelData.py
#
# Description:
#     Central data container and state manager for the Exudyn GUI.
#
#     - Stores the global `modelSequence`, a list of user-defined model items.
#     - Tracks associated components: node indices, mass points, logical connections.
#     - Maintains name uniqueness and creation indices for consistent labeling.
#     - Provides utility functions to:
#         - Normalize model items into consistent internal structure
#         - Auto-generate unique names
#         - Renumber all items
#         - Track and debug `creationIndex` duplicates
#         - Rebuild or clean name caches
#
#     This module ensures a shared, consistent view of the user's model across
#     GUI components, the system builder, and code generation modules.
#
# Authors:   Michael Pieber
# Date:      2025-05-12
# License:   BSD-3 license
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import sys
from pathlib import Path

# Ensure exudynGUI root is in sys.path
thisFile = Path(__file__).resolve()
projectRoot = thisFile.parents[1]  # exudynGUI
if str(projectRoot) not in sys.path:
    sys.path.insert(0, str(projectRoot))

from exudynGUI.core.debug import debugLog
from collections import defaultdict

modelSequence = []  # List of dicts, each with {'type': ..., 'modelSequence': {...}, 'GUI': {...}}
nodeIndices = []    # Stores node indices in order of creation
massPoints = []     # Each is a dict with keys: 'mass', 'position', 'velocity'
connections = []    # Track things like 'from' node, 'to' node, type='Spring'
existingNames = set()
usedUIDs = set()


# Tracks creation indices per object type
creationIndexCounter = defaultdict(int)
_creationIndexCounter = 0

# ✅ Optional debug utility
def debugModelState():
    debugLog(f"📋 modelSequence length: {len(modelSequence)}", origin="modelData.py")
    debugLog(f"📋 nodeIndices: {nodeIndices}", origin="modelData.py")
    debugLog(f"📋 massPoints: {massPoints}", origin="modelData.py")
    debugLog(f"📋 connections: {connections}", origin="modelData.py")
    debugLog(f"📋 connections: {existingNames}", origin="modelData.py")
    
def generateUniqueName(baseName: str, existing=None) -> str:
    if existing is None:
        from .modelData import existingNames
        existing = existingNames
    
    # Convert to case-insensitive comparison
    existing_lower = {name.lower() for name in existing}
    
    # First check if the provided name is already unique (case-insensitive)
    if baseName.lower() not in existing_lower:
        return baseName
    
    # If not unique, extract the base name and find a numbered suffix
    import re
    
    # Try to extract base name and existing number
    match = re.match(r'^(.+?)(\d+)$', baseName)
    if match:
        # Input has a number, use the part before the number as base
        actual_base = match.group(1)
        existing_number = int(match.group(2))
    else:
        # Input has no number, treat whole thing as base
        actual_base = baseName
        existing_number = 0
      # Find the lowest available number starting from existing_number + 1
    index = max(1, existing_number + 1)
    while f"{actual_base}{index}".lower() in existing_lower:
        index += 1
        index += 1
    
    return f"{actual_base}{index}"

def removeName(name):
    existingNames.discard(name)
    
def rebuildExistingNames():
    existingNames.clear()
    for item in modelSequence:
        # Always normalize to new structure
        if not ('modelSequence' in item and 'GUI' in item and 'type' in item):
            from exudynGUI.core.modelManager import build_model_item
            item = build_model_item(item)
        name = item['modelSequence'].get('name')
        if name:
            existingNames.add(name)
            
def renumberAllNames():
    existingNames.clear()
    counts = {}
    for i, item in enumerate(modelSequence):
        # Always normalize to new structure
        if not ('modelSequence' in item and 'GUI' in item and 'type' in item):
            from exudynGUI.core.modelManager import build_model_item
            item = build_model_item(item)
            modelSequence[i] = item
        objType = item['type']
        base = ''.join([c for c in objType if c.isalpha()])
        counts[base] = counts.get(base, 0) + 1
        newName = f"{base}{counts[base]}"
        item['modelSequence']['name'] = newName
        existingNames.add(newName)
        
def getNextCreationIndex():
    global _creationIndexCounter
    idx = _creationIndexCounter
    _creationIndexCounter += 1
    return idx

def checkDuplicateCreationIndices(modelSequence):
    seen = set()
    for item in modelSequence:
        idx = item.get('creationIndex')
        if idx in seen:
            debugLog(f"❌ Duplicate creationIndex found: {idx}")
        else:
            seen.add(idx)
    debugLog("✅ Checked all creation indices.")
    
def checkDuplicateCreationIndices(modelSequence):
    seen = set()
    for item in modelSequence:
        idx = item.get('creationIndex')
        if idx in seen:
            debugLog(f"❌ Duplicate creationIndex found: {idx}")
        else:
            seen.add(idx)
    debugLog("✅ Checked all creation indices.")

def normalize_model_sequence():
    """Ensure all items in modelSequence are normalized to the new structure and flatten double-wrapped items. Also, strictly remove any GUI/meta fields from modelSequence and move them to GUI. Ensure required builder fields like 'name' and 'show' are present in modelSequence (not GUI)."""
    from exudynGUI.core.modelManager import build_model_item
    global modelSequence
    for i, item in enumerate(modelSequence):
        # Flatten double-wrapped items
        while (
            isinstance(item, dict)
            and 'modelSequence' in item and isinstance(item['modelSequence'], dict)
            and ('modelSequence' in item['modelSequence'] or 'type' in item['modelSequence'])
        ):
            # If the inner 'modelSequence' looks like a model item, flatten
            if all(k in item['modelSequence'] for k in ('modelSequence', 'GUI', 'type')):
                item = item['modelSequence']
            elif 'modelSequence' in item['modelSequence']:
                item = item['modelSequence']
            else:
                break
        # If not normalized, build it
        if not (isinstance(item, dict) and 'modelSequence' in item and 'GUI' in item and 'type' in item):
            item = build_model_item(item)
        # --- Strictly remove any GUI/meta fields from modelSequence ---
        ms = item['modelSequence']
        gui = item['GUI']
        # Remove any nested GUI/meta fields from modelSequence
        for meta in GUIrequiredFields + ['GUI', 'creationIndex']:
            if meta in ms:
                # Move to GUI if not already present, except for 'show' (which should stay in modelSequence)
                if meta != 'GUI' and meta != 'show' and meta not in gui and meta in ms:
                    gui[meta] = ms[meta]
                # Remove from modelSequence unless it's 'show'
                if meta != 'show':
                    del ms[meta]
        # Remove any nested GUI dicts
        if 'GUI' in ms:
            del ms['GUI']
        # Remove any nested creationIndex
        if 'creationIndex' in ms:
            gui['creationIndex'] = ms['creationIndex']
            del ms['creationIndex']
        # --- Ensure required builder fields like 'name' and 'show' are present in modelSequence ---
        if 'name' not in ms:
            # Try to get from GUI or top-level item
            if 'name' in gui:
                ms['name'] = gui['name']
            elif 'name' in item:
                ms['name'] = item['name']
        if 'show' not in ms:
            # Try to get from GUI or top-level item
            if 'show' in gui:
                ms['show'] = gui['show']
                del gui['show']
            elif 'show' in item:
                ms['show'] = item['show']
        # Ensure only builder kwargs remain in modelSequence
        item['modelSequence'] = ms
        item['GUI'] = gui
        modelSequence[i] = item

GUIrequiredFields = [
    'codePreview', 'returnValues', 'objIndex', 'returnInfo', 'toCode',
    'creationUID', 'show', 'objectType', 'type', 'objectNumber', 'name',
    'creationIndex', 'GUI', 'misc', 'fullModelData', 'createdItems',
    'graphicsDataString', 'returnDict', 'VgraphicsDataList',
    # Add any other GUI/meta fields as needed
]