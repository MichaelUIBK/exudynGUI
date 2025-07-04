# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/exudynRenderer.py
#
# Description:
#     Exudyn OpenGL renderer widget for integration into the PyQt interface.
#
#     Provides:
#       - Start/stop/refresh controls for the external Exudyn visualization window
#       - Embedded status reporting and user feedback
#       - Thread-safe renderer launch without blocking the main GUI
#
# Authors:  Michael Pieber
# Date:     2025-06-18
#
# License:  BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import sys
import os
import subprocess
import time
import threading
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget, 
                             QMessageBox)
from PyQt5.QtGui import QPixmap
from exudynGUI.core.debug import debugLog

try:
    import exudyn as exu
    EXUDYN_AVAILABLE = True
except ImportError:
    EXUDYN_AVAILABLE = False
    debugLog("Warning: Exudyn not available - renderer widget will show placeholder")

class ExudynRendererWidget(QWidget):
    """
    Widget that integrates Exudyn's OpenGL renderer into the PyQt GUI.
    
    This widget provides several approaches to display Exudyn visualizations:
    1. External window coordination (default)
    2. Screenshot capture and display 
    3. Future: Direct OpenGL integration
    """
    
    rendererStarted = pyqtSignal()
    rendererStopped = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.SC = None  # SystemContainer
        self.mbs = None  # MainSystem
        self.renderer_active = False
        self.external_window_started = False
        
        self.setupUI()
        
    def setupUI(self):
        """Setup the renderer widget UI."""
        layout = QVBoxLayout(self)
        
        # Header with controls
        header_layout = QHBoxLayout()
        
        self.status_label = QLabel("Renderer: Not Started")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-weight: bold;
                padding: 5px;
            }
        """)
        header_layout.addWidget(self.status_label)
        
        header_layout.addStretch()
        
        # Control buttons
        self.start_button = QPushButton("Start Renderer")
        self.start_button.clicked.connect(self.startRenderer)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        header_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Renderer")
        self.stop_button.clicked.connect(self.stopRenderer)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        header_layout.addWidget(self.stop_button)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refreshRenderer)
        self.refresh_button.setEnabled(False)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        header_layout.addWidget(self.refresh_button)
        
        layout.addLayout(header_layout)
        
        # Main renderer area
        self.renderer_area = QWidget()
        self.renderer_area.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 2px solid #ced4da;
                border-radius: 4px;
            }
        """)
        self.renderer_area.setMinimumHeight(400)
        
        # Placeholder content
        renderer_layout = QVBoxLayout(self.renderer_area)
        
        self.placeholder_label = QLabel()
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.updatePlaceholder()
        renderer_layout.addWidget(self.placeholder_label)
        
        layout.addWidget(self.renderer_area)
        
        # Status and instructions
        self.instructions_label = QLabel()
        self.updateInstructions()
        self.instructions_label.setStyleSheet("""
            QLabel {
                color: #495057;
                font-size: 12px;
                padding: 10px;
                background-color: #e9ecef;
                border-radius: 4px;
                margin-top: 5px;
            }
        """)
        layout.addWidget(self.instructions_label)
        
    def updatePlaceholder(self):
        """Update the placeholder content based on current state."""
        if not EXUDYN_AVAILABLE:
            text = "⚠️ Exudyn Not Available\n\nExudyn library is not installed or accessible.\nPlease install Exudyn to use the renderer."
            self.placeholder_label.setStyleSheet("color: #dc3545; font-size: 14px; font-weight: bold;")
        elif not self.renderer_active:
            text = "🎬 Exudyn OpenGL Renderer\n\nClick 'Start Renderer' to begin visualization.\nRenderer will open in a separate window."
            self.placeholder_label.setStyleSheet("color: #6c757d; font-size: 14px;")
        else:
            text = "✅ Renderer Active\n\nExudyn renderer is running in external window.\nUse the controls above to manage the renderer."
            self.placeholder_label.setStyleSheet("color: #28a745; font-size: 14px; font-weight: bold;")
            
        self.placeholder_label.setText(text)
        
    def updateInstructions(self):
        """Update the instructions text."""
        if not EXUDYN_AVAILABLE:
            text = "To use the Exudyn renderer, please install the Exudyn library."
        elif not self.renderer_active:
            text = "Ready to start Exudyn renderer. Make sure your model is assembled before starting the renderer."
        else:
            text = "Renderer is active. The visualization window should be visible. Use renderer controls or close the window to stop."
            
        self.instructions_label.setText(text)
        
    def setExudynObjects(self, SC, mbs):
        """Set the Exudyn SystemContainer and MainSystem objects."""
        self.SC = SC
        self.mbs = mbs
        debugLog(f"ExudynRendererWidget: Set SC={SC}, mbs={mbs}")
        
    def startRenderer(self):
        """Start the Exudyn renderer."""
        if not EXUDYN_AVAILABLE:
            QMessageBox.warning(self, "Exudyn Not Available", 
                              "Exudyn library is not installed or accessible.\n"
                              "Please install Exudyn to use the renderer.")
            return
            
        if not self.mbs or not self.SC:
            QMessageBox.warning(self, "No Model", 
                              "No Exudyn model is loaded.\n"
                              "Please create or load a model before starting the renderer.")
            return
            
        try:
            # Make sure the model is assembled
            if hasattr(self.mbs, 'systemIsAssembled') and not self.mbs.systemIsAssembled:
                debugLog("Assembling model before starting renderer...")
                self.mbs.Assemble()
                  # Start the renderer
            debugLog("Starting Exudyn renderer...")
              # 🧵 Start Exudyn renderer in background thread to prevent GUI blocking
            import threading
            
            def run_renderer():
                debugLog("🧵 [THREAD] Starting external exu.StartRenderer() in background...")
                try:
                    exu.StartRenderer()
                    debugLog("🧵 [THREAD] External exu.StartRenderer() completed successfully")
                except Exception as e:
                    debugLog(f"🧵 [THREAD] External exu.StartRenderer() failed: {e}")
            
            debugLog("🚀 Creating background thread for external Exudyn renderer...")
            renderer_thread = threading.Thread(target=run_renderer, daemon=True)
            renderer_thread.start()
            debugLog(f"✅ External renderer thread started (Thread ID: {renderer_thread.ident})")
            
            self.renderer_active = True
            self.external_window_started = True
            
            # Update UI
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.refresh_button.setEnabled(True)
            self.status_label.setText("Renderer: Active")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #28a745;
                    font-weight: bold;
                    padding: 5px;
                }
            """)
            
            self.updatePlaceholder()
            self.updateInstructions()
            
            self.rendererStarted.emit()
            
            debugLog("Exudyn renderer started successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Renderer Error", 
                               f"Failed to start Exudyn renderer:\n{str(e)}")
            debugLog(f"Error starting renderer: {e}")
            
    def stopRenderer(self):
        """Stop the Exudyn renderer."""
        if not EXUDYN_AVAILABLE:
            return
            
        try:
            if self.renderer_active:
                debugLog("Stopping Exudyn renderer...")
                exu.StopRenderer()
                
            self.renderer_active = False
            self.external_window_started = False
            
            # Update UI
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.refresh_button.setEnabled(False)
            self.status_label.setText("Renderer: Stopped")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #6c757d;
                    font-weight: bold;
                    padding: 5px;
                }
            """)
            
            self.updatePlaceholder()
            self.updateInstructions()
            
            self.rendererStopped.emit()
            
            debugLog("Exudyn renderer stopped")
            
        except Exception as e:
            debugLog(f"Error stopping renderer: {e}")
            # Force reset UI state even if stop failed
            self.renderer_active = False
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.refresh_button.setEnabled(False)
            
    def refreshRenderer(self):
        """Refresh the renderer (useful when model changes)."""
        if not self.renderer_active:
            return
            
        try:
            # Force a refresh of the renderer
            debugLog("Refreshing Exudyn renderer...")
            
            # If we have access to renderer settings, we could update them here
            # For now, just make sure the current model state is reflected
            if hasattr(self.mbs, 'systemIsAssembled') and not self.mbs.systemIsAssembled:
                self.mbs.Assemble()
                
            # The renderer should automatically pick up changes
            debugLog("Renderer refreshed")
            
        except Exception as e:
            debugLog(f"Error refreshing renderer: {e}")
            
    def closeEvent(self, event):
        """Handle widget close event."""
        if self.renderer_active:
            self.stopRenderer()
        super().closeEvent(event)

    def isRendererActive(self):
        """Check if the renderer is currently active."""
        return self.renderer_active
        
    def getRendererStatus(self):
        """Get current renderer status information."""
        return {
            'active': self.renderer_active,
            'external_window': self.external_window_started,
            'has_model': self.mbs is not None and self.SC is not None,
            'exudyn_available': EXUDYN_AVAILABLE
        }
