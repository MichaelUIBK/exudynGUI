# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/visualizationSettings.py
#
# Description:
#     Generic visualization settings dialog that automatically discovers all
#     properties and nested objects in exudyn.SystemContainer.visualizationSettings
#     using Python introspection.
#
#     Features:
#       - Automatic discovery of all VisualizationSettings properties
#       - Hierarchical grouping of nested settings (bodies, materials, contact, etc.)
#       - Generic help text extraction using visualization-specific patterns
#       - Type-appropriate widgets (checkboxes for bools, color pickers for colors)
#       - Preserves existing values when editing
#       - Search functionality with tab navigation
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

def extractVisualizationHelp(obj, attr_name):
    """
    Extract meaningful help text for visualization settings attributes.
    Prioritizes domain-specific help over generic Python documentation.
    """
    try:
        # Method 1: Try visualization-specific pattern matching first (highest priority)
        generic_help = generateVisualizationHelp(attr_name)
        if generic_help and not generic_help.startswith("Visualization setting:"):
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
        
        # Method 3: Return the generic fallback (always returns something)
        return generic_help or f"Visualization setting: {attr_name.replace('_', ' ').title()}"
            
    except Exception as e:
        return f"Visualization setting: {attr_name.replace('_', ' ').title()}"

def generateVisualizationHelp(attr_name):
    """
    Generate meaningful help text based on exudyn visualization settings patterns.
    This provides domain-specific help for rendering and display parameters.
    """
    attr_lower = attr_name.lower()
    
    # Color settings
    if 'color' in attr_lower:
        if 'background' in attr_lower:
            return "Background color for the visualization window (RGBA values 0-1)"
        elif 'default' in attr_lower:
            return "Default color for objects when no specific color is assigned"
        elif 'ambient' in attr_lower:
            return "Ambient light color for global illumination (RGBA values 0-1)"
        elif 'base' in attr_lower:
            return "Base material color (diffuse reflection color)"
        elif 'specular' in attr_lower:
            return "Specular reflection color (highlights and shininess)"
        elif 'emission' in attr_lower:
            return "Emission color (self-illuminating objects)"
        elif 'trace' in attr_lower:
            return "Color for sensor traces and trajectories"
        return "Color setting for visualization elements (RGBA values 0-1)"
    
    # Material properties
    if any(word in attr_lower for word in ['material', 'alpha', 'shininess', 'reflectivity', 'ior']):
        if 'alpha' in attr_lower:
            return "Transparency value (0=fully transparent, 1=fully opaque)"
        elif 'shininess' in attr_lower:
            return "Material shininess factor (higher = more focused highlights)"
        elif 'reflectivity' in attr_lower:
            return "Surface reflectivity (0=no reflection, 1=mirror-like)"
        elif 'ior' in attr_lower:
            return "Index of refraction for transparent materials (1=air, 1.5=glass)"
        elif 'emission' in attr_lower:
            return "Self-illumination strength (makes objects glow)"
        return "Material property for realistic rendering"
    
    # Size and scaling settings
    if any(word in attr_lower for word in ['size', 'scaling', 'factor', 'radius', 'width', 'height']):
        if 'point' in attr_lower:
            return "Size of point markers in visualization"
        elif 'line' in attr_lower:
            return "Width of lines and edges in visualization"
        elif 'coordinate' in attr_lower:
            return "Size of coordinate system axes display"
        elif 'scene' in attr_lower:
            return "Overall scaling factor for the scene"
        elif 'window' in attr_lower:
            return "Window size in pixels [width, height]"
        elif 'light' in attr_lower:
            return "Light source size/radius for soft shadows"
        elif 'vector' in attr_lower:
            return "Scaling factor for vector displays"
        elif 'triad' in attr_lower:
            return "Size of coordinate triad displays"
        return "Size or scaling factor for visualization elements"
    
    # Display and show settings
    if any(word in attr_lower for word in ['show', 'display', 'draw', 'render']):
        if 'window' in attr_lower:
            return "Show/hide the visualization window"
        elif 'coordinate' in attr_lower:
            return "Display coordinate system axes"
        elif 'number' in attr_lower:
            return "Show object identification numbers"
        elif 'help' in attr_lower:
            return "Show help information on startup"
        elif 'computation' in attr_lower:
            return "Display computation progress and timing"
        elif 'solver' in attr_lower:
            return "Display solver status and information"
        elif 'trace' in attr_lower:
            return "Show sensor traces and trajectories"
        elif 'current' in attr_lower:
            return "Show current sensor values"
        elif 'past' in attr_lower:
            return "Show historical sensor data"
        elif 'future' in attr_lower:
            return "Show predicted future sensor values"
        return "Enable/disable display of visualization elements"
    
    # Tiling and tessellation
    if 'tiling' in attr_lower:
        if 'circle' in attr_lower:
            return "Number of segments for circular cross-sections"
        elif 'cylinder' in attr_lower:
            return "Number of segments around cylinder circumference"
        elif 'axial' in attr_lower:
            return "Number of segments along beam/cylinder axis"
        elif 'cross' in attr_lower:
            return "Tessellation detail for beam cross-sections"
        return "Tessellation detail (higher = smoother curves, more polygons)"
    
    # Ray tracing and rendering
    if any(word in attr_lower for word in ['ray', 'trace', 'reflection', 'transparency', 'thread']):
        if 'enable' in attr_lower:
            return "Enable ray tracing for realistic rendering"
        elif 'depth' in attr_lower:
            return "Maximum number of reflection/refraction bounces"
        elif 'thread' in attr_lower:
            return "Number of CPU threads for parallel ray tracing"
        elif 'tile' in attr_lower:
            return "Image tiles processed per thread (load balancing)"
        elif 'ambient' in attr_lower:
            return "Ambient lighting for ray traced scenes"
        elif 'fog' in attr_lower:
            return "Atmospheric fog effect settings"
        return "Ray tracing and advanced rendering setting"
    
    # Animation and timing
    if any(word in attr_lower for word in ['time', 'interval', 'every', 'span']):
        if 'update' in attr_lower:
            return "Update interval for graphics refresh (seconds)"
        elif 'span' in attr_lower:
            return "Time range for sensor trace display"
        elif 'every' in attr_lower:
            return "Display frequency (show every Nth data point)"
        return "Timing and animation setting"
    
    # File and export settings
    if any(word in attr_lower for word in ['export', 'save', 'file', 'image']):
        if 'png' in attr_lower:
            return "PNG image export settings"
        elif 'enhanced' in attr_lower:
            return "High-quality image export with anti-aliasing"
        elif 'text' in attr_lower:
            return "Export graphics as text/vector format"
        elif 'size' in attr_lower:
            return "Image resolution multiplier for export"
        return "File export and image saving setting"
    
    # Window and interface
    if any(word in attr_lower for word in ['window', 'mouse', 'key', 'timeout']):
        if 'always' in attr_lower:
            return "Keep window always on top of other applications"
        elif 'mouse' in attr_lower:
            return "Display mouse coordinates in window"
        elif 'ignore' in attr_lower:
            return "Ignore keyboard input in visualization window"
        elif 'maximize' in attr_lower:
            return "Start with maximized window"
        elif 'timeout' in attr_lower:
            return "Startup timeout for window initialization (milliseconds)"
        return "Window and user interface setting"
    
    # Precision and quality
    if any(word in attr_lower for word in ['precision', 'quality', 'simplified']):
        if 'renderer' in attr_lower:
            return "Numerical precision for rendering calculations"
        elif 'simplified' in attr_lower:
            return "Use simplified/faster rendering for better performance"
        return "Rendering quality and precision setting"
    
    # Default fallback with better description
    return f"Visualization setting: {attr_name.replace('_', ' ').title()}"

