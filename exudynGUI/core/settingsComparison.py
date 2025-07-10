# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project
#
# Filename: core/settingsComparison.py
#
# Description:
# Compares initial default values with current/selected values for both 
# simulationSettings and visualizationSettings, and prints only the 
# differences in generated code format.
#
# Authors:  Michael Pieber
# Date:     2025-07-010
# License:  BSD-3-Clause License
#
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


import sys
import os
import copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

import exudyn as exu
from exudynGUI.guiForms.simulationSettings import discoverSimulationSettingsStructure
from exudynGUI.guiForms.visualizationSettings import discoverVisualizationSettingsStructure
from exudynGUI.core.debug import debugLog

# Global cache for default settings to avoid creating multiple SystemContainers
_cached_default_simulation = None
_cached_default_visualization = None

def get_default_simulation_settings():
    """Get default simulation settings structure (cached)."""
    global _cached_default_simulation
    if _cached_default_simulation is None:
        default_settings = exu.SimulationSettings()
        _cached_default_simulation = discoverSimulationSettingsStructure(exu, default_settings)
    return _cached_default_simulation


def get_default_visualization_settings(reference_SC=None):
    """
    Get default visualization settings structure (cached).
    This function now always returns the cached structure and never creates a new SystemContainer.
    The cache must be set at GUI startup using cache_default_visualization_settings(main_SC).
    """
    global _cached_default_visualization
    if _cached_default_visualization is None:
        raise RuntimeError("Default visualization settings cache is not set. Call cache_default_visualization_settings(main_SC) at GUI startup.")
    return _cached_default_visualization

def cache_default_visualization_settings(main_SC):
    """
    Cache the default visualization settings from the main SystemContainer.
    Call this once when the main window starts.
    
    Args:
        main_SC: The main SystemContainer from the application
    """
    global _cached_default_visualization
    try:
        # Get the default state as our reference
        _cached_default_visualization = discoverVisualizationSettingsStructure(main_SC)
        debugLog("✅ Cached default visualization settings from main SC")
    except Exception as e:
        debugLog(f"⚠️ Error caching default visualization settings: {e}")
        _cached_default_visualization = {}

def values_are_equivalent(default_val, current_val, path=""):
    """
    Smart comparison that handles type mismatches between form data and defaults.
    
    Args:
        default_val: Value from default structure
        current_val: Value from form data
        path: Full path to the setting (e.g., "simulationSettings.timeIntegration.numberOfSteps")
        
    Returns:
        bool: True if values represent the same data despite type differences
    """
    import numpy as np
    
    # Exact match
    if default_val == current_val:
        return True
    
    # Handle None cases
    if default_val is None or current_val is None:
        return default_val == current_val
    
    # Convert both to comparable formats
    def normalize_value(val):
        """Convert value to a comparable format."""
        import enum
        # If it's an enum, use its name
        if isinstance(val, enum.Enum):
            debugLog(f"[DEBUG NORM] Enum detected: {val} -> {val.name}")
            return val.name
        # Also check if it has enum-like attributes (backup check)
        elif hasattr(val, 'name') and hasattr(val, 'value') and hasattr(type(val), '__members__'):
            debugLog(f"[DEBUG NORM] Enum-like detected: {val} -> {val.name}")
            return val.name
        # Handle string values (including string representations of enums)
        elif isinstance(val, str):
            # If it's a string that looks like EnumType.Value, always split and return the last part
            if '.' in val and any(enum_type in val for enum_type in ['Type', 'Mode', 'State', 'Index']):
                return val.split('.')[-1]
            # If it's a string with a single dot, also split and return the last part
            if val.count('.') == 1:
                return val.split('.')[-1]
            # Handle string representations of lists/arrays
            if val.startswith('[') and val.endswith(']'):
                try:
                    # Try to parse as list
                    import ast
                    return ast.literal_eval(val)
                except:
                    return val
            # Handle empty list strings
            elif val == '[]':
                return []
            else:
                # Try to parse as number
                try:
                    if '.' in val or 'e' in val.lower():
                        return float(val)
                    else:
                        return int(val)
                except:
                    return val
        elif isinstance(val, (list, tuple)):
            # Convert to list of floats for consistent comparison
            try:
                return [float(x) for x in val]
            except:
                return list(val)
        elif isinstance(val, np.ndarray):
            # Convert numpy arrays to lists
            return val.tolist()
        elif isinstance(val, (int, float)):
            return float(val)
        else:
            return val
    
    norm_default = normalize_value(default_val)
    norm_current = normalize_value(current_val)
    
    # Debug output for enum-like values
    if path and (isinstance(default_val, type(norm_default)) or '.' in str(default_val) or '.' in str(current_val)):
        debugLog(f"[DEBUG] Enum comparison at '{path}':")
        debugLog(f"  default: {repr(default_val)} (type: {type(default_val).__name__}) -> normalized: {repr(norm_default)}")
        debugLog(f"  current: {repr(current_val)} (type: {type(current_val).__name__}) -> normalized: {repr(norm_current)}")
        debugLog(f"  equal: {norm_default == norm_current}")
    
    # Only show debug for mismatches when path is provided
    if path and norm_default != norm_current:
        debugLog(f"[DEBUG] Mismatch at '{path}': default={default_val} (norm={norm_default}), current={current_val} (norm={norm_current})")
    
    # Direct comparison after normalization
    if norm_default == norm_current:
        return True
    
    # Handle floating point precision for lists
    if isinstance(norm_default, list) and isinstance(norm_current, list):
        if len(norm_default) != len(norm_current):
            return False
        
        try:
            # Compare with practical tolerance for GUI settings
            for d, c in zip(norm_default, norm_current):
                if abs(float(d) - float(c)) > 1e-6:
                    return False
            return True
        except:
            return norm_default == norm_current
    
    # Handle floating point precision for numbers
    if isinstance(norm_default, (int, float)) and isinstance(norm_current, (int, float)):
        return abs(float(norm_default) - float(norm_current)) < 1e-6
    
    # For enum comparisons, ensure case-insensitive string comparison
    if isinstance(norm_default, str) and isinstance(norm_current, str):
        return norm_default.lower() == norm_current.lower()
    
    # Fallback to direct comparison
    return norm_default == norm_current


