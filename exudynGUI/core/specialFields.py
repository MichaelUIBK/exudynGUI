# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: core/specialFields.py
#
# Description:
#     This module provides centralized logic for handling special fields in 
#     Exudyn GUI forms. It includes dispatching, custom widget generation, 
#     validation, and resolution for fields such as inertia, user functions,
#     graphics data, and more.
#
#     The SPECIAL_FIELD_HANDLERS dictionary maps field patterns to their
#     corresponding GUI widget builders and validators. This system supports
#     dynamic form generation and modular extensibility.
#
#     Also includes fallback detection for mutually exclusive field groups
#     (e.g., bodyNumbers vs bodyList) and custom highlightable model selectors.
#
# Authors:  Michael Pieber
# Date:     2025-07-03
#
# License:  BSD 3-Clause License
#
# Notes:
#     - Avoids hardcoding field logic in form builders.
#     - All field-specific GUI logic should be routed through this dispatch layer.
#     - To add new field types, extend SPECIAL_FIELD_HANDLERS accordingly.
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Import debug system
try:
    from .debug import debugInfo, debugWarning, debugError, debugTrace, debugField, DebugCategory
except ImportError:
    # Fallback if debug module not available
    def debugInfo(msg, origin=None, category=None):
        pass
    def debugWarning(msg, origin=None, category=None):
        pass
    def debugError(msg, origin=None, category=None):
        pass
    def debugTrace(msg, origin=None, category=None):
        pass
    def debugField(msg, origin=None, level=None):
        pass
    class DebugCategory:
        FIELD = "FIELD"

# core/graphicsUtils.py

import exudyn as exu
import exudyn.utilities as exuutils
import numpy as np

# Import debug system - use module-level import for better reliability
import core.debug as debug

# Legacy compatibility - map old debugLog calls to new system
def debugLog(msg, origin=None, level=None, category=None, summarize=False, **kwargs):
    """Legacy debugLog function - maps to new debug system"""
    if not debug.isDebugEnabled():
        return
        
    if "⚠️" in msg or "Error" in msg or "Failed" in msg:
        debug.debugWarning(msg, origin=origin or "specialFields", category=category or debug.DebugCategory.FIELD)
    elif "✅" in msg or "Successfully" in msg:
        debug.debugInfo(msg, origin=origin or "specialFields", category=category or debug.DebugCategory.FIELD)
    else:
        debug.debugTrace(msg, origin=origin or "specialFields", category=category or debug.DebugCategory.FIELD)
    """Legacy debugLog function - maps to new debug system"""
    # Only output if debug is enabled
    if not debug.isDebugEnabled():
        return
    
    if "⚠️" in msg or "Error" in msg or "Failed" in msg:
        debug.debugWarning(msg, origin=origin, category=debug.DebugCategory.FIELD)
    else:
        debug.debugTrace(msg, origin=origin, category=debug.DebugCategory.FIELD)
from exudynGUI.core.qtImports import *
from exudynGUI.guiForms.specialWidgets import MultiComponentSelectorWidget
from exudynGUI.guiForms.inertiaDataDialog import buildInertiaWidget
from exudynGUI.guiForms.specialWidgets import (
    buildGraphicsEditorWidget as buildGraphicsDataWidget,
    buildUserFunctionWidget,
    buildIndexSelectorWidget,
    buildMultiIndexSelectorWidget,
    buildVec3Widget,
    buildMatrix3x3Widget,
    MultiComponentSelectorWidget,
    buildBodyNumberWidget,
    buildNodeNumberWidget,
    buildMarkerNumberWidget,
    buildBoolWidget,
    buildSensorNumberWidget,
    buildLoadNumberWidget,
    buildBodyPairSelectorWidget,
    buildMarkerPairSelectorWidget,
    buildMultiComponentSelectorWidget,
    EnhancedInt3Widget,   
    buildInt3Widget, 
    buildInt6Widget,     
    buildBodyOrNodeListWidget,
    buildBodyListWidget,
    buildPairSelectorWidget,
    buildVec6Widget,
    buildColorWidget,
    buildOutputVariableTypeWidget,
    buildConfigurationTypeWidget,
    buildSmartOutputTypeWidget,
    buildFileNameWidget,
)
# exudynGUI/core/specialFields.py
from exudynGUI.core.fieldValidation import (
    validateNodeNumber,
    validateBodyNumber,
    validateMarkerNumber,
    validateSensorNumber,
    validateLoadNumber,
    validateMatrix3x3,
    validateBool,
    validateList,
    validateGraphicsData,
    validateIndex,
    validateListOfInts,    validateGraphicsDataList,
    validateDistance,
)