def discoverVisualizationSettingsStructure(SC):
    """
    Use exudyn's built-in GetDictionaryWithTypeInfo() to get complete structure with descriptions.
    """
    print(f"🚀 Starting visualization settings discovery using GetDictionaryWithTypeInfo()...")
    
    if not hasattr(SC, 'visualizationSettings'):
        print(f"❌ SC has no visualizationSettings attribute")
        return {}
    
    try:
        # Use exudyn's built-in method to get complete structure
        if hasattr(SC.visualizationSettings, 'GetDictionaryWithTypeInfo'):
            print(f"✅ Using GetDictionaryWithTypeInfo() method")
            type_info_dict = SC.visualizationSettings.GetDictionaryWithTypeInfo()
            
            # Convert the type info dictionary to our expected structure format
            structure = convert_type_info_to_structure(type_info_dict)
            
            print(f"\n🔍 DISCOVERED VISUALIZATION SETTINGS:")
            print(f"Total categories: {len(structure)}")
            total_settings = sum(count_nested_settings(info.get('nested', {})) for info in structure.values() if info.get('type') == 'object')
            print(f"Total settings: {total_settings}")
            print("Discovery complete! ✅\n")
            
            return structure
            
        else:
            print(f"⚠️ GetDictionaryWithTypeInfo() not available, falling back to introspection")
            return fallback_discovery(SC)
            
    except Exception as e:
        print(f"❌ Error using GetDictionaryWithTypeInfo(): {e}")
        return fallback_discovery(SC)

