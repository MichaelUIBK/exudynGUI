# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: main.py (Package version)
#
# Description:
#     Entry point for launching the Exudyn GUI application from installed package.
#     This is a package-aware version of the root main.py.
#
# Authors:  Michael Pieber
# Date:     2025-07-04
# License:  BSD-3 license 
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import os
import sys
from pathlib import Path
import traceback
import inspect
import time

# Import debug module FIRST, before anything else that might use it
try:
    from exudynGUI.core import debug
    #debug.configureForProduction()  # Only show errors, much quieter
    debug.setDebugLevel(debug.DebugLevel.TRACE)
except Exception as e:
    print(f"❌ Failed to import debug module: {e}")
    # Create a simple fallback debug function that matches the real signature
    def debugLog(msg, origin=None, level=None, category=None, summarize=False, **kwargs):
        origin_str = f"[{origin}]" if origin else "[unknown]"
        print(f"{origin_str} {msg}")
    
    import types
    debug = types.SimpleNamespace()
    debug.debugInfo = debugLog
    debug.debugError = debugLog
    debug.debugWarning = debugLog
    debug.debugLog = debugLog  # Export debugLog directly
    debug.DebugCategory = types.SimpleNamespace()
    debug.DebugCategory.GENERAL = "GENERAL"
    debug.DebugCategory.GUI = "GUI"
    debug.DebugCategory.CORE = "CORE"
    debug.DebugCategory.FILE_IO = "FILE_IO"

try:
    import exudyn as exu
    from exudyn import SystemContainer
    debug.debugInfo("✅ Successfully imported exudyn", origin="package.main.py", category=debug.DebugCategory.CORE)
except Exception as e:
    debug.debugError(f"❌ Failed to import exudyn: {e}", origin="package.main.py", category=debug.DebugCategory.CORE)
    print(f"❌ Critical error: exudyn not available: {e}")
    sys.exit(1)

# Import package modules using relative imports
try:
    from exudynGUI.guiForms.mainWindow import MainWindow
    debug.debugInfo("✅ Successfully imported MainWindow", origin="package.main.py", category=debug.DebugCategory.GUI)
