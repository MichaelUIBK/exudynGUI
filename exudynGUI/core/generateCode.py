# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: core/generateCode.py
#
# Description:
#     Generates symbolic Python code from the current model state (modelSequence).
#     Handles object creation via mbs.Create* and mbs.Add* functions, assigns symbolic
#     variable names, reconstructs parameters, and preserves return values for reuse.
#
#     Also maps return values to symbolic names (e.g., b0_bodyNumber), supporting
#     readable and reusable output for code export and reproducibility.
#
# Authors:  Michael Pieber
# Date:     2025-05-16
# Notes:    
#     - Converts numpy arrays, user functions, and graphicsData into code form.
#     - Supports both Create* and legacy        # Reference variable generation
#     - Integrates with symbolic reference tracking for consistent variable reuse.
#
# License:  BSD-3 license
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



import inspect
import exudyn as exu
import numpy as np
import re
import sys
try:
    from exudynGUI.core.debug import debugInfo, debugWarning, debugError, debugTrace, debugCodeGen, DebugCategory
except ImportError:
    try:
        from .debug import debugInfo, debugWarning, debugError, debugTrace, debugCodeGen, DebugCategory
    except ImportError:
        # Fallback: create no-op debug functions
        def debugInfo(msg, origin=None, category=None):
            pass
        def debugWarning(msg, origin=None, category=None):
            pass
        def debugError(msg, origin=None, category=None):
            pass
        def debugTrace(msg, origin=None, category=None):
            pass
        def debugCodeGen(msg, origin=None, level=None):
            pass
        class DebugCategory:
            CODEGEN = "CODEGEN"

# Import debug system - use module-level import for better reliability
import exudynGUI.core.debug as debug

# Legacy compatibility function for existing debugLog calls
def debugLog(msg, origin=None, level=None, category=None, **kwargs):
    """Legacy debugLog function - maps to new debug system"""
    # Only output if debug is enabled
    if not debug.isDebugEnabled():
        return
        
    if "⚠️" in msg or "Error" in msg or "Failed" in msg:
        debug.debugWarning(msg, origin=origin or "generateCode", category=category or debug.DebugCategory.CODEGEN)
    elif "✅" in msg or "Successfully" in msg:
        debug.debugInfo(msg, origin=origin or "generateCode", category=category or debug.DebugCategory.CODEGEN)
    elif "DEBUG" in msg or "🔧" in msg:
        debug.debugTrace(msg, origin=origin or "generateCode", category=category or debug.DebugCategory.CODEGEN)
    else:
        debug.debugCodeGen(msg, origin=origin or "generateCode")
try:
    from exudynGUI.core.fieldMetadata import FieldMetadataBuilder
except ImportError:
    try:
        from exudynGUI.core.fieldMetadata import FieldMetadataBuilder
    except ImportError:
        # Fallback: create a no-op FieldMetadataBuilder class
        class FieldMetadataBuilder:
            def getFieldInfo(self, objectType, fieldName):
                return {}
            def build(self):
                return {}
import numpy as np # Ensure numpy is imported for eval contexts
import exudyn.graphics as graphics # Ensure graphics is imported for eval contexts

# Sanity check: always use fresh set
codeLines = []
definedSymbols = set()