def convert_type_info_to_structure(type_info_dict, prefix="visualizationSettings"):
    """Convert exudyn's type info dictionary to our structure format."""
    structure = {}
    
    for category_key, category_info in type_info_dict.items():
        try:
            # Each category (nodes, bodies, etc.) contains settings
            if isinstance(category_info, dict):
                # Check if this is a category with nested settings
                if any(isinstance(v, dict) and 'value' in v for v in category_info.values()):
                    # This is a category with nested settings
                    nested_structure = {}
                    
                    for setting_key, setting_info in category_info.items():
                        if isinstance(setting_info, dict) and 'value' in setting_info:
                            # This is a leaf setting with type info
                            value = setting_info.get('value')
                            type_name = setting_info.get('type', type(value).__name__ if value is not None else 'unknown')
                            description = setting_info.get('description', f"Visualization setting: {setting_key.replace('_', ' ').title()}")
                            
                            nested_structure[setting_key] = {
                                'type': type_name,
                                'value': value,
                                'path': f"{prefix}.{category_key}.{setting_key}",
                                'help': description
                            }
                        else:
                            # This might be a nested object itself (like beams, kinematicTree in bodies)
                            if isinstance(setting_info, dict):
                                deeper_nested = convert_type_info_to_structure({setting_key: setting_info}, f"{prefix}.{category_key}")
                                nested_structure[setting_key] = deeper_nested.get(setting_key, {})
                    
                    structure[category_key] = {
                        'type': 'object',
                        'nested': nested_structure,
                        'value_type': 'VisualizationSettingsCategory',
                        'help': f"Visualization settings for {category_key.replace('_', ' ').title()}"
                    }
                else:
                    # This is a simple setting
                    value = category_info.get('value')
                    type_name = category_info.get('type', type(value).__name__ if value is not None else 'unknown')
                    description = category_info.get('description', f"Visualization setting: {category_key.replace('_', ' ').title()}")
                    
                    structure[category_key] = {
                        'type': type_name,
                        'value': value,
                        'path': f"{prefix}.{category_key}",
                        'help': description
                    }
            else:
                # Fallback for non-dict entries
                structure[category_key] = {
                    'type': type(category_info).__name__,
                    'value': category_info,
                    'path': f"{prefix}.{category_key}",
                    'help': f"Visualization setting: {category_key.replace('_', ' ').title()}"
                }
                
        except Exception as e:
            # Fallback for problematic entries
            structure[category_key] = {
                'type': 'unknown',
                'value': category_info,
                'path': f"{prefix}.{category_key}",
                'help': f"Error processing {category_key}: {e}"
            }
    
    return structure

def count_nested_settings(structure):
    """Count total number of leaf settings in a nested structure."""
    count = 0
    for info in structure.values():
        if info.get('type') == 'object':
            count += count_nested_settings(info.get('nested', {}))
        else:
            count += 1
    return count