except Exception as e:
    debug.debugError(f"❌ Failed to import MainWindow: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)
    traceback.print_exc()
    sys.exit(1)

try:
    from exudynGUI.core.qtImports import QApplication
    debug.debugInfo("✅ Successfully imported QApplication", origin="package.main.py", category=debug.DebugCategory.GUI)
except Exception as e:
    debug.debugError(f"❌ Failed to import QApplication: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)
    traceback.print_exc()
    sys.exit(1)

# Global reference to main window for external access
_main_window = None

# Global PDF documentation manager
_pdf_bookmarks = None
_pdf_path = None

APP_VERSION = "Exudyn Model Builder v0.4.2 (Glockturm)"

def ensureUserFunctions():
    """Ensure the functions/userFunctions.py file exists and can be imported."""
    try:
        # For installed package, use package directory
        package_dir = os.path.dirname(__file__)
        functions_dir = os.path.join(package_dir, "functions")
        user_func_path = os.path.join(functions_dir, "userFunctions.py")
        
        if not os.path.exists(user_func_path):
            os.makedirs(functions_dir, exist_ok=True)
            with open(user_func_path, "w") as f:
                f.write("# Define custom UF... user functions here\n")
            debug.debugInfo("Created default userFunctions.py", origin="package.main.py", category=debug.DebugCategory.FILE_IO)

        try:
            from exudynGUI.functions import userFunctions as uf
            import importlib
            importlib.reload(uf)
            debug.debugInfo("Loaded userFunctions.py", origin="package.main.py", category=debug.DebugCategory.FILE_IO)
        except Exception as e:
            debug.debugWarning(f"Could not import userFunctions.py: {e}", origin="package.main.py", category=debug.DebugCategory.FILE_IO)
    except Exception as e:
        debug.debugError(f"Error in ensureUserFunctions: {e}", origin="package.main.py", category=debug.DebugCategory.FILE_IO)

def loadGlobalPdfDocumentation():
    """Load PDF documentation bookmarks and extract category descriptions globally at application startup."""
    global _pdf_bookmarks, _pdf_path
    
    try:
        from exudynGUI.theDocHelper.theDocFieldHelp import loadBookmarks
        
        # For installed package, check package directory
        package_dir = os.path.dirname(__file__)
        possible_paths = [
            os.path.join(package_dir, "theDocHelper", "theDoc.pdf"),
            os.path.join(package_dir, "doc", "exudynDoc.pdf"),
            os.path.join(package_dir, "theDocHelper", "exudynDoc.pdf"),
        ]
        
        for pdfPath in possible_paths:
            if os.path.exists(pdfPath):
                _pdf_path = pdfPath
                _pdf_bookmarks = loadBookmarks(pdfPath)
                debug.debugInfo(f"✅ Global PDF documentation loaded from: {pdfPath}", origin="package.main.py", category=debug.DebugCategory.FILE_IO)
                
                # Also extract and store category descriptions during startup
                try:
                    from exudynGUI.guiForms.addItemDialog import extractCategoryDescriptionsFromPdf, updateCategoryDescriptionsWithPdf
                    # Set the global PDF path for the addItemDialog module
                    from exudynGUI.guiForms import addItemDialog
                    addItemDialog.pdfPath = Path(pdfPath)
                    
                    # Extract descriptions and update global storage
                    updateCategoryDescriptionsWithPdf()
                    debug.debugInfo("✅ Category descriptions extracted and stored during startup", origin="package.main.py", category=debug.DebugCategory.FILE_IO)
                except Exception as e:
                    debug.debugWarning(f"⚠️ Failed to extract category descriptions during startup: {e}", origin="package.main.py", category=debug.DebugCategory.FILE_IO)
                
                return True
        
        # If no PDF found, set to None
        _pdf_bookmarks = None
        _pdf_path = None
        debug.debugWarning("⚠️ No PDF documentation file found in any expected location", origin="package.main.py", category=debug.DebugCategory.FILE_IO)
        return False
        
    except Exception as e:
        _pdf_bookmarks = None
        _pdf_path = None
        debug.debugError(f"❌ Failed to load global PDF documentation: {e}", origin="package.main.py", category=debug.DebugCategory.FILE_IO)
        return False

def getGlobalPdfBookmarks():
    """Get the globally loaded PDF bookmarks."""
    return _pdf_bookmarks

def getGlobalPdfPath():
    """Get the globally loaded PDF path."""
    return _pdf_path

def launchGUI():
    """Launch the Exudyn GUI with splash screen and progress bar."""
    global _main_window
    
    try:
        from PyQt5.QtWidgets import QSplashScreen, QProgressBar, QApplication, QLabel
        from PyQt5.QtGui import QPixmap, QIcon
        from PyQt5.QtCore import Qt, QPropertyAnimation, QTimer

        app = QApplication.instance() or QApplication(sys.argv)

        debug.debugInfo("Starting Exudyn GUI from package...", origin="package.main.py", category=debug.DebugCategory.GUI)
        ensureUserFunctions()

        try:
            SC = SystemContainer()
            mbs = SC.AddSystem()
            debug.debugInfo("✅ Created SystemContainer and MainSystem", origin="package.main.py", category=debug.DebugCategory.CORE)
        except Exception as e:
            debug.debugError(f"❌ Failed to create SystemContainer: {e}", origin="package.main.py", category=debug.DebugCategory.CORE)
            traceback.print_exc()
            return

        # Splash screen setup
        try:
            # Use resource-based path that works for installed package
            try:
                import pkg_resources
                logo_path = pkg_resources.resource_filename('exudynGUI', 'design/assets/exudynLogo.png')
            except:
                # Fallback to package directory
                package_dir = os.path.dirname(__file__)
                logo_path = os.path.join(package_dir, "design", "assets", "exudynLogo.png")
            
            debug.debugInfo(f"Loading splash logo from: {logo_path}", origin="package.main.py", category=debug.DebugCategory.GUI)
            pixmap = QPixmap(logo_path)
            
            if pixmap.isNull():
                debug.debugError("❌ Failed to load splash screen pixmap", origin="package.main.py", category=debug.DebugCategory.GUI)
                return
                
            splash = QSplashScreen(pixmap)
            splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
            splash.show()
            app.processEvents()
            debug.debugInfo("✅ Splash screen created and shown", origin="package.main.py", category=debug.DebugCategory.GUI)
        except Exception as e:
            debug.debugError(f"❌ Failed to create splash screen: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)
            traceback.print_exc()
            return

        # Progress bar setup
        try:
            progress = QProgressBar(splash)
            margin = 40
            progress.setGeometry(margin, pixmap.height() - 50, pixmap.width() - 2*margin, 20)
            progress.setRange(0, 100)
            progress.setValue(0)
            progress.setTextVisible(False)
            
            # Style the progress bar with rounded corners
            progress.setStyleSheet("""
                QProgressBar {
                    border: 2px solid #444444;
                    border-radius: 10px;
                    background-color: rgba(255, 255, 255, 0.1);
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                                    stop: 0 #4CAF50, stop: 1 #45a049);
                    border-radius: 8px;
                    margin: 1px;
                }
            """)
            
            progress.show()
            app.processEvents()
        except Exception as e:
            debug.debugError(f"❌ Failed to create progress bar: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)

        # Version info
        try:
            version_label = QLabel(splash)
            version_label.setGeometry(0, pixmap.height() - 70, pixmap.width(), 20)
            version_label.setAlignment(Qt.AlignCenter)
            version_label.setStyleSheet("color: #e0e0e0; background: transparent; font-size: 10pt;")
            version_label.setText(APP_VERSION)
            version_label.show()
        except Exception as e:
            debug.debugError(f"❌ Failed to create version label: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)

        # Status text setup
        try:
            status = QLabel(splash)
            status.setGeometry(0, pixmap.height() - 30, pixmap.width(), 20)
            status.setAlignment(Qt.AlignCenter)
            status.setStyleSheet("color: white; background: transparent; font-size: 12pt;")
            status.setText("Loading PDF documentation...")
            status.show()
        except Exception as e:
            debug.debugError(f"❌ Failed to create status label: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)

        # Load PDF documentation
        try:
            progress.setValue(10)
            app.processEvents()
            loadGlobalPdfDocumentation()
            
            status.setText("Extracting category descriptions...")
            progress.setValue(20)
            app.processEvents()
        except Exception as e:
            debug.debugError(f"❌ Failed to load PDF documentation: {e}", origin="package.main.py", category=debug.DebugCategory.FILE_IO)

        # Create main window
        try:
            status.setText("Creating main window...")
            progress.setValue(30)
            app.processEvents()
            
            window = MainWindow(SC=SC, mbs=mbs, app_version=APP_VERSION, pdfBookmarks=getGlobalPdfBookmarks(), pdfPath=getGlobalPdfPath())
            window.setWindowIcon(QIcon(logo_path))
            window.hide()  # Ensure main window is hidden until splash fade-out completes
            window.resize(1280, 720)
            window.setMinimumSize(800, 450)
            debug.debugInfo("✅ Main window created successfully", origin="package.main.py", category=debug.DebugCategory.GUI)
        except Exception as e:
            debug.debugError(f"❌ Failed to create main window: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)
            traceback.print_exc()
            return

        # Animation: animated ellipsis for status
        try:
            ellipsis_states = ["", ".", "..", "..."]
            ellipsis_idx = [0]
            def animate_ellipsis():
                ellipsis_idx[0] = (ellipsis_idx[0] + 1) % len(ellipsis_states)
                if status.text().endswith("...") or status.text().endswith("..") or status.text().endswith("."):
                    base = status.text().rsplit(".", 1)[0].rstrip('.')
                else:
                    base = status.text()
                status.setText(base + ellipsis_states[ellipsis_idx[0]])
            ellipsis_timer = QTimer()
            ellipsis_timer.timeout.connect(animate_ellipsis)
            ellipsis_timer.start(400)
        except Exception as e:
            debug.debugError(f"❌ Failed to create ellipsis animation: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)

        # Precompute help with progress updates
        try:
            status.setText("Precomputing help content...")
            progress.setValue(50)
            app.processEvents()
            
            total_types = 1
            try:
                from exudynGUI.core.fieldMetadata import objectFieldMetadata
                total_types = len(objectFieldMetadata)
            except Exception:
                pass
            
            def precompute_with_progress(self):
                try:
                    from exudynGUI.guiForms.addItemDialog import AddModelElementDialog
                    from exudynGUI.core.fieldMetadata import objectFieldMetadata
                    import exudyn as exu
                    import inspect
                    legacy_types = list(objectFieldMetadata.keys())
                    dlg = AddModelElementDialog(parent=self, pdfBookmarks=getGlobalPdfBookmarks(), pdfPath=getGlobalPdfPath())
                    for idx, typeName in enumerate(legacy_types):
                        try:
                            if typeName.startswith("Create"):
                                func = getattr(exu.MainSystem, typeName, None)
                                if func is None:
                                    func = getattr(exu, typeName, None)
                                help_lines = []
                                help_lines.append(f"Exudyn {typeName} - High-Level Creation Function")
                                help_lines.append("=" * 60)
                                help_lines.append("")
                                try:
                                    sig = inspect.signature(func)
                                    help_lines.append("Function signature:")
                                    help_lines.append(f"  {typeName}{sig}")
                                    help_lines.append("")
                                except Exception:
                                    pass
                                doc = func.__doc__
                                if not doc:
                                    import io
                                    from contextlib import redirect_stdout
                                    f = io.StringIO()
                                    with redirect_stdout(f):
                                        help(func)
                                    doc = f.getvalue()
                                if doc:
                                    help_lines.append(doc.strip())
                                help_lines.append("")
                                help_lines.append("Usage Note:")
                                help_lines.append("This is a high-level creation function that automatically handles")
                                help_lines.append("the creation of nodes, objects, markers, and constraints as needed.")
                                help_lines.append("")
                                help_lines.append("For more detailed documentation, use the PDF help button.")
                                help_str = '\n'.join(help_lines)
                            else:
                                help_str = dlg._getLegacyHelpFromMetadata(typeName)
                            if help_str and len(help_str) > 100:
                                self.legacy_help_cache[typeName] = help_str
                        except Exception as e:
                            debug.debugWarning(f"Failed to precompute help for {typeName}: {e}", origin="package.main.py")
                        # Update progress bar and status text
                        progress_value = 50 + int((idx + 1) * 45 / total_types)
                        progress.setValue(progress_value)
                        status.setText(f"Loading help for {typeName}")
                        app.processEvents()
                    status.setText("Loading complete!")
                    progress.setValue(100)
                    app.processEvents()
                except Exception as e:
                    debug.debugError(f"❌ Error in precompute_with_progress: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)
                    traceback.print_exc()

            # Load global PDF documentation during startup
            # loadGlobalPdfDocumentation()
            
            window._precompute_legacy_help = precompute_with_progress.__get__(window)
            window._precompute_legacy_help()
        except Exception as e:
            debug.debugError(f"❌ Failed to precompute help: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)
            traceback.print_exc()

        _main_window = window

        # Fade out splash
        try:
            ellipsis_timer.stop()
            fade = QPropertyAnimation(splash, b"windowOpacity")
            fade.setDuration(2000)
            fade.setStartValue(1)
            fade.setEndValue(0)
            fade.start()
            
            def finish_splash():
                try:
                    splash.finish(window)
                    window.show()
                except Exception as e:
                    debug.debugError(f"❌ Error in finish_splash: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)
            fade.finished.connect(finish_splash)
        except Exception as e:
            debug.debugError(f"❌ Failed to fade splash: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)

        # Initialize additional components
        try:
            window.initRendererWidget()
        except Exception as e:
            debug.debugError(f"Failed to initialize renderer widget: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)
            traceback.print_exc()
        
        try:
            window.inject_debug_variables()
        except Exception as e:
            debug.debugError(f"Failed to inject debug variables: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)
            traceback.print_exc()
        
        try:
            from exudynGUI.core.rendererState import setupRendererTimer
            setupRendererTimer(window)
        except Exception as e:
            debug.debugError(f"Failed to setup renderer timer: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)
            traceback.print_exc()
        
        # try:
        #     # if hasattr(window, "stopIdleStateLoop"):
        #     #     window.stopIdleStateLoop()
        #     # if hasattr(window, "startIdleStateLoop"):
        #     #     window.startIdleStateLoop()
        # except Exception as e:
        #     debug.debugError(f"Failed to setup idle state loop: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)
        #     traceback.print_exc()
            
        debug.debugInfo("GUI launched successfully from package.", origin="package.main.py", category=debug.DebugCategory.GUI)
        sys.exit(app.exec_())
        
    except Exception as e:
        debug.debugError(f"❌ Critical error in launchGUI: {e}", origin="package.main.py", category=debug.DebugCategory.GUI)
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    try:
        launchGUI()
    except Exception as e:
        print(f"❌ Fatal error in package main: {e}")
        traceback.print_exc()
        sys.exit(1)
