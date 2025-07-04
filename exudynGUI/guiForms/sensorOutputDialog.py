# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/sensorOutputDialog.py
#
# Description:
#     Enhanced sensor creation dialog with intelligent output type selection
#     and real-time preview capabilities.
#
#     Features:
#       - Output type discovery based on referenced entity
#       - Smart default selection and configuration handling
#       - Recommendation display with use-case guidance
#       - Live preview of output values (if system available)
#       - Code generation for sensor creation
#
# Authors:  Michael Pieber
# Date:     2025-07-03
#
# License:  BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from exudynGUI.core.qtImports import *

try:
    from exudynGUI.core.outputDiscovery import (
        discover_supported_outputs,
        enhance_sensor_form_with_outputs,
        generate_sensor_creation_code,
        get_entity_output_safely,
        get_all_configuration_types
    )
except ImportError:
    # Fallback functions if outputDiscovery not available
    def discover_supported_outputs(mbs, entity_type, entity_index):
        return ['Position', 'Velocity', 'Displacement']
    
    def enhance_sensor_form_with_outputs(mbs, sensor_type, entity):
        return {
            'supported_outputs': ['Position', 'Velocity'],
            'recommendations': [],
            'default_output': 'Position',
            'default_config': 'Current'
        }
    
    def generate_sensor_creation_code(sensor_type, sensor_name, entity_ref, output_type, config_type='Current', params=None):
        return f"# {sensor_type} creation code"
    
    def get_entity_output_safely(mbs, entity_type, entity_index, output_type, config_type='Current'):
        return False, None, "Output discovery not available"
    
    def get_all_configuration_types():
        return ['Current', 'Initial', 'Reference']