# Debug import handled at module level
import exudyn.utilities as exuutils
import numpy as np



# External references
try:
    import exudynGUI.functions.userFunctions as userFunctions
except ImportError:
    userFunctions = None


# =============================================================================
# 🎨 Common Fields
# =============================================================================
def isNodeNumberField(fieldName: str) -> bool:
    return fieldName.lower() in ('nodenumber', 'nodenumbers')

def isBodyNumberField(fieldName: str) -> bool:
    return fieldName.lower() in ('bodynumber', 'bodynumbers')

# def isMarkerNumberField(fieldName: str) -> bool:
#     result = fieldName.lower() in ('markernumber', 'markernumbers')
#     debugLog(f"[isMarkerNumberField] fieldName='{fieldName}' → {result}")
#     return result



# =============================================================================
# 🎨 GraphicsDataList
# =============================================================================

def isGraphicsDataField(fieldName: str) -> bool:
    lname = fieldName.lower()
    result = lname == 'graphicsdatalist'
    debugLog(f"[isGraphicsDataField] fieldName='{fieldName}' → {result}")
    return result

# def validateGraphicsDataList(gList):
#     return True, ""  # GUI-only, always valid


# =============================================================================
# 👤 UserFunction
# =============================================================================

def isUserFunctionField(fieldName: str) -> bool:
    return fieldName.lower().endswith('userfunction')

def validateUserFunction(key, value):
    return True, ""  # GUI-only, always valid

def resolveUserFunction(funcName):
    if isinstance(funcName, str) and funcName.startswith("UF"):
        try:
            # 🔧 FIX: Import the module and get the function directly
            import exudynGUI.functions.userFunctions as userFunctions
            if hasattr(userFunctions, funcName):
                func = getattr(userFunctions, funcName)
                debugLog(f"[resolveUserFunction] ✅ Successfully resolved '{funcName}' → {func}", origin="resolveUserFunction")
                return func
            else:
                debugLog(f"[resolveUserFunction] ❌ Function '{funcName}' not found in userFunctions module", origin="resolveUserFunction")
                return 0
        except Exception as e:
            debugLog(f"[resolveUserFunction] ❌ Could not resolve user function '{funcName}': {e}", origin="resolveUserFunction")
            return 0  # fallback for Exudyn
    return funcName if callable(funcName) else 0



# =============================================================================
# 🧊 Inertia
# =============================================================================
def validateInertia(key, entry):
    """
    key:      the field name (e.g. "inertia")
    entry:    the value the user entered (should be a dict with {"name":…, "args":…})
    """
    if entry is None:
        #  → Accept "None" as a valid inertia
        return True, ""
    try:
        obj = resolveInertiaEntry(entry)
        isValid = isinstance(obj, exuutils.RigidBodyInertia)
        return isValid, "" if isValid else f"Invalid inertia object returned for {entry}"
    except Exception as e:
        return False, str(e)
    
def isInertiaField(fieldName: str) -> bool:
    return fieldName.lower() == 'inertia'

def getAvailableInertiaConstructors():
    return {
        name: getattr(exuutils, name)
        for name in dir(exuutils)
        if name.startswith("Inertia") and callable(getattr(exuutils, name))
    }

def resolveInertiaEntry(entry):
    if entry is None:
        return None
    name = entry.get("name")
    args = entry.get("args", "")
    
    # Clean up args string: remove None parameters
    if args:
        # Split args and filter out None values
        args_parts = []
        for part in args.split(','):
            part = part.strip()
            if part and not part.endswith('=None') and not part.endswith('= None'):
                args_parts.append(part)
        args = ', '.join(args_parts)
    
    try:
        constructor = getattr(exuutils, name, None)
        if constructor is None:
            raise ValueError(f"Constructor '{name}' not found")
        return eval(f"constructor({args})", {"constructor": constructor, "np": np})
    except Exception as e:
        return f"<Invalid inertia: {e}"

