# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: core/fieldValidation.py
#
# Description:
#     Helper functions to validate required fields and auto-fill missing values

# Import debug system
try:
    from . import debug
    # Create wrapper functions that always check the current debug state
    def debugInfo(msg, origin=None, category=None):
        if debug.isDebugEnabled():
            return debug.debugInfo(msg, origin, category)
    def debugWarning(msg, origin=None, category=None):
        if debug.isDebugEnabled():
            return debug.debugWarning(msg, origin, category)
    def debugError(msg, origin=None, category=None):
        if debug.isDebugEnabled():
            return debug.debugError(msg, origin, category)
    def debugTrace(msg, origin=None, category=None):
        if debug.isDebugEnabled():
            return debug.debugTrace(msg, origin, category)
    def debugField(msg, origin=None, level=None):
        if debug.isDebugEnabled():
            return debug.debugInfo(msg, origin, debug.DebugCategory.FIELD)
    DebugCategory = debug.DebugCategory
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

# Only log if debug mode is actually enabled (avoid early import messages)
# debugInfo("fieldValidation.py loaded", origin="fieldValidation.py", category=DebugCategory.FIELD)
# ^ Commented out to avoid import-time debug messages that can't be silenced
#     when building Create* function calls in the GUI. Also performs type checking.
#
# Authors:  Michael Pieber
# Date:     2025-05-16
# Notes:    Ensures all mandatory arguments are provided and correctly typed.
#
# License:  BSD-3 license
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import inspect
import numpy as np

import exudyn as exudyn
import exudyn.utilities as exuutils


import exudyn.graphics as gfx

# Debug compatibility layer
try:
    # Legacy compatibility for existing debugLog calls
    def debugLog(msg, origin=None, summarize=False):
        # Always check the current debug state, don't cache the functions
        if not debug.isDebugEnabled():
            return
        if "❌" in msg or "Error" in msg or "Failed" in msg:
            debug.debugError(msg, origin=origin, category=debug.DebugCategory.FIELD)
        elif "⚠️" in msg or "Warning" in msg:
            debug.debugWarning(msg, origin=origin, category=debug.DebugCategory.FIELD)
        else:
            debug.debugInfo(msg, origin=origin, category=debug.DebugCategory.FIELD)
except ImportError:
    try:
        from exudynGUI.core.debug import debugLog
    except ImportError:
        # Fallback if debug module not available
        def debugLog(msg, origin=None, summarize=False):
            pass

from exudynGUI.functions import userFunctions
from exudynGUI.functions.graphicsVisualizations import graphicsDataRegistry

from exudynGUI.core.variableManager import evaluateExpression, loadUserVariables


from exudynGUI.guiForms.specialWidgets import (
    buildGraphicsEditorWidget as buildGraphicsDataWidget,
    buildUserFunctionWidget,
    buildIndexSelectorWidget,
    buildMultiIndexSelectorWidget,
    buildVec3Widget,
    buildMatrix3x3Widget,
    MultiComponentSelectorWidget,
)
from exudyn.exudynCPP import ObjectIndex, NodeIndex, MarkerIndex, LoadIndex, SensorIndex


CURRENT_USER_VARS = loadUserVariables()

def validateVariableExpression(val, userVars=None):
    if userVars is None:
        userVars = CURRENT_USER_VARS
    try:
        evaluateExpression(val, userVars)
        return True
    except:
        return False


EXUDYN_INDEX_TYPES = (ObjectIndex, NodeIndex, MarkerIndex, LoadIndex, SensorIndex)

def validateGraphicsDataUserFunction(key, value):
    if value in (0, '0', '', None, 'None'):
        return None  # Explicitly no user function
    return value  # Else pass through (could be a function reference or name)

def validateNodeNumber(key, value):
    if isinstance(value, int) and value >= 0:
        return True, ""
    if isinstance(value, str) and value.startswith('n'):
        return True, ""
    return False, f"Invalid nodeNumber: {value}"

def validateBodyNumber(key, value):
    if isinstance(value, int) and value >= 0:
        return True, ""
    if isinstance(value, str) and value.startswith('b'):  # symbolic reference like 'b0'
        return True, ""
    return False, f"Invalid bodyNumber: {value}"

def validateMarkerNumber(key, value):
    if isinstance(value, int) and value >= 0:
        return True, ""
    if isinstance(value, str) and value.startswith('m'):
        return True, ""
    return False, f"Invalid markerNumber: {value}"

def validateSensorNumber(key, value):
    if isinstance(value, int) and value >= 0:
        return True, ""
    if isinstance(value, str) and value.startswith('s'):
        return True, ""
    return False, f"Invalid sensorNumber: {value}"


def validateLoadNumber(key, value):
    if isinstance(value, int) and value >= 0:
        return True, ""
    if isinstance(value, str) and value.startswith('l'):
        return True, ""
    return False, f"Invalid loadNumber: {value}"

def validateDistance(key, val):
    # Accept None (meaning “leave blank to compute automatically”) or any numeric value.
    if val is None:
        return True, ""
    if isinstance(val, (int, float)):
        return True, ""
    return False, f"'{key}' must be a number or left blank"

def unwrapExudynIndex(value):
    if isinstance(value, EXUDYN_INDEX_TYPES):
        return int(value)
    return value

def validateInt(key, value):
    return isinstance(value, int), f"Expected int for {key}"

def validateFloat(key, value):
    if value is None:
        return True, ""
    return isinstance(value, (int, float)), f"Expected float for {key}"

def validatePositiveFloat(key, value):
    return isinstance(value, (int, float)) and value >= 0, f"Expected non-negative float for {key}"

def validateString(key, value):
    return isinstance(value, str), f"Expected string for {key}"

def validateBool(key, value):
    if isinstance(value, bool):
        return True, ""
    return False, f"Expected boolean for {key}"

def validateIndex(key, value):
    return isinstance(value, int) and value >= 0, f"Expected valid index (>= 0) for {key}"

def validateList(key, value):
    # ✅ Allow None values to pass validation silently
    if value is None:
        return True, ""
    return isinstance(value, list), f"Expected list for {key}"