class SensorOutputDialog(QDialog):
    """Enhanced sensor creation dialog with intelligent output type selection"""
    
    def __init__(self, parent=None, mbs=None, sensor_type='SensorObject', referenced_entity=None):
        super().__init__(parent)
        self.mbs = mbs
        self.sensor_type = sensor_type
        self.referenced_entity = referenced_entity or {'type': 'object', 'index': 0}
        
        self.setWindowTitle(f"Create {sensor_type} with Output Selection")
        self.setModal(True)
        self.resize(500, 400)
        
        self.init_ui()
        self.update_output_options()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel(f"<h3>Create {self.sensor_type}</h3>")
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Entity info
        entity_info = QLabel(f"Monitoring: {self.referenced_entity['type']}[{self.referenced_entity['index']}]")
        entity_info.setStyleSheet("font-weight: bold; color: #666;")
        layout.addWidget(entity_info)
        
        layout.addWidget(QLabel())  # Spacer
        
        # Form layout
        form_layout = QFormLayout()
        
        # Sensor name
        self.name_edit = QLineEdit(f"{self.sensor_type.lower()}_{self.referenced_entity['index']}")
        form_layout.addRow("Sensor Name:", self.name_edit)
        
        # Output type selection
        self.output_combo = QComboBox()
        self.output_combo.currentTextChanged.connect(self.on_output_changed)
        form_layout.addRow("Output Type:", self.output_combo)
        
        # Configuration type selection
        self.config_combo = QComboBox()
        self.config_combo.currentTextChanged.connect(self.on_config_changed)
        form_layout.addRow("Configuration:", self.config_combo)
        
        layout.addLayout(form_layout)
        
        # Recommendations section
        self.recommendations_group = QGroupBox("Recommendations")
        self.recommendations_layout = QVBoxLayout(self.recommendations_group)
        layout.addWidget(self.recommendations_group)
        
        # Preview section
        self.preview_group = QGroupBox("Live Preview")
        self.preview_layout = QVBoxLayout(self.preview_group)
        
        self.preview_label = QLabel("Select an output type to preview values")
        self.preview_label.setWordWrap(True)
        self.preview_layout.addWidget(self.preview_label)
        
        self.refresh_button = QPushButton("Refresh Preview")
        self.refresh_button.clicked.connect(self.refresh_preview)
        self.preview_layout.addWidget(self.refresh_button)
        
        layout.addWidget(self.preview_group)
        
        # Generated code preview
        self.code_group = QGroupBox("Generated Code")
        self.code_text = QTextEdit()
        self.code_text.setMaximumHeight(100)
        self.code_text.setFont(QFont("Consolas", 9))
        
        code_layout = QVBoxLayout(self.code_group)
        code_layout.addWidget(self.code_text)
        
        layout.addWidget(self.code_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("Create Sensor")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
    def update_output_options(self):
        """Update available output options based on the referenced entity"""
        try:
            if not self.mbs:
                # No system available - use fallback options
                self.populate_fallback_options()
                return
                
            # Get enhanced sensor form data
            enhancement_data = enhance_sensor_form_with_outputs(
                self.mbs, 
                self.sensor_type, 
                self.referenced_entity
            )
            
            # Populate output types
            self.output_combo.clear()
            supported_outputs = enhancement_data.get('supported_outputs', [])
            
            if not supported_outputs:
                supported_outputs = ['Position', 'Velocity']  # Fallback
                
            for output_type in supported_outputs:
                self.output_combo.addItem(output_type)
            
            # Set default output
            default_output = enhancement_data.get('default_output', 'Position')
            index = self.output_combo.findText(default_output)
            if index >= 0:
                self.output_combo.setCurrentIndex(index)
            
            # Populate configuration types
            self.config_combo.clear()
            config_types = enhancement_data.get('configuration_types', ['Current'])
            
            for config_type in config_types:
                self.config_combo.addItem(config_type)
            
            # Set default configuration
            default_config = enhancement_data.get('default_config', 'Current')
            index = self.config_combo.findText(default_config)
            if index >= 0:
                self.config_combo.setCurrentIndex(index)
            
            # Update recommendations
            self.update_recommendations(enhancement_data.get('recommendations', []))
            
        except Exception as e:
            self.populate_fallback_options()
        
        # Update code preview and live preview
        self.update_code_preview()
        self.refresh_preview()
    
    def populate_fallback_options(self):
        """Populate with fallback options when system is not available"""
        # Output types
        self.output_combo.clear()
        fallback_outputs = ['Position', 'Velocity', 'Displacement', 'Force']
        for output in fallback_outputs:
            self.output_combo.addItem(output)
        
        # Configuration types
        self.config_combo.clear()
        fallback_configs = ['Current', 'Initial', 'Reference']
        for config in fallback_configs:
            self.config_combo.addItem(config)
        
        # No specific recommendations
        self.update_recommendations([])
    
    def update_recommendations(self, recommendations):
        """Update the recommendations display"""
        # Clear existing recommendations
        for i in reversed(range(self.recommendations_layout.count())):
            child = self.recommendations_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        if not recommendations:
            label = QLabel("No specific recommendations available")
            label.setStyleSheet("color: #666; font-style: italic;")
            self.recommendations_layout.addWidget(label)
            return
        
        for rec in recommendations:
            output_type = rec.get('output_type', '')
            description = rec.get('description', '')
            typical_use = rec.get('typical_use', '')
            
            # Create recommendation widget
            rec_widget = QWidget()
            rec_layout = QVBoxLayout(rec_widget)
            rec_layout.setContentsMargins(10, 5, 10, 5)
            
            # Title
            title_label = QLabel(f"<b>{output_type}</b>")
            rec_layout.addWidget(title_label)
            
            # Description
            if description:
                desc_label = QLabel(description)
                desc_label.setWordWrap(True)
                rec_layout.addWidget(desc_label)
            
            # Typical use
            if typical_use:
                use_label = QLabel(f"<i>Typical use: {typical_use}</i>")
                use_label.setStyleSheet("color: #666;")
                use_label.setWordWrap(True)
                rec_layout.addWidget(use_label)
            
            # Add selection button
            select_button = QPushButton(f"Use {output_type}")
            select_button.clicked.connect(lambda checked, ot=output_type: self.select_output_type(ot))
            rec_layout.addWidget(select_button)
            
            # Style the widget
            rec_widget.setStyleSheet("""
                QWidget {
                    background-color: #f0f0f0;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    margin: 2px;
                }
            """)
            
            self.recommendations_layout.addWidget(rec_widget)
    
    def select_output_type(self, output_type):
        """Select a specific output type"""
        index = self.output_combo.findText(output_type)
        if index >= 0:
            self.output_combo.setCurrentIndex(index)
    
    def on_output_changed(self):
        """Handle output type change"""
        self.update_code_preview()
        self.refresh_preview()
    
    def on_config_changed(self):
        """Handle configuration type change"""
        self.update_code_preview()
        self.refresh_preview()
    
    def update_code_preview(self):
        """Update the generated code preview"""
        try:
            sensor_name = self.name_edit.text() or "sensor"
            output_type = self.output_combo.currentText()
            config_type = self.config_combo.currentText()
            entity_ref = f"{self.referenced_entity['index']}"
            
            code = generate_sensor_creation_code(
                self.sensor_type,
                sensor_name,
                entity_ref,
                output_type,
                config_type
            )
            
            self.code_text.setPlainText(code)
            
        except Exception as e:
            self.code_text.setPlainText(f"# Error generating code: {e}")
    
    def refresh_preview(self):
        """Refresh the live preview of output values"""
        if not self.mbs:
            self.preview_label.setText("No system available for preview")
            return
            
        try:
            entity_type = self.referenced_entity['type']
            entity_index = self.referenced_entity['index']
            output_type = self.output_combo.currentText()
            config_type = self.config_combo.currentText()
            
            if not output_type:
                self.preview_label.setText("Select an output type to preview values")
                return
            
            success, value, error = get_entity_output_safely(
                self.mbs, entity_type, entity_index, output_type, config_type
            )
            
            if success:
                # Format the value nicely
                if isinstance(value, (list, tuple)):
                    if len(value) <= 6:  # Show individual components for small vectors
                        value_str = f"[{', '.join(f'{v:.4f}' if isinstance(v, float) else str(v) for v in value)}]"
                    else:
                        value_str = f"Array with {len(value)} elements: [{value[0]:.4f}, ..., {value[-1]:.4f}]"
                elif isinstance(value, float):
                    value_str = f"{value:.6f}"
                else:
                    value_str = str(value)
                
                self.preview_label.setText(f"<b>Current Value:</b><br>{value_str}")
                self.preview_label.setStyleSheet("color: #008000;")  # Green for success
            else:
                self.preview_label.setText(f"<b>Error:</b><br>{error}")
                self.preview_label.setStyleSheet("color: #800000;")  # Red for error
                
        except Exception as e:
            self.preview_label.setText(f"<b>Preview Error:</b><br>{str(e)}")
            self.preview_label.setStyleSheet("color: #800000;")
    
    def get_sensor_data(self):
        """Get the sensor configuration data"""
        return {
            'sensor_type': self.sensor_type,
            'sensor_name': self.name_edit.text(),
            'output_type': self.output_combo.currentText(),
            'configuration_type': self.config_combo.currentText(),
            'referenced_entity': self.referenced_entity,
            'generated_code': self.code_text.toPlainText()
        }


def create_sensor_with_output_dialog(parent=None, mbs=None, sensor_type='SensorObject', referenced_entity=None):
    """
    Convenience function to create and show the sensor output dialog
    
    Returns:
        tuple: (accepted, sensor_data) where accepted is bool and sensor_data is dict
    """
    dialog = SensorOutputDialog(parent, mbs, sensor_type, referenced_entity)
    accepted = dialog.exec_() == QDialog.Accepted
    
    if accepted:
        return True, dialog.get_sensor_data()
    else:
        return False, None


# Test function for standalone testing
def test_sensor_output_dialog():
    """Test the sensor output dialog"""
    import sys
    
    app = QApplication(sys.argv if hasattr(sys, 'argv') else [])
    
    # Mock entity
    entity = {'type': 'object', 'index': 0}
    
    dialog = SensorOutputDialog(sensor_type='SensorObject', referenced_entity=entity)
    dialog.show()
    
    app.exec_()


if __name__ == '__main__':
    test_sensor_output_dialog()