def resolveInertiaEntry(entry):
    if not entry or "name" not in entry:
        return "<Invalid inertia>"
    name = entry["name"]
    args = entry.get("args", "")
    return f"{name}({args})"






def buildModelElementSelectorWidget(
    fieldName, value=None, parent=None, meta=None, default=None, structure=None, elementType="body", **kwargs
):
    from PyQt5.QtWidgets import QWidget, QHBoxLayout, QComboBox, QPushButton
    container = QWidget(parent)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    combo = QComboBox()
    combo.setEditable(True)

    # Determine which list to use
    key_map = {
        "body": "objects",
        "object": "objects",
        "marker": "markers",
        "load": "loads",
        "sensor": "sensors",
        "node": "nodes",
    }
    struct_key = key_map.get(elementType, elementType + "s")
    items = structure.get(struct_key, []) if structure else []

    # For objects/bodies, skip Ground if needed
    filtered_items = []
    for item in items:
        if elementType in ("body", "object"):
            if str(item.get("data", {}).get("objectType", ""))[:6] == "Ground":
                continue
        filtered_items.append(item)

    # Add items to combo
    addedIndices = set()
    for item in filtered_items:
        idx = item.get("index", None)
        label = item.get("label", f"{elementType.capitalize()}_{idx}")
        display = f"{idx} - {label}"
        combo.addItem(display, userData=idx)
        addedIndices.add(idx)

    # Handle default selection
    defaultIndex = None
    if isinstance(default, int):
        defaultIndex = default
    elif isinstance(default, str):
        try:
            defaultIndex = int(default.split()[0])
        except Exception:
            pass

    if defaultIndex is not None and defaultIndex not in addedIndices:
        combo.addItem(f"{defaultIndex} - (unknown)", userData=defaultIndex)
    if defaultIndex is not None:
        idx = combo.findData(defaultIndex)
        if idx != -1:
            combo.setCurrentIndex(idx)

    layout.addWidget(combo)

    # Highlight button
    highlightBtn = QPushButton("Highlight")
    highlightBtn.setToolTip(f"Highlight selected {elementType} in the OpenGL window")
    highlightBtn.setMaximumWidth(80)
    highlightBtn.setCheckable(True)
    layout.addWidget(highlightBtn)

    # Highlight logic
    def do_highlight():
        selected_index = combo.currentData()
        from guiForms.specialWidgets import setupRendererHighlighting
        setupRendererHighlighting(parent, selected_index, elementType)

    def clear_highlight():
        from guiForms.specialWidgets import setupRendererHighlighting
        setupRendererHighlighting(parent, None, elementType)

    def on_combo_changed():
        if highlightBtn.isChecked():
            do_highlight()

    def on_highlight_toggled(checked):
        if checked:
            do_highlight()
            combo.currentIndexChanged.connect(on_combo_changed)
        else:
            try:
                combo.currentIndexChanged.disconnect(on_combo_changed)
            except Exception:
                pass
            clear_highlight()

    highlightBtn.toggled.connect(on_highlight_toggled)

    container.combo = combo
    container.fieldType = f"{elementType}Number"
    container.getValue = lambda: combo.currentData()
    container.highlightBtn = highlightBtn
    container._clear_highlight = clear_highlight
    return container
# =============================================================================
# 🧠 Special Field Dispatch System
# =============================================================================

