# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: core/debug.py
#
# Description:
#     Debug logging utilities for the Exudyn GUI.
#     Provides centralized logging with different verbose modes,
#     structured debug output, and summaries for graphicsDataList content.
#
# Authors:  Michael Pieber
# Date:     2025-06-16
#
# License:  BSD-3 license
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import sys
import datetime
from enum import IntEnum

# Global debug configuration
DEBUG_MODE = True  # Set to False to silence all debug logs

class DebugLevel(IntEnum):
    """Debug levels for controlling output verbosity"""
    NONE = 0     # No debug output
    ERROR = 1    # Only critical errors
    WARNING = 2  # Warnings and errors
    INFO = 3     # General information, warnings, and errors
    DEBUG = 4    # Detailed debug information
    TRACE = 5    # Very detailed trace information

# Current debug level - can be changed at runtime
CURRENT_DEBUG_LEVEL = DebugLevel.TRACE

class DebugCategory:
    """Categories for organizing debug output"""
    GENERAL = "GENERAL"
    GUI = "GUI"
    CORE = "CORE"
    MODEL = "MODEL"
    GRAPHICS = "GRAPHICS"
    CODEGEN = "CODEGEN"
    FIELD = "FIELD"
    WIDGET = "WIDGET"
    DIALOG = "DIALOG"
    FILE_IO = "FILE_IO"

def setDebugLevel(level):
    """Set the global debug level"""
    global CURRENT_DEBUG_LEVEL
    CURRENT_DEBUG_LEVEL = level

def setDebugMode(enabled):
    """Enable or disable debug mode globally"""
    global DEBUG_MODE
    DEBUG_MODE = enabled

def _shouldLog(level):
    """Check if a message should be logged based on current debug level"""
    if not DEBUG_MODE:
        return False
    
    # Handle legacy calls where level might be a string
    if isinstance(level, str):
        # Extract debug level from string patterns like "[DEBUG]", "[INFO]", etc.
        if "[DEBUG]" in level or "DEBUG" in level.upper():
            level = DebugLevel.DEBUG
        elif "[INFO]" in level or "INFO" in level.upper():
            level = DebugLevel.INFO
        elif "[WARNING]" in level or "WARNING" in level.upper():
            level = DebugLevel.WARNING
        elif "[ERROR]" in level or "ERROR" in level.upper():
            level = DebugLevel.ERROR
        elif "[TRACE]" in level or "TRACE" in level.upper():
            level = DebugLevel.TRACE
        else:
            # Default to DEBUG for unknown string patterns
            level = DebugLevel.DEBUG
    
    # Ensure we have a valid DebugLevel enum
    if not isinstance(level, DebugLevel):
        level = DebugLevel.DEBUG  # Default fallback
    
    return level <= CURRENT_DEBUG_LEVEL

def _formatMessage(msg, level, category=None, origin=None):
    """Format a debug message with timestamp and metadata"""
    if not _shouldLog(level):
        return None
    
    # Create timestamp
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    # Create level string
    level_str = level.name if hasattr(level, 'name') else str(level)
    
    # Create category/origin prefix
    prefix_parts = [f"[{timestamp}]", f"[{level_str}]"]
    
    if category:
        prefix_parts.append(f"[{category}]")
    
    if origin:
        prefix_parts.append(f"[{origin}]")
    
    prefix = " ".join(prefix_parts)
    
    return f"{prefix} {msg}"

def debugLog(msg, origin=None, level=DebugLevel.DEBUG, category=DebugCategory.GENERAL, summarize=False):
    """
    Main debug logging function with level and category support
    
    Args:
        msg: Message to log (can be string, dict, list, etc.)
        origin: Optional origin identifier (function name, class name, etc.)
        level: Debug level (DebugLevel enum)
        category: Debug category (DebugCategory class constants)
        summarize: If True and msg is a dict, will pretty-print a summary
    """
    # Early exit if debug is disabled
    if not DEBUG_MODE:
        return
      # Handle legacy calls where msg contains level information like "[DEBUG] message"
    if isinstance(msg, str):
        if msg.startswith("[DEBUG]"):
            level = DebugLevel.DEBUG
            msg = msg.replace("[DEBUG]", "").strip()
        elif msg.startswith("[INFO]"):
            level = DebugLevel.INFO
            msg = msg.replace("[INFO]", "").strip()
        elif msg.startswith("[WARNING]"):
            level = DebugLevel.WARNING
            msg = msg.replace("[WARNING]", "").strip()
        elif msg.startswith("[ERROR]"):
            level = DebugLevel.ERROR
            msg = msg.replace("[ERROR]", "").strip()
        elif msg.startswith("[TRACE]"):
            level = DebugLevel.TRACE
            msg = msg.replace("[TRACE]", "").strip()
    
    if not _shouldLog(level):
        return

    formatted_msg = _formatMessage("", level, category, origin)
    if formatted_msg is None:
        return

    if summarize and isinstance(msg, dict):
        from pprint import pprint
        # Using print here is intentional - this is the debug output function itself
        print(formatted_msg)
        pprint(summarizeDict(msg))
    else:
        # Using print here is intentional - this is the debug output function itself
        print(f"{formatted_msg}{msg}")