def compare_form_data_with_defaults(form_data, default_structure, settings_name):
    """
    Compare form data directly with default structure without creating/modifying SystemContainers.
    
    Args:
        form_data: Dictionary of collected form data
        default_structure: Default settings structure
        settings_name: Name for the settings object
        
    Returns:
        str: Generated code showing differences
    """
    # Extract default values from the structure
    default_values = extract_flat_values(default_structure)
    
    # Convert form data to flat structure for comparison
    current_values = {}
    
    def flatten_form_data(data, prefix=""):
        """Flatten nested form data dictionary."""
        flat = {}
        for key, value in data.items():
            if isinstance(value, dict):
                nested_flat = flatten_form_data(value, f"{prefix}.{key}" if prefix else key)
                flat.update(nested_flat)
            else:
                full_key = f"{prefix}.{key}" if prefix else key
                flat[full_key] = value
        return flat
    
    current_values = flatten_form_data(form_data)
    
    # Find differences
    differences = {}
    all_keys = set(default_values.keys()) | set(current_values.keys())
    
    for key in all_keys:
        default_val = default_values.get(key)
        current_val = current_values.get(key)
        
        # Check if values are different (with smart type handling)
        if current_val is not None and not values_are_equivalent(default_val, current_val, key):
            differences[key] = {
                'default': default_val,
                'current': current_val,
                'path': f"{settings_name}.{key}"
            }
    
    # Generate text output
    lines = []
    lines.append(f"# {settings_name.title()} Changes")
    lines.append("# " + "=" * 50)
    
    if not differences:
        lines.append(f"# No changes detected in {settings_name}")
        return "\n".join(lines)
    
    # Proper class name formatting
    if settings_name == "simulationSettings":
        class_name = "SimulationSettings"
    elif settings_name == "visualizationSettings":
        class_name = "VisualizationSettings"
    else:
        class_name = settings_name.title()
    
    lines.append(f"{settings_name} = exu.{class_name}()")
    
    # Sort by path for consistent output
    sorted_differences = sorted(differences.items(), key=lambda x: x[0])
    
    for key, info in sorted_differences:
        current_val = info['current']
        default_val = info['default']
        path = info['path']
        
        if current_val is not None:
            formatted_value = format_value_for_code(current_val)
            lines.append(f"{path} = {formatted_value}")
            
            # Add comment showing what changed from
            if default_val is not None:
                formatted_default = format_value_for_code(default_val)
                lines.append(f"# Changed from: {formatted_default}")
            else:
                lines.append("# New setting")
    
    return "\n".join(lines)


def initialize_settings_defaults(main_SC=None):
    """
    Initialize default settings cache for comparison functionality.
    Call this once at application startup.
    
    Args:
        main_SC: Optional main SystemContainer to cache visualization defaults from
    """
    debugLog("🔧 Initializing settings defaults cache...")
    
    # Initialize simulation defaults (safe - doesn't use OpenGL)
    try:
        get_default_simulation_settings()
        debugLog("✅ Simulation settings defaults cached")
    except Exception as e:
        debugLog(f"⚠️ Error caching simulation defaults: {e}")
    
    # Initialize visualization defaults from provided SC
    if main_SC:
        try:
            cache_default_visualization_settings(main_SC)
            debugLog("✅ Visualization settings defaults cached from main SC")
        except Exception as e:
            debugLog(f"⚠️ Error caching visualization defaults: {e}")
    else:
        debugLog("ℹ️ No main SC provided - visualization defaults will be created on demand")
    
    debugLog("✅ Settings defaults initialization complete")


