# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/simulationSettings.py
#
# Description:
#     Generic simulation settings dialog that automatically discovers all
#     properties and nested objects in exudyn.SimulationSettings using
#     Python introspection.
#
#     Features:
#       - Automatic discovery of all SimulationSettings properties
#       - Hierarchical grouping of nested settings (timeIntegration, solutionSettings, etc.)
#       - Generic help text extraction using introspection (__doc__, help(), etc.)
#       - Type-appropriate widgets (checkboxes for bools, line edits for numbers)
#       - Preserves existing values when editing
#       - Generic approach that works with any exudyn version
#
# Authors:  Michael Pieber
# Date:     2025-07-05
#
# License:  BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from exudynGUI.core.qtImports import *
import exudyn as exu
import inspect
import io
from contextlib import redirect_stdout

def extractGenericHelp(obj, attr_name):
    """
    Extract meaningful help text for simulation settings attributes.
    Prioritizes domain-specific help over generic Python documentation.
    """
    try:
        # Method 1: Try simulation-specific pattern matching first (highest priority)
        generic_help = generateGenericHelp(attr_name)
        if generic_help and not generic_help.startswith("Simulation setting:"):
            # We found a specific pattern match, use it
            return generic_help
        
        # Method 2: Try to get meaningful docstring from the attribute itself
        attr_obj = getattr(obj, attr_name, None)
        if attr_obj is not None and hasattr(attr_obj, '__doc__') and attr_obj.__doc__:
            doc = attr_obj.__doc__.strip()
            # Filter out unhelpful Python generic docs
            if (doc and len(doc) > 10 and 
                not doc.startswith(('bool(', 'int(', 'float(', 'str(')) and
                'instances of the class' not in doc.lower() and
                'built-in' not in doc.lower()):
                return doc
        
        # Method 3: Try to get help from the parent object's docstring
        if hasattr(obj, '__doc__') and obj.__doc__:
            doc = obj.__doc__
            # Look for attribute-specific help in the parent docstring
            lines = doc.split('\n')
            for i, line in enumerate(lines):
                if attr_name in line and (':' in line or '=' in line):
                    # Found a line mentioning our attribute, try to extract description
                    description_lines = []
                    # Look at the current line and a few following lines
                    for j in range(i, min(i+3, len(lines))):
                        if lines[j].strip():
                            description_lines.append(lines[j].strip())
                    if description_lines:
                        return ' '.join(description_lines)
        
        # Method 4: Try help() function but filter out unhelpful results
        try:
            f = io.StringIO()
            with redirect_stdout(f):
                help(obj)
            help_text = f.getvalue()
            
            if help_text and attr_name in help_text:
                lines = help_text.split('\n')
                for i, line in enumerate(lines):
                    if attr_name in line and (':' in line or '=' in line):
                        # Extract context around the attribute mention
                        context_lines = []
                        start = max(0, i-1)
                        end = min(len(lines), i+3)
                        for j in range(start, end):
                            line_text = lines[j].strip()
                            if (line_text and not line_text.startswith('|') and
                                'built-in' not in line_text.lower() and
                                'instances of the class' not in line_text.lower()):
                                context_lines.append(line_text)
                        if context_lines and len(' '.join(context_lines)) > 20:
                            return ' '.join(context_lines)
        except:
            pass  # help() can sometimes fail
        
        # Method 5: Return the generic fallback (always returns something)
        return generic_help or f"Simulation setting: {attr_name.replace('_', ' ').title()}"
            
    except Exception as e:
        return f"Simulation setting: {attr_name.replace('_', ' ').title()}"