# Convenience functions for different debug levels
def debugError(msg, origin=None, category=DebugCategory.GENERAL):
    """Log an error message"""
    debugLog(msg, origin, DebugLevel.ERROR, category)

def debugWarning(msg, origin=None, category=DebugCategory.GENERAL):
    """Log a warning message"""
    debugLog(msg, origin, DebugLevel.WARNING, category)

def debugInfo(msg, origin=None, category=DebugCategory.GENERAL):
    """Log an info message"""
    debugLog(msg, origin, DebugLevel.INFO, category)

def debugTrace(msg, origin=None, category=DebugCategory.GENERAL):
    """Log a trace message"""
    debugLog(msg, origin, DebugLevel.TRACE, category)

# Legacy compatibility function
def debug(msg, origin=None):
    """Legacy debug function - maps to debugInfo"""
    debugInfo(msg, origin, DebugCategory.GENERAL)
    
def summarizeDict(d, maxListLen=5):
    """Shorten long lists in nested dicts, useful for logging."""
    summary = {}
    for k, v in d.items():
        if isinstance(v, list):
            summary[k] = f"<list of {len(v)}: {v[:maxListLen]}...>"
        elif isinstance(v, dict):
            summary[k] = summarizeDict(v, maxListLen)
        else:
            summary[k] = v
    return summary

def logFieldValue(fieldName, value):
    return f"{fieldName} = {repr(value)} (type: {type(value).__name__})"

def summarizeIfLarge(key, value):
    if isinstance(value, list):
        if all(isinstance(v, dict) and 'call' in v for v in value):
            return f"<list of {len(value)}: {[v['call'] for v in value[:1]]}...>"
        elif all(isinstance(v, dict) and 'name' in v for v in value):
            return f"<list of {len(value)}: {[v['name'] for v in value[:1]]}...>"
        else:
            return f"<list of {len(value)}>"
    return value


def deepSummarize(obj, maxListLen=5):
    """
    Recursively shorten all lists inside obj deeper than maxListLen.
    Lists longer than maxListLen will be truncated with a summary string.
    Dicts are processed recursively.
    Other types returned as-is.
    """
    if isinstance(obj, dict):
        return {k: deepSummarize(v, maxListLen) for k, v in obj.items()}
    elif isinstance(obj, list):
        if len(obj) > maxListLen:
            # Show first maxListLen items summarized plus count
            summarized_items = [deepSummarize(v, maxListLen) for v in obj[:maxListLen]]
            return f"<list of {len(obj)}: {summarized_items} ...>"
        else:
            return [deepSummarize(v, maxListLen) for v in obj]
    else:
        return obj




    
    
def printGraphicsDataSummary(graphicsDataList, maxPreview=3):
    if not DEBUG_MODE:
        return
        
    for i, gd in enumerate(graphicsDataList):
        # These print statements are part of debug output functions, so they use print directly
        print(f"\n--- GraphicsData #{i} ---")
        if hasattr(gd, 'typeName'):
            print(f"Type: {gd.typeName}")
        
        # Common attributes
        if hasattr(gd, 'points'):
            n = len(gd.points)
            print(f"Points: {n}")
            for j, p in enumerate(gd.points[:maxPreview]):
                print(f"  Point {j}: {p}")
            if n > maxPreview:
                print(f"  ... ({n - maxPreview} more)")

        if hasattr(gd, 'triangles'):
            n = len(gd.triangles)
            print(f"Triangles: {n}")
            for j, t in enumerate(gd.triangles[:maxPreview]):
                print(f"  Triangle {j}: {t}")
            if n > maxPreview:
                print(f"  ... ({n - maxPreview} more)")

        if hasattr(gd, 'colors'):
            n = len(gd.colors)
            print(f"Colors: {n}")
            for j, c in enumerate(gd.colors[:maxPreview]):
                print(f"  Color {j}: {c}")
            if n > maxPreview:
                print(f"  ... ({n - maxPreview} more)")

        if hasattr(gd, 'faces'):
            print(f"Faces: {len(gd.faces)}")

        # Metadata
        if hasattr(gd, 'color'):
            print(f"Global color: {gd.color}")
        if hasattr(gd, 'name'):
            print(f"Name: {gd.name}")