def get_current_simulation_settings(current_settings):
    """Get current simulation settings structure."""
    return discoverSimulationSettingsStructure(exu, current_settings)


def get_current_visualization_settings(current_SC):
    """Get current visualization settings structure."""
    return discoverVisualizationSettingsStructure(current_SC)


def extract_flat_values(structure, prefix=""):
    """
    Extract all leaf values from a nested structure into a flat dictionary.
    
    Args:
        structure: Nested dictionary structure from discovery functions
        prefix: Path prefix for building full setting paths
        
    Returns:
        dict: Flat dictionary with full paths as keys and values
    """
    flat_values = {}
    
    for key, info in structure.items():
        if info.get('type') == 'object':
            # Nested object - recurse
            nested_prefix = f"{prefix}.{key}" if prefix else key
            nested_values = extract_flat_values(info.get('nested', {}), nested_prefix)
            flat_values.update(nested_values)
        else:
            # Leaf value
            full_path = f"{prefix}.{key}" if prefix else key
            flat_values[full_path] = info.get('value')
    
    return flat_values


def format_value_for_code(value):
    """Format a value for Python code generation."""
    if isinstance(value, str):
        return f'"{value}"'
    elif isinstance(value, bool):
        return str(value)
    elif isinstance(value, (int, float)):
        # Use scientific notation for very small/large numbers
        if isinstance(value, float) and (abs(value) < 1e-4 or abs(value) > 1e6) and value != 0:
            return f"{value:.2e}"
        else:
            return str(value)
    elif isinstance(value, list):
        # Format lists/vectors
        formatted_items = [format_value_for_code(item) for item in value]
        return f"[{', '.join(formatted_items)}]"
    else:
        return str(value)


def compare_and_get_differences(default_structure, current_structure, settings_name):
    """
    Compare default and current structures and return differences as text.
    
    Args:
        default_structure: Default settings structure
        current_structure: Current settings structure  
        settings_name: Name for the settings object ("simulationSettings" or "visualizationSettings")
        
    Returns:
        str: Generated code showing the differences
    """
    # Extract flat values from both structures
    default_values = extract_flat_values(default_structure)
    current_values = extract_flat_values(current_structure)
    
    # Find differences
    differences = {}
    all_keys = set(default_values.keys()) | set(current_values.keys())
    
    for key in all_keys:
        default_val = default_values.get(key)
        current_val = current_values.get(key)
        
        # Check if values are different (with smart type handling)
        if not values_are_equivalent(default_val, current_val, key):
            differences[key] = {
                'default': default_val,
                'current': current_val,
                'path': f"{settings_name}.{key}"
            }
    
    # Generate text output
    lines = []
    lines.append(f"# {settings_name.title()} Changes")
    lines.append("# " + "=" * 50)
    
    if not differences:
        lines.append(f"# No changes detected in {settings_name}")
        return "\n".join(lines)
    
    # Proper class name formatting
    if settings_name == "simulationSettings":
        class_name = "SimulationSettings"
    elif settings_name == "visualizationSettings":
        class_name = "VisualizationSettings"
    else:
        class_name = settings_name.title()
    
    lines.append(f"{settings_name} = exu.{class_name}()")
    
    # Sort by path for consistent output
    sorted_differences = sorted(differences.items(), key=lambda x: x[0])
    
    for key, info in sorted_differences:
        current_val = info['current']
        default_val = info['default']
        path = info['path']
        
        if current_val is not None:
            formatted_value = format_value_for_code(current_val)
            lines.append(f"{path} = {formatted_value}")
            
            # Add comment showing what changed from
            if default_val is not None:
                formatted_default = format_value_for_code(default_val)
                lines.append(f"# Changed from: {formatted_default}")
            else:
                lines.append("# New setting")
    
    return "\n".join(lines)

def compare_and_print_differences(default_structure, current_structure, settings_name):
    """
    Compare default and current structures and print differences in code format.
    
    Args:
        default_structure: Default settings structure
        current_structure: Current settings structure  
        settings_name: Name for the settings object ("simulationSettings" or "visualizationSettings")
    """
    result = compare_and_get_differences(default_structure, current_structure, settings_name)
    debugLog(result)