# Each handler defines how to match and optionally validate a field
SPECIAL_FIELD_HANDLERS = {
    # "distance": {
    #     "isMatch":   lambda key, typeHint=None: key.lower() == "distance",
    #     "buildWidget": lambda fieldName, default, meta, parent=None, structure=None: (
    #         QLineEdit("" if default is None else str(default))
    #     ),
    #     "validate":  validateDistance
    # },
    "graphicsDataList": {
        "isMatch": lambda key, typeHint=None: isGraphicsDataField(key),
        "validate": validateGraphicsDataList,
        "resolve": lambda x: x,
        "fieldType": "graphicsDataList",
        "buildWidget": buildGraphicsDataWidget
    },
    "VgraphicsData": {
        "isMatch": lambda key, typeHint=None: key == "VgraphicsData",
        "validate": validateGraphicsData,
        "resolve": lambda x: x,  # or a real resolver if needed
        "fieldType": "graphicsDataList",  # optional, could be reused from 'graphicsDataList'
        "buildWidget": buildGraphicsDataWidget  # optional: could use same widget as graphicsDataList
    },
    "userFunction": {
        "isMatch": lambda key, typeHint=None: isUserFunctionField(key),
        "validate": validateUserFunction,
        "resolve": resolveUserFunction,
        "fieldType": "userFunction",
        "buildWidget": buildUserFunctionWidget
    },
    "inertia": {
        "isMatch": lambda key, typeHint=None: key.lower() == "inertia",
        "validate": lambda k, v: (
            isinstance(v, dict) and "name" in v and "args" in v,
            "Expected dict with keys 'name' and 'args'"
        ),
        "resolve": resolveInertiaEntry,
        "fieldType": "inertia",
        "buildWidget": buildInertiaWidget
    },


    "bodyNumber": {
        "isMatch": lambda key, typeHint=None: key.lower() == "bodynumber",
        "buildWidget": lambda *args, **kwargs: buildModelElementSelectorWidget(*args, elementType="body", **kwargs),
        "validate": validateBodyNumber,
    },
    "markerNumber": {
        "isMatch": lambda key, typeHint=None: key.lower() == "markernumber",
        "buildWidget": lambda *args, **kwargs: buildModelElementSelectorWidget(*args, elementType="marker", **kwargs),
        "validate": validateMarkerNumber,
    },
    "objectNumber": {
        "isMatch": lambda key, typeHint=None: key.lower() == "objectnumber",
        "buildWidget": lambda *args, **kwargs: buildModelElementSelectorWidget(*args, elementType="object", **kwargs),
        "validate": validateIndex,
    },
    "sensorNumber": {
        "isMatch": lambda key, typeHint=None: key.lower() == "sensornumber",
        "buildWidget": lambda *args, **kwargs: buildModelElementSelectorWidget(*args, elementType="sensor", **kwargs),
        "validate": validateSensorNumber,
    },
    "loadNumber": {
        "isMatch": lambda key, typeHint=None: key.lower() == "loadnumber",
        "buildWidget": lambda *args, **kwargs: buildModelElementSelectorWidget(*args, elementType="load", **kwargs),
        "validate": validateLoadNumber,
    },
    
    
    
    "markerNumbers": {
        "isMatch": lambda key, typeHint=None: key.lower() == "markernumbers",
        "buildWidget": lambda fieldName, default, meta, parent=None, structure=None:
            buildPairSelectorWidget(fieldName, default, meta, parent, structure, "Marker"),
        "validate": lambda key, val: (
            isinstance(val, list) and len(val) == 2 and all(isinstance(x, int) for x in val),
            f"'{key}' must be a list of 2 integers"
        ),
    },
    "nodeNumbers": {
        "isMatch": lambda key, typeHint=None: key.lower() == "nodenumbers",
        "buildWidget": lambda name, default, meta, parent=None, structure=None:
            buildPairSelectorWidget(name, default, meta, parent, structure, "Node"),
        "validate": lambda key, val: (
            isinstance(val, list) and len(val) == 2 and all(isinstance(x, int) for x in val),
            f"'{key}' must be a list of 2 integers"
        ),
    },
    "objectNumbers": {
        "isMatch": lambda key, typeHint=None: key.lower() == "objectnumbers",
        "buildWidget": lambda name, default, meta, parent=None, structure=None:
            buildMultiComponentSelectorWidget(name, default, meta, parent, structure, group="object"),
        "validate": validateListOfInts,
    },  
    "sensorNumbers": {
        "isMatch": lambda key, typeHint=None: key.lower() == "sensornumbers",
        "buildWidget": lambda name, default, meta, parent=None, structure=None:
            buildMultiComponentSelectorWidget(name, default, meta, parent, structure, group="sensor"),
        "validate": validateListOfInts,
    },
    "loadNumbers": {
        "isMatch": lambda key, typeHint=None: key.lower() == "loadnumbers",
        "buildWidget": lambda name, default, meta, parent=None, structure=None:
            buildMultiComponentSelectorWidget(name, default, meta, parent, structure, group="load"),
        "validate": validateListOfInts,
    },
    "vector": {
        "isMatch": lambda key, typeHint=None: (
            isinstance(typeHint, str)
            and "vector" in typeHint.lower()
            and "3" in typeHint.lower()
            and "int" not in typeHint.lower()
        ),
        "buildWidget": buildVec3Widget,
        "validate": lambda key, val: (
            isinstance(val, list) and len(val) == 3,
            "Expected 3-element float vector"
        ),
    },
    "intvector3": {    
        "isMatch": lambda key, typeHint=None: (
            (isinstance(typeHint, str) and typeHint.lower() == "intvector3")
        ),     
        "buildWidget": buildInt3Widget,
        "validate": lambda key, val: (
            isinstance(val, list) and len(val) == 3 and all(isinstance(x, int) for x in val),
            f"'{key}' must be a 3-element list of ints"
        ),
    },
    
     "intvector6": {
        "isMatch": lambda key, typeHint=None: (
            key.lower() == "constrainedaxes"
            or (isinstance(typeHint, str) and typeHint.lower() == "intvector6")
        ),
        "buildWidget": lambda fieldName, default, meta, parent=None, structure=None: (
            # Patch: if SphericalJoint, use buildInt3Widget and [1,1,1]
            buildInt3Widget(fieldName, default=[1,1,1], meta=meta, parent=parent, structure=structure)
            if (
                hasattr(parent, 'objectType') and (
                    'sphericaljoint' in getattr(parent, 'objectType', '').lower() or
                    'createsphericaljoint' in getattr(parent, 'objectType', '').lower() or
                    'objectjointspherical' in getattr(parent, 'objectType', '').lower()
                )
            ) else buildInt6Widget(fieldName, default=default, meta=meta, parent=parent, structure=structure)
        ),
        "validate": lambda key, val: (
            (isinstance(val, list) and (len(val) == 6 or len(val) == 3) and all(isinstance(x, int) for x in val)),
            f"'{key}' must be a 6-element or 3-element list of ints"
        ),
     },    
    
    "matrix": {
        "isMatch": lambda key, typeHint=None: (
            isinstance(typeHint, str) and "matrix3x3" in typeHint.lower()
        ),
        "buildWidget": buildMatrix3x3Widget,
        "validate": validateMatrix3x3,
    },    "bool": {
        "isMatch": lambda key, typeHint=None: (str(typeHint).lower() == "bool") or key.lower() == "show",
        "buildWidget": buildBoolWidget,
        "validate": validateBool  # ✅ don't wrap it
    },
    "color": {
        "isMatch": lambda key, typeHint=None: (
            key.lower() == "color" or 
            key.lower() == "vcolor" or
            "color" in key.lower() and ("rgba" in str(typeHint).lower() or "vector" in str(typeHint).lower())
        ),
        "buildWidget": buildColorWidget,
        "validate": lambda key, val: (
            isinstance(val, list) and len(val) >= 3 and len(val) <= 4 and all(isinstance(x, (int, float)) for x in val),
            f"'{key}' must be a 3 or 4-element list of numbers (RGB or RGBA)"
        ),
    },
}