def validateVector3(key, value, expectedLength=3):
    import numpy as np
    
    # ✅ Allow None values to pass validation silently
    if value is None:
        return True, ""
    
    # 1) If it's literally a list/tuple of numbers, accept as before:
    if isinstance(value, (list, tuple)) \
       and len(value) == expectedLength \
       and all(isinstance(v, (int, float)) for v in value):
        return True, ""

    # 2) If it's a numpy array of correct length, also accept:
    if isinstance(value, np.ndarray) and value.ndim == 1 and value.shape[0] == expectedLength:
        return True, ""

    # 3) NEW: if it's a list/tuple of exactly three strings, allow it (we'll eval them later):
    if isinstance(value, (list, tuple)) \
       and len(value) == expectedLength \
       and all(isinstance(v, str) for v in value):
        return True, ""

    # 4) Otherwise, it's invalid:
    return False, f"'{key}' must be a {expectedLength}D vector of numbers or symbolic names"



def validateVector4(key, value):
    # ✅ Allow None values to pass validation silently
    if value is None:
        return True, ""
    return isinstance(value, list) and len(value) == 4, f"Expected 4D vector for {key}"



def validateMatrix3x3(key, value):
    """Validate a 3x3 matrix of floats."""
    import ast
    label = key if key else 'value'
    
    # ✅ Allow None values to pass validation silently
    if value is None:
        return True, ""
    
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except Exception as e:
            return False, f"Invalid matrix string for {label}: {e}"

    if not isinstance(value, list) or len(value) != 3:
        return False, f"{label} must be a 3x3 list of lists"
    for row in value:
        if not isinstance(row, list) or len(row) != 3:
            return False, f"Each row in {label} must contain 3 values"
        for item in row:
            if not isinstance(item, (int, float)):
                return False, f"Matrix elements in {label} must be int or float"
    return True, ""


def validateGraphicsData(key, value):
    if isinstance(value, list):  # minimal check — improve as needed
        return True, ""
    return False, f"Invalid VgraphicsData: must be a list, got {type(value).__name__}"




def validateFunction(key, value):
    return callable(value) or isinstance(value, str), f"Expected callable or function name string for {key}"

def validateMatrix(key, value):
    # ✅ Allow None values to pass validation silently
    if value is None:
        return True, ""
    return isinstance(value, list), f"Expected matrix-like list for {key}"

def validateNonEmptyList(key, value):
    if isinstance(value, (list, tuple)) and len(value) > 0:
        return True, ""
    return False, f"'{key}' must be a non-empty list"

def validateSquareMatrix(key, value):
    # ✅ Allow None values to pass validation silently
    if value is None:
        return True, ""
    if isinstance(value, list) and all(isinstance(row, list) for row in value):
        size = len(value)
        if all(len(row) == size for row in value):
            return True, ""
    return False, f"'{key}' must be a square matrix (list of equal-length lists)"

def validateVector(key, value):
    """Validate that value is a 1D list-like vector (list, tuple, or np.array)."""
    import numpy as np
    
    # ✅ Allow None values to pass validation silently
    if value is None:
        return True, ""
    
    if isinstance(value, (list, tuple)) and all(isinstance(v, (int, float)) for v in value):
        return True, ""
    if isinstance(value, np.ndarray) and value.ndim == 1:
        return True, ""
    return False, f"'{key}' must be a 1D list, tuple, or numpy array of numbers"

def validateDict(key, value):
    return isinstance(value, dict), f"Expected dict for {key}"

def isEmpty(value):
    if value is None:
        return True
    if isinstance(value, (str, list, dict, tuple)):
        return len(value) == 0
    if isinstance(value, np.ndarray):
        return value.size == 0
    return False

def validateRotationMatrix(x):
    try:
        if isinstance(x, str):
            x = eval(x, {"np": np})
        arr = np.array(x)
        if arr.shape != (3, 3):
            raise ValueError("Not a 3x3 matrix")
        return arr
    except Exception as e:
        raise ValueError(f"Invalid rotation matrix: {e}")
        
def simpleValidator(typeCheck, typeName):
    return lambda name, v: (typeCheck(v), "" if typeCheck(v) else f"{name} must be a {typeName}.")

def validatorUserFunction():
    return lambda name, v: (
        isinstance(v, (int, str)) or callable(v),
        "" if (isinstance(v, (int, str)) or callable(v)) else f"{name} must be an int, str, or callable (function)."
    )
def isUserFunctionField(fieldName: str) -> bool:
    lname = fieldName.lower()
    return lname.endswith("userfunction") or "userfunction" in lname or lname.startswith("uf")

def validateScalar(key, value):
    return isinstance(value, (int, float)), f"{key} must be a float or int"

def validateListOfInts(key, value):
    if isinstance(value, list):
        # Accept dummy [None, None] fallback for unused exclusive fields
        if all(v is None for v in value): # ✅ [None, None] is used to zero out inactive exclusive options (e.g. bodyList vs bodyNumbers)
            return True, ""
        if all(isinstance(v, int) for v in value):
            return True, ""
    return False, f"'{key}' must be a list of integers"

def validateIntVector3(key, value):
    return isinstance(value, list) and len(value) == 3 and all(isinstance(v, int) for v in value), f"{key} must be a list of 3 integers"

def validateIntVector6(key, value):
    return isinstance(value, list) and len(value) == 6 and all(isinstance(v, int) for v in value), f"{key} must be a list of 6 integers"


def validateGraphicsDataList(key, gList):
    # ✅ Allow None values to pass validation silently
    if gList is None:
        return True, ""
    if not isinstance(gList, list):
        return False, f"{key} is not a list"
    for entry in gList:
        # Accept both dict format {'name': ..., 'args': ...} and compact string format 'exu.graphics.NAME(...)'
        if isinstance(entry, dict):
            if 'name' not in entry or 'args' not in entry:
                return False, f"{key} entry must have 'name' and 'args'; got: {entry}"
        elif isinstance(entry, str):
            # Accept compact string format like 'exu.graphics.Sphere(...)'
            if not (entry.startswith('exu.graphics.') and '(' in entry and entry.endswith(')')):
                return False, f"{key} entry must be either dict with 'name'/'args' or compact string 'exu.graphics.NAME(...)'; got: {entry}"
        else:
            return False, f"{key} entry must be either dict with 'name'/'args' or compact string; got: {entry}"
    return True, ""