def compare_settings_with_forms():
    """Compare settings using form dialogs (interactive mode)."""
    from exudynGUI.core.qtImports import QApplication
    from exudynGUI.guiForms.simulationSettings import createSimulationSettingsForm
    from exudynGUI.guiForms.visualizationSettings import createVisualizationSettingsForm
    
    app = QApplication(sys.argv)
    
    debugLog("🔧 Interactive Settings Comparison")
    debugLog("=" * 60)
    
    # Get default settings
    debugLog("📊 Getting default settings...")
    default_sim_structure = get_default_simulation_settings()
    default_viz_structure = get_default_visualization_settings()
    
    # Show simulation settings form
    debugLog("🖥️  Opening Simulation Settings form...")
    sim_settings = exu.SimulationSettings()
    sim_form = createSimulationSettingsForm(None, sim_settings)
    
    if sim_form.exec_() == sim_form.Accepted:
        debugLog("✅ Simulation settings accepted")
        from exudynGUI.guiForms.simulationSettings import collectSimulationSettingsData, applySimulationSettings
        sim_data = collectSimulationSettingsData(sim_form)
        applySimulationSettings(sim_settings, sim_data)
        current_sim_structure = get_current_simulation_settings(sim_settings)
        compare_and_print_differences(default_sim_structure, current_sim_structure, "simulationSettings")
    else:
        debugLog("❌ Simulation settings cancelled")
    
    # Show visualization settings form  
    debugLog("\n🖥️  Opening Visualization Settings form...")
    SC = exu.SystemContainer()
    viz_form = createVisualizationSettingsForm(None, SC)
    
    if viz_form.exec_() == viz_form.Accepted:
        debugLog("✅ Visualization settings accepted")
        from exudynGUI.guiForms.visualizationSettings import collectVisualizationSettingsData, applyVisualizationSettings
        viz_data = collectVisualizationSettingsData(viz_form)
        applyVisualizationSettings(SC, viz_data)
        current_viz_structure = get_current_visualization_settings(SC)
        compare_and_print_differences(default_viz_structure, current_viz_structure, "visualizationSettings")
    else:
        debugLog("❌ Visualization settings cancelled")


def compare_with_example_modifications():
    """Compare settings with example modifications (demo mode)."""
    debugLog("🔧 Example Settings Comparison")
    debugLog("=" * 60)
    
    # Get default settings
    debugLog("📊 Getting default settings...")
    default_sim_structure = get_default_simulation_settings()
    default_viz_structure = get_default_visualization_settings()
    
    # Create modified simulation settings
    debugLog("🔧 Creating modified simulation settings...")
    modified_sim_settings = exu.SimulationSettings()
    modified_sim_settings.timeIntegration.numberOfSteps = 2000
    modified_sim_settings.timeIntegration.endTime = 2.0
    modified_sim_settings.displayComputationTime = False
    modified_sim_settings.solutionSettings.solutionWritePeriod = 1e-2
    modified_sim_settings.timeIntegration.generalizedAlpha.spectralRadius = 0.9
    
    current_sim_structure = get_current_simulation_settings(modified_sim_settings)
    compare_and_print_differences(default_sim_structure, current_sim_structure, "simulationSettings")
    
    # Create modified visualization settings
    debugLog("\n🔧 Creating modified visualization settings...")
    modified_SC = exu.SystemContainer()
    modified_SC.visualizationSettings.general.backgroundColor = [0.9, 0.9, 0.9, 1.0]
    modified_SC.visualizationSettings.nodes.show = False
    modified_SC.visualizationSettings.bodies.show = True
    modified_SC.visualizationSettings.window.renderWindowSize = [1200, 800]
    
    current_viz_structure = get_current_visualization_settings(modified_SC)
    compare_and_print_differences(default_viz_structure, current_viz_structure, "visualizationSettings")


def main():
    """Main function with command line argument handling."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare exudyn settings and show differences")
    parser.add_argument('--interactive', '-i', action='store_true', 
                       help='Use interactive forms to modify settings')
    parser.add_argument('--example', '-e', action='store_true',
                       help='Show example with predefined modifications')
    parser.add_argument('--simulation-only', '-s', action='store_true',
                       help='Only compare simulation settings')
    parser.add_argument('--visualization-only', '-v', action='store_true',
                       help='Only compare visualization settings')
    
    args = parser.parse_args()
    
    try:
        if args.interactive:
            compare_settings_with_forms()
        elif args.example:
            compare_with_example_modifications()
        else:
            # Default: show example
            debugLog("💡 Use --interactive (-i) for form-based comparison")
            debugLog("💡 Use --example (-e) for predefined example modifications")
            debugLog("💡 Use --help for all options\n")
            compare_with_example_modifications()
            
    except KeyboardInterrupt:
        debugLog("\n\n⏹️  Interrupted by user")
        return 1
    except Exception as e:
        debugLog(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 