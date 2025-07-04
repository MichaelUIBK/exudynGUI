#!/usr/bin/env python3
"""
Helper module to extract parameter help from Exudyn's internal documentation.
"""

import exudyn as exu
import io
from contextlib import redirect_stdout
import re
from typing import Dict, Optional
from exudynGUI.core.debug import debugLog

def extractParameterHelp(functionName: str, existing_mbs=None) -> Dict[str, str]:
    """
    Extract parameter descriptions from Exudyn's internal help for a given function.
    
    Args:
        functionName: Name of the Exudyn function (e.g., 'CreateGround')
        existing_mbs: Existing MainSystem to use (optional, creates temporary if None)
        
    Returns:
        Dictionary mapping parameter names to their descriptions
    """
    try:
        # Use existing MainSystem if provided, otherwise create temporary one
        if existing_mbs is not None:
            mbs = existing_mbs
        else:
            # Only create temporary SystemContainer if no existing one is available
            # This should be avoided when renderer is active
            debugLog("⚠️ Creating temporary SystemContainer for parameter help - this may conflict with active renderer", origin="parameterHelp.py")
            mbs = exu.SystemContainer().AddSystem()
            
        if not hasattr(mbs, functionName):
            return {}
        
        func = getattr(mbs, functionName)
        
        # Capture help() output
        f = io.StringIO()
        with redirect_stdout(f):
            help(func)
        help_text = f.getvalue()
        
        if not help_text:
            return {}
        
        # Extract parameter descriptions
        param_help = {}
        
        # Look for the input section
        lines = help_text.split('\n')
        in_input_section = False
        
        for line in lines:
            # Start of input section
            if '#**input:' in line:
                in_input_section = True
                continue
            
            # End of input section
            if in_input_section and line.strip().startswith('#**'):
                break
            
            # Parse parameter line
            if in_input_section and line.strip().startswith('#  ') and ':' in line:
                # Example: "#  name: name string for object"
                param_line = line.strip()[3:]  # Remove "#  "
                if ':' in param_line:
                    param_name, description = param_line.split(':', 1)
                    param_name = param_name.strip()
                    description = description.strip()
                    
                    # Clean up description
                    if description:
                        param_help[param_name] = description
        
        return param_help
        
    except Exception as e:
        debugLog(f"Error extracting parameter help for {functionName}: {e}")
        return {}

def getParameterDescription(functionName: str, parameterName: str, existing_mbs=None) -> Optional[str]:
    """
    Get the description for a specific parameter of an Exudyn function.
    
    Args:
        functionName: Name of the Exudyn function (e.g., 'CreateGround')
        parameterName: Name of the parameter (e.g., 'referencePosition')
        existing_mbs: Existing MainSystem to use (optional)
        
    Returns:
        Description string or None if not found
    """
    # If no existing MainSystem is provided, skip parameter help extraction
    # to avoid OpenGL renderer conflicts
    if existing_mbs is None:
        debugLog(f"⚠️ Skipping parameter help for {functionName}.{parameterName} - no existing MainSystem available", origin="parameterHelp.py")
        return None
        
    param_help = extractParameterHelp(functionName, existing_mbs)
    return param_help.get(parameterName)

# Test the functionality
if __name__ == "__main__":
    # Test with CreateGround - create a single SystemContainer for testing
    debugLog("⚠️ WARNING: This test creates a temporary SystemContainer which may conflict with active renderers", origin="parameterHelp.py")
    
    function_name = "CreateGround"
    # Create a test SystemContainer for testing
    test_sc = exu.SystemContainer()
    test_mbs = test_sc.AddSystem()
    
    param_help = extractParameterHelp(function_name, test_mbs)
    
    debugLog(f"Parameter help for {function_name}:")
    debugLog("=" * 50)
    for param, desc in param_help.items():
        debugLog(f"• {param}: {desc}")
    
    debugLog(f"\nTesting specific parameter lookup:")
    ref_pos_help = getParameterDescription("CreateGround", "referencePosition", test_mbs)
    debugLog(f"referencePosition: {ref_pos_help}")