def convertNumpyToListSafe(data):
    import numpy as np
    if isinstance(data, np.ndarray):
        return data.tolist()
    if isinstance(data, dict):
        return {k: convertNumpyToListSafe(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convertNumpyToListSafe(v) for v in data]
    return data


def getValidParams(func):
    try:
        return set(inspect.signature(func).parameters.keys())
    except Exception:
        return set()
    
    
def get_type_prefix(obj_type):
    """Extract the type prefix from an object type name (Create* or legacy)."""
    # Handle legacy types directly
    if obj_type in ['Point', 'Point2D', 'PointGround', 'NodePoint', 'NodePoint2D', 'NodePointGround']:
        return 'Node'
    elif obj_type.startswith('ObjectMass') or obj_type == 'ObjectGround' or obj_type == 'ObjectRigidBody':
        return 'Object'
    elif obj_type.startswith('ObjectConnector') or obj_type.startswith('ObjectJoint') or obj_type.startswith('ObjectSpringDamper'):
        return 'Object'  # Connectors, joints, and springs are all Object types
    elif obj_type.startswith('MarkerBody') or obj_type.startswith('MarkerNode') or obj_type == 'MarkerNodeCoordinate':
        return 'Marker'
    elif obj_type.startswith('LoadForce') or obj_type.startswith('LoadTorque'):
        return 'Load'
    elif obj_type.startswith('Sensor'):
        return 'Sensor'
    
    # Then try standard prefix detection
    for prefix in ['Object', 'Node', 'Marker', 'Sensor', 'Load']:
        if obj_type.startswith(prefix):
            return prefix
    
    debugWarning(f"Could not determine prefix for {obj_type}", origin="getTypePrefix", category=DebugCategory.CODEGEN)
    return None

def enforceReturnDictTrue(argStrs):
    # strip any existing returnDict=… and always append returnDict=True
    return [a for a in argStrs if not a.strip().startswith('returnDict=')] + ['    returnDict=True']

def generateExudynCodeFromItems(itemList, mbs, sortByIndex=True, globalIndexMap=None, fullScript=False):
    import re
    import os
    
    # Preprocess items to handle compact graphics format
    items = preprocessItemsForCodeGeneration(itemList)
    
    codeLines = []
    indexMap = {}
    definedSymbols = set()
    usesGraphics = False
    typeCounter = {'g': 0, 'b': 0, 'm': 0, 'l': 0, 's': 0, 'n': 0}
    
    # For debugging
    debugInfo("Generating code for items:", origin="generateExudynCode", category=DebugCategory.CODEGEN)
    for idx, item in enumerate(itemList):
        data = item.get('data', item)
        obj_type = data.get('objectType', '')
        name = data.get('name', f'item{idx}')
        debugTrace(f"Item {idx}: {obj_type} '{name}'", origin="generateExudynCode", category=DebugCategory.CODEGEN)
    
    # 🎯 BUILD EXACT INDEX MAPPING FIRST
    exact_mappings = buildExactIndexMapping(itemList)
    
    prefixMap   = {
        'Object': 'b',
        'Node': 'n',
        'Marker': 'm',
        'Load': 'l',
        'Sensor': 's',
    }
    items = sorted(itemList, key=lambda x: x.get('creationIndex', 0)) if sortByIndex else itemList
    
    # Initialize metadata builder for symbolic reference resolution
    try:
        metadataBuilder = FieldMetadataBuilder()
        # Don't call build() here - we'll call it per objectType as needed
    except Exception as e:
        debugError(f"Failed to initialize metadata builder: {e}", origin="generateExudynCode", category=DebugCategory.CODEGEN)
        metadataBuilder = None

    def shouldResolveSymbolically(objectType, fieldName):
        """Check if a field should undergo symbolic reference resolution based on metadata."""
        if not metadataBuilder:
            # Fallback to pattern-based detection if metadata not available
            return fieldName.lower().endswith(("number", "numbers"))
        
        try:
            # For Create* functions, check the transformed metadata directly
            if objectType.startswith("Create"):
                import json
                from pathlib import Path
                try:
                    model_path = Path(__file__).parent.parent / "model"
                    transformed_path = model_path / "exportedSystemFieldMetadata_transformed.json"
                    if transformed_path.exists():
                        with open(transformed_path, "r", encoding='utf-8') as f:
                            transformed_metadata = json.load(f)
                        
                        if objectType in transformed_metadata:
                            field_info = transformed_metadata[objectType].get(fieldName, {})
                            field_type = field_info.get('type', '')
                            
                            # Check if field type indicates it should be resolved symbolically
                            if field_type in ['bodyNumbers', 'nodeNumbers', 'markerNumbers', 'loadNumbers', 'sensorNumbers', 
                                             'bodyNumber', 'nodeNumber', 'markerNumber', 'loadNumber', 'sensorNumber', 'objectNumber']:
                                debugTrace(f"{objectType}.{fieldName}: type={field_type} (index type)", origin="shouldResolveSymbolically", category=DebugCategory.CODEGEN)
                                return True
                            else:
                                debugLog(f"[shouldResolveSymbolically] {objectType}.{fieldName}: type={field_type} (not an index field)")
                                return False
                except Exception as e:
                    debugLog(f"[shouldResolveSymbolically] Error accessing transformed metadata: {e}")
            
            # For legacy objects, use the original metadata
            fieldInfo = metadataBuilder.getFieldInfo(objectType, fieldName)
            
            # Check if metadata has isIndex flag
            isIndex = fieldInfo.get('isIndex', False)
            if isIndex:
                debugLog(f"[shouldResolveSymbolically] {objectType}.{fieldName}: isIndex={isIndex}")
                return True
                
            # Check if field type indicates it should be resolved symbolically
            field_type = fieldInfo.get('type', '')
            if field_type in ['bodyNumbers', 'nodeNumbers', 'markerNumbers', 'loadNumbers', 'sensorNumbers', 
                             'bodyNumber', 'nodeNumber', 'markerNumber', 'loadNumber', 'sensorNumber', 'objectNumber']:
                debugLog(f"[shouldResolveSymbolically] {objectType}.{fieldName}: type={field_type} (index type)")
                return True
                
            # If metadata is missing or incomplete, use pattern-based fallback
            if not fieldInfo or (not field_type and not isIndex):
                pattern_match = fieldName.lower().endswith(("number", "numbers"))
                debugLog(f"[shouldResolveSymbolically] {objectType}.{fieldName}: metadata incomplete, using pattern fallback: {pattern_match}")
                return pattern_match
                
            debugLog(f"[shouldResolveSymbolically] {objectType}.{fieldName}: type={field_type}, isIndex={isIndex} (not an index field)")
            return False
            
        except Exception as e:
            debugLog(f"[shouldResolveSymbolically] Error checking {objectType}.{fieldName}: {e}")
            # Fallback to pattern-based detection
            return fieldName.lower().endswith(("number", "numbers"))

    def getSuffixForField(fieldName, createdObjectType=None):
        """Determine the correct suffix for symbolic references based on field name and object type."""
        fieldLower = fieldName.lower()
        
        # Handle specific field name patterns first
        if fieldLower.endswith("bodynumber") or fieldLower.endswith("bodynumbers"):
            return "bodyNumber"
        elif fieldLower.endswith("nodenumber") or fieldLower.endswith("nodenumbers"):
            return "nodeNumber"
        elif fieldLower.endswith("markernumber") or fieldLower.endswith("markernumbers"):
            return "markerNumber"
        elif fieldLower.endswith("sensornumber") or fieldLower.endswith("sensornumbers"):
            return "sensorNumber"
        elif fieldLower.endswith("loadnumber") or fieldLower.endswith("loadnumbers"):
            return "loadNumber"
        elif "object" in fieldLower:
            return "objectNumber"
        
        # For generic cases, determine based on the type of object being created
        if createdObjectType:
            createdTypeLower = createdObjectType.lower()
            # Bodies have bodyNumber
            if any(body_type in createdTypeLower for body_type in ['masspoint', 'rigidbody', 'ground', 'flexiblebody']):
                return "bodyNumber"
            # Nodes have nodeNumber  
            elif 'node' in createdTypeLower:
                return "nodeNumber"
            # Markers have markerNumber
            elif 'marker' in createdTypeLower:
                return "markerNumber"
            # Sensors have sensorNumber
            elif 'sensor' in createdTypeLower:
                return "sensorNumber"
            # Loads have loadNumber
            elif 'load' in createdTypeLower:
                return "loadNumber"
            # Everything else (connectors, constraints, etc.) has objectNumber
            else:
                return "objectNumber"
        
        return "objectNumber"  # fallback

    # 🔧 Force returnDict=True on all Create* calls,
    #      even in single‐item previews
    for itm in items:
        # data may be in itm['data'] or itm directly if legacy
        data = itm.get('data', itm)
        if data.get('objectType', '').startswith("Create"):
            # override any user‐provided value
            data['returnDict'] = True

    symbolMap = globalIndexMap if globalIndexMap else indexMap

    # --- Always emit minimal deduplicated imports and system initialization at the very top ---
    baseHeader = [
        'import exudyn as exu',
        'from exudyn import SystemContainer',
        'import numpy as np',
        'from exudyn.utilities import *',
        '',
        'SC = SystemContainer()',
        'mbs = SC.AddSystem()',
        '',
    ]
    
    # Check if graphics import is needed
    usesGraphics = False
    usesLegacy = False
    
    for item in items:
        data = item['data'] if 'data' in item and isinstance(item['data'], dict) else item
        if 'graphicsDataList' in data and data['graphicsDataList']:
            usesGraphics = True
        
        # Check if this is a legacy item (not Create*)
        objType = data.get('objectType', '') or item.get('type', '')
        if not objType.startswith("Create"):
            usesLegacy = True
    
    # Add graphics import if needed
    if usesGraphics:
        if 'import exudyn.graphics as graphics' not in baseHeader:
            baseHeader.insert(3, 'import exudyn.graphics as graphics')
    
    # Add legacy imports if needed
    if usesLegacy:
        # Add imports for legacy constructors and visualization classes
        legacy_imports = [
            'from exudyn import *',  # Import all Exudyn classes including Point, MassPoint, etc.
        ]
        for imp in legacy_imports:
            if imp not in baseHeader:
                baseHeader.insert(-2, imp)  # Insert before the empty line

    # === User Variables ===
    try:
        with open('exudynGUI/functions/userVariables.py', 'r') as f:
            user_vars_text = f.read()
        baseHeader.append('# === User Variables ===')
        baseHeader.extend(user_vars_text.splitlines())
        baseHeader.append('')  # Blank line after user variables
        user_var_names = set()
        for line in user_vars_text.splitlines():
            if '=' in line:
                var = line.split('=')[0].strip()
                if var:
                    user_var_names.add(var)
    except Exception as e:
        baseHeader.append('# (Could not load userVariables.py: ' + str(e) + ')')
        baseHeader.append('')
        user_var_names = set()

    # --- Collect user variables and user functions before generating codeLines output ---
    userVariables = []
    userFunctionNames = set()
    userFunctionFieldToName = {}  # Map: (item idx, field) -> UF name
    
    # --- Collect all user function names used in items ---
    for idx, item in enumerate(items):
        data = item.get('data', item)
        for k, v in data.items():
            if k.lower().endswith('userfunction'):
                funcName = None
                if isinstance(v, str) and v.startswith('UF'):
                    # String function name like 'UFload'
                    funcName = v
                elif callable(v) and hasattr(v, '__name__') and v.__name__.startswith('UF'):
                    # Function object like <function UFload at 0x...>
                    funcName = v.__name__
                
                if funcName:
                    userFunctionNames.add(funcName)
                    userFunctionFieldToName[(idx, k)] = funcName
    
    # --- Extract user function definitions ---
    userFunctionDefinitions = []
    if userFunctionNames:
        try:
            import exudynGUI.functions.userFunctions as userFunctions
            
            for funcName in sorted(userFunctionNames):
                if hasattr(userFunctions, funcName):
                    func = getattr(userFunctions, funcName)
                    if callable(func):
                        # Get the source code of the function
                        try:
                            source = inspect.getsource(func)
                            # Clean up the source (remove extra indentation)
                            lines = source.split('\n')
                            if lines and lines[0].strip().startswith('def'):
                                userFunctionDefinitions.append(source.strip())
                            debugLog(f"[generateCode] ✅ Extracted user function: {funcName}")
                        except Exception as e:
                            debugLog(f"[generateCode] ⚠️ Could not extract source for {funcName}: {e}")
                            # Fallback: create a stub
                            userFunctionDefinitions.append(f"def {funcName}():\n    # Could not extract function definition\n    pass")
        except Exception as e:
            debugLog(f"[generateCode] ⚠️ Could not import userFunctions: {e}")
    
    guiDictLookup = []
    try:
        import sys
        MainWindow = sys.modules.get('exudynGUI.guiForms.mainWindow', None)
        if MainWindow and hasattr(MainWindow, 'MainWindow'):
            guiDictLookup = getattr(MainWindow.MainWindow, 'lastModelTreeDict', [])
    except Exception:
        pass

    # ── Force returnDict=True on all Create* calls up front ─────────────────────────
    for itm in items:
        d = itm.get('data', itm)
        if d.get('objectType', "").startswith("Create"):
            d['returnDict'] = True

    # ── Single unified pass over items ────────────────────────────────────────────
    for idx, item in enumerate(items):
        data    = item.get('data', item)
        objType = data.get('objectType')
        if not objType:
            continue        # 🔍 DEBUG: debugLog original return values before any processing
        original_return_values = item.get('returnValues', 'MISSING')
        debugLog(f"🔍 [DEBUG] Item {idx} ({objType}) original returnValues: {original_return_values}")
        
        # 🔍 DEBUGGING: Track Force object specifically
        if idx == 2:  # Force object in our test
            debugLog(f"🔍 [DEBUG] FORCE INITIAL - item id: {id(item)}")
            debugLog(f"🔍 [DEBUG] FORCE INITIAL - returnValues id: {id(item.get('returnValues', {}))}")
        # Always force dict return
        data['returnDict'] = True

        # 🔧 PRESERVE: Keep actual return values exactly as returned by Exudyn
        # No "corrections" needed - trust what the API returns

        # Preview override - only for actual preview cases, not for individual item display
        # When generating code for a single item (like when clicking in the tree), 
        # we want the full code, not just the preview
        if not fullScript and item.get('summaryPythonCode') and len(items) > 1:
            # Only use preview mode when generating multiple items, not for single item display
            # … emit citem preview call …
            # unpack every returnValue
            for field in data.get('returnValues', {}):
                if field == 'creationUID':
                    continue
                codeLines.append(f"citem{idx}_{field} = citem{idx}['{field}']")
            indexMap[data.get('objIndex', idx)] = f"citem{idx}"
            continue
        # ── 2) Create* branch: full call + unpack every returnValue ────────────────
        if objType.startswith("Create"):
            name       = data.get("name", f"item{idx}")
            baseName   = f"c{name}"
            # Handle duplicate names
            if baseName in definedSymbols:
                match = re.match(r'^(.+?)(\d+)$', name)
                if match:
                    base_part = match.group(1)
                    start_num = int(match.group(2))
                    suffix_num = start_num + 1
                else:
                    base_part = name
                    suffix_num = 1
                while f"c{base_part}{suffix_num}" in definedSymbols:
                    suffix_num += 1
                unique_name = f"{base_part}{suffix_num}"
                baseName = f"c{unique_name}"
            else:
                unique_name = name
            definedSymbols.add(baseName)
            createFunc = getattr(mbs, objType)
            validArgs  = set(inspect.signature(createFunc).parameters)
            argStrs = []
            has_return_dict = data.get('returnDict', False)
            for k, v in data.items():
                if k in {"objectType", "objIndex", "returnValues", "returnInfo", "connections", "creationUID", "creationIndex", "GUI", "summaryPythonCode", "isLegacy", "name"}:
                    continue
                if k == "markerType" and not objType.lower().startswith('createmarker'):
                    continue
                if k not in validArgs:
                    continue
                if k == "graphicsDataList" and isinstance(v, list):
                    formatted = []
                    for e in v:
                        if isinstance(e, dict) and 'name' in e and 'args' in e:
                            formatted.append(f"graphics.{e['name']}({e['args']})")
                        elif isinstance(e, str):
                            if e.startswith('exu.graphics.'):
                                graphics_call = e.replace('exu.graphics.', 'graphics.')
                            elif e.startswith('graphics.'):
                                graphics_call = e
                            else:
                                graphics_call = f"graphics.{e}"
                            formatted.append(graphics_call)
                        else:
                            formatted.append(repr(e))
                    argStrs.append(f"    {k}=[{', '.join(formatted)}]")
                elif k.lower().endswith("userfunction") and isinstance(v, str):
                    argStrs.append(f"    {k}={v}")
                elif k == 'returnDict':
                    if k in validArgs:
                        argStrs.append(f"    {k}={repr(v)}")
                    has_return_dict = bool(v)
                # --- CRITICAL PATCH: Always use indexMap for all reference fields (including lists) ---
                elif shouldResolveSymbolically(objType, k) and (k.lower().endswith('number') or k.lower().endswith('numbers')):
                    # Handle both single and list reference fields
                    if isinstance(v, list):
                        entries = []
                        for x in v:
                            x_val = int(x) if isinstance(x, str) and x.isdigit() else x
                            # Get the desired suffix for this field type
                            desired_suffix = getSuffixForField(k, objType)
                            # 🎯 USE EXACT MAPPING: Look up the precise object for this index and return value type
                            exact_symbol = exact_mappings.get(desired_suffix, {}).get(x_val)
                            if exact_symbol:
                                # Check if the symbol already has the desired suffix to avoid double suffixes
                                if '_' in exact_symbol and exact_symbol.endswith(f"_{desired_suffix}"):
                                    symbol = exact_symbol  # Already has the suffix
                                else:
                                    symbol = f"{exact_symbol}_{desired_suffix}"  # Add suffix
                                debugLog(f"✅ [EXACT MAPPING] Resolved {k}[{x}] → {symbol} (using exact mapping)")
                                entries.append(symbol)
                            else:
                                # Fallback: try to find any object with this index
                                fallback_symbol = None
                                fallback_found = False
                                
                                # Check all mapping types for this index
                                for return_type, mapping in exact_mappings.items():
                                    if x_val in mapping:
                                        fallback_symbol = f"{mapping[x_val]}_{return_type}"
                                        debugLog(f"⚠️  [EXACT MAPPING] {k}[{x}] not found for {desired_suffix}, using fallback: {fallback_symbol}")
                                        entries.append(fallback_symbol)
                                        fallback_found = True
                                        break
                                
                                if not fallback_found:
                                    # Ultimate fallback: use raw index
                                    debugLog(f"❌ [EXACT MAPPING] No mapping found for {k}[{x}], using raw index")
                                    entries.append(str(x))
                        listStr = "[" + ", ".join(entries) + "]"
                        argStrs.append(f"    {k}={listStr}")
                    else:
                        x_val = int(v) if isinstance(v, str) and v.isdigit() else v
                        # Get the desired suffix for this field type
                        desired_suffix = getSuffixForField(k, objType)
                        # 🎯 USE EXACT MAPPING: Look up the precise object for this index and return value type
                        exact_symbol = exact_mappings.get(desired_suffix, {}).get(x_val)
                        if exact_symbol:
                            # Check if the symbol already has the desired suffix to avoid double suffixes
                            if '_' in exact_symbol and exact_symbol.endswith(f"_{desired_suffix}"):
                                symbol = exact_symbol  # Already has the suffix
                            else:
                                symbol = f"{exact_symbol}_{desired_suffix}"  # Add suffix
                            debugLog(f"✅ [EXACT MAPPING] Resolved {k}={v} → {symbol} (using exact mapping)")
                            argStrs.append(f"    {k}={symbol}")
                        else:
                            # Fallback: try to find any object with this index
                            fallback_symbol = None
                            fallback_found = False
                            
                            # Check all mapping types for this index
                            for return_type, mapping in exact_mappings.items():
                                if x_val in mapping:
                                    fallback_symbol = f"{mapping[x_val]}_{return_type}"
                                    debugLog(f"⚠️  [EXACT MAPPING] {k}={v} not found for {desired_suffix}, using fallback: {fallback_symbol}")
                                    argStrs.append(f"    {k}={fallback_symbol}")
                                    fallback_found = True
                                    break
                            
                            if not fallback_found:
                                # Ultimate fallback: use raw index
                                debugLog(f"❌ [EXACT MAPPING] No mapping found for {k}={v}, using raw index")
                                argStrs.append(f"    {k}={v}")
                else:
                    # All other cases
                    if callable(v) and hasattr(v, '__name__') and k.lower().endswith('userfunction'):
                        argStrs.append(f"    {k}={v.__name__}")
                    elif isinstance(v, dict) and k.lower() == 'inertia' and 'name' in v and 'args' in v:
                        inertia_name = v['name']
                        inertia_args = v['args']
                        argStrs.append(f"    {k}=exu.utilities.{inertia_name}({inertia_args})")
                    elif k.lower() == 'nodetype' and hasattr(v, 'name'):
                        argStrs.append(f"    {k}=exu.NodeType.{v.name}")
                    elif k.lower() == 'nodetype' and isinstance(v, str):
                        if v.startswith('exu.NodeType.'):
                            argStrs.append(f"    {k}={v}")
                        elif v.startswith('NodeType.'):
                            enum_name = v.replace('NodeType.', '')
                            argStrs.append(f"    {k}=exu.NodeType.{enum_name}")
                        else:
                            nodetype_mapping = {
                                'RigidBodyEP': 'RotationEulerParameters',
                                'RigidBodyRxyz': 'RotationRxyz',
                                'RigidBodyRotVecLG': 'RotationRotationVector',
                                'Point': 'Point',
                                'Point2D': 'Point2D'
                            }
                            enum_name = nodetype_mapping.get(v, v)
                            argStrs.append(f"    {k}=exu.NodeType.{enum_name}")
                    elif (isinstance(v, list) and 
                          k.lower() in ['referencerotationmatrix', 'initialrotationmatrix', 'rotationmatrix', 'rotationmatrixaxes'] and
                          len(v) == 3 and all(isinstance(row, list) and len(row) == 3 for row in v)):
                        argStrs.append(f"    {k}=np.array({repr(v)})")
                    elif hasattr(v, '__class__') and 'numpy.ndarray' in str(type(v)):
                        array_as_list = v.tolist()
                        argStrs.append(f"    {k}=np.array({repr(array_as_list)})")
                    else:
                        argStrs.append(f"    {k}={repr(v)}")
            codeLines.append(
                f"{baseName} = mbs.{objType}(\n" +
                ",\n".join(argStrs) +
                "\n)"
            )
            # --- CRITICAL: Map all return values to variable names for correct reference resolution ---
            return_values = item.get('returnValues', data.get('returnValues', {}))
            if isinstance(return_values, dict):
                for return_type, return_index in return_values.items():
                    if isinstance(return_index, str) and return_index.isdigit():
                        return_index = int(return_index)
                    if isinstance(return_index, int):
                        # Update indexMap and exact_mappings for all return types
                        indexMap[return_index] = f"{baseName}_{return_type}"
                        if return_type in exact_mappings:
                            exact_mappings[return_type][return_index] = f"{baseName}_{return_type}"
                        debugLog(f"🔢 [CREATE] indexMap[{return_index}] = {baseName}_{return_type}")
            else:
                # Fallback: use objIndex for single return values
                objIndex = data.get("objIndex", idx)
                indexMap[objIndex] = baseName
                debugLog(f"🔢 [CREATE] indexMap[{objIndex}] = {baseName} (fallback)")
            
            # Handle return value unpacking based on whether returnDict was used
            debugLog(f"🔍 [DEBUG] Return value unpacking: objType={objType}")
            
            # Get return values - prioritize item.returnValues over data.returnValues
            # item.returnValues contains the actual Exudyn return values
            return_values = item.get('returnValues', data.get('returnValues', {}))
            debugLog(f"🔍 [DEBUG] Return values to unpack: {return_values}")
            
            # 🔧 Filter out non-Exudyn metadata fields from return value counting
            # creationUID is GUI metadata, not an actual Exudyn return value
            if isinstance(return_values, dict):
                exudyn_return_values = {k: v for k, v in return_values.items() if k != 'creationUID'}
            else:
                # If return_values is not a dict (e.g., single integer), keep it as-is
                exudyn_return_values = return_values
            debugLog(f"🔍 [DEBUG] Exudyn return values (excluding metadata): {exudyn_return_values}")
            
            # 🔧 MAJOR FIX: Handle both dictionary and single value returns
            # Dictionary return: unpack based on returnDict flag and number of keys
            # Single value return: simple assignment
            
            # Special handling for CreateGround to ensure it always has assignments
            objTypeLower = objType.lower()
            if objTypeLower.startswith('createground'):
                # Always ensure CreateGround has both assignments regardless of dict structure
                codeLines.append(f"{baseName}_objectNumber = {baseName}")
                codeLines.append(f"{baseName}_bodyNumber = {baseName}")
                debugLog(f"🔍 [DEBUG] Forced ground assignments: {baseName}_objectNumber = {baseName}, {baseName}_bodyNumber = {baseName}")
            elif isinstance(exudyn_return_values, dict):
                # Dictionary return values
                if len(exudyn_return_values) == 1:
                    # Single return value in dict - always use simple assignment
                    actual_key = list(exudyn_return_values.keys())[0]
                    codeLines.append(f"{baseName}_{actual_key} = {baseName}")
                    debugLog(f"🔍 [DEBUG] Single dict value assignment: {baseName}_{actual_key} = {baseName}")
                        
                elif len(exudyn_return_values) > 1:
                    # Multiple return values - ALWAYS unpack all of them
                    # User requirement: "ALL returnvalues we get should be listed/shown in generated code"
                    for field_name in exudyn_return_values.keys():
                        codeLines.append(f"{baseName}_{field_name} = {baseName}['{field_name}']")
                        debugLog(f"🔍 [DEBUG] Multi-value dict unpacking: {baseName}_{field_name} = {baseName}['{field_name}']")
                    
                else:
                    # Empty dict - fallback
                    codeLines.append(f"{baseName}_objectNumber = {baseName}")
                    debugLog(f"🔍 [DEBUG] Empty dict fallback: {baseName}_objectNumber = {baseName}")
            else:
                # Single value return (integer, etc.) - simple assignment
                # Determine appropriate key name based on object type
                if objType.lower().startswith('createground'):
                    key_name = 'objectNumber'
                elif objType.lower().startswith('createcartesian') or objType.lower().startswith('createspring'):
                    key_name = 'objectNumber'  
                elif objType.lower().startswith('createforce'):
                    key_name = 'loadNumber'
                else:
                    key_name = 'objectNumber'  # Default fallback
                    
                codeLines.append(f"{baseName}_{key_name} = {baseName}")
                debugLog(f"🔍 [DEBUG] Single value assignment: {baseName}_{key_name} = {baseName}")
                
                # Special case: Ground objects also get bodyNumber alias
                if objType.lower().startswith('createground') and key_name == 'objectNumber':
                    codeLines.append(f"{baseName}_bodyNumber = {baseName}")
                    debugLog(f"🔍 [DEBUG] Ground body alias: {baseName}_bodyNumber = {baseName}")
            
            # ✅ USER'S SIMPLE AND ELEGANT SOLUTION SUCCESSFULLY IMPLEMENTED
            # Single return value → Simple assignment (no dictionary access)
            # Multiple return values → Dictionary unpacking (only if returnDict=True)
            # This eliminates KeyError exceptions and makes code generation robust
            continue

        # ── 3) Legacy objects/nodes/markers/loads/sensors ──────────────────────────
        data = item.get('data', item)  # Extract data consistently
        obj_type = data.get('objectType', '') or data.get('type', '')
        type_prefix = get_type_prefix(obj_type)
        prefixMap = {'Object': 'b', 'Node': 'n', 'Marker': 'm', 'Load': 'l', 'Sensor': 's'}
        prefix = prefixMap.get(type_prefix, None)
        if prefix is None:
            debugLog(f"[generateExudynCode] ⚠️ Could not determine valid prefix for item: {item}")
            continue
        creationID = item.get('creationIndex', typeCounter[prefix])
        
        # Use consistent naming like lPoint, lMassPoint2, etc.
        # For legacy items, use FULL constructor names (not shortened ones)
        if obj_type.startswith("Node"):
            constructor_name = obj_type  # Use full name: NodePointGround -> NodePointGround
            descriptive_name = obj_type[4:] if obj_type != "NodePointGround" else "PointGround"  # For variable naming
        elif obj_type.startswith("Marker"):
            constructor_name = obj_type  # Keep full name: MarkerNodeCoordinate -> MarkerNodeCoordinate
            descriptive_name = constructor_name  # Same as constructor
        elif obj_type.startswith("Object"):
            constructor_name = obj_type  # Use full name: ObjectMassPoint -> ObjectMassPoint
            descriptive_name = obj_type[6:] if obj_type != "ObjectGround" else "Ground"  # For variable naming
        elif obj_type.startswith("Load"):
            constructor_name = obj_type  # Use full name: LoadForceVector -> LoadForceVector  
            descriptive_name = obj_type[4:]  # Strip "Load" for variable naming
        elif obj_type.startswith("Sensor"):
            # For sensors, use the full name (SensorBody, SensorNode, etc.)
            constructor_name = obj_type  # Keep full name: SensorBody -> SensorBody
            descriptive_name = constructor_name  # Same as constructor
        else:
            constructor_name = obj_type  # Fallback
            descriptive_name = obj_type  # Fallback
        
        # Use the descriptive name for variable naming, or user-provided name if available
        # For markers, always use the 'name' field if present for variable naming
        if obj_type.startswith("Marker") and 'name' in data and data['name']:
            item_name = data['name']
        else:
            item_name = item.get('name', descriptive_name)
        
        # Check if this name would conflict
        candidate_base = f"l{item_name}"
        if candidate_base in definedSymbols:
            # Add suffix to make it unique
            item_name = f"{item_name}{creationID}"
        baseName = f"l{item_name}"
        typeCounter[prefix] = max(typeCounter[prefix], creationID + 1)
        
        # Track this baseName as used (same as Create* branch)
        definedSymbols.add(baseName)
        
        # Map return values to baseName for symbolic reference resolution
        # Note: We'll update this mapping later with typed variable names after assignment
        return_values = item.get('returnValues', {})
        if isinstance(return_values, dict):
            for return_type, return_index in return_values.items():
                if isinstance(return_index, int):
                    # Temporarily use baseName, will be updated with typed name later
                    existing_mapping = indexMap.get(return_index)
                    if existing_mapping is not None:
                        is_current_body = any(body_type in objType.lower() for body_type in ['ground', 'masspoint', 'rigidbody', 'flexiblebody'])
                        if is_current_body:
                            debugLog(f"🔧 [LEGACY] return value {return_index} collision: replacing '{existing_mapping}' with '{baseName}' (prioritizing body object)")
                            # Will be updated with typed name later
                        else:
                            debugLog(f"🔧 [LEGACY] return value {return_index} collision: keeping '{existing_mapping}' over '{baseName}' (prioritizing body object)")
                            continue  # Don't override existing mapping
                    # Temporary mapping - will be updated with typed variable name
                    indexMap[return_index] = baseName
                    debugLog(f"🔢 [LEGACY] temporary indexMap[{return_index}] = {baseName} ({return_type})")
        else:
            # Fallback: also map item index temporarily
            objIndex = item.get("objIndex", idx)
            if objIndex is not None:
                indexMap[objIndex] = baseName
                debugLog(f"🔢 [LEGACY] temporary indexMap[{objIndex}] = {baseName} (fallback)")
                
        # Pre-generate return value assignments for legacy items
        # This ensures consistent generation of return value assignments for all items
        if isinstance(return_values, dict) and return_values:
            # Generate return value assignments early (will be added to codelines later)
            return_value_assignments = []
            for return_type, return_index in return_values.items():
                typed_var_name = f"{baseName}_{return_type}"
                return_value_assignments.append(f"{typed_var_name} = {baseName}")
                debugLog(f"🔢 [LEGACY] Prepared return value assignment: {typed_var_name} = {baseName}")
        else:
            return_value_assignments = []

        # --- Graphics variable extraction ---
        graphics_var_name = None
        graphics_fields = [k for k in item.keys() if k in {"graphicsDataList", "VgraphicsData", "graphicsData"}]
        for gfield in graphics_fields:
            gval = item[gfield]
            if isinstance(gval, list) and gval:
                graphics_var_name = f"graphics{item.get('name', baseName)}"
                formattedList = []
                for entry in gval:
                    if isinstance(entry, dict) and 'name' in entry and 'args' in entry:
                        name = entry['name']
                        if name.startswith('GraphicsData'):
                            name = name[len('GraphicsData'):]
                        formattedList.append(f"exu.graphics.{name}({entry['args']})")
                    elif isinstance(entry, str):
                        formattedList.append(entry)
                    else:
                        formattedList.append(str(entry))
                codeLines.append(f"{graphics_var_name} = [{', '.join(formattedList)}]")
                item[gfield] = graphics_var_name

        # --- Determine function name for legacy items ---
        # Use the constructor_name already determined above
        if objType.startswith("Node"):
            addFuncName = "AddNode"
        elif objType.startswith("Marker"):
            addFuncName = "AddMarker"
        elif objType.startswith("Object"):
            addFuncName = "AddObject" 
        elif objType.startswith("Load"):
            addFuncName = "AddLoad"
        elif objType.startswith("Sensor"):
            addFuncName = "AddSensor"
        else:
            # Fallback for unknown types
            addFuncName = f"Add{objType}"

        # Use the constructor_name already determined above
        constructorName = constructor_name

        # Ensure validParams is always defined - use constructorName, not objType
        import exudyn as exu
        if hasattr(exu, constructorName):
            createFunc = getattr(exu, constructorName)
            validParams = set(inspect.signature(createFunc).parameters) if createFunc else set()
        else:
            createFunc = None
            validParams = set()
            
        # debugLog debug info about valid parameters for this constructor
        debugLog(f"🔍 [LEGACY DEBUG] Valid parameters for {constructorName}: {validParams}")

        argStrs = []
        visualization_params = {}
        
        # Get the actual parameter data - for GUI items, this is in 'data' field
        param_source = item.get('data', item) if 'data' in item else item
        
        debugLog(f"\n🔍 [LEGACY DEBUG] PARAM SOURCE DATA for {obj_type}: {param_source}\n")
        
        # First pass: collect visualization parameters
        for k, v in param_source.items():
            if k.startswith('V'):  # All V-parameters are visualization parameters
                viz_param = k[1:]  # Remove 'V' prefix: Vshow -> show, VgraphicsData -> graphicsData
                if viz_param == 'graphicsData' and isinstance(v, list):
                    formattedList = []
                    for entry in v:
                        if isinstance(entry, dict) and 'name' in entry and 'args' in entry:
                            name = entry['name']
                            if name.startswith('GraphicsData'):
                                name = name[len('GraphicsData'):]
                            elif name.startswith('graphics.'):
                                name = name[len('graphics.'):]
                            args = entry['args']
                            if isinstance(args, dict):
                                arg_pairs = []
                                for arg_name, arg_value in args.items():
                                    arg_pairs.append(f"{arg_name}={repr(arg_value)}")
                                args_str = ', '.join(arg_pairs)
                            else:
                                args_str = str(args)
                            formattedList.append(f"exu.graphics.{name}({args_str})")
                        elif isinstance(entry, str):
                            import ast
                            try:
                                d = ast.literal_eval(entry)
                                if isinstance(d, dict) and 'name' in d and 'args' in d:
                                    name = d['name']
                                    if name.startswith('GraphicsData'):
                                        name = name[len('GraphicsData'):]
                                    elif name.startswith('graphics.'):
                                        name = name[len('graphics.'):]
                                    formattedList.append(f"exu.graphics.{name}({d['args']})")
                                    continue
                            except Exception:
                                pass
                            if entry.startswith('exu.graphics.'):
                                graphics_call = entry.replace('exu.graphics.', 'graphics.')
                            elif entry.startswith('graphics.'):
                                graphics_call = entry
                            else:
                                graphics_call = f"graphics.{entry}"
                            formattedList.append(graphics_call)
                        else:
                            formattedList.append(str(entry))
                    visualization_params[viz_param] = formattedList
                else:
                    visualization_params[viz_param] = v
        
        # Special processing for sensors
        sensor_output_variable_type = None
        if obj_type.startswith("Sensor"):
            # Extract outputVariableType from summaryPythonCode
            summary_code = param_source.get('summaryPythonCode', {})
            if isinstance(summary_code, dict) and 'outputVariableType' in summary_code:
                sensor_output_variable_type = summary_code['outputVariableType']
                debugLog(f"[LEGACY DEBUG] Found sensor outputVariableType: {sensor_output_variable_type}")
        
        # Second pass: process all other parameters (use same logic as Create* branch)
        for k, v in param_source.items():
            # Filter out GUI metadata fields but preserve actual object reference fields
            # Only filter GUI-specific metadata, not actual object reference parameters
            debugLog(f"[LEGACY DEBUG] Processing field {k}={v} for {obj_type}")
            if k in {"objectType", "objIndex", "returnValues", "returnInfo", "connections", "creationUID", "creationIndex", 
                     "GUI", "summaryPythonCode", "isLegacy"}:  # We should allow 'name' to be passed to constructor
                debugLog(f"[LEGACY DEBUG] Skipping {k} (reserved key)")
                continue
            if k.startswith('V'):  # Skip ALL visualization parameters (they're handled separately)
                debugLog(f"[LEGACY DEBUG] Skipping {k} (visualization parameter)")
                continue
            if k == 'returnDict':
                # Skip returnDict for regular constructors (they don't support it)
                debugLog(f"[LEGACY DEBUG] Skipping {k} (returnDict not supported)")
                continue
            # Filter out all *Type fields for legacy items as requested
            # IMPORTANT: Do NOT filter out fields that are actual reference fields:
            # bodyNumber, nodeNumber, markerNumber, etc. are legitimate parameters
            if k.endswith("Type") and k not in {"dataType"} and not shouldResolveSymbolically(obj_type, k):
                # Skip all *Type fields (nodeType, markerType, loadType, sensorType, etc.) for legacy items
                debugLog(f"[generateExudynCode] ⚠️ [LEGACY] Skipped {k} field for legacy item: {obj_type}")
                debugLog(f"[LEGACY DEBUG] Skipping {k} ({k} for legacy item)")
                continue
            # We'll only use the validation when we're sure we have the right constructor
            # For test cases and less common objects, we won't filter parameters
            # since they might be valid even if we can't verify them
            if validParams and k not in validParams and createFunc is not None and len(validParams) > 0:
                debugLog(f"[generateExudynCode] ⚠️ [LEGACY] Skipped unknown argument: {k} (not valid for {constructorName})")
                debugLog(f"[LEGACY DEBUG] Skipping {k} (not valid for {constructorName})")
                continue
            if isinstance(v, str) and v == graphics_var_name:
                argStrs.append(f"    {k}={graphics_var_name}")
                continue
            # --- Export all graphics fields as NAME(args) (not as dict, not repr) ---
            elif isinstance(v, list) and k in {"graphicsDataList", "VgraphicsData", "graphicsData"}:
                # Handle both compact dictionary format and expanded object format
                graphics_list = expandGraphicsFromCompactFormat(v)
                formattedList = []
                for entry in graphics_list:
                    if isinstance(entry, dict) and 'name' in entry and 'args' in entry:
                        name = entry['name']
                        if name.startswith('GraphicsData'):
                            name = name[len('GraphicsData'):]
                        elif name.startswith('graphics.'):
                            name = name[len('graphics.'):]
                        
                        # Handle different argument formats
                        args = entry['args']
                        if isinstance(args, dict):
                            # Convert dict to keyword arguments
                            arg_pairs = []
                            for arg_name, arg_value in args.items():
                                if isinstance(arg_value, str):
                                    arg_pairs.append(f"{arg_name}={repr(arg_value)}")
                                else:
                                    arg_pairs.append(f"{arg_name}={repr(arg_value)}")
                            args_str = ', '.join(arg_pairs)
                        else:
                            # Use args as-is (string or other format)
                            args_str = str(args)
                        
                        formattedList.append(f"exu.graphics.{name}({args_str})")
                        usesGraphics = True
                    elif isinstance(entry, str):
                        # Try to parse string of form "{'name': 'CheckerBoard', 'args': ...}" and convert to NAME(args)
                        import ast
                        try:
                            d = ast.literal_eval(entry)
                            if isinstance(d, dict) and 'name' in d and 'args' in d:
                                name = d['name']
                                if name.startswith('GraphicsData'):
                                    name = name[len('GraphicsData'):]
                                elif name.startswith('graphics.'):
                                    name = name[len('graphics.'):]
                                formattedList.append(f"exu.graphics.{name}({d['args']})")
                                usesGraphics = True
                                continue
                        except Exception:
                            pass
                        # Handle string format - convert to code without quotes
                        if isinstance(entry, str):
                            # Remove exu.graphics. prefix and use graphics. for import alias
                            if entry.startswith('exu.graphics.'):
                                graphics_call = entry.replace('exu.graphics.', 'graphics.')
                            elif entry.startswith('graphics.'):
                                graphics_call = entry
                            else:
                                # Add graphics prefix if missing
                                graphics_call = f"graphics.{entry}"
                            formattedList.append(graphics_call)
                        else:
                            formattedList.append(entry)
                    else:
                        # Handle actual graphics objects (for backward compatibility)
                        if hasattr(entry, '__class__') and hasattr(entry.__class__, '__name__'):
                            class_name = entry.__class__.__name__
                            formattedList.append(f"exu.graphics.{class_name}(**kwargs)")  # Simplified
                            usesGraphics = True
                        else:
                            formattedList.append(str(entry))
                argStrs.append(f"    {k}=[{', '.join(formattedList)}]")
            # --- NUMPY ARRAY HANDLING FOR LEGACY ITEMS ---
            elif isinstance(v, np.ndarray):
                debugLog(f"[LEGACY DEBUG] Converting numpy array for {k}: shape={v.shape}, dtype={v.dtype}")
                # Convert numpy array to list and wrap with np.array() for code generation
                array_as_list = v.tolist()
                argStrs.append(f"    {k}=np.array({repr(array_as_list)})")
            elif isinstance(v, str):
                # --- Fix: Always use variable name for user functions ---
                if k.lower().endswith('userfunction') and v.startswith('UF'):
                    argStrs.append(f"    {k}={v}")
                # If the string looks like a list, output as code (not as a string)
                elif v.strip().startswith('[') and v.strip().endswith(']'):
                    argStrs.append(f"    {k}={v.strip()}")
                # If the string matches a user variable, output as code (no quotes)
                elif v in user_var_names:
                    argStrs.append(f"    {k}={v}")
                else:
                    argStrs.append(f"    {k}={repr(v)}")
            elif v is None:
                # Special handling for None values
                if obj_type.startswith("Sensor") and k == 'fileName':
                    # For sensors, convert fileName=None to fileName=''
                    argStrs.append(f"    {k}=''")
                    debugLog(f"[LEGACY DEBUG] Sensor fileName: None -> ''")
                else:
                    argStrs.append(f"    {k}=None")
            # --- 🎯 EXACT INDEX MAPPING: Use precise mapping for single indices (LEGACY items) ---
            elif shouldResolveSymbolically(objType, k) and (isinstance(v, int) or (isinstance(v, str) and v.isdigit())):
                # Convert string indices to integers for consistent lookup
                index_val = int(v) if isinstance(v, str) else v
                # Get the desired suffix for this field type
                desired_suffix = getSuffixForField(k, objType)
                # 🎯 USE EXACT MAPPING: Look up the precise object for this index and return value type
                exact_symbol = exact_mappings.get(desired_suffix, {}).get(index_val)
                mapped_var = exact_symbol or indexMap.get(index_val)
                if mapped_var:
                    argStrs.append(f"    {k}={mapped_var}")
                    debugLog(f"✅ [LEGACY MAPPING] Resolved {k}={v} → {mapped_var}")
                else:
                    argStrs.append(f"    {k}={index_val}")
                    debugLog(f"❌ [LEGACY MAPPING] No mapping found for {k}={v}, using raw value")
            elif isinstance(v, (int, float, bool)):
                argStrs.append(f"    {k}={v}")
            # --- 🎯 EXACT INDEX MAPPING: Use precise mapping for index lists (LEGACY items) ---
            elif shouldResolveSymbolically(objType, k) and isinstance(v, list):
                entries = []
                for x in v:
                    x_val = int(x) if isinstance(x, str) and x.isdigit() else x
                    # Always use 'markerNumber' for markerNumbers fields
                    if k.lower() in ['markernumbers', 'markernumber']:
                        mapped_var = exact_mappings.get('markerNumber', {}).get(x_val) or indexMap.get(x_val)
                    else:
                        desired_suffix = getSuffixForField(k, objType)
                        mapped_var = exact_mappings.get(desired_suffix, {}).get(x_val) or indexMap.get(x_val)
                    if mapped_var:
                        entries.append(f"{mapped_var}")
                    else:
                        entries.append(f"UNRESOLVED_MARKER_{x_val}  # WARNING: Could not resolve markerNumber mapping")
                        debugLog(f"[generateCode] WARNING: Could not resolve markerNumber mapping for {k} index {x_val} in {objType}")
                # Add the complete list with mapped references
                listStr = "[" + ", ".join(entries) + "]"
                argStrs.append(f"    {k}={listStr}")
            else:
                # Special handling for function objects - use function name instead of repr
                if callable(v) and hasattr(v, '__name__'):
                    argStrs.append(f"    {k}={v.__name__}")
                else:
                    argStrs.append(f"    {k}={repr(v)}")

        # Add outputVariableType parameter for sensors
        if obj_type.startswith("Sensor") and sensor_output_variable_type:
            argStrs.append(f"    outputVariableType={sensor_output_variable_type}")
            debugLog(f"[LEGACY DEBUG] Added sensor outputVariableType: {sensor_output_variable_type}")

        # Add bundled visualization object if visualization parameters were found
        if visualization_params:
            # Determine visualization class name based on FULL constructor name
            # Rules: V + full_constructor_name (e.g., NodePointGround -> VNodePointGround, ObjectMassPoint -> VObjectMassPoint)
            viz_class = f"V{constructor_name}"  # Always use V + full constructor name
                
            # Format visualization parameters
            viz_args = []
            for param, value in visualization_params.items():
                # Special handling for graphics variables (like graphicsMassPoint)
                if isinstance(value, str) and param.lower() == 'graphicsdata' and value.startswith('graphics'):
                    viz_args.append(f"{param}={value}")  # No quotes for graphics variable references
                else:
                    viz_args.append(f"{param}={repr(value)}")
            
            # Multi-line format for visualization if it has multiple parameters
            if len(viz_args) > 1:
                joined_args = ',\n        '.join(viz_args)
                viz_call = f"{viz_class}(\n        {joined_args}\n    )"
            else:
                viz_call = f"{viz_class}({', '.join(viz_args)})"
            argStrs.append(f"    visualization={viz_call}")

        # Generate the legacy constructor call (NOT dictionary format)
        # Legacy format: lPoint = mbs.AddNode(Point(referenceCoordinates=[0,0,0], ...))
        if argStrs:
            # Multi-line format for better readability with proper indentation
            constructor_args = ",\n".join(argStrs)
            codeLines.append(f"{baseName} = mbs.{addFuncName}({constructor_name}(\n{constructor_args}\n))")
        else:
            # Single line format for empty constructors
            codeLines.append(f"{baseName} = mbs.{addFuncName}({constructor_name}())")
            
        definedSymbols.add(baseName)
        
        # Add properly typed variable assignment based on the correct return value type
        # Use the return values from the item to determine the correct suffix
        return_values = item.get('returnValues', {})
        if isinstance(return_values, dict) and return_values:
            # Map based on actual return values (same as CREATE items)
            for return_type, return_index in return_values.items():
                # Convert string indices to integers for consistent mapping
                if isinstance(return_index, str) and return_index.isdigit():
                    return_index = int(return_index)
                if isinstance(return_index, int):
                    # Update indexMap and exact_mappings for all return types
                    indexMap[return_index] = f"{baseName}_{return_type}"
                    if return_type in exact_mappings:
                        exact_mappings[return_type][return_index] = f"{baseName}_{return_type}"
                    debugLog(f"🔢 [CREATE] indexMap[{return_index}] = {baseName}_{return_type}")
        
        # 🔧 CRITICAL FIX: Always generate at least one typed return value assignment for all legacy items,
        # even if the item doesn't have returnValues or they're not a dictionary.
        # This ensures connectors, springs, joints, etc. always get proper assignments.
        
        # Determine the appropriate return type based on object type
        if objType.startswith("Node"):
            default_return_type = "nodeNumber"
        elif objType.startswith("Marker"):
            default_return_type = "markerNumber"
        elif objType.startswith("Load"):
            default_return_type = "loadNumber"
        elif objType.startswith("Sensor"):
            default_return_type = "sensorNumber"
        else:
            # All other items including Object*, connectors, springs, joints
            default_return_type = "objectNumber"
        
        # Generate default return value assignment if not already created by returnValues processing
        default_typed_var_name = f"{baseName}_{default_return_type}"
        if default_typed_var_name not in definedSymbols:
            codeLines.append(f"{default_typed_var_name} = {baseName}")
            definedSymbols.add(default_typed_var_name)
            debugLog(f"🔢 [LEGACY] Added default return value assignment: {default_typed_var_name} = {baseName}")
            
            # Also update indexMap if we have an index
            objIndex = item.get("objIndex", idx)
            if objIndex is not None:
                indexMap[objIndex] = default_typed_var_name
                # Update exact mappings for consistent reference resolution
                if default_return_type in exact_mappings and objIndex not in exact_mappings[default_return_type]:
                    exact_mappings[default_return_type][objIndex] = default_typed_var_name
                    debugLog(f"🔧 [EXACT MAPPING] Updated exact mapping (default): {default_return_type}[{objIndex}] → {default_typed_var_name}")
                    
        # Handle specific case for ObjectGround which should also have a bodyNumber assignment
        if objType == "ObjectGround":
            ground_body_var_name = f"{baseName}_bodyNumber"
            if ground_body_var_name not in definedSymbols:
                codeLines.append(f"{ground_body_var_name} = {baseName}")
                definedSymbols.add(ground_body_var_name)
                debugLog(f"🔢 [LEGACY] Added ground body assignment: {ground_body_var_name} = {baseName}")
                
                # Update bodyNumber mapping if we have an index
                objIndex = item.get("objIndex", idx)
                if objIndex is not None and "bodyNumber" in exact_mappings:
                    exact_mappings["bodyNumber"][objIndex] = ground_body_var_name
                    debugLog(f"🔧 [EXACT MAPPING] Updated ground body mapping: bodyNumber[{objIndex}] → {ground_body_var_name}")
            
        # Legacy items only generate code, they don't execute - skip the wrapper execution
        continue
        # call the wrapper (which may return a list or a dict)
        # Only include arguments accepted by the function
        createFunc = getattr(mbs, objType, None)
        if not createFunc:
            # Suppress warning: do not output any warning if function is not found
            continue
        validParams = getValidParams(createFunc)
        validCallArgs = {k: v for k, v in item.items() if k in validParams}
        
        # Process arguments for actual function call (convert GUI dicts to Exudyn objects)
        processedCallArgs = {}
        usesGraphics = False # Initialize usesGraphics here
        for arg_name, arg_value in validCallArgs.items():
            if arg_name == 'inertia' or (isinstance(arg_value, dict) and 'name' in arg_value and 'args' in arg_value and not arg_name.endswith("Expression")): # Check for graphics dict
                # This handles single graphicsData items like 'inertia' or 'graphicsData'
                try:
                    # Ensure 'graphics.' prefix if not present in name, as eval context is 'graphics'
                    obj_name = arg_value['name']
                    if not obj_name.startswith('graphics.'):
                         # Attempt to map to known graphics types if not fully qualified
                        if hasattr(graphics, obj_name): # e.g. Sphere
                            call_str = f"graphics.{obj_name}({arg_value['args']})"
                        elif hasattr(graphics, obj_name.replace("Inertia", "GraphicsData")): # e.g. InertiaSphere -> GraphicsDataSphere
                            call_str = f"graphics.{obj_name.replace('Inertia', 'GraphicsData')}({arg_value['args']})"
                        else: # Fallback to direct name if it's something like graphics.Sphere
                            call_str = f"{obj_name}({arg_value['args']})" 
                    else:  # Already has graphics. prefix
                        call_str = f"{obj_name}({arg_value['args']})"

                    processedCallArgs[arg_name] = eval(call_str, {"graphics": graphics, "np": np, "exu": exu}) # Added exu for potential exu.math.RandomXYZ
                    usesGraphics = True 
                except Exception as e:
                    debugLog(f"[generateExudynCode] ⚠️ Failed to eval graphics data for {arg_name}: {arg_value} - {e}")
                    processedCallArgs[arg_name] = arg_value # Fallback
            elif arg_name == "graphicsDataList" and isinstance(arg_value, list):
                eval_list = []
                for entry in arg_value:
                    if isinstance(entry, dict) and 'name' in entry and 'args' in entry:
                        try:
                            obj_name = entry['name']
                            # Ensure 'graphics.' prefix for eval context
                            if not obj_name.startswith('graphics.'):
                                if hasattr(graphics, obj_name):
                                    call_str = f"graphics.{obj_name}({entry['args']})"
                                else: # Fallback to direct name
                                    call_str = f"{obj_name}({entry['args']})"
                            else:
                                call_str = f"{obj_name}({entry['args']})"
                                
                            eval_list.append(eval(call_str, {"graphics": graphics, "np": np, "exu": exu}))
                            usesGraphics = True
                        except Exception as e:
                            debugLog(f"[generateExudynCode] ⚠️ Failed to eval graphics data in list: {entry} - {e}")
                            eval_list.append(entry) # Fallback
                    else:
                        eval_list.append(entry) 
                processedCallArgs[arg_name] = eval_list
            else:
                processedCallArgs[arg_name] = arg_value

        # --- Ensure all *Number(s) arguments are Exudyn indices ---
        def convert_indices(val, key=None):
            import exudyn as exu
            key_lower = (key or "").lower() if key else ""
            if isinstance(val, list):
                return [convert_indices(x, key) for x in val]
            if isinstance(val, str):
                try:
                    ival = int(float(val))
                    if "node" in key_lower:
                        return exu.NodeIndex(ival)
                    elif "body" in key_lower or "object" in key_lower:
                        return exu.ObjectIndex(ival)
                    elif "marker" in key_lower:
                        return exu.MarkerIndex(ival)
                    elif "sensor" in key_lower:
                        return exu.SensorIndex(ival)
                    elif "load" in key_lower:
                        return exu.LoadIndex(ival)
                    else:
                        return ival
                except Exception:
                    debugLog(f"[generateExudynCode] Could not convert value '{val}' to Exudyn index")
                    return val
            if isinstance(val, int):
                if "node" in key_lower:
                    return exu.NodeIndex(val)
                elif "body" in key_lower or "object" in key_lower:
                    return exu.ObjectIndex(val)
                elif "marker" in key_lower:
                    return exu.MarkerIndex(val)
                elif "sensor" in key_lower:
                    return exu.SensorIndex(val)
                elif "load" in key_lower:
                    return exu.LoadIndex(val)
                else:
                    return val
            return val

        for k in list(processedCallArgs.keys()):
            if k.lower().endswith("number") or k.lower().endswith("numbers"):
                processedCallArgs[k] = convert_indices(processedCallArgs[k], k)
                debugLog(f"[generateExudynCode] After conversion: {k} = {processedCallArgs[k]} (type: {type(processedCallArgs[k])})")
        
        returned = createFunc(**processedCallArgs)
        # Actually, replace the previous call() example with direct "returned = …" above in real code.

        if not isinstance(returned, dict):
            # If the wrapper gave back a list, the first element is the objectNumber
            if isinstance(returned, list) and len(returned) >= 1:
                returnedObj = returned[0]
            else:
                returnedObj = int(returned)
            result = {'objectNumber': returnedObj}
        else:
            result = returned

        # Always assign a valid objectNumber symbol
        objectField = None
        returnFields = result
        actual_obj_type = objType or data.get('objectType', '')
        
        debugLog(f"🔍 [DEBUG] Actual object type for return value assignment: {actual_obj_type}")
        
        if isinstance(returnFields, dict):
            # Determine if we need to generate the standard objectNumber assignment
            if 'objectNumber' in returnFields:
                if has_return_dict:
                    codeLines.append(f"{baseName}_objectNumber = {baseName}['objectNumber']")
                else:
                    codeLines.append(f"{baseName}_objectNumber = {baseName}")
                definedSymbols.add(f"{baseName}_objectNumber")
            
            # Always generate bodyNumber assignment for body objects and forces/torques
            is_force_or_torque = (actual_obj_type in ['CreateForce', 'CreateTorque'])
            debugLog(f"🔍 [DEBUG] Is force or torque: {is_force_or_torque}")
            
            if 'bodyNumber' in returnFields or is_force_or_torque:
                # If bodyNumber actually exists in returnFields, use it, otherwise use objectNumber
                if 'bodyNumber' in returnFields:
                    if has_return_dict:
                        codeLines.append(f"{baseName}_bodyNumber = {baseName}['bodyNumber']")
                    else:
                        codeLines.append(f"{baseName}_bodyNumber = {baseName}")
                else:
                    # For forces/torques with missing bodyNumber, use objectNumber as bodyNumber
                    if has_return_dict:
                        codeLines.append(f"{baseName}_bodyNumber = {baseName}['objectNumber']")
                    else:
                        codeLines.append(f"{baseName}_bodyNumber = {baseName}")
                definedSymbols.add(f"{baseName}_bodyNumber")
        else:
            # Single integer return value - treat as objectNumber
            codeLines.append(f"{baseName}_objectNumber = {baseName}")
            definedSymbols.add(f"{baseName}_objectNumber")
            
            # For forces and torques, also generate bodyNumber
            is_force_or_torque = (actual_obj_type in ['CreateForce', 'CreateTorque'])
            if is_force_or_torque:
                codeLines.append(f"{baseName}_bodyNumber = {baseName}")
                definedSymbols.add(f"{baseName}_bodyNumber")

            
        # Return unpacking
        validFields = item.get('returnValues', {})
        # Only unpack return values if validFields is a dict
        if isinstance(validFields, dict):
            for field, value in validFields.items():
                if isinstance(value, int):
                    symName = f"{baseName}_{field}"
                    # Only add assignment if not already defined (avoid duplicates from legacy processing)
                    if symName not in definedSymbols:
                        codeLines.append(f"{symName} = {baseName}['{field}']")
                        definedSymbols.add(symName)


    # Add a special case to always ensure that forces and torques get bodyNumber assignments
    # Fix the body number assignments for forces and torques
    if not fullScript:
        debugLog("🔧 [DEBUG] Post-processing to ensure force and torque bodyNumber assignments")
        for idx, item in enumerate(itemList):
            data = item.get('data', item)
            objType = item.get('objectType', data.get('objectType', ''))
            name = data.get('name', f'item{idx}')
            
            # Handle Create* items
            if objType.startswith('Create'):
                baseName = f"c{name}"
                if objType in ['CreateForce', 'CreateTorque']:
                    bodyNumberAssignment = f"{baseName}_bodyNumber = {baseName}"
                    
                    # Check if the assignment already exists
                    if not any(line.strip() == bodyNumberAssignment for line in codeLines):
                        debugLog(f"⚠️ [DEBUG] Adding missing bodyNumber assignment for {objType}: {bodyNumberAssignment}")
                        codeLines.append(bodyNumberAssignment)
                        definedSymbols.add(f"{baseName}_bodyNumber")
            
            # Handle legacy connector items
            elif 'type' in item and item['type'] == 'legacy' and (
                objType.startswith('ObjectConnector') or 
                objType.startswith('ConnectorCoordinate') or
                objType.startswith('Connector')):
                baseName = f"l{name}"
                objectNumberAssignment = f"{baseName}_objectNumber = {baseName}"
                
                # Check if the assignment already exists
                if not any(line.strip() == objectNumberAssignment for line in codeLines):
                    debugLog(f"⚠️ [DEBUG] Adding missing objectNumber assignment for legacy connector: {objectNumberAssignment}")
                    codeLines.append(objectNumberAssignment)
                    definedSymbols.add(f"{baseName}_objectNumber")

    # Deduplicate imports at the top
    seen_imports = set()
    deduped_headerLines = []
    for line in baseHeader:
        if line.strip().startswith('import') or line.strip().startswith('from'):
            if line not in seen_imports:
                deduped_headerLines.append(line)
                seen_imports.add(line)
        else:
            deduped_headerLines.append(line)
    baseHeader = deduped_headerLines

    # 🎯 EXACT MAPPINGS ARE NOW UPDATED DIRECTLY DURING PROCESSING
    # No need to rebuild as they are updated inline with typed variable names
    debugLog("🔄 [EXACT MAPPING] Exact mappings were updated directly during legacy processing")

    # Include user function definitions after imports but before object creation
    if userFunctionDefinitions:
        baseHeader.append("# === User Functions ===")
        for funcDef in userFunctionDefinitions:
            baseHeader.append(funcDef)
        baseHeader.append("")  # Add blank line after user functions

    # Only append mbs.Assemble() and SolveDynamic if fullScript flag is set
    output_lines = baseHeader + codeLines
    if fullScript:
        output_lines.append("")
        output_lines.append("mbs.Assemble()")
        output_lines.append("# mbs.SolveDynamic()  # Uncomment to run simulation")
        output_lines.append("")
        output_lines.append("simulationSettings = exu.SimulationSettings()")
        output_lines.append("simulationSettings.solutionSettings.solutionWritePeriod = 5e-3")
        output_lines.append("simulationSettings.solutionSettings.sensorsWritePeriod = 5e-3")
        output_lines.append("simulationSettings.timeIntegration.numberOfSteps = 1000")
        output_lines.append("simulationSettings.timeIntegration.endTime = 1.0")
        output_lines.append("simulationSettings.displayComputationTime = True")
        output_lines.append("simulationSettings.timeIntegration.verboseMode = 1")
        output_lines.append("simulationSettings.timeIntegration.generalizedAlpha.spectralRadius = 1")
        output_lines.append("")
        output_lines.append("exu.StartRenderer()")
        output_lines.append("mbs.WaitForUserToContinue()")
        output_lines.append("exu.SolveDynamic(mbs, simulationSettings)")
        output_lines.append("mbs.WaitForUserToContinue()")
        output_lines.append("exu.StopRenderer()")
    return '\n'.join(output_lines)

def buildExactIndexMapping(items):
    """
    Build a comprehensive exact mapping from indices to objects based on the actual model structure.
    This eliminates guesswork and handles all edge cases by using the precise data we already have.
    Uses the same variable naming logic as the main generation to ensure consistency.
    
    Returns:
        dict: Mapping structure with exact index->object mappings for each return value type
              Format: {
                  'bodyNumber': {0: 'lPoint_nodeNumber', 1: 'cMassPoint_bodyNumber', ...},
                  'nodeNumber': {0: 'lPoint_nodeNumber', 1: 'cNode2_nodeNumber', ...},
                  'objectNumber': {0: 'cGround_objectNumber', 1: 'cForce_objectNumber', ...},
                  'loadNumber': {0: 'cForce_loadNumber', 1: 'cForce2_loadNumber', ...},
                  ...
              }
    """
    debugLog("🎯 [EXACT MAPPING] Building comprehensive index mapping from model structure")
    
    # debugLog detailed debug info about each item
    debugLog("\n🔍 [EXACT MAPPING] Items to process:")
    for idx, item in enumerate(items):
        data = item.get('data', item)
        obj_type = data.get('objectType', '')
        # For legacy items, name comes from top-level item, not data
        name = item.get('name', data.get('name', f'item{idx}'))
        return_values = item.get('returnValues', data.get('returnValues', {}))
        debugLog(f"  Item {idx}: {obj_type} '{name}' with returnValues: {return_values}")
    
    # Initialize mapping tables for each return value type
    exact_mappings = {
        'bodyNumber': {},      # Bodies: Ground, MassPoint, RigidBody, FlexibleBody
        'nodeNumber': {},      # Nodes: Point masses, flexible body nodes, etc.
        'objectNumber': {},    # All objects: Ground, Bodies, Forces, Loads, Constraints
        'loadNumber': {},      # Loads: Forces, Torques, etc.
        'markerNumber': {},    # Markers
        'sensorNumber': {},    # Sensors
        'markerBodyMass': {},  # Special case for mass point markers
    }
    
    # 🔧 Use the same variable naming logic as the main code generation
    definedSymbols = set()
    typeCounter = {'b': 0, 'n': 0, 'm': 0, 'l': 0, 's': 0}
    
    # Process each item to build exact mappings
    for idx, item in enumerate(items):
        data = item.get('data', item)
        obj_type = data.get('objectType', '')
        # For legacy items, name comes from top-level item, not data
        name = item.get('name', data.get('name', f'item{idx}'))
        return_values = item.get('returnValues', data.get('returnValues', {}))
        
        # 🔧 Use the same variable naming logic as the main code generation
        if obj_type.startswith("Create"):
            # Create* naming logic (matching main function)
            base_name = f"c{name}"
            
            # Handle duplicate name collisions (same as main function)
            if base_name in definedSymbols:
                import re
                match = re.match(r'^(.+?)(\d+)$', name)
                if match:
                    base_part, existing_num = match.groups()
                    suffix_num = int(existing_num) + 1
                else:
                    base_part = name
                    suffix_num = 2
                
                while f"c{base_part}{suffix_num}" in definedSymbols:
                    suffix_num += 1
                
                unique_name = f"{base_part}{suffix_num}"
                base_name = f"c{unique_name}"
            
            definedSymbols.add(base_name)
        else:
            # Legacy naming logic (matching main function)
            type_prefix = get_type_prefix(obj_type)
            prefixMap = {'Object': 'b', 'Node': 'n', 'Marker': 'm', 'Load': 'l', 'Sensor': 's'}
            prefix = prefixMap.get(type_prefix, None)
            if prefix is None:
                debugLog(f"⚠️ [EXACT MAPPING] Could not determine valid prefix for {obj_type}")
                continue
            
            creationID = item.get('creationIndex', typeCounter[prefix])
            
            # Use consistent naming with unique suffixes
            # For legacy items, name comes from top-level item, not data
            item_name = item.get('name', data.get('name', obj_type))
            
            # Check if this name would conflict
            candidate_base = f"l{item_name}"
            if candidate_base in definedSymbols:
                # Add suffix to make it unique
                item_name = f"{item_name}{creationID}"
            base_name = f"l{item_name}"
            typeCounter[prefix] = max(typeCounter[prefix], creationID + 1)
            definedSymbols.add(base_name)
        
        debugLog(f"🔍 [EXACT MAPPING] Processing {obj_type} '{name}' → '{base_name}' with returnValues: {return_values}")
        
        # Map each return value to its exact index with typed variable names
        if isinstance(return_values, dict):
            for return_type, index_value in return_values.items():
                # Convert string indices to integers for consistent mapping
                if isinstance(index_value, str) and index_value.isdigit():
                    index_value = int(index_value)
                if isinstance(index_value, int) and return_type in exact_mappings:
                    # Create typed variable name (e.g., lPoint_nodeNumber)
                    typed_var_name = f"{base_name}_{return_type}"
                    exact_mappings[return_type][index_value] = typed_var_name
                    debugLog(f"� [EXACT MAPPING] {return_type}[{index_value}] → '{typed_var_name}'")
        
        # Handle special cases where objects should have return values but don't in the data
        if obj_type == 'CreateGround' and return_values.get('bodyNumber') is None:
            # Ground objects always have bodyNumber equal to their objectNumber
            object_number = return_values.get('objectNumber')
            if object_number is not None:
                # Create a typed variable name for bodyNumber
                if isinstance(object_number, str) and object_number.isdigit():
                    object_number = int(object_number)
                if isinstance(object_number, int):
                    typed_body_var_name = f"{base_name}_bodyNumber"
                    debugLog(f"� [EXACT MAPPING] Adding implicit bodyNumber mapping for Ground: bodyNumber[{object_number}] → '{typed_body_var_name}'")
                    if exact_mappings['bodyNumber'].get(object_number) is None:
                        exact_mappings['bodyNumber'][object_number] = typed_body_var_name
    
    # 🔧 Cross-map markerBodyMass to markerNumber for consistent referencing
    # Mass points create markerBodyMass, but other items reference them via markerNumbers
    if exact_mappings['markerBodyMass']:
        debugLog("🔧 [EXACT MAPPING] Cross-mapping markerBodyMass to markerNumber for consistent referencing...")
        for index, symbol in exact_mappings['markerBodyMass'].items():
            if index not in exact_mappings['markerNumber']:
                exact_mappings['markerNumber'][index] = symbol
                debugLog(f"� [EXACT MAPPING] Cross-mapped markerBodyMass to markerNumber: {index} → {symbol}")
            else:
                debugLog(f"🔧 [EXACT MAPPING] markerNumber[{index}] already exists: {exact_mappings['markerNumber'][index]}")
    
    # debugLog final mapping summary
    debugLog("📋 [EXACT MAPPING] Final index mappings:")
    for return_type, mapping in exact_mappings.items():
        if mapping:
            debugLog(f"   {return_type}: {mapping}")
    
    return exact_mappings

def convertGraphicsToCompactFormat(graphics_data):
    """
    Convert graphics objects to compact dictionary format for storage.
    This reduces memory usage when saving modelSequence.
    """
    if not isinstance(graphics_data, list):
        return graphics_data
    
    compact_list = []
    for item in graphics_data:
        if hasattr(item, '__class__') and hasattr(item.__class__, '__name__'):
            # This is a graphics object, convert to compact format
            class_name = item.__class__.__name__
            
            # Get the object's attributes as a dictionary
            if hasattr(item, '__dict__'):
                args_dict = item.__dict__.copy()
                compact_list.append({
                    'name': f'graphics.{class_name}',
                    'args': args_dict,
                    'compact': True  # Flag to indicate this is compact format
                })
            else:
                # Fallback for objects without __dict__
                compact_list.append({
                    'name': f'graphics.{class_name}',
                    'args': '**kwargs',  # Placeholder
                    'compact': True
                })
        elif isinstance(item, dict) and 'name' in item:
            # Already in dictionary format
            compact_list.append(item)
        else:
            # Unknown format, keep as-is
            compact_list.append(item)
    
    return compact_list

def expandGraphicsFromCompactFormat(graphics_data):
    """
    Expand compact graphics dictionary format back to objects if needed.
    """
    if not isinstance(graphics_data, list):
        return graphics_data
    
    expanded_list = []
    for item in graphics_data:
        if isinstance(item, dict) and item.get('compact', False):
            # This is compact format, we can keep it as dict for code generation
            # Remove the compact flag for cleaner output
            clean_item = item.copy()
            clean_item.pop('compact', None)
            expanded_list.append(clean_item)
        elif isinstance(item, dict) and 'name' in item and 'args' in item:
            # Already in the correct format for code generation
            expanded_list.append(item)
        else:
            # Keep as-is
            expanded_list.append(item)
    
    return expanded_list

def preprocessItemsForCodeGeneration(items):
    """
    Preprocess items to ensure graphics data is in the correct format for code generation.
    This handles both compact and expanded formats seamlessly.
    """
    processed_items = []
    for item in items:
        # Create a copy to avoid modifying the original
        import copy
        processed_item = copy.deepcopy(item)
        
        # Process graphics data in the main item
        graphics_fields = ['graphicsDataList', 'VgraphicsData', 'graphicsData']
        for field in graphics_fields:
            if field in processed_item:
                processed_item[field] = expandGraphicsFromCompactFormat(processed_item[field])
        
        # Process graphics data in the nested 'data' field
        if 'data' in processed_item and isinstance(processed_item['data'], dict):
            for field in graphics_fields:
                if field in processed_item['data']:
                    processed_item['data'][field] = expandGraphicsFromCompactFormat(processed_item['data'][field])
        
        processed_items.append(processed_item)
    
    return processed_items