def validateFloatOrExpressionVector6(key, value):
    """
    Validate that 'value' is either a 6D vector (list/tuple/numpy array of 6 numbers)
    or a string expression that evaluates to such a vector.
    """
    import numpy as np
    # If already a list, tuple, or numpy array, verify its length and numeric content:
    if isinstance(value, (list, tuple, np.ndarray)):
        if len(value) != 6:
            return False, f"Expected a 6D vector for {key}, but got length {len(value)}"
        try:
            # Verify each element is castable to float:
            vector = [float(x) for x in value]
            return True, ""
        except Exception as e:
            return False, f"Non-numeric element in {key}: {e}"
    # If a string is provided, try evaluating it:
    elif isinstance(value, str):
        try:
            evaluated = eval(value, {"__builtins__": None}, {})
            if isinstance(evaluated, (list, tuple, np.ndarray)) and len(evaluated) == 6:
                # Optionally verify numeric content
                vector = [float(x) for x in evaluated]
                return True, ""
            else:
                return False, f"Evaluated expression for {key} is not a 6D vector."
        except Exception as e:
            return False, f"Could not evaluate {key} expression: {e}"
    else:
        return False, f"Invalid type for {key}; expected a 6D vector or a string expression."
   

def validateFloatOrExpressionVector3(key, value):
    """Validate a 3D vector of floats or expressions."""
    # Accepts list/tuple of 3 floats or strings (expressions)
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return False, f"{key} must be a 3D vector (list/tuple of 3 elements)"
    for v in value:
        if not (isinstance(v, (float, int, str))):
            return False, f"{key} element '{v}' is not a float/int/str"
    return True, None


def validateAny1DArray(key, value):
    return isinstance(value, np.ndarray) and value.ndim == 1, f"{key} must be a 1D NumPy array"


def validateMatrixContainer(key, value):
    # ✅ Allow None values to pass validation silently
    if value is None:
        return True, ""
    # Replace with appropriate type check, e.g. for dict, sparse format, etc.
    return isinstance(value, dict) or hasattr(value, 'shape'), f"Expected matrix container for {key}"

import re
def makeMatrixValidator(shape):
    def validator(key, value):
        if isinstance(value, np.ndarray):
            if value.shape == shape:
                return True, ""
        if isinstance(value, list):
            if len(value) == shape[0] and all(isinstance(row, list) and len(row) == shape[1] for row in value):
                return True, ""
        return False, f"{key} must be a {shape[0]}x{shape[1]} matrix"
    return validator


def validateMatrixND(key, value):
    # ✅ Allow None values to pass validation silently
    if value is None:
        return True, ""
    if isinstance(value, np.ndarray):
        if value.shape == (3, 3):
            return True, ""
    if isinstance(value, list):
        if len(value) == 3 and all(isinstance(row, list) and len(row) == 3 for row in value):
            return True, ""
    return False, f"{key} must be a 3x3 matrix"




PATTERN_VALIDATORS = [
    (re.compile(r'^ndarray\(\d+,\)$'), lambda k, v: validateVector(k, v)),
    (re.compile(r'^ndarray\(6,6\)$'), makeMatrixValidator((6, 6))),  # ✅ Specific for (6,6)
    (re.compile(r'^ndarray\(\d+,\d+\)$'), lambda k, v: validateMatrix(k, v)),  # fallback
    (re.compile(r'^ndarray\(6,\s*6\)$'), validateMatrixND),
]





VALIDATORS_BY_TYPE = {
    'bool': simpleValidator(lambda v: isinstance(v, bool), "boolean"),
    'userfunction': validatorUserFunction(),
    'graphicsdata': validateGraphicsDataList,
    'vector4': validateVector4,
    'nparray1D': validateVector,
    # Add more as needed
    'int': validateInt,
    'float': validateFloat,
    'positiveFloat': validatePositiveFloat,
    'string': validateString,
    'function': validateFunction,

    # Containers
    'list': validateList,
    'vector3[ndarray]': validateVector3,
    'vector3[list]': validateVector3,
    'vector4[list]': validateVector4,
    'matrix3x3[list]': validateMatrix3x3,
    'matrix': validateMatrix,
    'nparray2D': validateMatrix,
    'matrix3x3': validateMatrix3x3,
    'vector3': validateVector3,
    
    'intvector3': validateIntVector3,
    'intvector6': validateIntVector6,

    'list_objectindex': validateListOfInts,
    'list_nodeindex': validateListOfInts,
    'list_markerindex': validateListOfInts,
    'list_sensorindex': validateListOfInts,
    'list_forceindex': validateListOfInts,

    'skip': lambda k, v: (True, ""),  # Bypass type
}

