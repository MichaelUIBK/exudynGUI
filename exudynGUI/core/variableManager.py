# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: core/variableManager.py
#
# Description:
#     This module manages symbolic user-defined variables (e.g., m = 2.0, k = 100)
#     for use in GUI field inputs. It provides live parsing, evaluation, and 
#     substitution of expressions entered in the Variables editor.
#
#     Key features include:
#     - Live evaluation of symbolic expressions in GUI fields
#     - Safe parsing and context-aware substitution of user variables
#     - Support for nested expressions and circular reference protection
#     - Integration with Exudyn types for enhanced flexibility
#
# Authors:  Michael Pieber
# Date:     2025-07-03
#
# License:  BSD 3-Clause License
#
# Notes:
#     - To add support for additional types or math functions, extend `safeGlobals`
#     - To evaluate values before system building, call `applyUserVariables()` or 
#       `resolveSymbolicExpressions()` on your data dictionary
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
import json
import numpy as np
import ast
import exudyn as exu
import exudyn.utilities as exucore
import inspect
import pathlib
import os
import functools
import sys, pathlib
import importlib.util
# sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from pathlib import Path
import sys
import re

thisFile = Path(__file__).resolve()
projectRoot = thisFile.parents[2]  # mainExudynGUI
modelPath = projectRoot / 'exudynGUI' / 'model'

if str(projectRoot) not in sys.path:
    sys.path.insert(0, str(projectRoot))

    

liveEditorRef = None

def setLiveEditor(editor):
    """
    Store a reference to the QTextEdit that is showing userVariables.py.
    Then getLiveUserVariableText() can always fetch editor.toPlainText().
    """
    global liveEditorRef
    liveEditorRef = editor



def getUserVariableText():
    """
    Read the entire userVariables.py file from disk (so that loadUserVariables() can be called once at startup).
    """
    userVarPath = Path(__file__).resolve().parent.parent / 'functions' / 'userVariables.py'
    if userVarPath.exists():
        with open(userVarPath, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def loadUserVariables():
    """
    Load userVariables.py from disk, exec() its contents, return resulting dict.
    Called once at startup or whenever you want to re‐read the file from disk.
    """
    text = getUserVariableText()
    return parseUserVariables(text)

def evaluateExpression(expr, userVars):
    """
    Evaluate a single expression (string) in a restricted namespace: 
    globals = {"__builtins__":{}, "math":math, "exudyn":exudyn, etc.}, locals = userVars.
    Returns the evaluated value, or original string if eval() fails.
    """
    try:
        # Include Exudyn types and common modules in evaluation context
        safeGlobals = {
            "__builtins__": {},
            "math": __import__('math'),
            "np": __import__('numpy'),
            "numpy": __import__('numpy'),
            "exu": exu,
            "exudyn": exu,
            "Point": getattr(exu, 'Point', None),
            "Vector3D": getattr(exu, 'Vector3D', None),
            "Vector": getattr(exu, 'Vector', None),
            "Matrix3D": getattr(exu, 'Matrix3D', None),
            "Matrix": getattr(exu, 'Matrix', None),
            "RigidBodyInertia": getattr(exu, 'RigidBodyInertia', None),
            # Add other common Exudyn types as needed
        }
        return eval(expr, safeGlobals, userVars)
    except Exception as e:
        debugLog(f"[VariableManager] ⚠️ Failed to eval '{expr}': {e}")
        return expr

def applyUserVariables(data, userVars):
    """
    Walk through data[key] for each key; if data[key] is a string, replace with evaluateExpression(data[key], userVars).
    This is typically called in buildSystemFromSequence, before handing kwargs to genericBuilder.
    """
    for key, val in data.items():
        if isinstance(val, str):
            # Add debug logs to trace variable evaluation failures
            debugLog(f"[DEBUG] Evaluating variable: key={key}, val={val}")
            try:
                data[key] = evaluateExpression(val, userVars)
                debugLog(f"[DEBUG] Updated variable: key={key}, val={data[key]}")
            except Exception as e:
                debugLog(f"[applyUserVariables] ⚠️ Failed to evaluate '{val}': {e}")

def getLiveUserVariableText():
    """
    Return the raw text from the Variables editor (QTextEdit),
    or "" if no editor has been registered yet.
    """
    if liveEditorRef is None:
        return ""
    return liveEditorRef.toPlainText()

def parseUserVariables(text):
    """
    Given a string of Python code ("m=2.0\nk=100"), exec it into a dict.
    """
    localDict = {}
    try:
        exec(text, {}, localDict)
    except Exception as e:
        debugLog(f"[variableManager] ⚠️ Failed to parse user variables: {e}")
    return localDict

def resolveSymbolicExpressions(inputDict, _seen_ids=None):
    """
    Walk through every value in `inputDict`. If a value is a string,
    attempt to eval(...) it using the user-variable namespace (re-parsed
    from the live Variables editor). If it's a list or dict, recurse into it.
    Otherwise leave it unchanged.
    
    _seen_ids: Set to track object IDs to prevent infinite recursion
    """
    if _seen_ids is None:
        _seen_ids = set()
    
    # Check for circular reference
    input_id = id(inputDict)
    if input_id in _seen_ids:
        debugLog(f"[resolveSymbolicExpressions] ⚠️ Circular reference detected for dict id {input_id}, returning copy")
        return dict(inputDict)  # Return a shallow copy to break the cycle
    
    _seen_ids.add(input_id)
    
    # First, re-parse whatever is currently in the Variables editor
    user_text = getLiveUserVariableText()
    userVariables = parseUserVariables(user_text)

    def evaluate(val, depth=0):
        # Prevent excessive recursion depth
        if depth > 10:
            debugLog(f"[resolveSymbolicExpressions] ⚠️ Maximum recursion depth reached, returning value as-is: {type(val)}")
            return val
            
        # If it's exactly a string, try to eval(…) in userVariables:
        if isinstance(val, str):
            try:
                return eval(val, {}, userVariables)
            except Exception as e:
                # If that fails, just leave it as-is (so we can catch errors later)
                return val

        # If it's a list, recurse into each element:
        elif isinstance(val, list):
            return [evaluate(item, depth + 1) for item in val]

        # If it's a dict, check for circular references:
        elif isinstance(val, dict):
            val_id = id(val)
            if val_id in _seen_ids:
                debugLog(f"[resolveSymbolicExpressions] ⚠️ Circular reference detected in nested dict id {val_id}")
                return dict(val)  # Return shallow copy
            _seen_ids.add(val_id)
            result = {k: evaluate(v, depth + 1) for k, v in val.items()}
            _seen_ids.remove(val_id)  # Remove after processing
            return result

        # Otherwise, return it unchanged:
        else:
            return val

    # Build and return a brand-new dict with every value "evaluated":
    result = {key: evaluate(value) for key, value in inputDict.items()}
    _seen_ids.remove(input_id)  # Remove after processing
    return result