def fallback_discovery(SC):
    """Fallback discovery method using introspection."""
    print(f"🔄 Using fallback introspection method...")
    
    visualizationSettings = SC.visualizationSettings
    
    # Get the main categories from the directory listing
    main_categories = [attr for attr in dir(visualizationSettings) 
                      if not attr.startswith('_') and not callable(getattr(visualizationSettings, attr, None))]
    
    structure = {}
    
    for category in main_categories:
        try:
            category_obj = getattr(visualizationSettings, category)
            
            # Check if this is a nested object
            if hasattr(category_obj, '__dict__') or (hasattr(category_obj, '__dir__') and 
                len([attr for attr in dir(category_obj) if not attr.startswith('_')]) > 5):
                
                # Get nested settings
                nested_settings = {}
                for attr in dir(category_obj):
                    if not attr.startswith('_') and not callable(getattr(category_obj, attr, None)):
                        try:
                            value = getattr(category_obj, attr)
                            help_text = extractVisualizationHelp(category_obj, attr)
                            nested_settings[attr] = {
                                'type': type(value).__name__,
                                'value': value,
                                'path': f"visualizationSettings.{category}.{attr}",
                                'help': help_text
                            }
                        except:
                            pass
                
                structure[category] = {
                    'type': 'object',
                    'nested': nested_settings,
                    'value_type': type(category_obj).__name__,
                    'help': f"Settings group: {category.replace('_', ' ').title()}"
                }
            else:
                # Simple value
                help_text = extractVisualizationHelp(visualizationSettings, category)
                structure[category] = {
                    'type': type(category_obj).__name__,
                    'value': category_obj,
                    'path': f"visualizationSettings.{category}",
                    'help': help_text
                }
                
        except Exception as e:
            structure[category] = {
                'type': 'error',
                'error': str(e),
                'path': f"visualizationSettings.{category}",
                'help': f"Error accessing {category}: {e}"
            }
    
    return structure

def createVisualizationSettingsForm(parent, existing_SC=None):
    """
    Create a comprehensive visualization settings form with search functionality.
    """
    # Import additional widgets needed for better UI
    from PyQt5.QtWidgets import QTabWidget, QFrame, QScrollArea
    
    # Create or use existing SystemContainer
    if existing_SC is None:
        SC = exu.SystemContainer()
    else:
        SC = existing_SC
    
    structure = discoverVisualizationSettingsStructure(SC)
    
    # Create main dialog
    form = QDialog(parent)
    form.setWindowTitle("Visualization Settings")
    form.setMinimumSize(900, 700)
    form.resize(1000, 800)
    
    # Main layout
    main_layout = QVBoxLayout(form)
    
    # Add search functionality (reuse from simulationSettings)
    from . import simulationSettings as ss
    search_frame = ss.create_search_frame(form)
    main_layout.addWidget(search_frame)
    
    # Create tab widget for major categories
    tab_widget = QTabWidget()
    
    # Organize settings into logical tabs based on exudyn's hierarchical structure
    tab_structure = {
        "Objects": ["nodes", "bodies", "connectors", "markers", "loads"],
        "Display": ["sensors", "contour", "interactive", "dialogs"], 
        "Graphics": ["window", "openGL", "raytracer"],
        "Export": ["exportimages"],
        "General": ["general", "contact"],
        "Advanced": []  # Everything else not explicitly categorized
    }
    
    # Create tabs
    for tab_name, field_list in tab_structure.items():
        tab_widget.addTab(create_visualization_tab(structure, field_list, tab_name), tab_name)
    
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
    show_changes_btn.clicked.connect(lambda: show_visualization_changes(form, existing_SC))
    
    # Standard buttons
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(form.accept)
    buttons.rejected.connect(form.reject)
    
    button_layout.addWidget(show_changes_btn)
    button_layout.addStretch()
    button_layout.addWidget(buttons)
    
    main_layout.addLayout(button_layout)
    
    # Add keyboard shortcuts for search
    ss.setup_keyboard_shortcuts(form, search_frame)
    
    # Store original tab names for proper cleanup
    form._original_tab_names = {
        0: "Objects", 1: "Display", 2: "Graphics", 
        3: "Export", 4: "General", 5: "Advanced"
    }
    
    return form