VALIDATORS_BY_KEY = {
    #node, marker, body numbervalidators
    "nodeNumber": validateNodeNumber,
    "bodyNumber": validateBodyNumber,
    "markerNumber": validateMarkerNumber,
    # Vectors and offsets (commonly 3D) - BUT NOT for legacy items with known scalar types
    'referenceposition': validateVector3,
    # 'offset': validateVector3,  # ❌ REMOVED: This overrides metadata for legacy items  
    'position': validateVector3,
    'velocityoffset': validateFloat,
    'velocity': validateVector3,
    'initialvelocity': validateVector3,  # For 3D velocity vectors
    'acceleration': validateVector3,
    # ✅ Scalar velocity fields that should NOT be validated as vectors
    'minimumimpactvelocity': validateFloat,
    'nparray2D': validateMatrix,

    # Rotation matrices
    'massmatrix': validateMatrixContainer,
    'dampingmatrix': validateMatrixContainer,
    'rotationmatrix': validateMatrix3x3,
    'referencerotationmatrix': validateMatrix3x3,
    'referenceRotationMatrix': lambda x: np.array(eval(x)) if isinstance(x, str) else np.array(x),
    "stiffnessmatrix": validateMatrixContainer,
    "massmatrixreduced": validateMatrixContainer,
    "stiffnessmatrixreduced": validateMatrixContainer,
    "dampingmatrixreduced": validateMatrixContainer,
    
    'graphicsDataUserFunction': validateGraphicsDataUserFunction,

    # Color (RGBA vector, expected to be length 4)
    'color': lambda k, v: (
        isinstance(v, list) and len(v) == 4,
        f"Expected RGBA color list of length 4 for {k}"
    ),


    # Misc heuristics
    'mass': validateFloat,
    'springconstant': validateFloat,
    'frequency': validateFloat,
    'amplitude': validateFloat,
    # Name fields
    'name': validateString,
}
TYPE_NORMALIZATION = {
    'ndarray(0, 0)': 'nparray2D',
    'ndarray(6,)': 'nparray1D',
    'graphicsdata': 'graphicsdata',
    'userFunction': 'userfunction',
    'list[ObjectIndex]': 'list_objectindex',
    'list[NodeIndex]': 'list_nodeindex',
    'list[MarkerIndex]': 'list_markerindex',
    'list[LoadIndex]': 'list_markerindex',
    'list[SensorIndex]': 'list_markerindex',
    'ndarray(0,)': 'nparray1D',
    'matrix3x3[ndarray]': 'matrix3x3',
    'vector3[ndarray]': 'vector3',
    'list[objectindex]': 'list',
    'NodeNumber': 'int',
    'ObjectNumber': 'int',
    'MarkerNumber': 'int',
    'SensorNumber': 'int',
    'ForceNumber': 'int',
    'BodyNumber': 'int',
    'dict': 'list',  # or 'skip' if you prefer
    'NodeType': 'int',
    'ObjectType': 'int',  # if you have it
    'AccessFunctionType': 'int',
    'ArrayIndex': 'list',
    'ArrayIndex&': 'list',
    'ArrayMarkerIndex': 'list',
    'ArrayNodeIndex': 'list',
    'ArraySensorIndex': 'list',
    'BeamSection': 'list',
    'BeamSectionGeometry': 'list',
    'Bool': 'bool',
    'CNodeGroup': 'int',
    'CNodeODE2*': 'int',
    'CObjectType': 'int',
    'ConstSizeVector<maxRotationCoordinates>': 'list',
    "constrainedAxes": "intVector6",
    "rotationMatrixAxes": "matrix3x3",
    'Float4': 'vector4[list]',
    'HomogeneousTransformation': 'matrix3x3[list]',
    'Index': 'int',
    'InertiaList': 'list',
    'JacobianType::Type': 'int',
    'JointTypeList': 'list',
    'LinkedDataVector': 'list',
    'LoadIndex': 'int',
    'LoadType': 'int',
    'Marker::Type': 'int',
    'MarkerIndex': 'int',
    'Matrix2D': 'list',
    'Matrix3D': 'matrix3x3[list]',
    'Matrix3DList': 'list',
    'Matrix6D': 'list',
    'Node::Type': 'int',
    'NodeIndex': 'int',
    'NodeIndex2': 'list',
    'NodeIndex3': 'list',
    'NodeIndex4': 'list',
    'NumpyMatrix': 'list',
    'NumpyMatrixI': 'matrix',
    'NumpyVector': 'list',
    'ObjectIndex': 'int',
    'OutputVariableType': 'int',
    'PInt': 'int',
    'PReal': 'float',
    'PyFunctionMatrixContainerMbsScalarIndex2Vector': 'function',
    'PyFunctionMatrixContainerMbsScalarIndex2Vector2Scalar': 'function',
    'PyFunctionMatrixContainerMbsScalarIndex2VectorBool': 'function',
    'PyFunctionMatrixMbsScalarIndex2Vector': 'function',
    'PyFunctionMbsScalar2': 'function',
    'PyFunctionMbsScalarIndexScalar': 'function',
    'PyFunctionMbsScalarIndexScalar11': 'function',
    'PyFunctionMbsScalarIndexScalar5': 'function',
    'PyFunctionMbsScalarIndexScalar9': 'function',
    'PyFunctionVector3DmbsScalarIndexScalar4Vector3D': 'function',
    'PyFunctionVector3DmbsScalarVector3D': 'function',
    'PyFunctionVector6DmbsScalarIndex4Vector3D2Matrix6D2Matrix3DVector6D': 'function',
    'PyFunctionVector6DmbsScalarIndexVector6D': 'function',
    'PyFunctionVectorMbsScalarArrayIndexVectorConfiguration': 'function',
    'PyFunctionVectorMbsScalarIndex2Vector': 'function',
    'PyFunctionVectorMbsScalarIndex2VectorBool': 'function',
    'PyFunctionVectorMbsScalarIndex4VectorVector3D2Matrix6D2Matrix3DVector6D': 'function',
    'PyFunctionVectorMbsScalarIndexVector': 'function',
    'PyMatrixContainer': 'matrix',
    'Real': 'float',
    'ResizableMatrix': 'list',
    'ResizableVector': 'list',
    'STDstring': 'string',
    'SensorIndex': 'int',
    'SensorType': 'int',
    'SlimVector<nSFperNode*nNodes>': 'list',
    'String': 'string',
    'Transformation66List': 'list',
    'UInt': 'int',
    'UReal': 'positiveFloat',
    'Vector': 'list',
    'Vector2D': 'list',
    'Vector3D': 'vector3[list]',
    'Vector3DList': 'vector3[list]',
    'Vector4D': 'vector4[list]',
    'Vector6D': 'list',
    'Vector6DList': 'list',
    'Vector7D': 'list',
    'Vector9D': 'list',
    'bool': 'bool',
    'const ArrayIndex&': 'list',
    'const char*': 'string',
    'float': 'float',
    'template<class TReal, Index ancfSize> void': 'skip',
    'template<class TReal> void': 'skip',
    'template<typename TReal> TReal': 'skip',
    'void': 'skip',
}










DRAW_SIZE_VECTOR_OBJECTS = {"CreateRigidBody", "CreateMassPoint"}  # Extend as needed

