# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: guiForms/menubar.py
#
# Description:
#     menue bar for Exudyn GUI
#
# Authors:  Michael Pieber
# Date:     2025-05-12
# Notes:    Uses object registry and modelSequence for full flexibility.
#
# License:  BSD-3 license
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from PyQt5.QtWidgets import QMenuBar, QMenu, QAction, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QKeySequence, QDesktopServices
import os
import json


try:
    from exudynGUI.core.debug import debugInfo, debugError, debugWarning, debugLog, DebugCategory
except ImportError:
    def debugInfo(msg, origin="menubar.py", category="GENERAL"):
        print(f"[{origin}] {msg}")
    def debugError(msg, origin="menubar.py", category="GENERAL"):
        print(f"[{origin}] ERROR: {msg}")
    def debugWarning(msg, origin="menubar.py", category="GENERAL"):
        print(f"[{origin}] WARNING: {msg}")
    class DebugCategory:
        GENERAL = "GENERAL"
        GUI = "GUI"
        FILE_IO = "FILE_IO"


class ExudynMenuBar:
    """
    Comprehensive menu bar for the Exudyn GUI application.
    Provides file operations, edit functions, view controls, simulation commands,
    tools, and help resources.
    """
    
    def __init__(self, parent_window):
        """
        Initialize the menu bar with reference to the parent main window.
        
        Args:
            parent_window: The MainWindow instance that owns this menu bar
        """
        self.parent = parent_window
        self.menubar = None
        
    def setupMenuBar(self):
        """
        Create and configure the complete menu bar structure.
        Returns the configured QMenuBar instance.
        """
        try:
            self.menubar = self.parent.menuBar()
            
            # Create all main menus
            self._createFileMenu()
            self._createEditMenu()
            self._createViewMenu()
            self._createSimulationMenu()
            self._createToolsMenu()
            self._createHelpMenu()
            
            debugInfo("Menu bar setup completed successfully", origin="menubar.py", category=DebugCategory.GUI)
            return self.menubar
            
        except Exception as e:
            debugError(f"Failed to setup menu bar: {e}", origin="menubar.py", category=DebugCategory.GUI)
            return None
    
    def _createFileMenu(self):
        """Create the File menu with all file operations."""
        file_menu = self.menubar.addMenu("&File")
        
        # New Model
        new_action = QAction("&New Model", self.parent)
        new_action.setShortcut(QKeySequence.New)
        new_action.setStatusTip("Create a new Exudyn model")
        new_action.triggered.connect(self._newModel)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        # Open Model
        open_action = QAction("&Open Model...", self.parent)
        open_action.setShortcut(QKeySequence.Open)
        open_action.setStatusTip("Open an existing Exudyn model")
        open_action.triggered.connect(self._openModel)
        file_menu.addAction(open_action)
        
        # Recent Files submenu
        self.recent_menu = file_menu.addMenu("Recent Files")
        self._updateRecentFilesMenu()
        
        file_menu.addSeparator()
        
        # Save Model
        save_action = QAction("&Save Model", self.parent)
        save_action.setShortcut(QKeySequence.Save)
        save_action.setStatusTip("Save the current model")
        save_action.triggered.connect(self._saveModel)
        file_menu.addAction(save_action)
        
        # Save As
        save_as_action = QAction("Save &As...", self.parent)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.setStatusTip("Save the model with a new name")
        save_as_action.triggered.connect(self._saveModelAs)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # Export submenu
        export_menu = file_menu.addMenu("&Export")
        
        export_python_action = QAction("Export as Python Script...", self.parent)
        export_python_action.setStatusTip("Export model as Python script")
        export_python_action.triggered.connect(self._exportPython)
        export_menu.addAction(export_python_action)
        
        export_config_action = QAction("Export Configuration...", self.parent)
        export_config_action.setStatusTip("Export model configuration")
        export_config_action.triggered.connect(self._exportConfig)
        export_menu.addAction(export_config_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction("E&xit", self.parent)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.parent.close)
        file_menu.addAction(exit_action)
    
    def _createEditMenu(self):
        """Create the Edit menu with editing operations."""
        edit_menu = self.menubar.addMenu("&Edit")
        
        # Undo
        undo_action = QAction("&Undo", self.parent)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.setStatusTip("Undo the last action")
        undo_action.triggered.connect(self._undo)
        edit_menu.addAction(undo_action)
        
        # Redo
        redo_action = QAction("&Redo", self.parent)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.setStatusTip("Redo the last undone action")
        redo_action.triggered.connect(self._redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        # Cut
        cut_action = QAction("Cu&t", self.parent)
        cut_action.setShortcut(QKeySequence.Cut)
        cut_action.setStatusTip("Cut selection")
        cut_action.triggered.connect(self._cut)
        edit_menu.addAction(cut_action)
        
        # Copy
        copy_action = QAction("&Copy", self.parent)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.setStatusTip("Copy selection")
        copy_action.triggered.connect(self._copy)
        edit_menu.addAction(copy_action)
        
        # Paste
        paste_action = QAction("&Paste", self.parent)
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.setStatusTip("Paste from clipboard")
        paste_action.triggered.connect(self._paste)
        edit_menu.addAction(paste_action)
        
        edit_menu.addSeparator()
        
        # Delete
        delete_action = QAction("&Delete", self.parent)
        delete_action.setShortcut(Qt.Key_Delete)
        delete_action.setStatusTip("Delete selected items")
        delete_action.triggered.connect(self._delete)
        edit_menu.addAction(delete_action)
        
        # Select All
        select_all_action = QAction("Select &All", self.parent)
        select_all_action.setShortcut(QKeySequence.SelectAll)
        select_all_action.setStatusTip("Select all items")
        select_all_action.triggered.connect(self._selectAll)
        edit_menu.addAction(select_all_action)
        
        edit_menu.addSeparator()
        
        # Preferences
        preferences_action = QAction("&Preferences...", self.parent)
        preferences_action.setShortcut(QKeySequence.Preferences)
        preferences_action.setStatusTip("Open application preferences")
        preferences_action.triggered.connect(self._showPreferences)
        edit_menu.addAction(preferences_action)
    
    def _createViewMenu(self):
        """Create the View menu with view controls."""
        view_menu = self.menubar.addMenu("&View")
        
        # Zoom controls
        zoom_in_action = QAction("Zoom &In", self.parent)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        zoom_in_action.setStatusTip("Zoom in the view")
        zoom_in_action.triggered.connect(self._zoomIn)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom &Out", self.parent)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.setStatusTip("Zoom out the view")
        zoom_out_action.triggered.connect(self._zoomOut)
        view_menu.addAction(zoom_out_action)
        
        zoom_fit_action = QAction("&Fit to Window", self.parent)
        zoom_fit_action.setShortcut("Ctrl+0")
        zoom_fit_action.setStatusTip("Fit all objects in the view")
        zoom_fit_action.triggered.connect(self._zoomFit)
        view_menu.addAction(zoom_fit_action)
        
        view_menu.addSeparator()
        
        # View modes
        view_modes_menu = view_menu.addMenu("View &Mode")
        
        wireframe_action = QAction("&Wireframe", self.parent)
        wireframe_action.setStatusTip("Show wireframe view")
        wireframe_action.triggered.connect(self._setWireframeView)
        view_modes_menu.addAction(wireframe_action)
        
        solid_action = QAction("&Solid", self.parent)
        solid_action.setStatusTip("Show solid view")
        solid_action.triggered.connect(self._setSolidView)
        view_modes_menu.addAction(solid_action)
        
        view_menu.addSeparator()
        
        # Renderer controls
        refresh_action = QAction("&Refresh Renderer", self.parent)
        refresh_action.setShortcut("F5")
        refresh_action.setStatusTip("Refresh the 3D renderer")
        refresh_action.triggered.connect(self._refreshRenderer)
        view_menu.addAction(refresh_action)
        
        restart_renderer_action = QAction("&Restart Renderer", self.parent)
        restart_renderer_action.setStatusTip("Restart the 3D renderer")
        restart_renderer_action.triggered.connect(self._restartRenderer)
        view_menu.addAction(restart_renderer_action)
    
    def _createSimulationMenu(self):
        """Create the Simulation menu with simulation controls."""
        sim_menu = self.menubar.addMenu("&Simulation")
        
        # Run simulation
        run_action = QAction("&Run Simulation", self.parent)
        run_action.setShortcut("F9")
        run_action.setStatusTip("Start the simulation")
        run_action.triggered.connect(self._runSimulation)
        sim_menu.addAction(run_action)
        
        # Stop simulation
        stop_action = QAction("&Stop Simulation", self.parent)
        stop_action.setShortcut("Shift+F9")
        stop_action.setStatusTip("Stop the running simulation")
        stop_action.triggered.connect(self._stopSimulation)
        sim_menu.addAction(stop_action)
        
        sim_menu.addSeparator()
        
        # Simulation settings
        settings_action = QAction("Simulation &Settings...", self.parent)
        settings_action.setStatusTip("Configure simulation parameters")
        settings_action.triggered.connect(self._showSimulationSettings)
        sim_menu.addAction(settings_action)
        
        # Solver settings
        solver_action = QAction("S&olver Settings...", self.parent)
        solver_action.setStatusTip("Configure solver parameters")
        solver_action.triggered.connect(self._showSolverSettings)
        sim_menu.addAction(solver_action)
        
        sim_menu.addSeparator()
        
        # Results
        results_action = QAction("View &Results...", self.parent)
        results_action.setStatusTip("View simulation results")
        results_action.triggered.connect(self._viewResults)
        sim_menu.addAction(results_action)
    
    def _createToolsMenu(self):
        """Create the Tools menu with utility functions."""
        tools_menu = self.menubar.addMenu("&Tools")
        
        # Model validation
        validate_action = QAction("&Validate Model", self.parent)
        validate_action.setStatusTip("Check model for errors and warnings")
        validate_action.triggered.connect(self._validateModel)
        tools_menu.addAction(validate_action)
        
        # Model statistics
        stats_action = QAction("Model &Statistics", self.parent)
        stats_action.setStatusTip("Show model statistics")
        stats_action.triggered.connect(self._showModelStats)
        tools_menu.addAction(stats_action)
        
        tools_menu.addSeparator()
        
        # Console
        console_action = QAction("Show &Console", self.parent)
        console_action.setShortcut("Ctrl+Shift+C")
        console_action.setStatusTip("Show debug console")
        console_action.triggered.connect(self._showConsole)
        tools_menu.addAction(console_action)
        
        # Log viewer
        log_action = QAction("Show &Log", self.parent)
        log_action.setStatusTip("Show application log")
        log_action.triggered.connect(self._showLog)
        tools_menu.addAction(log_action)
        
        tools_menu.addSeparator()
        
        # User functions
        user_func_action = QAction("Edit &User Functions...", self.parent)
        user_func_action.setStatusTip("Edit custom user functions")
        user_func_action.triggered.connect(self._editUserFunctions)
        tools_menu.addAction(user_func_action)
    
    def _createHelpMenu(self):
        """Create the Help menu with help and about information."""
        help_menu = self.menubar.addMenu("&Help")
        
        # Online Documentation
        doc_action = QAction("&Online Documentation", self.parent)
        doc_action.setShortcut("F1")
        doc_action.setStatusTip("Open online documentation")
        doc_action.triggered.connect(self._showOnlineDocumentation)
        help_menu.addAction(doc_action)
        
        # PDF Documentation
        pdf_action = QAction("&PDF Documentation", self.parent)
        pdf_action.setStatusTip("Open PDF documentation")
        pdf_action.triggered.connect(self._showPdfDocumentation)
        help_menu.addAction(pdf_action)
        
        # Examples
        examples_action = QAction("&Examples", self.parent)
        examples_action.setStatusTip("Open example models")
        examples_action.triggered.connect(self._showExamples)
        help_menu.addAction(examples_action)
        
        help_menu.addSeparator()
        
        # Keyboard shortcuts
        shortcuts_action = QAction("&Keyboard Shortcuts", self.parent)
        shortcuts_action.setStatusTip("Show keyboard shortcuts")
        shortcuts_action.triggered.connect(self._showKeyboardShortcuts)
        help_menu.addAction(shortcuts_action)
        
        help_menu.addSeparator()
        
        # About
        about_action = QAction("&About Exudyn GUI", self.parent)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(self._showAbout)
        help_menu.addAction(about_action)
    
    # File menu handlers
    def _newModel(self):
        """Create a new model."""
        if hasattr(self.parent, 'newModel'):
            self.parent.newModel()
        else:
            debugInfo("New model requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _openModel(self):
        """Open an existing model."""
        if hasattr(self.parent, 'openModel'):
            self.parent.openModel()
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self.parent,
                "Open Exudyn Model",
                "",
                "Exudyn Models (*.json *.py);;All Files (*)"
            )
            if file_path:
                debugInfo(f"Opening model: {file_path}", origin="menubar.py", category=DebugCategory.FILE_IO)
    
    def _saveModel(self):
        """Save the current model."""
        if hasattr(self.parent, 'saveModel'):
            self.parent.saveModel()
        else:
            debugInfo("Save model requested", origin="menubar.py", category=DebugCategory.FILE_IO)
    
    def _saveModelAs(self):
        """Save the model with a new name."""
        if hasattr(self.parent, 'saveModelAs'):
            self.parent.saveModelAs()
        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self.parent,
                "Save Exudyn Model As",
                "",
                "Exudyn Models (*.json);;Python Scripts (*.py);;All Files (*)"
            )
            if file_path:
                debugInfo(f"Saving model as: {file_path}", origin="menubar.py", category=DebugCategory.FILE_IO)
    
    def _exportPython(self):
        """Export model as Python script."""
        if hasattr(self.parent, 'exportPython'):
            self.parent.exportPython()
        else:
            debugInfo("Export Python requested", origin="menubar.py", category=DebugCategory.FILE_IO)
    
    def _exportConfig(self):
        """Export model configuration."""
        if hasattr(self.parent, 'exportConfig'):
            self.parent.exportConfig()
        else:
            debugInfo("Export config requested", origin="menubar.py", category=DebugCategory.FILE_IO)
    
    # Edit menu handlers
    def _undo(self):
        """Undo the last action."""
        if hasattr(self.parent, 'undo'):
            self.parent.undo()
        else:
            debugInfo("Undo requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _redo(self):
        """Redo the last undone action."""
        if hasattr(self.parent, 'redo'):
            self.parent.redo()
        else:
            debugInfo("Redo requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _cut(self):
        """Cut selection."""
        if hasattr(self.parent, 'cut'):
            self.parent.cut()
        else:
            debugInfo("Cut requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _copy(self):
        """Copy selection."""
        if hasattr(self.parent, 'copy'):
            self.parent.copy()
        else:
            debugInfo("Copy requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _paste(self):
        """Paste from clipboard."""
        if hasattr(self.parent, 'paste'):
            self.parent.paste()
        else:
            debugInfo("Paste requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _delete(self):
        """Delete selected items."""
        if hasattr(self.parent, 'deleteSelected'):
            self.parent.deleteSelected()
        else:
            debugInfo("Delete requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _selectAll(self):
        """Select all items."""
        if hasattr(self.parent, 'selectAll'):
            self.parent.selectAll()
        else:
            debugInfo("Select all requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _showPreferences(self):
        """Show preferences dialog."""
        if hasattr(self.parent, 'showPreferences'):
            self.parent.showPreferences()
        else:
            debugInfo("Preferences requested", origin="menubar.py", category=DebugCategory.GUI)
    
    # View menu handlers
    def _zoomIn(self):
        """Zoom in the view."""
        if hasattr(self.parent, 'zoomIn'):
            self.parent.zoomIn()
        else:
            debugInfo("Zoom in requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _zoomOut(self):
        """Zoom out the view."""
        if hasattr(self.parent, 'zoomOut'):
            self.parent.zoomOut()
        else:
            debugInfo("Zoom out requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _zoomFit(self):
        """Fit all objects in the view."""
        if hasattr(self.parent, 'zoomFit'):
            self.parent.zoomFit()
        else:
            debugInfo("Zoom fit requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _setWireframeView(self):
        """Set wireframe view mode."""
        if hasattr(self.parent, 'setWireframeView'):
            self.parent.setWireframeView()
        else:
            debugInfo("Wireframe view requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _setSolidView(self):
        """Set solid view mode."""
        if hasattr(self.parent, 'setSolidView'):
            self.parent.setSolidView()
        else:
            debugInfo("Solid view requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _refreshRenderer(self):
        """Refresh the 3D renderer."""
        if hasattr(self.parent, 'refreshRenderer'):
            self.parent.refreshRenderer()
        else:
            debugInfo("Refresh renderer requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _restartRenderer(self):
        """Restart the 3D renderer."""
        if hasattr(self.parent, 'restartRenderer'):
            self.parent.restartRenderer()
        else:
            debugInfo("Restart renderer requested", origin="menubar.py", category=DebugCategory.GUI)
    
    # Simulation menu handlers
    def _runSimulation(self):
        """Start the simulation."""
        if hasattr(self.parent, 'runSimulation'):
            self.parent.runSimulation()
        else:
            debugInfo("Run simulation requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _stopSimulation(self):
        """Stop the running simulation."""
        if hasattr(self.parent, 'stopSimulation'):
            self.parent.stopSimulation()
        else:
            debugInfo("Stop simulation requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _showSimulationSettings(self):
        """Show simulation settings dialog."""
        if hasattr(self.parent, 'showSimulationSettings'):
            self.parent.showSimulationSettings()
        else:
            debugInfo("Simulation settings requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _showSolverSettings(self):
        """Show solver settings dialog."""
        if hasattr(self.parent, 'showSolverSettings'):
            self.parent.showSolverSettings()
        else:
            debugInfo("Solver settings requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _viewResults(self):
        """View simulation results."""
        if hasattr(self.parent, 'viewResults'):
            self.parent.viewResults()
        else:
            debugInfo("View results requested", origin="menubar.py", category=DebugCategory.GUI)
    
    # Tools menu handlers
    def _validateModel(self):
        """Validate the current model."""
        if hasattr(self.parent, 'validateModel'):
            self.parent.validateModel()
        else:
            debugInfo("Model validation requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _showModelStats(self):
        """Show model statistics."""
        if hasattr(self.parent, 'showModelStats'):
            self.parent.showModelStats()
        else:
            debugInfo("Model statistics requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _showConsole(self):
        """Show debug console."""
        if hasattr(self.parent, 'showConsole'):
            self.parent.showConsole()
        else:
            debugInfo("Console requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _showLog(self):
        """Show application log."""
        if hasattr(self.parent, 'showLog'):
            self.parent.showLog()
        else:
            debugInfo("Log viewer requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _editUserFunctions(self):
        """Edit user functions."""
        if hasattr(self.parent, 'editUserFunctions'):
            self.parent.editUserFunctions()
        else:
            debugInfo("Edit user functions requested", origin="menubar.py", category=DebugCategory.GUI)
    
    # Help menu handlers
    def _showOnlineDocumentation(self):
        """Show online documentation."""
        if hasattr(self.parent, 'showOnlineDocumentationDialog'):
            self.parent.showOnlineDocumentationDialog()
        else:
            QDesktopServices.openUrl(QUrl("https://github.com/jgerstmayr/EXUDYN"))
    
    def _showPdfDocumentation(self):
        """Show PDF documentation."""
        if hasattr(self.parent, 'showPdfDocumentation'):
            self.parent.showPdfDocumentation()
        else:
            debugInfo("PDF documentation requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _showExamples(self):
        """Show example models."""
        if hasattr(self.parent, 'showExamples'):
            self.parent.showExamples()
        else:
            debugInfo("Examples requested", origin="menubar.py", category=DebugCategory.GUI)
    
    def _showKeyboardShortcuts(self):
        """Show keyboard shortcuts dialog."""
        shortcuts_text = """
        <h3>Keyboard Shortcuts</h3>
        <table>
        <tr><td><b>File Operations:</b></td></tr>
        <tr><td>Ctrl+N</td><td>New Model</td></tr>
        <tr><td>Ctrl+O</td><td>Open Model</td></tr>
        <tr><td>Ctrl+S</td><td>Save Model</td></tr>
        <tr><td>Ctrl+Shift+S</td><td>Save As</td></tr>
        <tr><td>Ctrl+Q</td><td>Exit</td></tr>
        
        <tr><td><b>Edit Operations:</b></td></tr>
        <tr><td>Ctrl+Z</td><td>Undo</td></tr>
        <tr><td>Ctrl+Y</td><td>Redo</td></tr>
        <tr><td>Ctrl+X</td><td>Cut</td></tr>
        <tr><td>Ctrl+C</td><td>Copy</td></tr>
        <tr><td>Ctrl+V</td><td>Paste</td></tr>
        <tr><td>Delete</td><td>Delete Selected</td></tr>
        <tr><td>Ctrl+A</td><td>Select All</td></tr>
        
        <tr><td><b>View Controls:</b></td></tr>
        <tr><td>Ctrl++</td><td>Zoom In</td></tr>
        <tr><td>Ctrl+-</td><td>Zoom Out</td></tr>
        <tr><td>Ctrl+0</td><td>Fit to Window</td></tr>
        <tr><td>F5</td><td>Refresh Renderer</td></tr>
        
        <tr><td><b>Simulation:</b></td></tr>
        <tr><td>F9</td><td>Run Simulation</td></tr>
        <tr><td>Shift+F9</td><td>Stop Simulation</td></tr>
        
        <tr><td><b>Tools:</b></td></tr>
        <tr><td>Ctrl+Shift+C</td><td>Show Console</td></tr>
        
        <tr><td><b>Help:</b></td></tr>
        <tr><td>F1</td><td>Online Documentation</td></tr>
        </table>
        """
        
        QMessageBox.information(self.parent, "Keyboard Shortcuts", shortcuts_text)
    
    def _showAbout(self):
        """Show about dialog."""
        if hasattr(self.parent, 'showAboutDialog'):
            self.parent.showAboutDialog()
        else:
            about_text = f"""
            <h2>Exudyn GUI</h2>
            <p><b>Version:</b> {getattr(self.parent, 'app_version', 'Unknown')}</p>
            <p><b>A graphical user interface for Exudyn</b></p>
            <p>Exudyn is a flexible multibody dynamics simulation package.</p>
            <p>For more information, visit: <a href="https://exudyn.eu">https://exudyn.eu</a></p>
            """
            QMessageBox.about(self.parent, "About Exudyn GUI", about_text)
    
    def _updateRecentFilesMenu(self):
        """Update the recent files menu."""
        if hasattr(self, 'recent_menu'):
            self.recent_menu.clear()
            
            # Get recent files from parent if available
            recent_files = []
            if hasattr(self.parent, 'getRecentFiles'):
                recent_files = self.parent.getRecentFiles()
            
            if recent_files:
                for file_path in recent_files[:10]:  # Show last 10 files
                    action = QAction(os.path.basename(file_path), self.parent)
                    action.setStatusTip(file_path)
                    action.triggered.connect(lambda checked, path=file_path: self._openRecentFile(path))
                    self.recent_menu.addAction(action)
            else:
                no_recent_action = QAction("No recent files", self.parent)
                no_recent_action.setEnabled(False)
                self.recent_menu.addAction(no_recent_action)
    
    def _openRecentFile(self, file_path):
        """Open a recent file."""
        if hasattr(self.parent, 'openFile'):
            self.parent.openFile(file_path)
        else:
            debugInfo(f"Opening recent file: {file_path}", origin="menubar.py", category=DebugCategory.FILE_IO)


def createMenuBar(parent_window):
    """
    Convenience function to create and setup a menu bar for the given parent window.
    
    Args:
        parent_window: The MainWindow instance
        
    Returns:
        ExudynMenuBar instance
    """
    menu_bar = ExudynMenuBar(parent_window)
    menu_bar.setupMenuBar()
    return menu_bar