def create_visualization_tab(structure, field_list, tab_name):
    """Create a single tab with organized visualization settings."""
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
                # Create collapsible group for nested objects (reuse from simulationSettings)
                from . import simulationSettings as ss
                group_widget = ss.create_collapsible_group(field_name, info, processed_fields)
                content_layout.addWidget(group_widget)
            else:
                # Create simple field
                field_widget = create_visualization_field_widget(field_name, info)
                content_layout.addWidget(field_widget)
            processed_fields.add(field_name)
    
    # For "Advanced" tab, add remaining unprocessed fields
    if tab_name == "Advanced":
        remaining_fields = [k for k in structure.keys() if k not in processed_fields]
        if remaining_fields:
            for field_name in remaining_fields:
                info = structure[field_name]
                if info['type'] == 'object':
                    from . import simulationSettings as ss
                    group_widget = ss.create_collapsible_group(field_name, info, processed_fields)
                    content_layout.addWidget(group_widget)
                else:
                    field_widget = create_visualization_field_widget(field_name, info)
                    content_layout.addWidget(field_widget)
    
    # Add stretch to push everything to top
    content_layout.addStretch()
    
    # Set up scroll area
    scroll.setWidget(content_widget)
    
    # Tab layout
    tab_layout = QVBoxLayout(tab_widget)
    tab_layout.addWidget(scroll)
    
    return tab_widget

def create_visualization_field_widget(field_name, info):
    """Create a field widget specifically for visualization settings."""
    frame = QFrame()
    frame.setMaximumHeight(60)
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(10, 5, 10, 5)
    
    # Label
    label = QLabel(field_name.replace('_', ' ').title())
    label.setMinimumWidth(200)
    label.setStyleSheet("font-weight: bold;")
    
    # Widget - use visualization-specific widget creation
    widget = create_visualization_widget_for_type(info['type'], info.get('value'))
    widget.setMinimumWidth(200)
    
    # Enhanced tooltip
    help_text = info.get('help', f"Visualization setting: {field_name}")
    tooltip_text = f"<b>{field_name}</b><br/>{help_text}"
    widget.setToolTip(tooltip_text)
    label.setToolTip(tooltip_text)
    
    # Store path
    widget.setProperty('settings_path', info['path'])
    
    layout.addWidget(label)
    layout.addWidget(widget)
    layout.addStretch()
    
    return frame

def create_visualization_widget_for_type(type_name, default_value):
    """Create specialized widgets for visualization settings types."""
    
    # Color picker for VectorFloat with 4 values (RGBA colors)
    if type_name == 'VectorFloat' and isinstance(default_value, list) and len(default_value) == 4:
        return create_color_picker_widget(default_value)
    
    # Vector input for VectorFloat with other sizes
    elif type_name == 'VectorFloat' and isinstance(default_value, list):
        return create_vector_input_widget(default_value)
    
    # Unsigned integer types
    elif type_name in ['UInt', 'PInt']:
        widget = QSpinBox()
        widget.setRange(0, 999999999)
        if default_value is not None:
            widget.setValue(int(default_value))
        widget.setStyleSheet("QSpinBox { padding: 3px; }")
        return widget
    
    # Boolean type
    elif type_name == 'bool':
        widget = QCheckBox()
        if default_value is not None:
            widget.setChecked(default_value)
        widget.setStyleSheet("QCheckBox { font-size: 11px; }")
        return widget
    
    # Float type
    elif type_name == 'float':
        widget = QDoubleSpinBox()
        widget.setRange(-999999999.0, 999999999.0)
        widget.setDecimals(6)
        if default_value is not None:
            widget.setValue(float(default_value))
        widget.setStyleSheet("QDoubleSpinBox { padding: 3px; }")
        return widget
    
    # Fallback to simulation settings widget creation
    else:
        from . import simulationSettings as ss
        return ss.create_enhanced_widget_for_type(type_name, default_value)