# --- Default value heuristics ---
def guessDefaultValue(name, metaType=None, objectType=None):
    lname = name.lower()
    # Special case: 6D offset for CreateRigidBodySpringDamper
    if objectType == "CreateRigidBodySpringDamper" and lname == "offset":
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    if lname in ['bodynumber', 'markernumber', 'nodenumber', 'objectnumber']:
        return 0
    elif lname == 'drawsize':
        return 0.1
    elif lname in ['bodynumbers', 'markernumbers', 'nodenumbers', 'objectnumbers', 'bodyornodelist']:
        return [0, 1]
    elif lname in ['referenceposition', 'initialdisplacement', 'initialvelocity', 'gravity', 'position', 'offset']:
        return [0.0, 0.0, 0.0]
    elif 'rotationmatrix' in lname:
        return np.eye(3).tolist()
    elif 'color' in lname:
        return [-1.0, -1.0, -1.0, -1.0]

    
    return None




def isMeaningfulDefault(val, fieldName=None):
    """Return False for common placeholders like -1, None, '', empty list/dict, or field-specific dummy values."""

    if val is None:
        return False

    if isinstance(val, (int, float, str)) and val in [-1, '', 'default', 'not set']:
        return False

    if isinstance(val, (list, tuple, dict)) and len(val) == 0:
        return False

    # --- NEW: Catch all-zero NumPy arrays ---
    if isinstance(val, np.ndarray):
        if val.size == 0 or np.all(val == 0):
            return False

    # --- NEW: Also catch all-zero vectors/lists ---
    if isinstance(val, (list, tuple)) and all(isinstance(v, (int, float)) and v == 0 for v in val):
        return False

    if isinstance(val, (list, tuple)) and all(
        isinstance(row, (list, np.ndarray)) and all(isinstance(v, (int, float)) and v == 0 for v in row)
        for row in val
    ):
        return False  # 3x3 zero matrix

    # Field-specific overrides
    if fieldName:
        lname = fieldName.lower()

        if lname in ['bodynumber', 'markernumber', 'nodenumber', 'objectnumber']:
            return not (isinstance(val, int) and val == -1)

        if lname in ['physicsmass', 'mass', 'stiffness', 'damping', 'springconstant']:
            return not (isinstance(val, (float, int)) and val == 0.0)

        if isinstance(val, int) and val == -1 and 'number' in lname:
            return False

    return True



_knownFieldDefaults = {
    'show': True,
    'drawSize': -1.0,
    'color': [1.0, 0.0, 0.0, 1.0],  # Default red color (RGBA)
    'graphicsdatauserfunction': 0,
    'intrinsicformulation': False,
    'bodyNumber': 0,  # Default to first body
    'graphicsDataList': [],  # Default to empty list
    'nodeNumber': 0,  # Default to first node
    'markerNumber': 0,  # Default to first marker
    'objectNumber': 0,  # Default to first object
    'loadNumber': 0,  # Default to first load
}

_knownFieldValidators = {
    'show': validateBool,
    'drawsize': validateFloat,
    'color': validateVector4,  # you may need to define this
    'bodyfixed': validateBool,        # ✅ corrects type from 'int' to 'bool'
    'loadvector': validateVector3,    # ✅ corrects type from NoneType to vector
    'intrinsicformulation': validateBool,
}

def getDefaultForField(fieldName: str):
    lname = fieldName.lower()
    return _knownFieldDefaults.get(lname, None)

def getValidatorForField(fieldName: str):
    lname = fieldName.lower()
    return _knownFieldValidators.get(lname, None)

def tryParseMatrix3x3(value):
    import numpy as np
    try:
        if isinstance(value, str):
            arr = np.array(eval(value))
            if arr.shape == (3, 3):
                return arr.tolist()
    except Exception:
        pass
    return None