# Alias VgraphicsData to same handler as graphicsDataList
SPECIAL_FIELD_HANDLERS["VgraphicsData"] = {
    "isMatch": lambda name, typeHint=None: name.lower() == "vgraphicsdata",
    "validate": lambda key, val: (True, ""),  # ✅ skip strict validation for legacy
    "resolve": lambda val: val,               # passthrough
    "buildWidget": buildGraphicsDataWidget,
    "fieldType": "graphicsDataList"
}

SPECIAL_FIELD_HANDLERS["bodyNumbers"] = {
    "isMatch": lambda key, typeHint=None: key.lower() == "bodynumbers",
    "buildWidget": buildBodyPairSelectorWidget,
    "validate": lambda key, val: (
        True, ""   # first, if it's exactly [None,None], accept it:
    ) if val == [None, None] else (  # otherwise, run the old 2-int check
        isinstance(val, list) and len(val) == 2 and all(isinstance(x, int) for x in val),
        f"'{key}' must be a list of 2 integers"
    ),
}


SPECIAL_FIELD_HANDLERS["bodyOrNodeList"] = {
    "isMatch": lambda key, typeHint=None: key.lower() == "bodyornodelist",
    "buildWidget": buildBodyOrNodeListWidget,
    "validate": lambda key, val: (
        isinstance(val, list) and all(
            isinstance(x, tuple) and len(x) == 2 and x[0] in ("body", "node") and isinstance(x[1], int)
            for x in val
        ),
        f"'{key}' must be a list of ('body' or 'node', idx) tuples"
    ),
}