# Utility functions for easy debug control throughout the application

def disableAllDebug():
    """Completely disable all debug output"""
    global DEBUG_MODE, CURRENT_DEBUG_LEVEL
    DEBUG_MODE = False
    CURRENT_DEBUG_LEVEL = DebugLevel.NONE

def enableDebugWithLevel(level=DebugLevel.INFO):
    """Enable debug output with a specific level"""
    global DEBUG_MODE, CURRENT_DEBUG_LEVEL
    DEBUG_MODE = True
    CURRENT_DEBUG_LEVEL = level

def getDebugStatus():
    """Get current debug status and level"""
    return {
        'enabled': DEBUG_MODE,
        'level': CURRENT_DEBUG_LEVEL,
        'level_name': CURRENT_DEBUG_LEVEL.name if hasattr(CURRENT_DEBUG_LEVEL, 'name') else str(CURRENT_DEBUG_LEVEL)
    }

def configureDebugFromEnvironment():
    """Configure debug settings from environment variables"""
    import os
    
    # Check DEBUG_MODE environment variable
    debug_env = os.getenv('EXUDYN_DEBUG_MODE', '').lower()
    if debug_env in ['false', '0', 'no', 'off']:
        disableAllDebug()
        return
    elif debug_env in ['true', '1', 'yes', 'on']:
        setDebugMode(True)
    
    # Check DEBUG_LEVEL environment variable
    level_env = os.getenv('EXUDYN_DEBUG_LEVEL', '').upper()
    level_mapping = {
        'NONE': DebugLevel.NONE,
        'ERROR': DebugLevel.ERROR,
        'WARNING': DebugLevel.WARNING,
        'INFO': DebugLevel.INFO,
        'DEBUG': DebugLevel.DEBUG,
        'TRACE': DebugLevel.TRACE
    }
    
    if level_env in level_mapping:
        setDebugLevel(level_mapping[level_env])

# Configuration function for easy GUI integration
def configureForProduction():
    """Configure debug system for production - minimal output"""
    global DEBUG_MODE, CURRENT_DEBUG_LEVEL
    DEBUG_MODE = True  # Keep enabled but minimal
    CURRENT_DEBUG_LEVEL = DebugLevel.ERROR  # Only show errors

def configureForDevelopment():
    """Configure debug system for development - full output"""
    global DEBUG_MODE, CURRENT_DEBUG_LEVEL
    DEBUG_MODE = True
    CURRENT_DEBUG_LEVEL = DebugLevel.DEBUG  # Show debug and above

def configureSilent():
    """Completely disable all debug output"""
    global DEBUG_MODE, CURRENT_DEBUG_LEVEL
    DEBUG_MODE = False
    CURRENT_DEBUG_LEVEL = DebugLevel.NONE

# Simple function to check if debug output is enabled
def isDebugEnabled():
    """Check if debug output is currently enabled"""
    return DEBUG_MODE

def getCurrentLevel():
    """Get the current debug level"""
    return CURRENT_DEBUG_LEVEL

# Convenience functions for specific categories
def debugGUI(msg, origin=None, level=DebugLevel.DEBUG):
    """Debug message for GUI-related operations"""
    debugLog(msg, origin, level, DebugCategory.GUI)

def debugCore(msg, origin=None, level=DebugLevel.DEBUG):
    """Debug message for core operations"""
    debugLog(msg, origin, level, DebugCategory.CORE)

def debugModel(msg, origin=None, level=DebugLevel.DEBUG):
    """Debug message for model operations"""
    debugLog(msg, origin, level, DebugCategory.MODEL)

def debugGraphics(msg, origin=None, level=DebugLevel.DEBUG):
    """Debug message for graphics operations"""
    debugLog(msg, origin, level, DebugCategory.GRAPHICS)

def debugCodeGen(msg, origin=None, level=DebugLevel.DEBUG):
    """Debug message for code generation operations"""
    debugLog(msg, origin, level, DebugCategory.CODEGEN)

def debugField(msg, origin=None, level=DebugLevel.DEBUG):
    """Debug message for field operations"""
    debugLog(msg, origin, level, DebugCategory.FIELD)

def debugWidget(msg, origin=None, level=DebugLevel.DEBUG):
    """Debug message for widget operations"""
    debugLog(msg, origin, level, DebugCategory.WIDGET)

# Initialize debug settings from environment on import
configureDebugFromEnvironment()