def generateGenericHelp(attr_name):
    """
    Generate meaningful help text based on exudyn simulation settings patterns.
    This provides domain-specific help for simulation parameters.
    """
    attr_lower = attr_name.lower()
    
    # Export settings (solution output)
    if 'export' in attr_lower:
        if 'ode1' in attr_lower:
            return "Export ODE1 velocities (first-order differential equations) to solution file"
        elif 'velocities' in attr_lower:
            return "Export velocity coordinates to solution file"
        elif 'accelerations' in attr_lower:
            return "Export acceleration coordinates to solution file"
        elif 'algebraic' in attr_lower:
            return "Export algebraic coordinates (constraints) to solution file"
        elif 'data' in attr_lower:
            return "Export data coordinates to solution file"
        return "Export this data type to solution file"
    
    # File and output settings
    if 'file' in attr_lower:
        if 'binary' in attr_lower:
            return "Use binary format for solution file (smaller, faster)"
        elif 'header' in attr_lower:
            return "Write header information to output file"
        elif 'footer' in attr_lower:
            return "Write footer information to output file"
        elif 'flush' in attr_lower:
            return "Flush file buffers to disk (for data safety)"
        return "File output configuration setting"
    
    # Append settings
    if 'append' in attr_lower:
        return "Append to existing file instead of overwriting"
    
    # Time-related settings
    if 'time' in attr_lower:
        if 'end' in attr_lower:
            return "End time of the simulation in seconds"
        elif 'start' in attr_lower:
            return "Start time of the simulation in seconds"
        elif 'period' in attr_lower:
            return "Time interval for periodic operations (in seconds)"
        elif 'step' in attr_lower:
            return "Time step size for integration (in seconds)"
        elif 'integration' in attr_lower:
            return "Time integration method configuration"
    
    # Step-related settings  
    if 'step' in attr_lower:
        if 'number' in attr_lower:
            return "Total number of integration steps"
        elif 'size' in attr_lower:
            return "Size of each integration step"
        elif 'adaptive' in attr_lower:
            return "Use adaptive step size control"
        elif 'automatic' in attr_lower:
            return "Automatically determine step size"
        elif 'recovery' in attr_lower:
            return "Settings for step size recovery after convergence failure"
    
    # Tolerance settings
    if 'tolerance' in attr_lower:
        if 'absolute' in attr_lower:
            return "Absolute tolerance for convergence (smaller = more accurate)"
        elif 'relative' in attr_lower:
            return "Relative tolerance for convergence (smaller = more accurate)"
        return "Convergence tolerance setting"
    
    # Newton method settings
    if 'newton' in attr_lower:
        if 'iterations' in attr_lower:
            return "Maximum number of Newton iterations per step"
        elif 'modified' in attr_lower:
            return "Use modified Newton method (reuse Jacobian)"
        elif 'residual' in attr_lower:
            return "Newton residual calculation mode"
        return "Newton method configuration parameter"
    
    # Alpha method settings  
    if 'alpha' in attr_lower:
        if 'spectral' in attr_lower:
            return "Spectral radius for generalized alpha method (0-1, affects stability)"
        elif 'generalized' in attr_lower:
            return "Generalized alpha method for time integration"
        return "Alpha method parameter for time integration"
    
    # Newmark method settings
    if 'newmark' in attr_lower:
        if 'beta' in attr_lower:
            return "Newmark beta parameter (affects stability and accuracy)"
        elif 'gamma' in attr_lower:
            return "Newmark gamma parameter (affects damping)"
        return "Newmark method parameter"
    
    # Solver settings
    if 'solver' in attr_lower:
        if 'linear' in attr_lower:
            return "Linear solver type (dense, sparse, iterative)"
        elif 'static' in attr_lower:
            return "Static solver configuration"
        elif 'dynamic' in attr_lower:
            return "Dynamic solver type for explicit integration"
        return "Solver configuration setting"
    
    # Load settings
    if 'load' in attr_lower:
        if 'step' in attr_lower:
            return "Load step configuration for static/quasi-static analysis"
        elif 'factor' in attr_lower:
            return "Load factor for incremental loading"
        elif 'jacobian' in attr_lower:
            return "Compute Jacobian of loads (for load-dependent systems)"
        return "Load application setting"
    
    # Verbosity and output
    if 'verbose' in attr_lower:
        return "Verbosity level for output (0=silent, 1=minimal, 2=detailed)"
    
    # Display settings
    if 'display' in attr_lower:
        if 'computation' in attr_lower:
            return "Display computation time during simulation"
        elif 'statistics' in attr_lower:
            return "Display solver statistics"
        elif 'global' in attr_lower:
            return "Display global timing information"
        return "Display/output setting"
    
    # Memory and performance
    if 'memory' in attr_lower:
        return "Memory management setting"
    
    # Precision settings
    if 'precision' in attr_lower:
        return "Number of decimal places for output"
    
    # Parallel settings
    if 'parallel' in attr_lower or 'thread' in attr_lower:
        return "Parallel computation and threading setting"
    
    # Specific boolean settings (most important patterns first)
    specific_bool_settings = {
        'ignoreMaxIterations': 'Ignore maximum iteration limit in discontinuous iteration (continue even if not converged)',
        'useRecommendedStepSize': 'Use solver-recommended step size for discontinuous iterations',
        'useNewtonSolver': 'Use Newton solver method for nonlinear equations',
        'useModifiedNewton': 'Use modified Newton method (reuse Jacobian matrix for multiple iterations)',
        'useIndex2Constraints': 'Use index-2 constraints in generalized alpha method',
        'useNewmark': 'Use Newmark method instead of generalized alpha',
        'resetAccelerations': 'Reset accelerations at each time step in generalized alpha method',
        'computeInitialAccelerations': 'Compute initial accelerations for consistent initial conditions',
        'writeInitialValues': 'Write initial values to solution file',
        'writeFileHeader': 'Write column headers to solution files',
        'writeFileFooter': 'Write footer information to solution files',
        'writeSolutionToFile': 'Write solution coordinates to file during simulation',
        'writeRestartFile': 'Write restart file for continuing interrupted simulations',
        'flushFilesImmediately': 'Flush file buffers to disk immediately (slower but safer)',
        'sensorsStoreAndWriteFiles': 'Store sensor data and write to files',
        'sensorsWriteFileHeader': 'Write headers to sensor output files',
        'sensorsWriteFileFooter': 'Write footers to sensor output files',
        'sensorsAppendToFile': 'Append sensor data to existing files instead of overwriting',
        'binarySolutionFile': 'Use binary format for solution files (faster, smaller)',
        'appendToFile': 'Append to existing files instead of overwriting',
        'automaticStepSize': 'Use automatic step size control during time integration',
        'adaptiveStep': 'Use adaptive step size based on convergence and accuracy',
        'simulateInRealtime': 'Run simulation synchronized with real time',
        'cleanUpMemory': 'Clean up memory after simulation (slower but uses less memory)',
        'displayComputationTime': 'Display computation time information during simulation',
        'displayGlobalTimers': 'Display global timing statistics',
        'displayStatistics': 'Display solver statistics and convergence information',
        'pauseAfterEachStep': 'Pause execution after each time step (for debugging)',
        'reuseConstantMassMatrix': 'Reuse mass matrix if it remains constant (performance optimization)',
        'reuseAnalyzedPattern': 'Reuse analyzed sparse matrix pattern (performance optimization)',
        'ignoreSingularJacobian': 'Continue computation even with singular Jacobian matrix',
        'showCausingItems': 'Show which items cause solver problems in error messages',
        'computeLoadsJacobian': 'Compute Jacobian of loads (needed for load-dependent systems)',
        'constrainODE1coordinates': 'Apply constraints to ODE1 coordinates in static solver',
        'loadStepGeometric': 'Use geometric progression for load steps',
        'useLoadFactor': 'Use load factor approach in static analysis'
    }
    
    if attr_name in specific_bool_settings:
        return specific_bool_settings[attr_name]
    
    # Generic boolean settings fallback
    if attr_name.startswith(('use', 'enable', 'compute', 'ignore', 'write')):
        if attr_name.startswith('use'):
            action = attr_name[3:]  # Remove 'use'
        elif attr_name.startswith('enable'):
            action = attr_name[6:]  # Remove 'enable'
        elif attr_name.startswith('compute'):
            action = attr_name[7:]  # Remove 'compute'
        elif attr_name.startswith('ignore'):
            action = attr_name[6:]  # Remove 'ignore'
        elif attr_name.startswith('write'):
            action = attr_name[5:]  # Remove 'write'
        else:
            action = attr_name
        return f"Enable/disable {action.replace('_', ' ').lower()}"
    
    # Damping settings
    if 'damp' in attr_lower:
        return "Damping parameter for numerical stability"
    
    # Default fallback with better description
    return f"Simulation setting: {attr_name.replace('_', ' ').title()}"