SPECIAL_FIELD_HANDLERS["bodyList"] = {
    "isMatch": lambda key, typeHint=None: key.lower() == "bodylist",
    "buildWidget": buildBodyListWidget,
    "validate": validateListOfInts,
}
    
SPECIAL_FIELD_HANDLERS["outputVariableType"] = {
    "isMatch": lambda key, typeHint=None: key.lower() in ("outputvariabletype", "outputtype"),
    "buildWidget": buildOutputVariableTypeWidget,
    "validate": lambda key, val: (True, ""),  # Accept string values
    "resolve": lambda val: val,
    "fieldType": "outputVariableType"
}

SPECIAL_FIELD_HANDLERS["configurationType"] = {
    "isMatch": lambda key, typeHint=None: key.lower() in ("configurationtype", "configtype"),
    "buildWidget": buildConfigurationTypeWidget,
    "validate": lambda key, val: (True, ""),  # Accept string values
    "resolve": lambda val: val,
    "fieldType": "configurationType"
}

SPECIAL_FIELD_HANDLERS["smartOutputType"] = {
    "isMatch": lambda key, typeHint=None: key.lower() in ("smartoutputtype", "sensoroutput"),
    "buildWidget": buildSmartOutputTypeWidget,
    "validate": lambda key, val: (True, ""),  # Accept dict values
    "resolve": lambda val: val,
    "fieldType": "smartOutputType"
}

SPECIAL_FIELD_HANDLERS["fileName"] = {
    "isMatch": lambda key, typeHint=None: key.lower() == "filename",
    "buildWidget": lambda fieldName, default, meta, parent=None, structure=None: buildFileNameWidget(fieldName, default, meta, parent, structure),
    "validate": lambda key, val: (True, "") if val is None or isinstance(val, str) else (False, f"Expected string or None for {key}"),
    "resolve": lambda val: "" if val is None else val,
    "fieldType": "fileName"
}

# Generic fallback patterns to auto-detect exclusive field groups
# (used if no per-class override is defined)
DEFAULT_EXCLUSIVE_FIELD_PATTERNS = [
    {
        'groupName': 'Connection',
        'options':   ['bodyNumbers', 'bodyOrNodeList', 'bodyList']
    }
]

# We remove any per-class overrides here, since our generic rule covers them all.
MUTUALLY_EXCLUSIVE_FIELD_GROUPS = {
    # no entries needed for Create… classes if you want them all to be handled generically
}


def detectExclusiveFieldGroups(fieldNames):
    """
    Look at the flat list of fieldNames.  If more than one of
    'bodyNumbers', 'bodyOrNodeList', 'bodyList' appear, then
    we return a single group with label='Connection'.
    Otherwise, return an empty list (no grouping).
    """
    result = []
    fields = set(fieldNames or [])
    for group in DEFAULT_EXCLUSIVE_FIELD_PATTERNS:
        included = [opt for opt in group['options'] if opt in fields]
        if len(included) > 1:
            # Only one label ("Connection") but the actual options list is whatever
            # subset of those three fields appeared:
            result.append({
                'label':   group['groupName'],  # "Connection"
                'options': included,            # e.g. ["bodyNumbers", "bodyList"]
                'default': included[0]          # e.g. "bodyNumbers"
            })
    return result


