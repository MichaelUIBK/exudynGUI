# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: core/fieldMetadata.py
#
# Description:
#     Field utilities for Exudyn GUI auto-forms: mapping names to dependency types,
#     guessing defaults, preprocessing fields, and performing validation based on heuristics.
#
# Authors:  Michael Pieber
# Date:     2025-05-21
#
# License:  BSD-3 license
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
import json
import numpy as np
import ast
import exudyn as exu
import exudyn.utilities as exucore
import exudyn.graphics as exugraphics
import inspect
import pathlib
import os
import functools
import sys, pathlib
import importlib.util
# sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import inspect
from pathlib import Path
import sys
import re

thisFile = Path(__file__).resolve()
projectRoot = thisFile.parents[2]  # mainExudynGUI
modelPath = projectRoot / 'exudynGUI' / 'model'

if str(projectRoot) not in sys.path:
    sys.path.insert(0, str(projectRoot))

    
import exudyn.utilities as exuutils
from exudyn.utilities import __dict__ as utilDict


from exudynGUI.functions.graphicsVisualizations import graphicsDataRegistry
from exudynGUI.core.debug import debugLog
from exudynGUI.core.debug import debugLog, summarizeDict
from exudynGUI.core.specialFields import SPECIAL_FIELD_HANDLERS, getExclusiveFieldGroups
from exudynGUI.core.fieldValidation import (
    getValidator,
    getValidatorForField,
    isMeaningfulDefault,
    getDefaultForField,
    guessDefaultValue,
    tryValidateField,
)

# from exudynUtilities import debugLog
# from exudynGUI.core.fieldValidation import getValidator
from exudynGUI.core.fieldValidation import TYPE_NORMALIZATION, VALIDATORS_BY_TYPE, VALIDATORS_BY_KEY
# from exudynGUI.core.fieldMetadataTools import getDefaultsFor, getDefaultForField, inferTypeFromValue, isMeaningfulDefault, fixMatrixDefaults, importdetectRequiredFieldsWithoutJSON, guessHeuristicDefault

def normalizeMatrixFormat(value):
    """
    Comprehensive matrix format normalization.
    Handles numpy arrays, malformed matrix strings, and various matrix formats.
    """
    import numpy as np
    
    # Handle numpy arrays first
    if isinstance(value, np.ndarray):
        return value.tolist()
    
    # Handle numpy scalar types
    if isinstance(value, np.generic):
        return value.item()
    
    # Handle strings that might be malformed matrices
    if isinstance(value, str):
        v = value.strip()
        
        # Handle common malformed matrix patterns
        if v.startswith('[[') and v.endswith(']]'):
            try:
                # Fix missing commas in matrix format: [[1 2 3][4 5 6]] → [[1,2,3],[4,5,6]]
                # Pattern: number-space-number → number-comma-number
                v = re.sub(r'(?<=\d)\s+(?=\d)', ', ', v)
                # Pattern: ][  → ],[
                v = re.sub(r'\]\s*\[', '], [', v)
                # Remove extra whitespace
                v = re.sub(r'\s+', ' ', v)
                return ast.literal_eval(v)
            except Exception as e:
                debugLog(f"[normalizeMatrixFormat] ⚠️ Failed to parse matrix string '{value}': {e}")
                
        # Handle vector format: [1 2 3] → [1, 2, 3]
        elif v.startswith('[') and v.endswith(']'):
            try:
                v = re.sub(r'(?<=\d)\s+(?=\d)', ', ', v)
                return ast.literal_eval(v)
            except Exception as e:
                debugLog(f"[normalizeMatrixFormat] ⚠️ Failed to parse vector string '{value}': {e}")
    
    # Handle lists recursively
    if isinstance(value, list):
        return [normalizeMatrixFormat(item) for item in value]
    
    # Handle tuples recursively
    if isinstance(value, tuple):
        return tuple(normalizeMatrixFormat(item) for item in value)
    
    # Handle dictionaries recursively
    if isinstance(value, dict):
        return {k: normalizeMatrixFormat(v) for k, v in value.items()}
    
    # Return as-is for other types
    return value

basePath = pathlib.Path(__file__).resolve().parent.parent / "model"
fieldMetaPath = basePath / "fieldMetadataOutput.py"

try:
    debugLog("📂 Loading metadata from:", modelPath)
    
    # --- Load object metadata from JSON ---
    fieldMetaPath = modelPath / "fieldMetadataOutput.json"
    debugLog("✅ Exists?", fieldMetaPath.exists())
    
    if fieldMetaPath.exists():
        with open(fieldMetaPath, "r", encoding='utf-8') as f:
            objectFieldMetadata = json.load(f)
        debugLog(f"✅ Loaded {len(objectFieldMetadata)} object metadata entries")
    else:
        debugLog(f"⚠️ fieldMetadataOutput.json not found at {fieldMetaPath}")
        objectFieldMetadata = {}
    
    # --- Load system metadata from JSON ---
    sysMetaPath = modelPath / "systemFieldMetadataOutput.json"
    
    if sysMetaPath.exists():
        with open(sysMetaPath, "r", encoding='utf-8') as f:
            systemFieldMetadata = json.load(f)
        debugLog(f"✅ Loaded {len(systemFieldMetadata)} system metadata entries")
    else:
        debugLog(f"⚠️ systemFieldMetadataOutput.json not found at {sysMetaPath}")
        systemFieldMetadata = {}
except Exception as e:
    debugLog(f"⚠️ Fallback import failed: {e}")
    objectFieldMetadata = {}
    systemFieldMetadata = {}


    
    
    
_dummySystemContainer = exu.SystemContainer()
_dummyMbs = _dummySystemContainer.AddSystem()