def validateAndPrepareFields(mbs, typeName, data):
    """Validate and auto-fill missing fields using fieldMetadata and guessDefaultValue."""

    from exudynGUI.core.fieldMetadata import FieldMetadataBuilder
    # from exudynGUI.core.fieldValidation import isMeaningfulDefault
    from exudynGUI.core.fieldValidation import tryValidateField
    from .specialFields import SPECIAL_FIELD_HANDLERS
    from exudynGUI.core.debug import debugLog
    import inspect
    import re
    import ast

    def isEmpty(value):
        return value is None or (isinstance(value, str) and value.strip() == '') or (isinstance(value, (list, dict, tuple)) and len(value) == 0)

    def tryParseMatrix3x3(val):
        if isinstance(val, str):
            try:
                val = ast.literal_eval(val)
            except Exception:
                return None
        if isinstance(val, list) and len(val) == 3 and all(isinstance(row, list) and len(row) == 3 for row in val):
            return val
        return None

    builder = FieldMetadataBuilder(useExtracted=True)
    metadata = builder.build(typeName)

    method = getattr(mbs, typeName, None)
    sig = inspect.signature(method) if callable(method) and typeName.startswith("Create") else None
    fieldsToCheck = sig.parameters.keys() if sig else metadata.keys()

    missingFields = []
    failedFields = []

    for name in fieldsToCheck:
        if name == "returnDict":
            continue

        value = data.get(name)

        if name.endswith("UserFunction"):
            if isinstance(value, str) and value.startswith("UF"):
                debugLog(f"[validateAndPrepareFields] 🧩 Retained symbolic user function: {name} = '{value}'")
                continue  # skip normalization, it’s valid
            if value in ["None", "", None, '0']:
                value = 0
                data[name] = 0
                debugLog(f"[validateAndPrepareFields] 🧩 Normalized {name} = 0 (explicit empty)")


        if isEmpty(value):
            meta = metadata.get(name, {})
            metaDefault = meta.get("defaultValue", meta.get("default", None))

            # --- PATCH: Robust fallback for 'name' field ---
            if name == 'name':
                nameFieldPresent = isinstance(data.get("name"), str) and data["name"].strip() != ''
                debugLog(f"[validateAndPrepareFields] [LEGACY PATCH] nameFieldPresent = {nameFieldPresent}")
                if nameFieldPresent:
                    continue
            # --- END PATCH ---

            if name.lower() == 'drawsize' and value is None and metaDefault is None:
                metaDefault = -1.0

            # 0. Specific override: typeName + name combo for 6D offset
            if typeName == "CreateRigidBodySpringDamper" and name.lower() == "offset":
                data[name] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                debugLog(f"[validateAndPrepareFields] 🧩 Filled {name} = {[0.0]*6} for CreateRigidBodySpringDamper")
                continue

            if name.lower() == 'drawsize' and isinstance(metaDefault, list):
                metaDefault = 0.1

            if isMeaningfulDefault(metaDefault, name):
                data[name] = metaDefault
                debugLog(f"[validateAndPrepareFields] 🧩 Filled {name} = {repr(metaDefault)} from metadata")
            elif name == "graphicsDataList":
                data[name] = []
            elif name == "graphicsDataUserFunction":
                data[name] = None
            else:
                required = meta.get("required", True)
                if not required or meta.get("guiOnly", False):
                    continue
                missingFields.append(name)
                debugLog(f"[validateAndPrepareFields] ❌ Missing required field: {name}")

    for key, val in list(data.items()):
        meta = metadata.get(key, {})
        metaType = meta.get("type", "")

        # --- Robust normalization for 'offset' fields (3D or 6D depending on type) ---
        if key.lower() == 'offset' and isinstance(val, str):
            import ast
            txt = val.strip()
            if txt.startswith("[") and txt.endswith("]"):
                try:
                    parsed = ast.literal_eval(txt)
                    # Determine expected length from metaType (vector3[list] or vector6[list])
                    expectedLength = 3
                    if metaType in ("vector6[list]", "vector6[ndarray]", "Vector6D", "vector6"):
                        expectedLength = 6
                    elif metaType in ("vector3[list]", "vector3[ndarray]", "Vector3D", "vector3"):
                        expectedLength = 3
                    elif isinstance(parsed, (list, tuple)):
                        expectedLength = len(parsed)  # fallback: use length of parsed
                    if isinstance(parsed, (list, tuple)) and len(parsed) == expectedLength:
                        data[key] = list(parsed)
                        debugLog(f"[validateAndPrepareFields] 🩹 Normalized string 'offset' to list (len={expectedLength}) for '{key}': {parsed}")
                except Exception as e:
                    failedFields.append((key, f"Could not parse 'offset' string: {e}"))
                    continue

        # --- DEBUG: Log offset type/value after normalization ---
        if key.lower() == 'offset':
            debugLog(f"[validateAndPrepareFields] [DEBUG] After normalization: offset type={type(data[key])}, value={data[key]}")

        # If the user literally typed “[k,k,k]” for a 3-vector,
        # split out the tokens "k","k","k" and keep them as strings:
        if isinstance(val, str) and metaType in ("vector3[list]", "vector3[ndarray]"):
            txt = val.strip()
            if txt.startswith("[") and txt.endswith("]"):
                inner = txt[1:-1]
                tokens = [t.strip() for t in inner.split(",")]
                # tokens is now ["k","k","k"], not numbers
                data[key] = tokens
                debugLog(f"[validateAndPrepareFields] 🩹 Parsed symbolic 3-vector for '{key}': {tokens}")
                # (Don’t try convertToType—leave them as ["k","k","k"] so that
                # validateVector3( ["k","k","k"] ) returns True.)

            else:
                # If they wrote “k” (no brackets), do a single‐symbol fallback:
                try:
                    data[key] = [float(val)]
                except Exception:
                    data[key] = val

        # Your existing matrix3x3 logic:
        elif isinstance(val, str) and metaType == "matrix3x3[list]":
            parsed = tryParseMatrix3x3(val)
            if parsed:
                data[key] = parsed
                debugLog(f"[validateAndPrepareFields] 🩹 Parsed string to matrix for '{key}': {parsed}")
            else:
                failedFields.append((key, f"Invalid matrix string for {key}"))
                continue

        # Otherwise, if it’s still a raw string, let convertToType handle it:
        elif isinstance(val, str):
            from exudynGUI.core.fieldMetadata import convertToType
            try:
                data[key] = convertToType(val, metaType)
            except Exception as e:
                failedFields.append((key, f"Could not convert '{val}' → {metaType}: {e}"))
                continue

        # Finally validate each field after whatever conversion we did:
        valid, msg = tryValidateField(key, data[key], specialFieldHandlers=SPECIAL_FIELD_HANDLERS, objectType=typeName)
        if not valid:
            failedFields.append((key, msg))
            debugLog(f"[validateAndPrepareFields] ❌ Failed validation: {key} → {msg}")

    result = len(missingFields) == 0 and len(failedFields) == 0
    debugLog(f"[validateAndPrepareFields] ✅ Validation result = {result}, missing = {missingFields}, failed = {failedFields}")
    return result, missingFields, failedFields