def getExclusiveFieldGroups(objectType, fieldNames=None):
    # 1) check if there is a class-specific override (probably none for Create… classes)
    if objectType in MUTUALLY_EXCLUSIVE_FIELD_GROUPS:
        return MUTUALLY_EXCLUSIVE_FIELD_GROUPS[objectType]

    # 2) for any Create… class, auto-collapse these three into one "Connection" combo
    if objectType.startswith("Create") and isinstance(fieldNames, (list, tuple)):
        opts = [f for f in ("bodyNumbers", "bodyOrNodeList", "bodyList") if f in fieldNames]
        if len(opts) > 1:
            return [{
                "selector": "Connection",   # key under which the user's choice is stored
                "label":    "Connection",   # the UI text above the combo-box
                "options":  opts,          # <-- this is what AutoGeneratedForm tries to read
                "fields":   opts,          # <-- this is what cleanExclusiveFields expects
                "default":  opts[0]
            }]

    # 3) fallback: try any other generic patterns you configured
    return detectExclusiveFieldGroups(fieldNames)





def dispatchSpecialFieldBuilder(fieldName, typeHint=None, default=None, parent=None, structure=None, objectType=None):
    debugTrace(f"dispatchSpecialFieldBuilder called with fieldName={fieldName!r}, typeHint={typeHint!r}", origin="dispatchSpecialFieldBuilder", category=DebugCategory.FIELD)
    # Treat both offset and velocityOffset for CreateRigidBodySpringDamper specifically
    if objectType == "CreateRigidBodySpringDamper" and fieldName in ("offset", "velocityOffset") and typeHint and ("vector" in str(typeHint).lower()):
        if "vector3" in str(typeHint).lower():
            val = default if isinstance(default, list) else [0]*3
            debugLog(f"[DBG] Using buildVec3Widget for {objectType}.{fieldName} (typeHint: {typeHint})")
            return buildVec3Widget(fieldName, value=val, parent=parent)
        elif "vector6" in str(typeHint).lower():
            val = default if isinstance(default, list) else [0]*6
            debugLog(f"[DBG] Using buildVec6Widget for {objectType}.{fieldName} (typeHint: {typeHint})")
            return buildVec6Widget(fieldName, value=val, parent=parent)

    # --- UserFunction fields: always use buildUserFunctionWidget ---
    if "userfunction" in fieldName.lower():
        from guiForms.specialWidgets import buildUserFunctionWidget
        debugLog(f"[dispatchSpecialFieldBuilder] 🔍 UserFunction field '{fieldName}' with default={default} (type: {type(default)})")
        return buildUserFunctionWidget(fieldName, value=default, parent=parent, meta=None, default=default)

    debugLog(f"[DBG]   SPECIAL_FIELD_HANDLERS keys: {list(SPECIAL_FIELD_HANDLERS.keys())}")
    for handlerKey, handler in SPECIAL_FIELD_HANDLERS.items():
        if handler["isMatch"](fieldName, typeHint):
            debugLog(f"[DBG]   matched handlerKey={handlerKey!r} for fieldName={fieldName!r}")
            meta = { "type": typeHint, "label": fieldName }
            return handler["buildWidget"](
                fieldName=fieldName,
                default=default,
                meta=meta,
                parent=parent,
                structure=structure
            )
    return None



def handleSpecialField(fieldName):
    for key, handler in SPECIAL_FIELD_HANDLERS.items():
        if handler['isMatch'](fieldName):
            return {
                "field": fieldName,
                "handler": key,
                "resolved": None,
                "valid": True,
                "message": "(Handled in GUI)"
            }
    return None

# # Import output discovery utilities
# try:
#     from .outputDiscovery import (
#         get_all_output_variable_types, 
#         get_all_configuration_types,
#         enhance_sensor_form_with_outputs
#     )
# except ImportError:
#     try:
#         from outputDiscovery import (
#             get_all_output_variable_types, 
#             get_all_configuration_types,
#             enhance_sensor_form_with_outputs
#         )
#     except ImportError:
#         # Fallback functions if outputDiscovery not available
#         def get_all_output_variable_types():
#             return ['Position', 'Velocity', 'Displacement', 'Force']
#         def get_all_configuration_types():
#             return ['Current', 'Initial', 'Reference']
#         def enhance_sensor_form_with_outputs(mbs, sensor_type, entity):
#             return {'supported_outputs': [], 'recommendations': []}