def inferTypeFromValue(value):
    import exudyn as exu
    if isinstance(value, bool):
        return "bool"
     # If "val" is 6 integers, treat it as an IntVector6
    elif isinstance(value, list) and len(value) == 6 and all(isinstance(x, int) for x in value):
        return "intVector6"

     # If "val" is a 3×3 nested list/tuple→ treat it as a 3×3 matrix
    elif isinstance(value, (list, tuple)) and len(value) == 3 \
         and all(isinstance(row, (list, tuple)) and len(row) == 3 for row in value):
         return "matrix3x3"
       
    elif isinstance(value, int):
        return "int"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, list):
        if (
            len(value) == 3
            and all(isinstance(row, list) and len(row) == 3 and all(isinstance(x, (float, int)) for x in row) for row in value)
        ):
            return "matrix3x3[list]"
        elif len(value) == 3 and all(isinstance(x, (float, int)) for x in value):
            return "vector3[list]"
        return "list"
    elif isinstance(value, dict):
        return "dict"
    elif isinstance(value, np.ndarray):
        shape = value.shape
        if shape == (3,):
            return "vector3[list]"
        elif shape == (3, 3):
            return "matrix3x3[list]"
        else:
            return f"ndarray{shape}"
    elif isinstance(value, (exu.NodeIndex, exu.ObjectIndex, exu.MarkerIndex)):
        return type(value).__name__
    elif value is None:
        return "NoneType"
    else:
        return type(value).__name__

    