def discoverSimulationSettingsStructure(exu, existing_settings=None):
    """
    Improved discovery of all properties and nested objects in exudyn.SimulationSettings.
    """
    import inspect
    
    # Use existing settings if provided, otherwise create a fresh one
    if existing_settings is not None:
        simulationSettings = existing_settings
    else:
        simulationSettings = exu.SimulationSettings()
    
    def is_settings_object(value, attr_name):
        """Determine if a value is a settings object that should be expanded."""
        if value is None:
            return False
            
        # Skip basic types
        if isinstance(value, (int, float, str, bool, list, tuple)):
            return False
            
        # Skip callable objects
        if callable(value):
            return False
            
        # Skip enum types - they should be treated as leaf values, not nested objects
        if hasattr(value, '__class__') and hasattr(value.__class__, '__name__'):
            type_name = value.__class__.__name__
            if 'Type' in type_name and hasattr(value, 'name') and hasattr(value, 'value'):
                return False
            
        # Known settings object patterns
        settings_patterns = [
            'Settings', 'settings', 'Integration', 'Solver', 'Parallel',
            'Alpha', 'alpha', 'Newton', 'newton', 'Discontinuous', 'discontinuous'
        ]
        
        # Check if the attribute name suggests it's a settings object
        attr_lower = attr_name.lower()
        if any(pattern.lower() in attr_lower for pattern in settings_patterns):
            return True
            
        # Check if the value's type name suggests it's a settings object
        type_name = type(value).__name__
        if any(pattern in type_name for pattern in settings_patterns):
            return True
            
        # Check if the object has attributes that suggest it's a settings container
        try:
            attrs = [attr for attr in dir(value) if not attr.startswith('_')]
            # If it has multiple non-callable attributes, it's likely a settings object
            non_callable_attrs = [attr for attr in attrs if not callable(getattr(value, attr, None))]
            if len(non_callable_attrs) > 1:
                return True
        except:
            pass
        
        # Additional checks for specific exudyn objects
        type_name = type(value).__name__
        if any(pattern in type_name for pattern in ['Alpha', 'Newton', 'Discontinuous', 'Implicit', 'Explicit']):
            return True
            
        # Check for objects with numeric/boolean attributes (likely settings)
        try:
            attrs = [attr for attr in dir(value) if not attr.startswith('_')]
            if len(attrs) > 0:
                # Sample a few attributes to see if they're settings-like
                sample_attrs = attrs[:min(3, len(attrs))]
                for attr in sample_attrs:
                    try:
                        attr_value = getattr(value, attr)
                        if isinstance(attr_value, (int, float, bool)):
                            return True
                    except:
                        pass
        except:
            pass
            
        return False
    
    def discover_object_structure(obj, name="simulationSettings", level=0, max_level=5):
        """Recursively discover the structure with improved detection."""
        structure = {}
        
        # Prevent infinite recursion
        if level > max_level:
            return structure
        
        # Get all attributes that don't start with underscore
        try:
            attrs = [attr for attr in dir(obj) if not attr.startswith('_')]
        except:
            return structure
        
        for attr in attrs:
            try:
                value = getattr(obj, attr)
                
                # Skip methods and properties
                if callable(value):
                    continue
                
                # Check if this is a nested settings object
                if is_settings_object(value, attr):
                    # Recursively discover nested structure
                    nested_structure = discover_object_structure(value, f"{name}.{attr}", level+1, max_level)
                    
                    structure[attr] = {
                        'type': 'object',
                        'nested': nested_structure,
                        'value_type': type(value).__name__
                    }
                else:
                    # This is a leaf value - extract its properties
                    attr_type = type(value).__name__
                    
                    # Check if this is an enum type and get better type information
                    if hasattr(value, '__class__') and hasattr(value.__class__, '__module__'):
                        full_type = f"{value.__class__.__module__}.{value.__class__.__name__}"
                        if 'exudyn' in full_type and 'Type' in attr_type:
                            attr_type = value.__class__.__name__
                    
                    help_text = extractGenericHelp(obj, attr)
                    
                    structure[attr] = {
                        'type': attr_type,
                        'value': value,
                        'path': f"{name}.{attr}",
                        'help': help_text
                    }
                    
            except Exception as e:
                # Some attributes might not be accessible
                structure[attr] = {
                    'type': 'unknown',
                    'error': str(e),
                    'path': f"{name}.{attr}",
                    'help': f"Error accessing {attr}: {e}"
                }
        
        return structure
    
    # Discover the complete structure
    discovered_structure = discover_object_structure(simulationSettings)
    
    # Debug print to see what was discovered
    print(f"\n🔍 DISCOVERED SIMULATION SETTINGS STRUCTURE:")
    print(f"Total top-level attributes: {len(discovered_structure)}")
    for key, info in discovered_structure.items():
        if info['type'] == 'object':
            nested_count = len(info.get('nested', {}))
            print(f"  📁 {key} ({info.get('value_type', 'unknown')}) - {nested_count} nested items")
            # Show nested structure for debugging
            nested = info.get('nested', {})
            for nested_key, nested_info in nested.items():
                if nested_info['type'] == 'object':
                    deep_nested_count = len(nested_info.get('nested', {}))
                    print(f"    📁 {nested_key} ({nested_info.get('value_type', 'unknown')}) - {deep_nested_count} nested items")
                    # Show even deeper nesting
                    deep_nested = nested_info.get('nested', {})
                    for deep_key, deep_info in deep_nested.items():
                        if deep_info['type'] == 'object':
                            deeper_count = len(deep_info.get('nested', {}))
                            print(f"      📁 {deep_key} ({deep_info.get('value_type', 'unknown')}) - {deeper_count} nested items")
                        else:
                            print(f"      📄 {deep_key} = {deep_info.get('value')} ({deep_info['type']})")
                else:
                    print(f"    📄 {nested_key} = {nested_info.get('value')} ({nested_info['type']})")
        else:
            print(f"  📄 {key} = {info.get('value')} ({info['type']})")
    print()
    
    return discovered_structure

def create_search_frame(parent_form):
    """Create a search frame with search functionality."""
    search_frame = QFrame()
    search_frame.setFrameStyle(QFrame.StyledPanel)
    search_frame.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; }")
    
    search_layout = QHBoxLayout(search_frame)
    search_layout.setContentsMargins(10, 5, 10, 5)
    
    # Search icon/label
    search_label = QLabel("🔍 Search:")
    search_label.setStyleSheet("font-weight: bold; color: #495057;")
    
    # Search input
    search_input = QLineEdit()
    search_input.setPlaceholderText("Search settings... See clickable tab overview below")
    search_input.setStyleSheet("""
        QLineEdit {
            padding: 5px;
            border: 1px solid #ced4da;
            border-radius: 3px;
            font-size: 11px;
        }
        QLineEdit:focus {
            border: 2px solid #007bff;
        }
    """)
    
    # Clear button
    clear_button = QPushButton("✕")
    clear_button.setFixedSize(25, 25)
    clear_button.setStyleSheet("""
        QPushButton {
            border: 1px solid #ced4da;
            border-radius: 3px;
            background-color: #ffffff;
            color: #6c757d;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #f8f9fa;
            color: #dc3545;
        }
    """)
    clear_button.setToolTip("Clear search")
    
    # Results info
    results_label = QLabel("")
    results_label.setStyleSheet("color: #6c757d; font-size: 10px;")
    
    # Layout
    search_layout.addWidget(search_label)
    search_layout.addWidget(search_input)
    search_layout.addWidget(clear_button)
    search_layout.addWidget(results_label)
    search_layout.addStretch()
    
    # Store references for search functionality
    search_frame.search_input = search_input
    search_frame.clear_button = clear_button
    search_frame.results_label = results_label
    
    # Connect signals
    search_input.textChanged.connect(lambda text: perform_search(parent_form, text))
    clear_button.clicked.connect(lambda: clear_search(parent_form))
    
    # Add keyboard shortcuts
    search_input.setToolTip("Search all settings simultaneously\n\n✨ Visual Indicators:\n• 📍 Blue overview bar with clickable tab buttons\n• 🔍 Tab titles updated with match counts  \n• 🟡 All matching fields highlighted across tabs\n• 📊 Detailed results show distribution\n\n⌨️ Shortcuts:\n• Ctrl+F to focus search\n• Escape to clear\n\n💡 Try: 'solver', 'tolerance', 'step', 'time'")
    
    return search_frame

def perform_search(form, search_text):
    """Perform search and highlight matching settings."""
    search_text = search_text.lower().strip()
    
    # Find search frame and results label
    search_frame = form.findChild(QFrame)
    if not search_frame or not hasattr(search_frame, 'results_label'):
        return
    
    results_label = search_frame.results_label
    
    if not search_text:
        # Clear search - restore all widgets
        restore_all_widgets(form)
        clear_tab_overview(form)
        results_label.setText("")
        return
    
    # Find all widgets with settings paths and their associated labels
    matching_widgets = []
    all_setting_widgets = []
    
    # First pass: collect all setting widgets and their labels
    for widget in form.findChildren(QWidget):
        path = widget.property('settings_path')
        if path:
            all_setting_widgets.append(widget)
            
            # Check if path matches search (more comprehensive matching)
            widget_matches = False
            
            # Match against path components
            path_parts = path.lower().replace('simulationsettings.', '').split('.')
            if any(search_text in part for part in path_parts):
                widget_matches = True
            
            # Match against tooltip (help text)
            if search_text in widget.toolTip().lower():
                widget_matches = True
            
            # Match against widget text/value
            if hasattr(widget, 'text') and search_text in widget.text().lower():
                widget_matches = True
            elif hasattr(widget, 'currentText') and search_text in widget.currentText().lower():
                widget_matches = True
            
            # Find associated label by looking at parent layout
            if widget_matches:
                matching_widgets.append(widget)
                # Also find and highlight the associated label
                label_widget = find_associated_label(widget)
                if label_widget and label_widget not in matching_widgets:
                    matching_widgets.append(label_widget)
    
    # Update results info
    actual_matches = len([w for w in matching_widgets if w.property('settings_path')])
    if actual_matches > 0:
        results_label.setText(f"Found {actual_matches} matches")
        results_label.setStyleSheet("color: #28a745; font-size: 10px;")
    else:
        results_label.setText("No matches found")
        results_label.setStyleSheet("color: #dc3545; font-size: 10px;")
    
    # Highlight ALL matching widgets simultaneously
    highlight_all_search_results(form, matching_widgets, all_setting_widgets)
    
    # Show tabs containing matches
    show_tabs_with_matches(form, matching_widgets)