def getValidator(metaType: str, fieldName: str = "", objectType: str = None):
    fieldNameLower = fieldName.lower()

    # 🔁 Always normalize metaType before all matching
    normalizedType = TYPE_NORMALIZATION.get(metaType, metaType.lower())

    # 1. Match via _knownFieldValidators (field name exact)
    if fieldNameLower in _knownFieldValidators:
        debugLog(f"[getValidator] ✅ Matched '{fieldName}' via _knownFieldValidators")
        return _knownFieldValidators[fieldNameLower]

    # 2. Match via VALIDATORS_BY_KEY (prioritize exact matches, then substring matches)
    # First check for exact matches
    if fieldNameLower in VALIDATORS_BY_KEY:
        validator = VALIDATORS_BY_KEY[fieldNameLower]
        debugLog(f"[getValidator] 🎯 Exact match for '{fieldName}' via VALIDATORS_BY_KEY")
        return validator
    
    # Then check for substring matches, prioritizing longer keys (more specific)
    matching_keys = [(key, validator) for key, validator in VALIDATORS_BY_KEY.items() if key in fieldNameLower]
    if matching_keys:
        # Sort by key length (descending) to prioritize more specific matches
        matching_keys.sort(key=lambda x: len(x[0]), reverse=True)
        key, validator = matching_keys[0]
        debugLog(f"[getValidator] 🔍 Substring match for '{fieldName}' via VALIDATORS_BY_KEY (key: '{key}')")
        return validator

    # 3. Match via VALIDATORS_BY_TYPE (type exact match)
    validator = VALIDATORS_BY_TYPE.get(normalizedType)
    if validator:
        debugLog(f"[getValidator] 🔄 Matched '{fieldName}' via VALIDATORS_BY_TYPE (type: '{normalizedType}')")
        return validator

    # 4. Match via PATTERN_VALIDATORS (normalized type pattern)
    for pattern, validator in PATTERN_VALIDATORS:
        if pattern.match(normalizedType):
            debugLog(f"[getValidator] 🧬 Matched '{fieldName}' via PATTERN_VALIDATORS (pattern: '{pattern.pattern}')")
            return validator

    # 4.5 Fallback for float/int/list if value is a valid variable expression
    def variableFallbackValidator(val):
        return isinstance(val, (int, float, list)) or (isinstance(val, str) and validateVariableExpression(val))

    if normalizedType in ['float', 'real', 'int', 'vector', 'list<float>', 'list<real>', 'list<int>']:
        debugLog(f"[getValidator] 🧪 Using fallback variable-aware validator for type '{normalizedType}'")
        return variableFallbackValidator

    # 5. No match
    debugLog(f"[getValidator] ⚠️ No validator matched for field='{fieldName}', metaType='{metaType}' (normalized: '{normalizedType}')")
    return None




def evalOrStr(val):
    """Evaluate widget content or string to real value if possible."""
    # Extract from widget
    if hasattr(val, "value"):
        val = val.value()
    elif hasattr(val, "text"):
        val = val.text()

    # Early return for safe types
    if isinstance(val, (int, float, list, tuple, dict, bool, type(None), np.ndarray)):
        return val

    # Try eval
    try:
        return eval(val, {
            "__builtins__": {},
            "np": __import__("numpy"),
            "array": np.array,
            "numpy": np,
            "exu": exudyn,
            "exudyn": exudyn,
            "exuUtils": exudyn.utilities,
            "exuGraphics": exudyn.graphics,
            **globals()
        })
    except Exception as e:
        debugLog(f"[evalOrStr] ⚠️ Failed to eval '{val}': {e}")
        return val


def getPlainText(self):
    return self.editor.toPlainText()



def tryValidateField(key, value, typeHint=None, specialFieldHandlers=None, objectType=None):
    value = unwrapExudynIndex(value)
    lname = key.lower()

    # --- SPECIAL CASE: nodeType field (accept any enum with class name 'NodeType') ---
    debugLog(f"[tryValidateField] [DEBUG] key={key!r}, type(value)={type(value)}, value={value}")
    if key.lower() == "nodetype":
        debugLog(f"[tryValidateField] [DEBUG] nodeType special-case check: class={getattr(value, '__class__', None)}, class name={getattr(value.__class__, '__name__', None)}")
        if getattr(value, "__class__", None) and value.__class__.__name__ == "NodeType":
            debugLog(f"[tryValidateField] ✅ Accepted NodeType-like enum for 'nodeType': {value}")
            return True, ""
        else:
            debugLog(f"[tryValidateField] ❌ nodeType special-case did NOT match: type={type(value)}, value={value}")

    # --- SPECIAL CASE: Handle numpy arrays for coordinate fields ---
    if key.lower() in ['referencecoordinates', 'referenceposition', 'position'] and isinstance(value, np.ndarray):
        if value.ndim == 1 and value.shape[0] == 3:
            debugLog(f"[tryValidateField] ✅ Accepted numpy array for '{key}': shape={value.shape}")
            return True, ""
        else:
            debugLog(f"[tryValidateField] ❌ Invalid numpy array shape for '{key}': {value.shape}")
            return False, f"'{key}' numpy array must be 1D with 3 elements, got shape {value.shape}"

    # Allow symbolic expressions as strings like 'm', 'k+3*m'
    if isinstance(value, str):
        stripped = value.strip()
        if re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_+\-*/(). ]*", stripped):
            debugLog(f"[tryValidateField] ✴️ Accepted symbolic expression for '{key}': {value}")
            return True, ""
        else:
            value = evalOrStr(value)  # fallback to evaluation if it's not symbolic

    # --- Handle numpy arrays in general validation ---
    if isinstance(value, np.ndarray):
        debugLog(f"[tryValidateField] 🔢 Found numpy array for '{key}': shape={value.shape}, dtype={value.dtype}")
        # For 1D arrays, check if they match expected vector lengths
        if value.ndim == 1:
            if value.shape[0] == 3 and any(coord in lname for coord in ['position', 'coordinate', 'offset', 'velocity', 'acceleration']):
                return True, ""
            elif value.shape[0] == 4 and 'color' in lname:
                return True, ""
            elif value.shape[0] == 6 and 'offset' in lname:
                return True, ""
        # For 2D arrays, check if they're matrices
        elif value.ndim == 2:
            if value.shape == (3, 3) and any(matrix in lname for matrix in ['matrix', 'rotation', 'inertia']):
                return True, ""
        
        # If we reach here, it's a numpy array but doesn't match expected patterns
        debugLog(f"[tryValidateField] ✅ Accepting numpy array for '{key}' (generic numpy support)")
        return True, ""
    
    debugLog(f"[tryValidateField] DEBUG type={type(value)} for field '{key}' → value={value}")

    # ❌ REMOVED: Hard-coded offset validation that overrides metadata
    # For legacy items, we should trust the metadata type completely
    # if key.lower() == "offset":
    #     if objectType == "CreateRigidBodySpringDamper":
    #         debugLog(f"[tryValidateField] 🚧 Validating 'offset' as 6D for {objectType}")
    #         return validateFloatOrExpressionVector6(key, value)
    #     else:
    #         debugLog(f"[tryValidateField] 🧩 Validating 'offset' as 3D (default)")
    #         return validateFloatOrExpressionVector3(key, value)

    # --- UserFunction fields: must be validated as string, callable, or 0 (must come first!) ---
    if "userfunction" in lname:
        if value in (0, "0", None, "") or isinstance(value, str) or callable(value):
            return True, ""
        return False, f"{key} must be a user function name (string), a function object, or 0"

    # Step 1: Use typeHint if provided
    if typeHint:
        validator = getValidator(typeHint, key, objectType=objectType)
        if validator:
            debugLog(f"[tryValidateField] ✅ Using typeHint '{typeHint}' → {validator.__name__} for '{key}' with value={value}")
            return validator(key, value)
        else:
            if value is None:
                debugLog(f"[tryValidateField] ✅ No validator for '{key}' (type '{typeHint}'), but value is None — accepted")
                return True, ""
            debugLog(f"[tryValidateField] ⚠️ No validator found for typeHint '{typeHint}', skipping name-based fallback")
            return False, f"No validator available for '{key}' with type '{typeHint}'"

    # --- Step 2: Special field handlers (if available) ---
    if specialFieldHandlers is not None:
        for handler in specialFieldHandlers.values():
            if handler['isMatch'](key):
                debugLog(f"[tryValidateField] 🛠️ Using special field handler for '{key}'")
                return handler['validate'](key, value)


    # --- Step 3: Fallback on field name prefix match ---
    # Prefer exact key match before substring match
    if lname in VALIDATORS_BY_KEY:
        validator = VALIDATORS_BY_KEY[lname]
        debugLog(f"[tryValidateField] 🔍 Using exact-key validator '{validator.__name__}' for key '{key}'")
        return validator(key, value)
    for prefix, validator in VALIDATORS_BY_KEY.items():
        if prefix in lname:
            debugLog(f"[tryValidateField] 🔍 Using prefix-based validator '{validator.__name__}' for key '{key}'")
            return validator(key, value)

    # --- Step 4: Generic Python type fallback ---
    if isinstance(value, (int, float, str, list, dict, bool)):
        debugLog(f"[tryValidateField] 🧪 Accepted basic Python type for '{key}': {type(value).__name__}")
        return True, ""
    if value is None:
        debugLog(f"[tryValidateField] ✅ '{key}' is None, accepted")
        return True, ""

    # --- Step 6: Unrecognized type ---
    debugLog(f"[tryValidateField] ❌ Unrecognized type for '{key}': {type(value).__name__}")
    return False, f"Unrecognized type for field '{key}': {type(value).__name__}'"