def guessHeuristicDefault(fieldName: str, objectType: str):
    lname = fieldName.lower()
    if fieldName.lower() == "create2d":
        return False
    # —————————— SPECIAL CASE #1 ——————————
    # ─── CreateSpringDamper: force, velocityOffset, referenceLength ───
    if objectType == "CreateSpringDamper":
        if lname == "stiffness":
            return 1.0
        if lname == "damping":
            return 0.1
        if lname == "force":
            return 0.0
        if lname == "velocityoffset":
            return 0.0
        if lname == "referencelength":
            # We want "referenceLength=None" so the system computes it automatically.
            # If you return None here, getCreateFunctionDefaults will see None and drop
            # the key entirely, exactly like "distance" in CreateDistanceConstraint.
            return None
    
    # —————————— SPECIAL CASE #2 ——————————
    # CreateCartesianSpringDamper expects a 3-element vector stiffness/damping
    if objectType == "CreateCartesianSpringDamper":
        if lname in ("stiffness", "damping"):
            # Return a 3‐element list (or numpy array) with identical components,
            # e.g. "[1.0, 1.0, 1.0]" for stiffness, "[0.1, 0.1, 0.1]" for damping
            return [1.0, 1.0, 1.0] if lname == "stiffness" else [0.1, 0.1, 0.1]
        
        
    # —————————— SPECIAL CASE #3 ——————————
    # CreateCartesianSpringDamper expects a 3-element vector stiffness/damping
    if objectType == "CreateSphericalJoint":
        if lname in "constrainedaxes":
            # Return a 3‐element list (or numpy array) with identical components,
            # e.g. "[1.0, 1.0, 1.0]" for stiffness, "[0.1, 0.1, 0.1]" for damping
            return [1, 1, 1]  
        
    # —————————— SPECIAL CASE #4 ——————————
    # CreateRigidBodySpringDamper expects a 6x6 matrix for stiffness/damping
    if objectType == "CreateRigidBodySpringDamper":
        if lname in ("stiffness", "damping"):
            # Return a 6x6 diagonal matrix with typical values
            val = 100.0 if lname == "stiffness" else 10.0
            return [[val if i == j else 0.0 for j in range(6)] for i in range(6)]
        
    # —————————— SPECIAL CASE #5 ——————————
    # CreateRigidBodySpringDamper: rotationMatrixJoint should default to np.eye(3)
    if objectType == "CreateRigidBodySpringDamper" and lname == "rotationmatrixjoint":
        import numpy as np
        return np.eye(3)
    
        # —————————— SPECIAL CASE #6 ——————————
    # CreateRigidBodySpringDamper expects a 6-element vector stiffness/damping
    if objectType == "CreateRigidBodySpringDamper":
        if lname in "offset":
            # Return a 3‐element list (or numpy array) with identical components,
            # e.g. "[1.0, 1.0, 1.0]" for stiffness, "[0.1, 0.1, 0.1]" for damping
            return [0, 0, 0, 0, 0, 0]  
    
    # Special field name heuristics
    if lname in ['bodyornodelist']:
        return [None, None]
    if lname in ['bodynumber', 'markernumber', 'nodenumber', 'objectnumber']:
        return 0
    if lname in ['bodynumbers', 'markernumbers', 'nodenumbers', 'objectnumbers']:
        return [None, None]
    if 'userfunction' in lname:
        return 0  # convention: 0 = no function
    if lname in ['referencerotationmatrix', 'referenceRotation', 'rotationmatrixaxes','initialrotationmatrix']:
        return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]    
    if lname == "constrainedaxes":
        return [1, 1, 1, 1, 1, 1]
    # ── Special case: useGlobalFrame should always be a bool ──
    if lname == "useglobalframe":
        return False
    # 1) Catch the exact scalar fields first:
    if lname == 'axislength':
        return 0.4
    if lname == 'axeslength':
        return 0.4
    if lname == 'axisradius':
        return 0.2
    if lname == 'drawsize':
        return -1.0
    if lname == 'bodyfixed':
        return 0  # treated as False in Exudyn   
    if lname == 'distance':
        return 1.0
    
    
    # Semantic-based heuristics
    if 'position' in lname or 'offset' in lname:
        return [0.0, 0.0, 0.0]
    if 'velocity' in lname:
        return [0.0, 0.0, 0.0]
    if 'displacement' in lname:
        return [0.0, 0.0, 0.0]
    if lname in ['rotationmatrix', 'massmatrix', 'stiffnessmatrix', 'dampingmatrix']:
        return [[100.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    if 'axis' in lname and lname not in ("axisradius", "axislength"):
        return [0.0, 0.0, 1.0]
    if 'color' in lname:
        return [-1.0, -1.0, -1.0, -1.0]
    if 'name' in lname:
        return ""
    if 'mass' in lname:
        return 1.0
    if 'gravity' in lname:
        return [0.0, 0.0, -9.81]
    if 'stiffness' in lname or 'damping' in lname:
        # Let the metadata infer scalar vs. vector later
        return [100.0, 100.0, 100.0]  # safe vector default
    # For plural or indexed values
    if 'numbers' in lname or 'list' in lname:
        return [None, None]
    if 'radius' in lname:
        return 0.1
    if 'index' in lname:
        return 0
    if 'store' in lname:
        return False
    # Default fallback
    return None



def cleanExclusiveFields(data: dict, objectType: str = "") -> dict:
    cleaned = dict(data)
    for group in getExclusiveFieldGroups(objectType):
        selector      = group['selector']      # expects "Connection"
        selectedField = cleaned.get(selector)  # e.g. "bodyOrNodeList"
        if selectedField in group['fields']:
            for field in group['fields']:
                if field != selectedField and field in cleaned:
                    del cleaned[field]
    return cleaned

def fixMatrixDefaults(metadata):
    """Convert string matrix defaults to list of lists."""
    for fieldName, meta in metadata.items():
        val = meta.get("defaultValue", None)
        if isinstance(val, str) and "[[" in val:
            try:
                cleaned = val.replace(" ", ",")
                parsed = ast.literal_eval(cleaned)
                if isinstance(parsed, list) and all(isinstance(row, list) for row in parsed):
                    meta["defaultValue"] = parsed
            except Exception as e:
                debugLog(f"[fieldMetadata] ⚠️ Failed to parse matrix default for {fieldName}: {e}")
    return metadata


def getInertiaConstructors():
    return {name: getattr(exuutils, name)
            for name in dir(exuutils)
            if name.startswith('Inertia') and callable(getattr(exuutils, name))}

def getDefaultArgsString(func):
    sig = inspect.signature(func)
    args = []
    for name, param in sig.parameters.items():
        if param.default != inspect.Parameter.empty:
            args.append(f"{name}={repr(param.default)}")
    return ", ".join(args)

def getDefaultInertiaEntry():
    inertiaConstructors = getInertiaConstructors()
    defaultFn = 'InertiaCuboid'
    if defaultFn not in inertiaConstructors:
        return None
    defaultArgs = getDefaultArgsString(inertiaConstructors[defaultFn])
    return {'name': defaultFn, 'args': defaultArgs}


def _convertLatexLikeToHtml(text: str) -> str:
    # 1) Replace common $x$ patterns with <i>x</i>
    text = re.sub(r"\$([A-Za-z0-9_]+)\$", r"<i>\1</i>", text)
    # 2) Convert "^2" or "_2" into <sup>2</sup> or <sub>2</sub>, etc.
    text = re.sub(r"\^(\d+)", r"<sup>\1</sup>", text)
    text = re.sub(r"_(\d+)", r"<sub>\1</sub>", text)
    # 3) Wrap in <html>
    return f"<html>{text}</html>"


class FieldMetadataBuilder:
    def __init__(self, useExtracted=True):
        self.useExtracted = useExtracted
        self.extracted = None

    
    def build(self, objectType: str) -> dict:
        """Build full metadata dictionary for a given Exudyn object type."""
        debugLog(f"[FieldMetadataBuilder] Building metadata for {objectType}")

        defaults = getDefaultsFor(objectType)

        # 🛑 Handle unsupported objects
        if isinstance(defaults, dict) and defaults.get("supported") is False:
            debugLog(f"[build] ❌ Unsupported objectType: {objectType} → {defaults.get('error')}",
                     origin="FieldMetadataBuilder.build")
            return {
                "objectType": objectType,
                "shortName": defaults.get("shortName", objectType),
                "supported": False,
                "error": defaults.get("error", "Unknown error"),
                "fields": {}
            }

        if not defaults:
            return {}

        # ─── Pull in the JSON‐exported fieldInfo, which already contains "description" keys ──
        infoDict       = self._getFieldInfo(objectType)
        requiredFields = set(importdetectRequiredFieldsWithoutJSON(objectType))

        metadata = {}
        for fieldName in defaults:
            
            dv = defaults.get(fieldName, None)
            overriddenType = None
            if fieldName.lower() == "rotationmatrixaxes":
                overriddenType = "matrix3x3"
            if fieldName.lower() == "constrainedaxes":
                if objectType == "CreateGenericJoint":
                    overriddenType = "intVector6"
                elif objectType == "CreateRevoluteJoint":
                    overriddenType = "intVector3"   
            
            # A) Grab raw JSON metadata for this field, if any
            rawFieldInfo = infoDict.get(fieldName, {})
        
            inferredType = rawFieldInfo.get("type", None)
            if overriddenType is not None:
                inferredType = overriddenType
            elif inferredType is None:
                inferredType = inferTypeFromValue(defaults.get(fieldName, None))
        
            # C) Default value
            if "default" in rawFieldInfo:
                defaultValue = rawFieldInfo["default"]
            else:
                defaultValue = defaults.get(fieldName, None)
        
            defaultStr = rawFieldInfo.get("defaultStr")
            if defaultStr is not None and isinstance(defaultStr, str):
                try:
                    defaultValue = ast.literal_eval(defaultStr)
                except:
                    defaultValue = defaultStr.strip('"')
        
            # D) Required flag
            if "required" in rawFieldInfo:
                required = rawFieldInfo["required"]
            else:
                required = fieldName in requiredFields
        
            # E) Tooltip text
            descriptionText = rawFieldInfo.get("description", "")

        
            # F) Validator lookup
            normalizedType = TYPE_NORMALIZATION.get(inferredType, inferredType)
            validator = (
                VALIDATORS_BY_KEY.get(fieldName)
                or VALIDATORS_BY_TYPE.get(normalizedType)
                or getValidator(normalizedType, fieldName, objectType)
            )
        
            # G) Copy additional flags directly
            optional       = rawFieldInfo.get("optional", False)
            readOnly       = rawFieldInfo.get("readOnly", False)
            isIndex        = rawFieldInfo.get("isIndex", False)
            isUserFunction = rawFieldInfo.get("isUserFunction", False)
            symbol         = rawFieldInfo.get("symbol", None)
            cFlags         = rawFieldInfo.get("cFlags", "")
            destination    = rawFieldInfo.get("destination", "")
            size           = rawFieldInfo.get("size", "")
        
            # H) GUI‐only override if needed
            guiOnly = False
            for specialType, handler in SPECIAL_FIELD_HANDLERS.items():
                if handler["isMatch"](fieldName):
                    inferredType = specialType
                    defaultValue = 0 if fieldName.endswith("UserFunction") else None
                    validator    = None
                    guiOnly      = True
                    break
        
            # I) Assemble the final metadata entry
            metadata[fieldName] = {
                "name":                fieldName,
                "type":                inferredType,
                "default":             defaultValue,
                "required":            required,
                "manualInputRequired": required and not isMeaningfulDefault(defaultValue, fieldName),
                "validator":           validator,
                "guiOnly":             guiOnly,
                "description":         descriptionText,
        
                # Extra raw flags (optional, readOnly, isIndex, symbol, cFlags, destination, size)
                "optional":            optional,
                "readOnly":            readOnly,
                "isIndex":             isIndex,
                "isUserFunction":      isUserFunction,
                "symbol":              symbol,
                "cFlags":              cFlags,
                "destination":         destination,
                "size":                size
            }


        # Fix any matrix‐default quirks (unchanged) 
        metadata = fixMatrixDefaults(metadata)

        # ✅ Normalize broken defaults like 'graphicsDataUserFunction = 0' → None
        for fName, meta in metadata.items():
            if fName.endswith('UserFunction') and meta.get('default') in (0, '0', '', 'None'):
                meta['default'] = None
                debugLog(f"[build] 🧼 Normalized default for '{fName}' → None",
                         origin="FieldMetadataBuilder.build")

        # ✅ Force 'show' default to True for all Create* functions
        if objectType.startswith("Create") and "show" in metadata:
            metadata["show"]["default"] = True
            debugLog(f"[build] 🛠 Forced 'show' = True for {objectType}",
                     origin="FieldMetadataBuilder.build")

        return metadata





    
    def validateFieldType(self, objectType: str, fieldName: str, expectedType: type) -> bool:
        """Use default value to validate against expected Python type."""
        val = self.getDefaults(objectType).get(fieldName, None)
        return isinstance(val, expectedType)

    def getRequiredFields(self, objectType: str) -> list:
        """Return list of required fields for a given object type."""
        if self.useExtracted:
            meta = self.build(objectType)
            return [k for k, v in meta.items() if v.get("required", False)]
        else:
            return importdetectRequiredFieldsWithoutJSON(objectType)

    def getDefaults(self, objectType: str) -> dict:
        """Return default field dictionary for an object type."""
        return getDefaultsFor(objectType)

    def getFieldInfo(self, objectType: str, fieldName: str) -> dict:
        """Return metadata dictionary for a specific field."""
        infoDict = self._getFieldInfo(objectType)
        return infoDict.get(fieldName, {})

    def getFieldType(self, objectType: str, fieldName: str) -> str:
        """Return field type from extracted metadata."""
        info = self.getFieldInfo(objectType, fieldName)
        return info.get("type", "unknown")

    def guessDefaultValue(self, fieldName: str):
        """Return heuristic default value for a field."""
        return guessDefaultValue(fieldName)

    # def tryValidateField(self, fieldName: str, value, objectType: str):
    #     """Validate value for a field using built-in logic and objectType."""
    #     return tryValidateField(fieldName, value, objectType=objectType)

    def summarizeGraphicsData(self, gd):
        """Return summary string for a GraphicsData dictionary."""
        return summarizeGraphicsData(gd)


    def _getFieldInfo(self, objectType: str) -> dict:
        debugLog(f"[_getFieldInfo] Called for objectType = {objectType}")
        debugLog(f"[_getFieldInfo] All objectFieldMetadata keys:   {list(objectFieldMetadata.keys())}")
        debugLog(f"[_getFieldInfo] All systemFieldMetadata keys:  {list(systemFieldMetadata.keys())}")
    
        key = objectType  # no prefix-stripping, because JSON uses full class names
        debugLog(f"[_getFieldInfo] Looking up key = {key}")
    
        rawList = objectFieldMetadata.get(key) or systemFieldMetadata.get(key)
        if not rawList:
            debugLog(f"[_getFieldInfo] rawList is empty for key = {key} → returning {{}}")
            return {}
    
        debugLog(f"[_getFieldInfo] Found rawList for {key}, type = {type(rawList).__name__}")
    
        if isinstance(rawList, list):
            return {
                entry["pythonName"]: entry.copy()
                for entry in rawList
                if "pythonName" in entry
            }
        elif isinstance(rawList, dict):
            return {fname: fmeta.copy() for fname, fmeta in rawList.items()}
    
        return {}






from exudyn import MainSystem



def importdetectRequiredFieldsWithoutJSON(objectType: str):
    ms = exu.MainSystem()

    # Match pattern like ObjectMassPoint, SensorMarker, etc.
    match = re.match(r"^(Object|Node|Marker|Load|Sensor)(.+)", objectType)
    if not match:
        debugLog(f"⚠️ Unrecognized objectType format: {objectType}")
        return []

    prefix, exudynType = match.groups()
    addMethod = getattr(ms, f"Add{prefix}", None)
    getDefaultsMethod = getattr(ms, f"Get{prefix}Defaults", None)

    if not addMethod or not getDefaultsMethod:
        debugLog(f"⚠️ No Add or GetDefaults method found for prefix '{prefix}'")
        return []

    # ✅ Step 1: Try creating the object with an empty dict
    try:
        addMethod(exudynType, {})  # If this works, nothing is required
        return []
    except:
        pass  # Must check field-by-field

    # Step 2: Test field-by-field by excluding each field
    try:
        defaults = getDefaultsMethod(exudynType)
    except Exception as e:
        debugLog(f"⚠️ Cannot get defaults for {objectType}: {e}")
        return []

    required = []
    for k in defaults:
        testDict = {kk: vv for kk, vv in defaults.items() if kk != k}
        try:
            addMethod(exudynType, testDict)
        except:
            required.append(k)

    return required





def getDependencyHints(requiredArgs):
    debugLog(f"🧠 Inferring dependencies from: {requiredArgs}", origin="dependencyCheck.py:getDependencyHints")
    found = {'body': 0, 'node': 0, 'marker': 0}

    for f in requiredArgs:
        fLower = f.lower()
        if fLower in ['objecttype', 'nodetype', 'markertype', 'sensortype', 'loadtype']:
            continue

        depType = mapFieldToDependencyType(f)
        if depType:
            count = 2 if 'numbers' in fLower or 'list' in fLower else 1
            found[depType] = max(found[depType], count)
            debugLog(f"  - '{f}' ➜ {depType} ({count})", origin="dependencyCheck.py:getDependencyHints")

    alternatives = []
    if 'bodyornodelist' in (f.lower() for f in requiredArgs):
        alternatives.append({'body': 2})
        alternatives.append({'node': 2})
    elif found['body'] > 0 and found['node'] > 0:
        alternatives.append({'body': found['body']})
        alternatives.append({'node': found['node']})
    else:
        single = {k: v for k, v in found.items() if v > 0}
        if single:
            alternatives.append(single)

    debugLog(f"📦 Final inferred dependencies: {alternatives}", origin="dependencyCheck.py:getDependencyHints")
    return alternatives




def hasDependencies(mbs, dependencyOptions):
    d = mbs.GetDictionary()
    available = {
        'marker': len(d.get('markerList', [])),
        'node': len(d.get('nodeList', [])),
        'body': len(d.get('objectList', [])),
    }
    debugLog(f"🔍 Checking dependencies: {dependencyOptions}", origin="dependencyCheck.py:hasDependencies")

    if not dependencyOptions:
        debugLog(f"✅ No dependencies required.", origin="dependencyCheck.py:hasDependencies")
        return True

    for option in dependencyOptions:
        satisfied = True
        for depType, requiredCount in option.items():
            actualCount = available.get(depType, 0)
            debugLog(f"  - {depType}: {actualCount} / {requiredCount} → {'OK' if actualCount >= requiredCount else 'MISSING'}", origin="dependencyCheck.py:hasDependencies")
            if actualCount < requiredCount:
                satisfied = False
                break
        if satisfied:
            debugLog(f"✅ Satisfied dependency group: {option}", origin="dependencyCheck.py:hasDependencies")
            return True

    debugLog(f"❌ No dependency groups satisfied.", origin="dependencyCheck.py:hasDependencies")
    return False




def summarizeGraphicsData(gd):
    """Return a short readable summary string for a GraphicsData dictionary."""
    try:
        if isinstance(gd, dict) and 'type' in gd:
            typename = gd['type'].replace("GraphicsData", "")
            priorityKeys = ['point', 'p0', 'p1', 'radius', 'size', 'normal', 'nTiles']
            otherKeys = [k for k in gd if k not in priorityKeys and k != 'type']
            keys = priorityKeys + otherKeys
            args = []
            for k in keys:
                if k in gd:
                    val = gd[k]
                    if isinstance(val, (float, int)):
                        valStr = f"{val:.3g}"
                    elif isinstance(val, list) and len(val) <= 6:
                        valStr = str(val)
                    elif isinstance(val, str):
                        valStr = f"'{val}'"
                    else:
                        valStr = "..."
                    args.append(f"{k}={valStr}")
            return f"{typename}({', '.join(args)})"
        return str(gd)
    except Exception as e:
        return f"<Invalid GD: {e}>"







def getDefaultsFor(objectType: str):
    ms = exu.MainSystem()

    match = re.match(r"^(Object|Node|Marker|Load|Sensor|Create)(.+)", objectType)
    if not match:
        debugLog(f"[getDefaultsFor] ⚠️ Unrecognized objectType format: {objectType}")
        return {}

    prefix, exudynType = match.groups()

    try:
        if prefix == "Object":
            return ms.GetObjectDefaults(exudynType)
        elif prefix == "Node":
            return ms.GetNodeDefaults(exudynType)
        elif prefix == "Marker":
            return ms.GetMarkerDefaults(exudynType)
        elif prefix == "Load":
            return ms.GetLoadDefaults(exudynType)
        elif prefix == "Sensor":
            return ms.GetSensorDefaults(exudynType)
        elif prefix == "Create":
            defaults, _ = getCreateFunctionDefaults(objectType)
            return defaults or {}
    except Exception as e:
        debugLog(f"[getDefaultsFor] ⚠️ Failed to get defaults for {objectType} (subtype: '{exudynType}'): {e}")
        return {}

    return {}








def getGraphicsConstructors():
    """Return list of (name, constructor) for GraphicsData functions from exudyn.utilities."""
    graphicsConstructors = []
    for name, obj in utilDict.items():
        if callable(obj) and name.startswith("GraphicsData"):
            try:
                sig = inspect.signature(obj)
                if any("color" in p.lower() for p in sig.parameters):
                    graphicsConstructors.append((name, obj))
            except Exception:
                continue
    return graphicsConstructors



def reconstructGraphicsDataList(dataDictList):
    """
    Rebuild list of graphics data entries from stored metadata.
    Returns a list of dicts: {name: str, args: str, object: dict}
    """
    gList = []
    for item in dataDictList:
        name = item.get('name', '')
        argsStr = item.get('args', '')
        try:
            func = getattr(exucore, name, None) or getattr(exu.utilities, name, None) or getattr(exugraphics, name, None)
            if not func:
                raise AttributeError(f"Function '{name}' not found in exudyn.utilities or core")

            debugLog(f"[reconstructGraphicsDataList] ⏳ Evaluating: {name}({argsStr})")
            gd = eval(f'func({argsStr})', {"np": np, "func": func})
            debugLog(f"✅ Success: {summarizeDict(gd)}", origin="reconstructGraphicsDataList")
            gList.append({"name": name, "args": argsStr, "object": gd})

        except Exception as e:
            debugLog(f"[reconstructGraphicsDataList] ❌ Failed to rebuild {name}({argsStr}): {e}")
            # Append placeholder so list length stays in sync if needed
            gList.append({"name": name, "args": argsStr, "object": None})

    return gList



# --- Dependency type inference ---
def mapFieldToDependencyType(fieldName):
    lname = fieldName.lower()
    if 'body' in lname:
        return 'body'
    if 'node' in lname:
        return 'node'
    if 'marker' in lname:
        return 'marker'
    return None






import ast
import re


def convertToType(value, metaType: str):
    """Convert string (from GUI) to actual Python type based on metadata."""
    if metaType == 'userfunction':
        return value  # keep raw name or 0

    if isinstance(value, str):
        v = value.strip()

        # None cases
        if v.lower() == "none" or v == "":
            return None

        # ✅ Use comprehensive matrix format normalization for matrix/vector types
        if any(t in metaType for t in ["vector3", "matrix3x3", "list", "ndarray", "dict"]):
            normalized = normalizeMatrixFormat(v)
            if normalized != v:  # If normalization worked, return it
                return normalized
            
            # Fallback to original regex-based approach if normalization didn't work
            # Replace number-space-number with number-comma-number
            v = re.sub(r'(?<=\d)\s+(?=\d)', ', ', v)
            v = v.replace('\n', '')  # Remove line breaks

        try:
            if metaType.startswith(("vector3", "list", "matrix3x3", "ndarray", "dict")):
                result = ast.literal_eval(v)
                # Apply final normalization to the result
                return normalizeMatrixFormat(result)
            elif metaType == "int":
                return int(v)
            elif metaType == "float":
                return float(v)
            elif metaType == "bool":
                return v.lower() in ["true", "1"]
        except Exception as e:
            debugLog(f"[convertToType] ⚠️ Failed to parse '{value}' as {metaType}: {e}")
            return value

    # ✅ Apply matrix normalization to non-string values too
    return normalizeMatrixFormat(value)






def getCreateFunctionDefaults(typeName):
    try:
        debugLog(f"\n[getCreateFunctionDefaults] 🔍 Extracting defaults for: {typeName}")

        _dummySystemContainer.__init__()         # Reset our dummy Exudyn system
        localMbs = _dummySystemContainer.AddSystem()
        method   = getattr(localMbs, typeName)
        sig      = inspect.signature(method)

        kwargs        = {}
        supportedArgs = list(sig.parameters.keys())

        # Any field‐specific overrides you already had:
        _knownFieldTypes    = {
            'bodyfixed':         'bool',
            'show':              'bool',
            'color':             'vector4[list]',
            'loadvector':        'vector3[list]',
            'localposition':     'vector3[list]',
        }
        _knownFieldDefaults = {
            'loadvector':       [0.0, 0.0, 0.0],
            'graphicsDataList': []
        }

        for name, param in sig.parameters.items():
            try:
                lname = name.lower()

                # 1) returnDict → always False in GUI (we re-add it later if needed)
                if name == 'returnDict':
                    kwargs[name] = False
                    continue

                elif name == 'inertia':
                    val = getDefaultInertiaEntry()
                    debugLog(f"[getCreateFunctionDefaults] 🧩 Inserted default inertia entry: {val}")
                    kwargs[name] = val
                    continue  # inertia is fully handled → skip remaining logic for this field

                # ✅ PRIORITY 1: Use actual param.default from inspect.signature()
                # ✅ Use 'is' comparison to avoid numpy array "ambiguous truth value" error
                if param.default is not inspect.Parameter.empty:
                    val = param.default
                    # ✅ Use comprehensive matrix format normalization
                    val = normalizeMatrixFormat(val)
                    debugLog(f"[getCreateFunctionDefaults] ✅ Using real default for '{name}': {val}")
                else:
                    # ✅ PRIORITY 2: Special handling only if no real default exists
                    val_override = getDefaultForField(name)
                    if val_override is not None:
                        val = normalizeMatrixFormat(val_override)
                        debugLog(f"[getCreateFunctionDefaults] ✅ Special default for '{name}': {val}")
                    else:
                        # ✅ PRIORITY 3: Heuristic guessing only as last resort
                        val = guessHeuristicDefault(name, typeName)
                        if val is not None:
                            val = normalizeMatrixFormat(val)
                            debugLog(f"[getCreateFunctionDefaults] 🔍 Heuristic default for '{name}': {val}")

                # 4) if still None, try your "knownFieldDefaults" table
                # ✅ Fix: Use 'is None' check that works with numpy arrays
                try:
                    if val is None:
                        val = _knownFieldDefaults.get(lname)
                        if val is not None:
                            val = normalizeMatrixFormat(val)
                            debugLog(f"[getCreateFunctionDefaults] 🧠 Patched '{name}' with knownFieldDefault → {val}")
                except Exception as e:
                    debugLog(f"[getCreateFunctionDefaults] ❌ Error in step 4 (knownFieldDefaults) for '{name}': {e}")
                    raise

                # 5) attempt annotation‐based fallback
                try:
                    expected = param.annotation
                    if val is None and expected in [int, float, bool, str]:
                        val = expected()  # e.g. float() → 0.0, int() → 0
                        debugLog(f"[getCreateFunctionDefaults] 🧪 Filled '{name}' from annotation: {val}")
                    elif expected in [list, tuple] and isinstance(val, (int, float)):
                        # e.g. scalar → [scalar, scalar, scalar]
                        val = [val, val, val]
                        debugLog(f"[getCreateFunctionDefaults] 🧩 Promoted scalar to vector3 for '{name}' → {val}")
                    elif expected is float and isinstance(val, int):
                        val = float(val)
                    elif expected is bool and isinstance(val, int):
                        val = bool(val)
                    
                    # ✅ Apply matrix normalization after annotation processing
                    val = normalizeMatrixFormat(val)
                except Exception as e:
                    debugLog(f"[getCreateFunctionDefaults] ❌ Error in step 5 (annotation fallback) for '{name}': {e}")
                    raise

                # 6) final override: enforce a few known field types
                try:
                    finalType = _knownFieldTypes.get(lname)
                    if finalType:
                        if finalType == 'bool' and isinstance(val, int):
                            val = bool(val)
                            debugLog(f"[getCreateFunctionDefaults] 🔁 Forcing '{name}' to bool → {val}")
                        elif finalType == 'vector3[list]' and isinstance(val, (int, float)):
                            val = [val, val, val]
                            debugLog(f"[getCreateFunctionDefaults] 🔁 Forcing '{name}' to vector3 → {val}")
                except Exception as e:
                    debugLog(f"[getCreateFunctionDefaults] ❌ Error in step 6 (final override) for '{name}': {e}")
                    raise

                # 8) Finally, put whatever we wound up with into kwargs
                try:
                    kwargs[name] = val
                    debugLog(f"[getCreateFunctionDefaults] ✅ Successfully stored '{name}' = {repr(val)}")
                except Exception as e:
                    debugLog(f"[getCreateFunctionDefaults] ❌ Error storing '{name}': {e}")
                    raise

            except Exception as e:
                debugLog(f"[getCreateFunctionDefaults] ❌ Exception processing parameter '{name}': {e}")
                # Continue with next parameter instead of failing completely
                continue

        # 9) If name wasn't set, give it a default
        try:
            name_val = kwargs.get('name')
            # ✅ Handle numpy arrays in name field
            if isinstance(name_val, np.ndarray):
                name_val = name_val.tolist()
                kwargs['name'] = name_val
            
            # ✅ Safe boolean check that works with arrays and None
            if name_val is None or (isinstance(name_val, str) and name_val.strip() == ''):
                kwargs['name'] = typeName
                debugLog(f"[getCreateFunctionDefaults] 🆕 Assigned default name: {kwargs['name']}")
        except Exception as e:
            debugLog(f"[getCreateFunctionDefaults] ❌ Error in step 9 (name assignment): {e}")
            # Fallback: ensure name is set
            kwargs['name'] = typeName

        # 10) Re-insert any previously saved graphicsDataList entries
        try:
            entryName = kwargs['name']
            if entryName in graphicsDataRegistry:
                entryGraphics = graphicsDataRegistry[entryName]
                rebuiltObjects = reconstructGraphicsDataList(entryGraphics)
                # Only keep the "dict form" here (so GUI can show name+args)
                metaList = []
                for idx, gdObj in enumerate(rebuiltObjects):
                    rec = entryGraphics[idx]
                    nameStr = rec.get("name", gdObj.get("type", "<Unknown>"))
                    argsStr = rec.get("args", summarizeGraphicsData(gdObj).rstrip(")"))
                    metaList.append({"name": nameStr, "args": argsStr, "object": gdObj})
                kwargs['graphicsDataList'] = metaList
                debugLog(f"[getCreateFunctionDefaults] 🧩 Restored {len(metaList)} graphicsData entries for '{entryName}'")
        except Exception as e:
            debugLog(f"[getCreateFunctionDefaults] ❌ Error in step 10 (graphics restoration): {e}")
            # Continue anyway - graphics restoration is optional

        debugLog(f"[getCreateFunctionDefaults] ✅ Completed processing for {typeName} with {len(kwargs)} fields")
        return kwargs, supportedArgs

    except Exception as e:
        debugLog(f"[getCreateFunctionDefaults] ❌ Unexpected error for {typeName}: {e}")
        # ✅ Return partial results instead of complete failure
        debugLog(f"[getCreateFunctionDefaults] 🔄 Returning partial results: {len(kwargs)} fields")
        return kwargs if kwargs else {}, supportedArgs if 'supportedArgs' in locals() else []






    
# --- Public API convenience function ---
_metadataBuilder = FieldMetadataBuilder()

def getFieldMetadataFor(fieldName: str, objectType: str = None) -> dict:
    if objectType is None:
        return {}
    meta = _metadataBuilder.build(objectType)
    return meta.get(fieldName, {})

def guessGraphicsArgDefault(argName: str) -> str:
    lname = argName.lower()
    if 'color' in lname:
        return '[0.0, 0.0, 0.0, 1.0]'
    if 'radius' in lname:
        return '0.1'
    if lname in ['p0', 'p1', 'point', 'size']:
        return '[0.0, 0.0, 0.0]'
    if 'min' in lname or 'max' in lname:
        return '0.0'
    return '0'




# import re, ast

import ast
import re

def patchDefaultFromCppString(valueStr):
    """Convert known C++ default strings to valid Python values."""

    # ✅ Fix malformed graphicsData placeholder like ["{'graphicsData': '<not requested>'}"]
    if isinstance(valueStr, list) and len(valueStr) == 1:
        single = valueStr[0]
        if isinstance(single, str) and 'graphicsData' in single and '<not requested>' in single:
            return []

    # ✅ Handle specific malformed stringified dict
    if isinstance(valueStr, str) and "'graphicsData': '<not requested>'" in valueStr:
        return []
        
    # Already usable
    if not isinstance(valueStr, str):
        # ✅ Apply matrix normalization to non-string values too
        return normalizeMatrixFormat(valueStr)

    valueStr = valueStr.strip()

    # ✅ Try parsing valid literals early (with matrix normalization)
    try:
        parsed = ast.literal_eval(valueStr)
        if isinstance(parsed, (list, dict, int, float, bool)):
            return normalizeMatrixFormat(parsed)
    except:
        pass  # fall back to manual mappings

    # ✅ Handle malformed numpy array strings like "[[1 2 3][4 5 6]]"
    if valueStr.startswith('[[') and valueStr.endswith(']]') and ',' not in valueStr:
        # Likely a malformed numpy array string
        normalized = normalizeMatrixFormat(valueStr)
        if normalized != valueStr:  # If normalization worked
            return normalized

    # 🔁 Handle EXUmath defaults
    if valueStr in ["EXUmath::unitMatrix3D", "EXUmath::unitMatrix"]:
        return [[1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0]]

    if valueStr == "EXUmath::zeroVector3D":
        return [0.0, 0.0, 0.0]

    if valueStr == "EXUmath::zeroMatrix3D":
        return [[0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0]]

    # ✅ Handle Float4(...) manually
    if valueStr.startswith("Float4("):
        try:
            matches = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", valueStr)
            return [float(x) for x in matches]
        except:
            return [-1.0, -1.0, -1.0, -1.0]

    # ✅ Handle booleans
    if valueStr.lower() == "false":
        return False
    if valueStr.lower() == "true":
        return True

    # ✅ Handle explicit empty list string
    if valueStr == "[]":
        return []

    # ✅ Apply matrix normalization to the final fallback
    return normalizeMatrixFormat(valueStr)







def transformSystemFieldMetadata(raw):
    transformed = {}

    for className, fields in raw.items():
        classDict = {}
    
        requiredFields = importdetectRequiredFieldsWithoutJSON(className) if className.startswith(('Object', 'Node', 'Marker', 'Load', 'Sensor')) else []
    
        # Create* function block
        if isinstance(fields, dict) and all(isinstance(v, (str, int, float, list, bool, type(None))) for v in fields.values()):
            for fieldName, defaultValue in fields.items():
                # ✅ Apply matrix normalization
                defaultValue = normalizeMatrixFormat(defaultValue)
                inferredType = inferTypeFromValue(defaultValue)
                validator = getValidator(inferredType, fieldName, objectType=className)
    
                classDict[fieldName] = {
                    "name": fieldName,
                    "type": inferredType,
                    "default": defaultValue,
                    "required": fieldName in requiredFields,
                    "manualInputRequired": fieldName in requiredFields and not isMeaningfulDefault(defaultValue, fieldName),
                    "validator": validator.__name__ if validator else None
                }
    
            transformed[className] = classDict
            continue  # done with this class
    
        # Standard Object/Node/... block
        for fieldName, field in fields.items():
            guiFieldName = fieldName
            # 🔁 Patch raw C++ name to GUI name
            if className.startswith("Object") and fieldName == "graphicsData":
                guiFieldName = "VgraphicsData"
        
            defaultRaw = field.get("defaultStr", field.get("default", "None"))
            patchedDefault = patchDefaultFromCppString(defaultRaw)
        
            # ✅ Step 2: Evaluate if still a string
            if isinstance(patchedDefault, str):
                try:
                    if patchedDefault.lower() in ['true', 'false']:
                        defaultValue = eval(patchedDefault.capitalize())
                    else:
                        defaultValue = eval(patchedDefault)
                except Exception:
                    defaultValue = patchedDefault
            else:
                defaultValue = patchedDefault
        
            # ✅ Apply matrix normalization
            defaultValue = normalizeMatrixFormat(defaultValue)
            inferredType = inferTypeFromValue(defaultValue)
            validator = getValidator(inferredType, guiFieldName)
        
            classDict[guiFieldName] = {
                "name": guiFieldName,
                "type": inferredType,
                "default": defaultValue,
                "required": guiFieldName in requiredFields,
                "manualInputRequired": guiFieldName in requiredFields and not isMeaningfulDefault(defaultValue, guiFieldName),
                "validator": validator.__name__ if validator else None
            }

        transformed[className] = classDict

    return transformed





def serializeDefault(val):
    """Serialize default values for JSON export, with comprehensive matrix normalization."""
    # ✅ Apply matrix normalization first
    val = normalizeMatrixFormat(val)
    
    if isinstance(val, (int, float, str, bool)) or val is None:
        return val
    elif isinstance(val, (list, tuple)):
        return [serializeDefault(v) for v in val]
    elif isinstance(val, np.ndarray):
        return val.tolist()
    elif hasattr(val, '__int__') and np.ndim(val) == 0:
        return int(val)
    elif hasattr(val, '__int__'):  # For things like ContactTypeIndex
        return int(val)
    elif hasattr(val, '__str__'):
        return str(val)
    else:
        return str(val)  # fallback




if __name__ == "__main__":
    from exudynGUI.model.objectRegistry import registry

    builder = FieldMetadataBuilder()

    # 🔁 Build full metadata using builder.build(...)
    allTransformed = {}
    for objectType in sorted(registry.keys()):
        try:
            meta = builder.build(objectType)
            allTransformed[objectType] = {
                k: {
                    "type": v["type"],
                    "defaultValue": serializeDefault(v["default"]),
                    "required": v["required"],
                    "validator": v["validator"].__name__ if v.get("validator") else None
                }
                for k, v in meta.items()
            }
        except Exception as e:
            debugLog(f"❌ Failed for {objectType}: {e}")

    # ✅ Write full metadata
    outputPath = modelPath / "exportedSystemFieldMetadata_transformed.json"
    with open(outputPath, "w") as f:
        json.dump(allTransformed, f, indent=2)

    debugLog(f"✅ Exported complete metadata to {outputPath}")