def find_associated_label(widget):
    """Find the label widget associated with a settings widget."""
    # Look for QLabel widgets in the same parent layout
    parent = widget.parent()
    if not parent:
        return None
    
    # Check siblings for QLabel
    for sibling in parent.findChildren(QLabel):
        # Check if they're in the same row/layout
        sibling_parent = sibling.parent()
        if sibling_parent == parent:
            return sibling
    
    # If not found, look in parent's parent (for nested layouts)
    grandparent = parent.parent()
    if grandparent:
        for label in grandparent.findChildren(QLabel):
            # Check if this label is close to our widget
            if label.parent() == parent or label.parent() == grandparent:
                return label
    
    return None

def highlight_all_search_results(form, matching_widgets, all_setting_widgets):
    """Highlight ALL matching widgets simultaneously without dimming others."""
    # Store original stylesheets if not already stored
    if not hasattr(form, '_original_styles'):
        form._original_styles = {}
    
    # First, restore all widgets to original state
    for widget in form.findChildren(QWidget):
        widget_id = id(widget)
        if widget_id in form._original_styles:
            widget.setStyleSheet(form._original_styles[widget_id])
    
    # Now highlight all matching widgets
    for widget in matching_widgets:
        widget_id = id(widget)
        
        # Store original style if not stored
        if widget_id not in form._original_styles:
            form._original_styles[widget_id] = widget.styleSheet()
        
        # Apply highlight style
        current_style = form._original_styles[widget_id]
        if isinstance(widget, QLabel):
            # Special highlighting for labels
            highlighted_style = current_style + """
                QLabel {
                    background-color: #fff3cd !important;
                    border: 2px solid #ffc107 !important;
                    border-radius: 3px !important;
                    padding: 2px !important;
                    font-weight: bold !important;
                    color: #856404 !important;
                }
            """
        else:
            # Highlighting for input widgets
            highlighted_style = current_style + """
                QWidget {
                    background-color: #fff3cd !important;
                    border: 2px solid #ffc107 !important;
                    border-radius: 3px !important;
                }
                QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                    background-color: #fff3cd !important;
                    border: 2px solid #ffc107 !important;
                    border-radius: 3px !important;
                }
                QCheckBox {
                    background-color: #fff3cd !important;
                    border-radius: 3px !important;
                    padding: 2px !important;
                }
            """
        
        widget.setStyleSheet(highlighted_style)

def find_widget_tab_index(widget, tab_widget):
    """Find which tab index contains the given widget using multiple strategies."""
    if not widget or not tab_widget:
        return None
    
    # Strategy 1: Walk up the widget hierarchy to find a direct tab child
    current = widget
    for depth in range(15):  # Reasonable depth limit
        if not current:
            break
        
        # Check if current widget is a direct child of any tab
        for i in range(tab_widget.count()):
            tab_content = tab_widget.widget(i)
            if current == tab_content:
                return i
            
            # Also check if current is a child of the tab content
            if current.parent() == tab_content:
                return i
        
        current = current.parent()
    
    # Strategy 2: Check if the widget is anywhere within any tab's widget tree
    for i in range(tab_widget.count()):
        tab_content = tab_widget.widget(i)
        if is_widget_descendant(widget, tab_content):
            return i
    
    return None

def is_widget_descendant(widget, potential_ancestor):
    """Check if widget is a descendant of potential_ancestor."""
    if not widget or not potential_ancestor:
        return False
    
    # Use Qt's isAncestorOf method if available
    try:
        return potential_ancestor.isAncestorOf(widget)
    except:
        # Fallback: manual tree traversal
        current = widget
        for depth in range(20):  # Reasonable depth limit
            if not current:
                break
            if current == potential_ancestor:
                return True
            current = current.parent()
        return False