def create_color_picker_widget(rgba_values):
    """Create a color picker widget for RGBA values."""
    frame = QFrame()
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 0)
    
    # Color display button
    color_button = QPushButton()
    color_button.setFixedSize(50, 25)
    
    # Convert RGBA to QColor
    if rgba_values and len(rgba_values) >= 3:
        r = int(rgba_values[0] * 255)
        g = int(rgba_values[1] * 255)
        b = int(rgba_values[2] * 255)
        a = int(rgba_values[3] * 255) if len(rgba_values) > 3 else 255
        
        color = QColor(r, g, b, a)
        color_button.setStyleSheet(f"QPushButton {{ background-color: rgba({r}, {g}, {b}, {a}); border: 1px solid #000; }}")
    
    # RGBA value display
    rgba_label = QLineEdit()
    rgba_label.setReadOnly(True)
    if rgba_values:
        rgba_text = f"[{rgba_values[0]:.3f}, {rgba_values[1]:.3f}, {rgba_values[2]:.3f}, {rgba_values[3]:.3f}]"
        rgba_label.setText(rgba_text)
    
    # Color picker functionality
    def pick_color():
        if rgba_values and len(rgba_values) >= 3:
            r = int(rgba_values[0] * 255)
            g = int(rgba_values[1] * 255)
            b = int(rgba_values[2] * 255)
            a = int(rgba_values[3] * 255) if len(rgba_values) > 3 else 255
            initial_color = QColor(r, g, b, a)
        else:
            initial_color = QColor(255, 255, 255, 255)
        
        color = QColorDialog.getColor(initial_color, None, "Choose Color", QColorDialog.ShowAlphaChannel)
        if color.isValid():
            # Update the values
            rgba_values[0] = color.red() / 255.0
            rgba_values[1] = color.green() / 255.0
            rgba_values[2] = color.blue() / 255.0
            rgba_values[3] = color.alpha() / 255.0
            
            # Update display
            r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
            color_button.setStyleSheet(f"QPushButton {{ background-color: rgba({r}, {g}, {b}, {a}); border: 1px solid #000; }}")
            rgba_text = f"[{rgba_values[0]:.3f}, {rgba_values[1]:.3f}, {rgba_values[2]:.3f}, {rgba_values[3]:.3f}]"
            rgba_label.setText(rgba_text)
    
    color_button.clicked.connect(pick_color)
    color_button.setToolTip("Click to choose color")
    
    layout.addWidget(color_button)
    layout.addWidget(rgba_label)
    
    # Store the RGBA values for data collection
    frame.setProperty('rgba_values', rgba_values)
    
    return frame

def create_vector_input_widget(vector_values):
    """Create a vector input widget for VectorFloat values."""
    frame = QFrame()
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 0)
    
    # Create input fields for each component
    inputs = []
    for i, value in enumerate(vector_values):
        input_field = QDoubleSpinBox()
        input_field.setRange(-999999999.0, 999999999.0)
        input_field.setDecimals(6)
        input_field.setValue(float(value))
        input_field.setMinimumWidth(80)
        input_field.setStyleSheet("QDoubleSpinBox { padding: 2px; }")
        inputs.append(input_field)
        layout.addWidget(input_field)
    
    # Store the inputs for data collection
    frame.setProperty('vector_inputs', inputs)
    frame.setProperty('vector_values', vector_values)
    
    return frame

def visualizationSettingsToDict(visualizationSettings):
    """Convert visualization settings to a dictionary for saving."""
    if visualizationSettings is None:
        return {}
    
    # Method 1: Try to use GetDictionary() method if available
    try:
        if hasattr(visualizationSettings, 'GetDictionary'):
            print("📊 Using GetDictionary() method for visualization settings")
            return visualizationSettings.GetDictionary()
    except Exception as e:
        print(f"⚠️  GetDictionary() failed: {e}")
    
    # Method 2: Fallback to discovery mechanism 
    SC = exu.SystemContainer()
    SC.visualizationSettings = visualizationSettings
    structure = discoverVisualizationSettingsStructure(SC)
    
    def extract_values_from_structure(structure, prefix=""):
        """Extract all values from the discovered structure."""
        result = {}
        for key, info in structure.items():
            if info['type'] == 'object':
                result[key] = extract_values_from_structure(info['nested'], f"{prefix}.{key}")
            else:
                result[key] = info.get('value')
        return result
    
    return extract_values_from_structure(structure)

def visualizationSettingsFromDict(settings_dict, existing_SC=None):
    """Create or update visualization settings from a dictionary."""
    import exudyn as exu
    
    if not settings_dict:
        return exu.SystemContainer()  # Return default if empty
    
    # Use existing SystemContainer if provided, otherwise create new
    if existing_SC is None:
        SC = exu.SystemContainer()
    else:
        SC = existing_SC
    
    # Apply the settings
    applyVisualizationSettings(SC, settings_dict)
    
    return SC