def convertGraphicsDataForStorage(data):
    """
    Convert graphics data to compact format for storage in modelSequence.
    This significantly reduces memory usage for complex graphics objects.
    """
    if not isinstance(data, dict):
        return data
    
    # Make a copy to avoid modifying the original
    storage_data = data.copy()
    
    # Convert graphics fields to compact format
    graphics_fields = ['graphicsDataList', 'VgraphicsData', 'graphicsData']
    for field in graphics_fields:
        if field in storage_data:
            graphics_value = storage_data[field]
            if isinstance(graphics_value, list):
                compact_graphics = []
                for item in graphics_value:
                    if hasattr(item, '__class__') and hasattr(item.__class__, '__name__'):
                        # Convert graphics object to compact dictionary
                        class_name = item.__class__.__name__
                        
                        # Extract key attributes for common graphics objects
                        if hasattr(item, '__dict__'):
                            # Get all attributes
                            args_dict = {}
                            for attr_name, attr_value in item.__dict__.items():
                                # Skip private attributes and methods
                                if not attr_name.startswith('_'):
                                    args_dict[attr_name] = attr_value
                            
                            compact_graphics.append({
                                'name': f'graphics.{class_name}',
                                'args': args_dict,
                                'compact': True
                            })
                        else:
                            # Fallback for objects without __dict__
                            compact_graphics.append({
                                'name': f'graphics.{class_name}',
                                'args': '**kwargs',
                                'compact': True
                            })
                    elif isinstance(item, dict):
                        # Already in dictionary format
                        compact_graphics.append(item)
                    else:
                        # Keep as-is for unknown types
                        compact_graphics.append(item)
                
                storage_data[field] = compact_graphics
    
    return storage_data

def prepareItemForModelSequence(item_data):
    """
    Prepare item data for storage in modelSequence by converting graphics objects to compact format.
    This should be called before adding items to modelSequence to reduce memory usage.
    """
    if not isinstance(item_data, dict):
        return item_data
    
    # Create a deep copy to avoid modifying the original
    import copy
    storage_data = copy.deepcopy(item_data)
    
    # Convert graphics data to compact format
    storage_data = convertGraphicsDataForStorage(storage_data)
    
    # Also convert any nested data fields
    if 'data' in storage_data and isinstance(storage_data['data'], dict):
        storage_data['data'] = convertGraphicsDataForStorage(storage_data['data'])
    
    return storage_data

def restoreItemFromModelSequence(item_data):
    """
    Restore item data from modelSequence by expanding compact graphics format if needed.
    This should be called when loading items from modelSequence.
    """
    if not isinstance(item_data, dict):
        return item_data
    
    # Create a copy to avoid modifying the original
    import copy
    restored_data = copy.deepcopy(item_data)
    
    # Expand graphics data from compact format
    graphics_fields = ['graphicsDataList', 'VgraphicsData', 'graphicsData']
    
    def expand_graphics_in_dict(data_dict):
        for field in graphics_fields:
            if field in data_dict and isinstance(data_dict[field], list):
                expanded_graphics = []
                for item in data_dict[field]:
                    if isinstance(item, dict) and item.get('compact', False):
                        # Remove compact flag for cleaner data
                        clean_item = item.copy()
                        clean_item.pop('compact', None)
                        expanded_graphics.append(clean_item)
                    else:
                        expanded_graphics.append(item)
                data_dict[field] = expanded_graphics
    
    # Expand graphics in the main data
    expand_graphics_in_dict(restored_data)
    
    # Also expand in nested data fields
    if 'data' in restored_data and isinstance(restored_data['data'], dict):
        expand_graphics_in_dict(restored_data['data'])
    
    return restored_data