def show_tabs_with_matches(form, matching_widgets):
    """Show all tabs that contain matching widgets by adding prominent visual indicators."""
    # Find tab widget
    tab_widget = form.findChild(QTabWidget)
    if not tab_widget:
        return
    
    # Reset all tab styling and text to original clean names
    original_tab_names = get_original_tab_names(tab_widget)
    for i in range(tab_widget.count()):
        # Use original clean name instead of trying to clean corrupted text
        original_name = original_tab_names.get(i, f"Tab {i}")
        tab_widget.setTabText(i, original_name)
    
    # Reset tab bar styling
    tab_widget.setStyleSheet("")
    
    # Track which tabs have matches and count matches per tab
    tabs_with_matches = {}
    
    for widget in matching_widgets:
        # Only count widgets with settings_path (actual settings, not labels)
        path = widget.property('settings_path')
        if not path:
            continue
            
        # Find which tab contains this widget using a more robust approach
        found_tab_index = find_widget_tab_index(widget, tab_widget)
        
        if found_tab_index is not None:
            tabs_with_matches[found_tab_index] = tabs_with_matches.get(found_tab_index, 0) + 1
    
    # Style tabs with matches and add indicators
    if tabs_with_matches:
        # Add text indicators with match counts using original clean names
        for tab_index, match_count in tabs_with_matches.items():
            original_name = original_tab_names.get(tab_index, f"Tab {tab_index}")
            tab_widget.setTabText(tab_index, f"🔍 {original_name} ({match_count})")
        
        # Apply global tab styling that works reliably in PyQt5
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                border: 1px solid #c0c0c0;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom: 1px solid #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #e0e0e0;
            }
        """)
        
        # Store which tabs have matches for alternative highlighting
        tab_widget.setProperty('tabs_with_matches', list(tabs_with_matches.keys()))
        
        # Alternative: Set individual tab properties for custom highlighting
        for tab_index, match_count in tabs_with_matches.items():
            try:
                # Try to access the actual tab widget if possible
                tab_bar = tab_widget.tabBar()
                if tab_bar:
                    # Set custom data to identify matching tabs
                    tab_bar.setTabData(tab_index, {'has_matches': True, 'match_count': match_count})
            except Exception as e:
                print(f"Note: Could not set tab data: {e}")
    
    # Switch to first tab with matches if not already on a matching tab
    current_tab = tab_widget.currentIndex()
    if tabs_with_matches and current_tab not in tabs_with_matches:
        first_match_tab = min(tabs_with_matches.keys())
        tab_widget.setCurrentIndex(first_match_tab)
    
    # Update search results to show tab distribution
    update_search_results_with_tab_info(form, tabs_with_matches)
    
    # Add visual tab overview
    add_tab_overview_widget(form, tabs_with_matches)

def restore_all_widgets(form):
    """Restore all widgets to their original appearance."""
    if not hasattr(form, '_original_styles'):
        return
    
    for widget in form.findChildren(QWidget):
        widget_id = id(widget)
        if widget_id in form._original_styles:
            widget.setStyleSheet(form._original_styles[widget_id])

def setup_keyboard_shortcuts(form, search_frame):
    """Set up keyboard shortcuts for search functionality."""
    # Ctrl+F to focus search
    search_shortcut = QShortcut(QKeySequence("Ctrl+F"), form)
    search_shortcut.activated.connect(lambda: search_frame.search_input.setFocus())
    
    # Escape to clear search
    escape_shortcut = QShortcut(QKeySequence("Escape"), form)
    escape_shortcut.activated.connect(lambda: clear_search(form))
    
    # Enter to search for next match (if multiple matches)
    enter_shortcut = QShortcut(QKeySequence("Return"), search_frame.search_input)
    enter_shortcut.activated.connect(lambda: focus_next_match(form))

def focus_next_match(form):
    """Focus the next matching widget in search results."""
    # Find all highlighted widgets
    matching_widgets = []
    for widget in form.findChildren(QWidget):
        if widget.property('settings_path') and '#fff3cd' in widget.styleSheet():
            matching_widgets.append(widget)
    
    if matching_widgets:
        # Simple cycling through matches
        for widget in matching_widgets:
            if hasattr(widget, 'setFocus'):
                widget.setFocus()
                break

def clear_search(form):
    """Clear the search and restore all widgets."""
    # Find search frame and clear input
    search_frame = form.findChild(QFrame)
    if search_frame and hasattr(search_frame, 'search_input'):
        search_frame.search_input.clear()
    
    # Restore all widgets
    restore_all_widgets(form)
    
    # Clear tab indicators
    clear_tab_indicators(form)
    
    # Remove tab overview widget
    clear_tab_overview(form)
    
    # Clear results label
    if search_frame and hasattr(search_frame, 'results_label'):
        search_frame.results_label.setText("")

def clear_tab_overview(form):
    """Remove the tab overview widget."""
    existing_overview = form.findChild(QWidget, "tab_overview")
    if existing_overview:
        existing_overview.setParent(None)
        existing_overview.deleteLater()

def get_original_tab_names(tab_widget):
    """Get the original clean tab names, using stored originals if available."""
    # Try to get stored original names from the form
    form = tab_widget.parent()
    while form and not hasattr(form, '_original_tab_names'):
        form = form.parent()
    
    if form and hasattr(form, '_original_tab_names'):
        return form._original_tab_names
    
    # Fallback: Clean current tab names
    original_names = {}
    for i in range(tab_widget.count()):
        current_text = tab_widget.tabText(i)
        
        # Remove all search indicators and clean up the text
        clean_text = current_text
        
        # Remove search icons and indicators
        clean_text = clean_text.replace('🔍 ', '').replace(' 🔍', '')
        
        # Remove match count parentheses (e.g., "(5)")
        import re
        clean_text = re.sub(r'\s*\(\d+\)$', '', clean_text)
        
        # Remove any remaining numbers that might be artifacts
        # This handles cases like "Linear Solver 5 2 2 5 5 5 5 5"
        clean_text = re.sub(r'\s+\d+(\s+\d+)*$', '', clean_text)
        
        # Final cleanup - remove extra spaces
        clean_text = ' '.join(clean_text.split())
        
        original_names[i] = clean_text
    
    return original_names

def add_tab_overview_widget(form, tabs_with_matches):
    """Add a prominent visual overview of which tabs contain matches."""
    # Remove any existing overview widget
    existing_overview = form.findChild(QWidget, "tab_overview")
    if existing_overview:
        existing_overview.setParent(None)
        existing_overview.deleteLater()
    
    if not tabs_with_matches:
        return
    
    # Find the main layout and tab widget
    main_layout = form.layout()
    tab_widget = form.findChild(QTabWidget)
    if not main_layout or not tab_widget:
        return
    
    # Create overview widget
    overview_widget = QFrame()
    overview_widget.setObjectName("tab_overview")
    overview_widget.setFrameStyle(QFrame.StyledPanel)
    overview_widget.setStyleSheet("""
        QFrame#tab_overview {
            background-color: #e3f2fd;
            border: 2px solid #2196f3;
            border-radius: 5px;
            padding: 5px;
        }
    """)
    
    overview_layout = QHBoxLayout(overview_widget)
    overview_layout.setContentsMargins(10, 5, 10, 5)
    
    # Add info label
    info_label = QLabel("📍 Tabs with matches:")
    info_label.setStyleSheet("font-weight: bold; color: #1976d2;")
    overview_layout.addWidget(info_label)
    
    # Create clickable tab buttons for each tab with matches
    total_matches = sum(tabs_with_matches.values())
    
    # Get original clean tab names (before any search modifications)
    original_tab_names = get_original_tab_names(tab_widget)
    
    for tab_index, match_count in sorted(tabs_with_matches.items()):
        # Use original clean tab name
        clean_name = original_tab_names.get(tab_index, f"Tab {tab_index}")
        
        # Create clickable button for each tab
        tab_button = QPushButton(f"🔍 {clean_name} ({match_count})")
        tab_button.setStyleSheet("""
            QPushButton {
                background-color: #fff3cd;
                border: 2px solid #ffc107;
                border-radius: 3px;
                padding: 5px 10px;
                font-weight: bold;
                color: #856404;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #ffc107;
                color: #212529;
            }
            QPushButton:pressed {
                background-color: #e0a800;
            }
        """)
        
        # Connect button to switch to that tab
        tab_button.clicked.connect(lambda checked, idx=tab_index: tab_widget.setCurrentIndex(idx))
        tab_button.setToolTip(f"Click to go to {clean_name} tab\n{match_count} matches found")
        
        overview_layout.addWidget(tab_button)
    
    # Add total count
    total_label = QLabel(f"Total: {total_matches} matches")
    total_label.setStyleSheet("font-weight: bold; color: #1976d2; margin-left: 10px;")
    overview_layout.addWidget(total_label)
    
    overview_layout.addStretch()
    
    # Insert the overview widget after the search frame
    tab_widget_index = -1
    for i in range(main_layout.count()):
        item = main_layout.itemAt(i)
        if item and item.widget() == tab_widget:
            tab_widget_index = i
            break
    
    if tab_widget_index >= 0:
        main_layout.insertWidget(tab_widget_index, overview_widget)

def update_search_results_with_tab_info(form, tabs_with_matches):
    """Update the search results label with detailed tab information."""
    # Find search frame and results label
    search_frame = form.findChild(QFrame)
    if not search_frame or not hasattr(search_frame, 'results_label'):
        return
    
    results_label = search_frame.results_label
    
    if not tabs_with_matches:
        return
    
    # Find tab widget to get tab names
    tab_widget = form.findChild(QTabWidget)
    if not tab_widget:
        return
    
    # Calculate total matches and create detailed info
    total_matches = sum(tabs_with_matches.values())
    tab_info = []
    
    # Get original clean tab names
    original_tab_names = get_original_tab_names(tab_widget)
    
    for tab_index, match_count in sorted(tabs_with_matches.items()):
        clean_name = original_tab_names.get(tab_index, f"Tab {tab_index}")
        tab_info.append(f"{clean_name}({match_count})")
    
    # Create comprehensive results text
    if len(tabs_with_matches) == 1:
        results_text = f"Found {total_matches} matches in {tab_info[0]}"
    else:
        results_text = f"Found {total_matches} matches across {len(tabs_with_matches)} tabs: {', '.join(tab_info)}"
    
    results_label.setText(results_text)
    results_label.setStyleSheet("color: #28a745; font-size: 10px; font-weight: bold;")

def clear_tab_indicators(form):
    """Remove search indicators and styling from all tabs."""
    tab_widget = form.findChild(QTabWidget)
    if not tab_widget:
        return
    
    # Store original tab names if not already stored
    if not hasattr(form, '_original_tab_names'):
        form._original_tab_names = {
            0: "General", 1: "Time Integration", 2: "Linear Solver", 
            3: "Solution Settings", 4: "Static Solver", 5: "Parallel", 6: "Advanced"
        }
    
    # Reset all tab text to original clean names
    for i in range(tab_widget.count()):
        original_name = form._original_tab_names.get(i, f"Tab {i}")
        tab_widget.setTabText(i, original_name)
    
    # Reset tab styling
    tab_widget.setStyleSheet("")

def createSimulationSettingsForm(parent, existing_settings=None):
    """
    Create an improved simulation settings form with better UI organization and search functionality.
    """
    # Import additional widgets needed for better UI
    from PyQt5.QtWidgets import QTabWidget, QFrame, QScrollArea
    
    structure = discoverSimulationSettingsStructure(exu, existing_settings)
    
    # Create main dialog
    form = QDialog(parent)
    form.setWindowTitle("Simulation Settings")
    form.setMinimumSize(800, 600)
    form.resize(900, 700)
    
    # Main layout
    main_layout = QVBoxLayout(form)
    
    # Add search functionality
    search_frame = create_search_frame(form)
    main_layout.addWidget(search_frame)
    
    # Create tab widget for major categories
    tab_widget = QTabWidget()
    
    # Organize settings into logical tabs based on actual structure
    tab_structure = {
        "General": ["displayComputationTime", "displayGlobalTimers", "displayStatistics", "cleanUpMemory", "outputPrecision", "pauseAfterEachStep"],
        "Time Integration": ["timeIntegration"],  # Contains numberOfSteps, endTime, etc.
        "Linear Solver": ["linearSolverType", "linearSolverSettings"],
        "Solution Settings": ["solutionSettings"],  # File output settings 
        "Static Solver": ["staticSolver"],
        "Parallel": ["parallel"],
        "Advanced": []  # Everything else including numericalDifferentiation, etc.
    }
    
    # Create tabs
    for tab_name, field_list in tab_structure.items():
        tab_widget.addTab(create_settings_tab(structure, field_list, tab_name), tab_name)
    
    main_layout.addWidget(tab_widget)
    
    # Add buttons
    button_layout = QHBoxLayout()
    
    # Show Changes button
    show_changes_btn = QPushButton("📊 Show Changes")
    show_changes_btn.setStyleSheet("""
        QPushButton {
            background-color: #17a2b8;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #138496;
        }
    """)
    show_changes_btn.clicked.connect(lambda: show_simulation_changes(form, existing_settings))
    
    # Standard buttons
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(form.accept)
    buttons.rejected.connect(form.reject)
    
    button_layout.addWidget(show_changes_btn)
    button_layout.addStretch()
    button_layout.addWidget(buttons)
    
    main_layout.addLayout(button_layout)
    
    # Add keyboard shortcuts for search
    setup_keyboard_shortcuts(form, search_frame)
    
    # Store original tab names for proper cleanup
    form._original_tab_names = {
        0: "General", 1: "Time Integration", 2: "Linear Solver", 
        3: "Solution Settings", 4: "Static Solver", 5: "Parallel", 6: "Advanced"
    }
    
    return form

def create_settings_tab(structure, field_list, tab_name):
    """Create a single tab with organized settings."""
    tab_widget = QWidget()
    
    # Create scroll area for the tab
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameStyle(QFrame.NoFrame)
    
    # Content widget
    content_widget = QWidget()
    content_layout = QVBoxLayout(content_widget)
    content_layout.setSpacing(15)
    
    # Track which fields we've processed
    processed_fields = set()
    
    # Add specified fields first
    for field_name in field_list:
        if field_name in structure:
            info = structure[field_name]
            if info['type'] == 'object':
                # Create collapsible group for nested objects
                group_widget = create_collapsible_group(field_name, info, processed_fields)
                content_layout.addWidget(group_widget)
            else:
                # Create simple field
                field_widget = create_enhanced_field_widget(field_name, info)
                content_layout.addWidget(field_widget)
            processed_fields.add(field_name)
    
    # For "Advanced" tab, add remaining unprocessed fields
    if tab_name == "Advanced":
        remaining_fields = [k for k in structure.keys() if k not in processed_fields]
        if remaining_fields:
            for field_name in remaining_fields:
                info = structure[field_name]
                if info['type'] == 'object':
                    group_widget = create_collapsible_group(field_name, info, processed_fields)
                    content_layout.addWidget(group_widget)
                else:
                    field_widget = create_enhanced_field_widget(field_name, info)
                    content_layout.addWidget(field_widget)
    
    # Add stretch to push everything to top
    content_layout.addStretch()
    
    # Set up scroll area
    scroll.setWidget(content_widget)
    
    # Tab layout
    tab_layout = QVBoxLayout(tab_widget)
    tab_layout.addWidget(scroll)
    
    return tab_widget

def create_collapsible_group(field_name, info, processed_fields):
    """Create a collapsible group box for nested settings."""
    from PyQt5.QtWidgets import QFrame
    
    # Main frame for the group
    frame = QFrame()
    frame.setFrameStyle(QFrame.StyledPanel)
    frame_layout = QVBoxLayout(frame)
    
    # Group header
    header_label = QLabel(f"📁 {field_name.replace('_', ' ').title()}")
    header_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #2c3e50; padding: 5px;")
    frame_layout.addWidget(header_label)
    
    # Content area with form layout
    content_frame = QFrame()
    content_frame.setFrameStyle(QFrame.Box)
    content_frame.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; }")
    content_layout = QFormLayout(content_frame)
    content_layout.setSpacing(8)
    
    # Add nested fields (handle both leaf values and nested objects)
    nested_structure = info.get('nested', {})
    for nested_field, nested_info in nested_structure.items():
        if nested_info['type'] == 'object':
            # Recursively create nested group for deeper objects
            nested_group = create_collapsible_group(nested_field, nested_info, processed_fields)
            content_layout.addRow(nested_group)
        else:
            # Create leaf widget
            widget = create_enhanced_widget_for_type(nested_info['type'], nested_info.get('value'))
            label = QLabel(nested_field.replace('_', ' ').title())
            
            # Enhanced tooltips
            help_text = nested_info.get('help', f"Setting: {nested_field}")
            widget.setToolTip(f"<b>{nested_field}</b><br/>{help_text}")
            label.setToolTip(f"<b>{nested_field}</b><br/>{help_text}")
            
            # Store path for data collection
            widget.setProperty('settings_path', nested_info['path'])
            
            content_layout.addRow(label, widget)
    
    frame_layout.addWidget(content_frame)
    return frame

def create_enhanced_field_widget(field_name, info):
    """Create an enhanced widget for a single field."""
    frame = QFrame()
    frame.setMaximumHeight(60)
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(10, 5, 10, 5)
    
    # Label
    label = QLabel(field_name.replace('_', ' ').title())
    label.setMinimumWidth(200)
    label.setStyleSheet("font-weight: bold;")
    
    # Widget
    widget = create_enhanced_widget_for_type(info['type'], info.get('value'))
    widget.setMinimumWidth(200)
    
    # Enhanced tooltip
    help_text = info.get('help', f"Setting: {field_name}")
    tooltip_text = f"<b>{field_name}</b><br/>{help_text}"
    widget.setToolTip(tooltip_text)
    label.setToolTip(tooltip_text)
    
    # Store path
    widget.setProperty('settings_path', info['path'])
    
    layout.addWidget(label)
    layout.addWidget(widget)
    layout.addStretch()
    
    return frame

def should_use_scientific_notation(value):
    """
    Determine if a float value should use scientific notation widget.
    
    Args:
        value: The float value to check
        
    Returns:
        bool: True if scientific notation should be used
    """
    if value == 0:
        return False
    
    abs_value = abs(value)
    
    # Use scientific notation for:
    # - Very small values (< 1e-4) that would show as 0.0000...
    # - Very large values (> 1e6) 
    # - Values that would have more than 6 decimal places in normal notation
    return (abs_value < 1e-4 or abs_value > 1e6 or 
            (abs_value < 1.0 and f"{abs_value:.6f}".count('0') > 3))

def create_scientific_notation_widget(default_value):
    """Create a specialized widget for scientific notation values."""
    widget = QLineEdit()
    
    # Set up validator for scientific notation
    # Pattern allows: 1.23e-4, -1.23E+4, 1.23e4, 1e-6, .5e3, 0.001, 1000, etc.
    sci_pattern = QRegExp(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")
    validator = QRegExpValidator(sci_pattern)
    widget.setValidator(validator)
    
    # Format the default value in scientific notation
    if default_value is not None:
        if should_use_scientific_notation(default_value):
            # Use consistent scientific notation format
            formatted = f"{default_value:.2e}"
            # Ensure we use period as decimal separator for consistency
            formatted = formatted.replace(',', '.')
            widget.setText(formatted)
        else:
            widget.setText(str(default_value))
    
    # Enhanced styling for scientific notation
    widget.setStyleSheet("""
        QLineEdit { 
            padding: 3px; 
            font-family: 'Courier New', monospace;
            background-color: #f0f8ff;
            border: 1px solid #4a90e2;
        }
        QLineEdit:focus {
            border: 2px solid #2c5aa0;
            background-color: #ffffff;
        }
    """)
    
    # Add tooltip explaining the format
    widget.setToolTip("Scientific notation format: 1.23e-4, -5.67E+8, etc.")
    
    # Mark as scientific notation widget for data collection
    widget.setProperty('is_scientific', True)
    
    return widget

def create_enhanced_widget_for_type(type_name, default_value):
    """Create enhanced widgets with better styling and functionality."""
    if type_name == 'bool':
        widget = QCheckBox()
        if default_value is not None:
            widget.setChecked(default_value)
        widget.setStyleSheet("QCheckBox { font-size: 11px; }")
        return widget
        
    elif type_name in ['int', 'float']:
        if type_name == 'int':
            widget = QSpinBox()
            widget.setRange(-999999999, 999999999)
            if default_value is not None:
                widget.setValue(int(default_value))
            widget.setStyleSheet("QSpinBox { padding: 3px; }")
        else:
            # For float values, check if we need scientific notation
            if default_value is not None and should_use_scientific_notation(default_value):
                # Use scientific notation line edit for very small/large values
                widget = create_scientific_notation_widget(default_value)
            else:
                # Use regular double spin box for normal range values
                widget = QDoubleSpinBox()
                widget.setRange(-999999999.0, 999999999.0)
                widget.setDecimals(6)
                if default_value is not None:
                    widget.setValue(float(default_value))
                widget.setStyleSheet("QDoubleSpinBox { padding: 3px; }")
        
        return widget
        
    elif type_name == 'str':
        widget = QLineEdit()
        if default_value is not None:
            widget.setText(str(default_value))
        widget.setStyleSheet("QLineEdit { padding: 3px; }")
        return widget
        
    else:
        # Check if this is an enum type that should be a dropdown
        widget = create_enum_dropdown(type_name, default_value)
        if widget is not None:
            return widget
        
        # Enhanced fallback with better styling
        widget = QLineEdit()
        if default_value is not None:
            widget.setText(str(default_value))
        widget.setStyleSheet("QLineEdit { padding: 3px; }")
        return widget

def create_enum_dropdown(type_name, default_value):
    """Create a dropdown widget for exudyn enum types."""
    # List of known exudyn enum types
    enum_types = [
        'LinearSolverType', 'DynamicSolverType', 'NodeType', 'OutputVariableType',
        'AccessFunctionType', 'ConfigurationType', 'ContactTypeIndex', 
        'CrossSectionType', 'ItemType', 'JointType', 'ObjectType'
    ]
    
    # Check if the type_name contains any of the enum types
    detected_enum = None
    for enum_type in enum_types:
        if enum_type in type_name:
            detected_enum = enum_type
            break
    
    if detected_enum is None:
        return None
    
    # Create dropdown widget
    widget = QComboBox()
    widget.setStyleSheet("QComboBox { padding: 3px; }")
    
    try:
        # Get the enum class from exudyn
        enum_class = getattr(exu, detected_enum)
        
        # Get all enum values (include _None but exclude Python private attributes)
        enum_values = [attr for attr in dir(enum_class) 
                      if not attr.startswith('__') and attr not in ['name', 'value']
                      and not callable(getattr(enum_class, attr, None))]
        
        # Add items to dropdown
        widget.addItems(enum_values)
        
        # Set current selection based on default value
        if default_value is not None:
            current_text = str(default_value)
            
            # Handle different formats of enum values
            if '.' in current_text:
                # Format: "LinearSolverType.EigenSparse" or "exu.LinearSolverType.EigenSparse"
                current_text = current_text.split('.')[-1]
            
            # Try to find matching item
            index = widget.findText(current_text)
            if index >= 0:
                widget.setCurrentIndex(index)
            else:
                # If not found, try to match by enum value
                try:
                    for i, enum_val in enumerate(enum_values):
                        if getattr(enum_class, enum_val) == default_value:
                            widget.setCurrentIndex(i)
                            break
                except:
                    pass
        
        # Store enum information for data collection
        widget.setProperty('enum_type', detected_enum)
        widget.setProperty('enum_class', enum_class)
        
        return widget
        
    except Exception as e:
        print(f"⚠️  Failed to create dropdown for {detected_enum}: {e}")
        # Fallback to line edit
        widget = QLineEdit()
        if default_value is not None:
            widget.setText(str(default_value))
        widget.setStyleSheet("QLineEdit { padding: 3px; }")
        return widget

def simulationSettingsToDict(simulationSettings):
    """Convert simulation settings to a dictionary for saving."""
    if simulationSettings is None:
        return {}
    
    # Use the same discovery mechanism to extract all values
    structure = discoverSimulationSettingsStructure(exu, simulationSettings)
    
    def extract_values_from_structure(structure, prefix=""):
        """Extract all values from the discovered structure."""
        result = {}
        for key, info in structure.items():
            if info['type'] == 'object':
                result[key] = extract_values_from_structure(info['nested'], f"{prefix}.{key}")
            else:
                value = info.get('value')
                
                # Convert enum values to string names for proper serialization
                if value is not None and hasattr(value, '__class__') and hasattr(value.__class__, '__module__'):
                    full_type = f"{value.__class__.__module__}.{value.__class__.__name__}"
                    if 'exudyn' in full_type and 'Type' in value.__class__.__name__:
                        # This is an enum - store the string name
                        value = str(value).split('.')[-1]  # Get just the enum name part
                
                result[key] = value
        return result
    
    return extract_values_from_structure(structure)

def simulationSettingsFromDict(settings_dict, existing_settings=None):
    """Create or update simulation settings from a dictionary."""
    import exudyn as exu
    
    if not settings_dict:
        return exu.SimulationSettings()  # Return default if empty
    
    # Use existing settings if provided, otherwise create new
    if existing_settings is None:
        simulationSettings = exu.SimulationSettings()
    else:
        simulationSettings = existing_settings
    
    # Apply the settings
    applySimulationSettings(simulationSettings, settings_dict)
    
    return simulationSettings

def collectSimulationSettingsData(form):
    """
    Collect data from the enhanced form and return a structured dictionary.
    """
    data = {}
    
    # Find all widgets with settings_path property
    for widget in form.findChildren(QWidget):
        path = widget.property('settings_path')
        if path:
            # Extract value based on widget type
            if isinstance(widget, QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                value = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                value = widget.value()
            elif isinstance(widget, QComboBox):
                # Handle enum types
                text = widget.currentText()
                enum_type = widget.property('enum_type')
                enum_class = widget.property('enum_class')
                
                if enum_type and enum_class:
                    try:
                        # Get the actual enum value
                        enum_value = getattr(enum_class, text)
                        # Store the string name for proper serialization
                        value = text
                    except AttributeError:
                        print(f"⚠️  Unknown enum value '{text}' for {enum_type}, using as-is")
                        value = text
                else:
                    # Fallback for non-enum comboboxes
                    value = text
            elif isinstance(widget, QLineEdit):
                text = widget.text().strip()
                if not text:
                    continue  # Skip empty values
                
                # Check if this is a scientific notation widget
                if widget.property('is_scientific'):
                    try:
                        # Parse scientific notation
                        value = float(text)
                    except ValueError:
                        print(f"⚠️  Invalid scientific notation: {text}")
                        continue
                else:
                    # Regular line edit - try to convert to appropriate type
                    try:
                        if '.' in text or 'e' in text.lower():
                            value = float(text)
                        else:
                            value = int(text)
                    except ValueError:
                        value = text
            else:
                value = widget.text() if hasattr(widget, 'text') else str(widget)
            
            # Store in nested dictionary structure
            set_nested_value(data, path, value)
    
    return data

def set_nested_value(dictionary, path, value):
    """Set a value in a nested dictionary using dot notation path"""
    keys = path.split('.')[1:]  # Skip 'simulationSettings' prefix
    current = dictionary
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value

def applySimulationSettings(simulationSettings, settings_data):
    """
    Apply the collected settings data to the actual SimulationSettings object.
    """
    def apply_nested_settings(obj, data, path=""):
        for key, value in data.items():
            if isinstance(value, dict):
                # Nested object - recurse
                nested_obj = getattr(obj, key, None)
                if nested_obj is not None:
                    apply_nested_settings(nested_obj, value, f"{path}.{key}")
            else:
                # Direct value - apply if attribute exists
                if hasattr(obj, key):
                    try:
                        # Handle enum string conversion
                        if isinstance(value, str):
                            # Check if this might be an enum value
                            attr_value = getattr(obj, key)
                            if hasattr(attr_value, '__class__') and hasattr(attr_value.__class__, '__module__'):
                                full_type = f"{attr_value.__class__.__module__}.{attr_value.__class__.__name__}"
                                if 'exudyn' in full_type and 'Type' in attr_value.__class__.__name__:
                                    # This is an enum field - convert string to enum
                                    enum_class = attr_value.__class__
                                    try:
                                        enum_value = getattr(enum_class, value)
                                        setattr(obj, key, enum_value)
                                        print(f"✅ Set {path}.{key} = {enum_value} (from string '{value}')")
                                        continue
                                    except AttributeError:
                                        print(f"⚠️  Unknown enum value '{value}' for {path}.{key}, using as-is")
                        
                        # Regular value assignment
                        setattr(obj, key, value)
                        print(f"✅ Set {path}.{key} = {value}")
                    except Exception as e:
                        print(f"❌ Failed to set {path}.{key}: {e}")
    
    apply_nested_settings(simulationSettings, settings_data, "simulationSettings")


class ShowChangesDialog(QDialog):
    """Dialog to display settings changes in generated code format."""
    
    def __init__(self, parent, changes_text, title="Settings Changes"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        
        # Layout
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("📝 Generated Code for Your Changes:")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; padding: 10px;")
        layout.addWidget(header_label)
        
        # Info label
        info_label = QLabel("Copy this code to reproduce your settings in a script:")
        info_label.setStyleSheet("color: #7f8c8d; padding: 0 10px;")
        layout.addWidget(info_label)
        
        # Text area with code
        self.text_area = QTextEdit()
        self.text_area.setPlainText(changes_text)
        self.text_area.setFont(QFont("Courier New", 10))
        self.text_area.setStyleSheet("""
            QTextEdit {
                background-color: #2d3748;
                color: #e2e8f0;
                border: 1px solid #4a5568;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        self.text_area.setReadOnly(True)
        layout.addWidget(self.text_area)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        copy_button = QPushButton("📋 Copy to Clipboard")
        copy_button.clicked.connect(self.copy_to_clipboard)
        copy_button.setStyleSheet("""
            QPushButton {
                background-color: #3182ce;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2c5282;
            }
        """)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #718096;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4a5568;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(copy_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
    
    def copy_to_clipboard(self):
        """Copy the changes text to clipboard."""
        print("🔄 Copy to clipboard called...")
        try:
            print("🔄 Getting QApplication instance...")
            app = QApplication.instance()
            if app is None:
                print("❌ No QApplication instance found!")
                return
                
            print("🔄 Getting clipboard...")
            clipboard = app.clipboard()
            if clipboard is None:
                print("❌ Failed to get clipboard!")
                return
                
            print("🔄 Getting text from text area...")
            text_content = self.text_area.toPlainText()
            print(f"🔄 Text length: {len(text_content)} characters")
            
            print("🔄 Setting clipboard text...")
            clipboard.setText(text_content)
            print("✅ Clipboard text set successfully!")
            
            # Show brief confirmation with proper button reference capture
            print("🔄 Getting sender button...")
            sender_button = self.sender()
            if sender_button:
                print("🔄 Setting button text to 'Copied!'...")
                sender_button.setText("✅ Copied!")
                print("🔄 Scheduling button text reset...")
                # Use proper button reference instead of self.sender() in lambda
                QTimer.singleShot(2000, lambda: self._reset_button_text(sender_button))
                print("✅ Copy operation completed successfully!")
            else:
                print("⚠️ No sender button found")
                
        except Exception as e:
            import traceback
            print(f"❌ Failed to copy to clipboard: {e}")
            print("❌ Full traceback:")
            traceback.print_exc()
            
            # Still show confirmation even if copy failed
            try:
                sender_button = self.sender()
                if sender_button:
                    sender_button.setText("❌ Copy Failed!")
                    QTimer.singleShot(2000, lambda: self._reset_button_text(sender_button))
            except Exception as e2:
                print(f"❌ Even error handling failed: {e2}")
    
    def _reset_button_text(self, button):
        """Helper method to reset button text."""
        try:
            button.setText("📋 Copy to Clipboard")
        except Exception as e:
            print(f"❌ Failed to reset button text: {e}")


def show_simulation_changes(form, original_settings):
    """Show the changes made to simulation settings."""
    try:
        from exudynGUI.core.settingsComparison import compare_form_data_with_defaults
        
        # Always compare against factory defaults, not the original settings passed to the dialog
        # This ensures that when reopening the dialog, we show changes from factory defaults
        baseline_structure = discoverSimulationSettingsStructure(exu, exu.SimulationSettings())
        
        # Get current form data (but don't apply it to any settings object)
        current_data = collectSimulationSettingsData(form)
        
        # Compare form data directly with factory defaults
        if current_data and baseline_structure:
            changes_text = compare_form_data_with_defaults(
                current_data, 
                baseline_structure, 
                "simulationSettings"
            )
        else:
            # Fallback: minimal changes text
            if not baseline_structure:
                changes_text = "# No baseline simulation settings available\n# Please check exudyn installation"
            else:
                changes_text = "# No current settings data collected from form\n# Please ensure form widgets are properly configured"
        
        # Show dialog
        dialog = ShowChangesDialog(form, changes_text, "Simulation Settings Changes")
        dialog.exec_()
        
    except Exception as e:
        import traceback
        print(f"❌ Error in show_simulation_changes: {e}")
        traceback.print_exc()
        
        # Fallback error dialog
        error_dialog = QMessageBox(form)
        error_dialog.setWindowTitle("Error")
        error_dialog.setText(f"Could not generate changes: {str(e)}\n\nSee console for details.")
        error_dialog.setIcon(QMessageBox.Warning)
        error_dialog.exec_()