def collectVisualizationSettingsData(form):
    """
    Collect data from the visualization form and return a structured dictionary.
    """
    data = {}
    
    # Find all widgets with settings_path property
    for widget in form.findChildren(QWidget):
        path = widget.property('settings_path')
        if path:
            # Extract value based on widget type
            value = None
            
            # Handle color picker widgets
            if widget.property('rgba_values'):
                value = widget.property('rgba_values')
            
            # Handle vector input widgets
            elif widget.property('vector_inputs'):
                inputs = widget.property('vector_inputs')
                value = [input_field.value() for input_field in inputs]
            
            # Handle standard widget types
            elif isinstance(widget, QCheckBox):
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
                        value = getattr(enum_class, text)
                    except:
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
            
            # Store in nested dictionary structure if we got a value
            if value is not None:
                set_nested_value(data, path, value)
    
    return data

def set_nested_value(dictionary, path, value):
    """Set a value in a nested dictionary using dot notation path"""
    keys = path.split('.')[1:]  # Skip 'visualizationSettings' prefix
    current = dictionary
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value

def applyVisualizationSettings(SC, settings_data):
    """
    Apply the collected settings data to the actual VisualizationSettings object.
    """
    if not hasattr(SC, 'visualizationSettings'):
        print("❌ No visualizationSettings found in SystemContainer")
        return
    
    print(f"🔧 Applying visualization settings...")
    print(f"Settings data keys: {list(settings_data.keys())}")
    
    # Method 1: Try to use SetDictionary() method if available
    try:
        if hasattr(SC.visualizationSettings, 'SetDictionary'):
            print("📊 Using SetDictionary() method for visualization settings")
            # Convert data to proper format for exudyn
            converted_data = convert_settings_data_for_exudyn(settings_data)
            SC.visualizationSettings.SetDictionary(converted_data)
            print("✅ Visualization settings applied via SetDictionary()")
            return
    except Exception as e:
        print(f"⚠️  SetDictionary() failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Method 2: Fallback to manual attribute setting with proper conversion
    def apply_nested_settings(obj, data, path=""):
        for key, value in data.items():
            if isinstance(value, dict):
                # Nested object - recurse
                nested_obj = getattr(obj, key, None)
                if nested_obj is not None:
                    apply_nested_settings(nested_obj, value, f"{path}.{key}")
                else:
                    print(f"⚠️ Nested object {path}.{key} not found")
            else:
                # Direct value - apply if attribute exists
                if hasattr(obj, key):
                    try:
                        setattr(obj, key, value)
                        print(f"✅ Set {path}.{key} = {value}")
                    except Exception as e:
                        print(f"❌ Failed to set {path}.{key}: {e}")
                else:
                    print(f"⚠️ Attribute {path}.{key} not found")
    
    # Convert data for manual setting
    converted_data = convert_settings_data_for_exudyn(settings_data)
    apply_nested_settings(SC.visualizationSettings, converted_data, "visualizationSettings")

def convert_settings_data_for_exudyn(settings_data):
    """
    Convert collected settings data to proper format for exudyn.
    Ensures that vector/color values are in the correct type for exudyn C++ interface.
    """
    import numpy as np
    
    def convert_value(value):
        """Convert a single value to exudyn-compatible format."""
        if isinstance(value, list) and len(value) in [3, 4]:
            # Convert to numpy array for proper typing
            return np.array(value, dtype=np.float32)
        elif isinstance(value, dict):
            # Recursively convert nested dictionaries
            return {k: convert_value(v) for k, v in value.items()}
        else:
            # Return other values unchanged
            return value
    
    return {k: convert_value(v) for k, v in settings_data.items()}

def getVisualizationSettingsWithHelp(SC):
    """
    Get the complete visualization settings dictionary with comprehensive help text.
    
    Returns:
        dict: Complete structure with current values and help text for each setting
    """
    if not hasattr(SC, 'visualizationSettings'):
        return {}
    
    # Discover the complete structure with help text
    structure = discoverVisualizationSettingsStructure(SC)
    
    # Get current values using GetDictionary if available
    current_values = {}
    try:
        if hasattr(SC.visualizationSettings, 'GetDictionary'):
            current_values = SC.visualizationSettings.GetDictionary()
            print("📊 Current values obtained via GetDictionary()")
    except Exception as e:
        print(f"⚠️  GetDictionary() failed: {e}")
    
    def merge_structure_with_values(structure, values_dict, prefix=""):
        """Merge discovered structure with current values."""
        result = {}
        for key, info in structure.items():
            if info['type'] == 'object':
                # Nested object - recurse
                nested_values = values_dict.get(key, {}) if isinstance(values_dict.get(key), dict) else {}
                result[key] = {
                    'type': 'object',
                    'help': f"Settings group: {key.replace('_', ' ').title()}",
                    'nested': merge_structure_with_values(info['nested'], nested_values, f"{prefix}.{key}")
                }
            else:
                # Leaf value - combine structure info with current value
                current_value = values_dict.get(key, info.get('value'))
                result[key] = {
                    'type': info['type'],
                    'value': current_value,
                    'default': info.get('value'),
                    'path': info['path'],
                    'help': info['help']
                }
        return result
    
    return merge_structure_with_values(structure, current_values)

def getVisualizationSettingsSummary(SC):
    """
    Get a summary of visualization settings with key statistics.
    
    Returns:
        dict: Summary information about the visualization settings
    """
    if not hasattr(SC, 'visualizationSettings'):
        return {'error': 'No visualization settings found'}
    
    # Get complete structure with help
    settings_with_help = getVisualizationSettingsWithHelp(SC)
    
    def count_settings(structure):
        """Count total settings and categories."""
        total_settings = 0
        categories = 0
        
        for key, info in structure.items():
            if info['type'] == 'object':
                categories += 1
                nested_count, _ = count_settings(info.get('nested', {}))
                total_settings += nested_count
            else:
                total_settings += 1
        
        return total_settings, categories
    
    total_settings, categories = count_settings(settings_with_help)
    
    # Get current values dictionary
    current_dict = {}
    try:
        if hasattr(SC.visualizationSettings, 'GetDictionary'):
            current_dict = SC.visualizationSettings.GetDictionary()
    except:
        pass
    
    return {
        'total_settings': total_settings,
        'categories': categories,
        'has_get_dictionary': hasattr(SC.visualizationSettings, 'GetDictionary'),
        'has_set_dictionary': hasattr(SC.visualizationSettings, 'SetDictionary'),
        'current_values_count': len(str(current_dict)),
        'structure_available': len(settings_with_help) > 0
    }


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


def show_visualization_changes(form, original_SC):
    """Show the changes made to visualization settings."""
    try:
        from exudynGUI.core.settingsComparison import compare_form_data_with_defaults
        
        # Get baseline settings structure from the ORIGINAL SC passed to the dialog
        # This ensures we compare against the actual starting values, not factory defaults
        if original_SC is not None:
            baseline_structure = discoverVisualizationSettingsStructure(original_SC)
        else:
            # Fallback to factory defaults if no original SC provided
            import exudyn as exu
            fallback_SC = exu.SystemContainer()
            baseline_structure = discoverVisualizationSettingsStructure(fallback_SC)
        
        # Get current form data (but don't apply it to any SC)
        current_data = collectVisualizationSettingsData(form)
        
        # Compare form data directly with baseline (safer approach)
        if current_data and baseline_structure:
            changes_text = compare_form_data_with_defaults(
                current_data, 
                baseline_structure, 
                "visualizationSettings"
            )
        else:
            # Fallback: minimal changes text
            if not baseline_structure:
                changes_text = "# No baseline visualization settings available\n# Please check exudyn installation"
            else:
                changes_text = "# No current settings data collected from form\n# Please ensure form widgets are properly configured"
        
        # Show dialog
        dialog = ShowChangesDialog(form, changes_text, "Visualization Settings Changes")
        dialog.exec_()
        
    except Exception as e:
        import traceback
        print(f"❌ Error in show_visualization_changes: {e}")
        traceback.print_exc()
        
        # Fallback error dialog
        error_dialog = QMessageBox(form)
        error_dialog.setWindowTitle("Error")
        error_dialog.setText(f"Could not generate changes: {str(e)}\n\nSee console for details.")
        error_dialog.setIcon(QMessageBox.Warning)
        error_dialog.exec_()

