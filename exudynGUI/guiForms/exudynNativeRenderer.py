# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/constructorArgsDialogInertia.py
#
# Description:
#     Dialog to edit constructor arguments for inertia utility functions
#     from exudyn.utilities (e.g., InertiaCuboid, InertiaSphere).
#
#     Features:
#       - Dropdown to select an Inertia* constructor
#       - Auto-generates form fields for arguments using introspection
#       - Restores values from a saved argument string
#       - Validates Python syntax of arguments before accepting
#
# Authors:  Michael Pieber
# Date:     2025-05-22
#
# License:  BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import sys
import os
import time
import ctypes
import platform
from PyQt5.QtCore import QTimer, pyqtSignal, Qt, QThread, QObject, QRect
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget, 
                             QMessageBox, QApplication, QSizePolicy)
from PyQt5.QtGui import QWindow, QCursor
from exudynGUI.core.rendererState import (
    saveRendererStateFor as _saveRendererStateFor, 
    restoreRendererStateFor as _restoreRendererStateFor, 
    saveViewState as _saveViewState, 
    restoreViewState as _restoreViewState
)
from exudynGUI.core.debug import debugLog
import traceback
import threading

# Platform-specific imports for window embedding
if platform.system() == "Windows":
    import win32gui
    import win32con
    import win32process
    
try:
    import exudyn as exu
    EXUDYN_AVAILABLE = True
except ImportError:
    EXUDYN_AVAILABLE = False



# Global reference to the main window for external access
_main_window = None

def setMainWindow(window):
    """Set the global reference to the main window."""
    global _main_window
    _main_window = window

class ExudynRendererEmbedder(QObject):
    """
    Helper class that manages the embedding of Exudyn's renderer window.
    """
    
    windowFound = pyqtSignal(int)  # Emit window handle when found
    
    def __init__(self):
        super().__init__()
        self.exudyn_hwnd = None
        self.search_timer = QTimer()
        self.search_timer.timeout.connect(self.findExudynWindow)
        
    def startSearching(self):
        """Start searching for the Exudyn window."""
        self.search_timer.start(100)  # Check every 100ms
        
    def stopSearching(self):
        """Stop searching for the Exudyn window."""
        self.search_timer.stop()
        
    def findExudynWindow(self):
        """Find the Exudyn renderer window using pywin32."""
        if platform.system() != "Windows":
            return
        try:
            def enum_windows_proc(hwnd, lParam):
                try:
                    title = win32gui.GetWindowText(hwnd)
                    if ("EXUDYN" in title.upper() and 
                        "MODEL BUILDER" not in title.upper() and
                        "GUI" not in title.upper()):
                        self.exudyn_hwnd = hwnd
                        self.stopSearching()
                        self.windowFound.emit(hwnd)
                        return False  # Stop enumeration
                except Exception as e:
                    pass
                return True  # Continue enumeration
            win32gui.EnumWindows(enum_windows_proc, 0)
        except Exception as e:
            pass

class ExudynNativeRendererWidget(QWidget):
    """
    Widget that embeds the native Exudyn OpenGL renderer for seamless integration.
    Auto-starts when Exudyn objects are set.
    """
    
    rendererStarted = pyqtSignal()
    rendererStopped = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set focus policy for keyboard input
        self.setFocusPolicy(Qt.ClickFocus)
        
        self.SC = None  # SystemContainer
        self.mbs = None  # MainSystem
        self.renderer_active = False
        self.embedded_window = None
        self.exudyn_hwnd = None
        self._prefer_undocked = False  # Default to docked mode
        self._resize_control_active = True  # Default to enabled for docked mode
        # Window embedder
        self.embedder = ExudynRendererEmbedder()
        self.embedder.windowFound.connect(self.delayedEmbedWindow)
        
        # Mouse tracking for continuous focus
        self.setMouseTracking(True)  # Enable mouse tracking
        self._focus_timer = QTimer()
        self._focus_timer.timeout.connect(self.checkMouseAndSetFocus)
        self._focus_timer.start(100)  # Check every 100ms
        
        self.setupUI()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Only resize embedded window if we're in docked mode and resize control is active
        if (hasattr(self, 'exudyn_hwnd') and self.exudyn_hwnd and 
            platform.system() == "Windows" and 
            getattr(self, '_resize_control_active', True) and
            not getattr(self, '_prefer_undocked', False)):
            
            rect = self.renderer_container.geometry()
            try:
                import win32gui
                import win32con
                win32gui.SetWindowPos(
                    self.exudyn_hwnd,
                    0,
                    0, 0,
                    rect.width(), rect.height(),
                    win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW
                )
            except Exception as e:
                pass

    def enableResizeControl(self):
        """Enable automatic resizing of embedded window (for docked mode)."""
        self._resize_control_active = True
        debugLog("[DEBUG] ExudynNativeRenderer: Resize control enabled")
        
    def disableResizeControl(self):
        """Disable automatic resizing (for undocked mode)."""
        self._resize_control_active = False
        debugLog("[DEBUG] ExudynNativeRenderer: Resize control disabled")

    def setupUI(self):
        """Setup the widget UI - streamlined for automatic embedding."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)  # Minimal margins for seamless integration
        
        # Container for embedded renderer - simplified and seamless
        self.renderer_container = QWidget()
        self.renderer_container.setMinimumHeight(300)
        self.renderer_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.renderer_container.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
                border: 1px solid #34495e;
                border-radius: 2px;
            }
        """)
        
        container_layout = QVBoxLayout(self.renderer_container)
        container_layout.setContentsMargins(0, 0, 0, 0)  # Remove all padding
        
        self.placeholder_label = QLabel("🎬 Initializing Exudyn Renderer...")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("""
            QLabel {
                color: #ecf0f1;
                font-size: 12px;
                font-weight: bold;
                border: none;
                background: transparent;
            }
        """)
        container_layout.addWidget(self.placeholder_label)
        
        layout.addWidget(self.renderer_container)
        
    def setExudynObjects(self, SC, mbs):
        """Set the Exudyn SystemContainer and MainSystem objects and auto-start renderer."""
        debugLog(f"[DEBUG] ExudynNativeRenderer: setExudynObjects called - renderer_active={self.renderer_active}")
        self.SC = SC
        self.mbs = mbs
        
        # Only auto-start the renderer if it's not already active
        if EXUDYN_AVAILABLE and self.SC and self.mbs and not self.renderer_active:
            debugLog("[DEBUG] ExudynNativeRenderer: Auto-starting renderer (not active yet)")
            # Use a timer to start slightly delayed, allowing GUI to fully initialize
            QTimer.singleShot(500, self.startRenderer)
        elif self.renderer_active:
            debugLog("[DEBUG] ExudynNativeRenderer: Renderer already active, updating model...")
            # Update the model without restarting the renderer
            self.updateModel()
        else:
            debugLog("[DEBUG] ExudynNativeRenderer: Cannot start renderer - Exudyn not available or objects not set")
            # Cannot auto-start renderer: Exudyn not available or objects not set
            pass

        
    def startRenderer(self):
        """Start the native Exudyn renderer and embed it."""
        
        is_active = self.SC.renderer.IsActive()
        if not is_active:
            self.SC.renderer.Start()
        
        if not EXUDYN_AVAILABLE:
            return False
        
        if not self.mbs or not self.SC:
            return False
            
        # Check if renderer is already active
        if self.renderer_active:
            return True
        
        try:
            # Make sure the model is assembled
            if hasattr(self.mbs, 'systemIsAssembled') and not self.mbs.systemIsAssembled:
                self.mbs.Assemble()

            # Start Exudyn's renderer in background thread to prevent GUI blocking
            # def run_renderer():
            #     try:
            #         self.SC.renderer.Start()
            #     except Exception as e:
            #         pass

            # renderer_thread = threading.Thread(target=run_renderer, daemon=True)
            # renderer_thread.start()
            
            # Only start embedding if we prefer docked mode
            if not self._prefer_undocked:
                # Start the embedder to search for the window
                self.embedder.startSearching()
            
            
            self.renderer_active = True
            self.rendererStarted.emit()           

            return True
            
        except Exception as e:
            return False
    
    def stopRenderer(self):
        """Stop the native Exudyn renderer."""
        if not EXUDYN_AVAILABLE:
            return

        try:
            # Stop searching for windows
            self.embedder.stopSearching()
            
            # Restore window if it was embedded
            if self.exudyn_hwnd and platform.system() == "Windows":
                self.restoreExudynWindow()

            # Stop Exudyn renderer
            if self.renderer_active:
                self.SC.renderer.Stop()
                self.renderer_active = False
                self.rendererStopped.emit()
                # Reset placeholder
                self.placeholder_label.setText("🎬 Renderer Stopped")
                self.placeholder_label.show()
                
        
        except Exception as e:
            pass
    
    def updateModel(self):
        """Update the renderer with new model data without restarting."""
        if not self.renderer_active or not self.mbs:
            return False
            
        try:
            debugLog("[DEBUG] ExudynNativeRenderer: Updating model data...")
            
            # Make sure the model is assembled with new data
            if hasattr(self.mbs, 'systemIsAssembled') and not self.mbs.systemIsAssembled:
                debugLog("[DEBUG] ExudynNativeRenderer: Assembling model...")
                self.mbs.Assemble()
            
            # Force the renderer to refresh its display with the new model
            if hasattr(self.SC, 'renderer') and self.renderer_active:
                # Use DoIdleTasks to force a renderer update
                debugLog("[DEBUG] ExudynNativeRenderer: Forcing renderer update with DoIdleTasks...")
                self.SC.renderer.DoIdleTasks(waitSeconds=0.1)
                
                # Additional step: force graphics update if available
                if hasattr(self.SC.renderer, 'forceGraphicsUpdate'):
                    self.SC.renderer.forceGraphicsUpdate()
                elif hasattr(self.SC.renderer, 'Refresh'):
                    self.SC.renderer.Refresh()
                    
                debugLog("[DEBUG] ExudynNativeRenderer: Model update completed")
                return True
            else:
                debugLog("[DEBUG] ExudynNativeRenderer: No active renderer to update")
                return False
                
        except Exception as e:
            debugLog(f"[ERROR] ExudynNativeRenderer: Failed to update model: {e}")
            return False
    
    def doIdleTasks(self, waitSeconds=0.1):
        """Call DoIdleTasks on the renderer if available."""
        try:
            if hasattr(self.SC, 'renderer') and self.renderer_active:
                self.SC.renderer.DoIdleTasks(waitSeconds=waitSeconds)
                return True
        except Exception as e:
            pass
        return False
    
    def refreshRenderer(self):
        """Refresh the renderer by restarting it."""
        
        self.stopRenderer()
        QTimer.singleShot(1000, self.startRenderer)  # Wait 1 second before restarting
        return True
    
    def isRendererActive(self):
        """Check if the renderer is currently active."""
        return self.renderer_active
    
    def checkForIndependentWindow(self):
        """Check if there's an independent Exudyn window (undocked mode)."""
        if platform.system() != "Windows":
            return False
        
        try:
            def enum_windows_proc(hwnd, lParam):
                try:
                    title = win32gui.GetWindowText(hwnd)
                    if ("EXUDYN" in title.upper() and 
                        "MODEL BUILDER" not in title.upper() and
                        "GUI" not in title.upper()):
                        # Check if this window is not a child (independent)
                        parent = win32gui.GetParent(hwnd)
                        if parent == 0:  # No parent = independent window
                            return False  # Found independent window, stop enumeration
                except Exception as e:
                    pass
                return True  # Continue enumeration
            
            # Return True if we find an independent window
            found_independent = [False]  # Use list to modify in closure
            def check_independent(hwnd, lParam):
                try:
                    title = win32gui.GetWindowText(hwnd)
                    if ("EXUDYN" in title.upper() and 
                        "MODEL BUILDER" not in title.upper() and
                        "GUI" not in title.upper()):
                        parent = win32gui.GetParent(hwnd)
                        if parent == 0:
                            found_independent[0] = True
                            return False
                except Exception as e:
                    pass
                return True
            
            win32gui.EnumWindows(check_independent, 0)
            return found_independent[0]
            
        except Exception as e:
            return False
    
    def getRendererStatus(self):
        """Get detailed status information about the renderer."""
        return {
            'active': self.renderer_active,
            'embedded': self.exudyn_hwnd is not None,
            'has_model': self.mbs is not None and self.SC is not None,
            'external_window': False,  # We embed, so no external window
            'exudyn_available': EXUDYN_AVAILABLE,
            'platform_supported': platform.system() == "Windows"
        }
    
    # Renderer State Management Methods
    def saveRendererState(self):
        """Save the current renderer state (camera position, view settings, etc.)."""
        try:
            if self.renderer_active and self.SC:
                return _saveRendererStateFor(self)
            return None
        except Exception as e:
            debugLog(f"❌ Error saving renderer state: {e}", origin="ExudynNativeRenderer")
            return None
    
    def restoreRendererState(self, state):
        """Restore the renderer state (camera position, view settings, etc.)."""
        try:
            if self.renderer_active and self.SC and state:
                return _restoreRendererStateFor(self, state)
            return False
        except Exception as e:
            debugLog(f"❌ Error restoring renderer state: {e}", origin="ExudynNativeRenderer")
            return False
    
    def saveRendererStateFor(self, identifier):
        """Save the current renderer state with a specific identifier."""
        try:
            if self.renderer_active and self.SC:
                return _saveViewState(self, identifier)
            return False
        except Exception as e:
            debugLog(f"❌ Error saving renderer state for '{identifier}': {e}", origin="ExudynNativeRenderer")
            return False
    
    def restoreRendererStateFor(self, identifier):
        """Restore the renderer state for a specific identifier."""
        try:
            if self.renderer_active and self.SC:
                return _restoreViewState(self, identifier)
            return False
        except Exception as e:
            debugLog(f"❌ Error restoring renderer state for '{identifier}': {e}", origin="ExudynNativeRenderer")
            return False
    
    def saveViewState(self):
        """Save the current view state (camera position and orientation)."""
        try:
            if self.renderer_active and self.SC:
                # Use a default key for the widget's view state
                return _saveViewState(self, "widget_default")
            return None
        except Exception as e:
            debugLog(f"❌ Error saving view state: {e}", origin="ExudynNativeRenderer")
            return None
    
    def restoreViewState(self, view_state):
        """Restore the view state (camera position and orientation).
        
        Args:
            view_state: Either a key string or a state dict for backward compatibility
        """
        try:
            if self.renderer_active and self.SC and view_state:
                if isinstance(view_state, str):
                    # If it's a key, use the key-based restore
                    return _restoreViewState(self, view_state)
                else:
                    # If it's a state dict, use the legacy restore function
                    return _restoreRendererStateFor(self, view_state)
            return False
        except Exception as e:
            debugLog(f"❌ Error restoring view state: {e}", origin="ExudynNativeRenderer")
            return False
        
    def delayedEmbedWindow(self, hwnd):
        """Set up the renderer window with a slight delay to ensure main window stability."""
        # Check if we're in undocked mode - if so, don't embed the window
        if getattr(self, '_prefer_undocked', False):
            debugLog("🚫 Skipping delayed window embedding - undocked mode preferred")
            return
        QTimer.singleShot(200, lambda: self.embedWindow(hwnd))
        
    def embedWindow(self, hwnd):
        """Embed the Exudyn window into this widget using pywin32."""
        if platform.system() != "Windows":
            # Window embedding only supported on Windows
            return
        
        # Check if we're in undocked mode - if so, don't embed the window
        if getattr(self, '_prefer_undocked', False):
            debugLog("🚫 Skipping window embedding - undocked mode preferred")
            return
        
        try:
            self.exudyn_hwnd = hwnd
            main_window = self.window()
            container_hwnd = int(self.renderer_container.winId())
            
            # 1. Set parent to the Qt container
            win32gui.SetParent(hwnd, container_hwnd)
            
            # 2. Set WS_CHILD style and remove top-level styles
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style = style | win32con.WS_CHILD
            style = style & ~win32con.WS_CAPTION
            style = style & ~win32con.WS_BORDER
            style = style & ~win32con.WS_DLGFRAME
            style = style & ~win32con.WS_SYSMENU
            style = style & ~win32con.WS_POPUP
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
            
            # 3. Remove topmost/toolwindow/layered from extended style
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style = ex_style & ~win32con.WS_EX_TOPMOST
            ex_style = ex_style & ~win32con.WS_EX_TOOLWINDOW
            ex_style = ex_style & ~0x00080000  # Remove WS_EX_LAYERED
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
            
            # 4. Position and resize the embedded window
            container_rect = self.renderer_container.geometry()
            win32gui.SetWindowPos(
                hwnd, 0, 0, 0,
                container_rect.width(), container_rect.height(),
                win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW
            )
            
            # 5. Simple focus attempt (like old version) - just try once, don't force
            try:
                win32gui.SetForegroundWindow(hwnd)  # Use SetForegroundWindow instead of SetFocus
            except Exception as e:
                pass
                
            self.placeholder_label.hide()
            self.configureContainerForEmbedding()
        except Exception as e:
            pass

    def configureContainerForEmbedding(self):
        """Configure the container widget for proper mouse and keyboard event handling."""
        try:
            # Make sure the container widget doesn't interfere with mouse events
            self.renderer_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            # Allow keyboard focus for interactive simulations (SPACE, Q keys)
            self.renderer_container.setFocusPolicy(Qt.ClickFocus)
            
            # Allow the main window to receive mouse events for moving
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            
        except Exception as e:
            pass
    
    def mousePressEvent(self, event):
        """Set focus to renderer when mouse is pressed."""
        super().mousePressEvent(event)
        self.setFocusToRenderer()

    def enterEvent(self, event):
        """Set focus to renderer when mouse enters the widget."""
        super().enterEvent(event)
        self.setFocusToRenderer()

    def setFocusToRenderer(self):
        """Set keyboard focus to the renderer container for interactive simulations."""
        try:
            # Set focus to the container widget
            self.renderer_container.setFocus()
            
            # Simple focus attempt (like old version) - just try once
            if hasattr(self, 'exudyn_hwnd') and self.exudyn_hwnd and platform.system() == "Windows":
                try:
                    import win32gui
                    win32gui.SetForegroundWindow(self.exudyn_hwnd)  # Use SetForegroundWindow instead of SetFocus

                except Exception as e:
                    pass
            
            return True
        except Exception as e:




            return False

    def restoreExudynWindow(self):
        """Restore the Exudyn window to its original state."""
        if not self.exudyn_hwnd or platform.system() != "Windows":
            return
            
        try:
            # Restore to desktop
            win32gui.SetParent(self.exudyn_hwnd, 0)
            
            # Restore window styles
            style = win32gui.GetWindowLong(self.exudyn_hwnd, win32con.GWL_STYLE)
            style = style & ~win32con.WS_CHILD
            style = style | win32con.WS_CAPTION
            style = style | win32con.WS_BORDER
            style = style | win32con.WS_SYSMENU
            win32gui.SetWindowLong(self.exudyn_hwnd, win32con.GWL_STYLE, style)
            
            # Show the window
            win32gui.ShowWindow(self.exudyn_hwnd, win32con.SW_SHOW)
            

            
        except Exception as e:
            pass

    def focusInEvent(self, event):
        """Automatically set focus to renderer when widget gains focus."""
        super().focusInEvent(event)
        self.setFocusToRenderer()

    # def checkMouseAndSetFocus(self):
    #     # Only set focus if no modal window is open
    #     if not QApplication.activeModalWidget():
    #         # Check if mouse is over this widget
    #         cursor_pos = QCursor.pos()
    #         top_left = self.mapToGlobal(self.rect().topLeft())
    #         bottom_right = self.mapToGlobal(self.rect().bottomRight())
    #         global_rect = QRect(top_left, bottom_right)
    #         if global_rect.contains(cursor_pos):
    #             self.setFocusToRenderer()

    def checkMouseAndSetFocus(self):
        # Only set focus if no modal window is open
        if not QApplication.activeModalWidget():
            # Check if mouse is over this widget
            cursor_pos = QCursor.pos()
            widget_under_cursor = QApplication.widgetAt(cursor_pos)
            # Only set focus if the widget under the cursor is this renderer widget or its container
            if widget_under_cursor is self or widget_under_cursor is self.renderer_container:
                self.setFocusToRenderer()

    def restartRendererDocked(self):
        """Restart the renderer for docked (embedded) mode.
        
        Preserves renderer state (camera position, view settings) across restart.
        """
        if not EXUDYN_AVAILABLE:
            debugLog("❌ Exudyn not available for renderer restart")
            return False
        
        def restart_operation():
            try:
                debugLog(f"🔄 Restarting renderer for docked mode... (Thread ID: {threading.get_ident()})")
                
                # 1. Set docked preference
                self._prefer_undocked = False
                
                if self.renderer_active:
                    debugLog("🛑 Stopping current renderer...")
                    try:
                        debugLog(f"Before StopRenderer: renderer_active={self.renderer_active}")
                        self.stopRenderer()
                        debugLog(f"After StopRenderer: renderer_active={self.renderer_active}")
                        # Wait for renderer to actually stop
                        timeout = 5.0
                        start = time.time()
                        while hasattr(self.SC, 'renderer') and getattr(self.SC.renderer, 'IsActive', lambda: False)():
                            if time.time() - start > timeout:
                                debugLog("❌ Renderer did not stop within timeout (5s)")
                                try:
                                    QMessageBox.critical(self, "Renderer Error", "OpenGL Renderer could not be stopped safely after 5 seconds. Please close any modal dialogs and try again.")
                                except Exception:
                                    pass
                                return False
                            debugLog("Waiting for renderer to stop...")
                            time.sleep(0.1)
                        debugLog("✅ Renderer stopped successfully.")
                        QTimer.singleShot(500, self._startFreshDockedRenderer)
                    except Exception as e:
                        debugLog(f"❌ Error stopping renderer: {e}")
                        import traceback
                        traceback.print_exc()
                        try:
                            QMessageBox.critical(self, "Renderer Error", f"Error stopping renderer: {e}")
                        except Exception:
                            pass
                        return False
                else:
                    self._startFreshDockedRenderer()
                
                # 2. ENABLE resize control after restart (delayed to allow window to be created)
                QTimer.singleShot(1000, self.enableResizeControl)
                
                return True
            except Exception as e:
                debugLog(f"❌ Error restarting renderer for docked mode: {e}")
                import traceback
                traceback.print_exc()
                try:
                    QMessageBox.critical(self, "Renderer Error", f"Error restarting renderer: {e}")
                except Exception:
                    pass
                return False
        result = restart_operation()
        return result
    
    def restartRendererUndocked(self):
        """Restart the renderer to create a truly undocked window.
        
        This is the most reliable approach - stop the current renderer and start
        a new one that won't be embedded, creating a truly independent window.
        Preserves renderer state (camera position, view settings) across restart.
        """
        if not EXUDYN_AVAILABLE:
            debugLog("❌ Exudyn not available for renderer restart")
            return False
        if not self.mbs or not self.SC:
            debugLog("❌ No model available for renderer restart")
            return False
        def restart_operation():
            try:
                debugLog(f"🔄 Restarting renderer for true undocked mode... (Thread ID: {threading.get_ident()})")
                
                # 1. DISABLE resize control FIRST to prevent window from being re-embedded
                self.disableResizeControl()
                
                # 2. Set undocked preference
                self._prefer_undocked = True
                
                if self.renderer_active:
                    debugLog("🛑 Stopping current renderer...")
                    try:
                        debugLog(f"Before StopRenderer: renderer_active={self.renderer_active}")
                        self.stopRenderer()
                        debugLog(f"After StopRenderer: renderer_active={self.renderer_active}")
                        # Wait for renderer to actually stop
                        timeout = 5.0
                        start = time.time()
                        while hasattr(self.SC, 'renderer') and getattr(self.SC.renderer, 'IsActive', lambda: False)():
                            if time.time() - start > timeout:
                                debugLog("❌ Renderer did not stop within timeout (5s)")
                                try:
                                    QMessageBox.critical(self, "Renderer Error", "OpenGL Renderer could not be stopped safely after 5 seconds. Please close any modal dialogs and try again.")
                                except Exception:
                                    pass
                                # Re-enable resize control on failure
                                self.enableResizeControl()
                                return False
                            debugLog("Waiting for renderer to stop...")
                            time.sleep(0.1)
                        debugLog("✅ Renderer stopped successfully.")
                        QTimer.singleShot(500, self._startFreshUndockedRenderer)
                    except Exception as e:
                        debugLog(f"❌ Error stopping renderer: {e}")
                        import traceback
                        traceback.print_exc()
                        try:
                            QMessageBox.critical(self, "Renderer Error", f"Error stopping renderer: {e}")
                        except Exception:
                            pass
                        # Re-enable resize control on failure
                        self.enableResizeControl()
                        return False
                else:
                    self._startFreshUndockedRenderer()
                return True
            except Exception as e:
                debugLog(f"❌ Error restarting renderer: {e}")
                import traceback
                traceback.print_exc()
                try:
                    QMessageBox.critical(self, "Renderer Error", f"Error restarting renderer: {e}")
                except Exception:
                    pass
                # Re-enable resize control on failure
                self.enableResizeControl()
                return False
        result = restart_operation()
        return result

    def _startFreshDockedRenderer(self):
        """Start a fresh renderer that will be embedded (docked)."""
        try:
            debugLog("🚀 Starting fresh docked renderer...")
            # Set preference to embed the window when it's found
            self._prefer_undocked = False
            self._restart_mode = True  # Flag to indicate this is a restart for docking
            # Enable resize control for docked mode
            self.enableResizeControl()
            # Update UI to show we're restarting
            self.placeholder_label.setText("🔄 Restarting Renderer (Docked Mode)...")
            self.placeholder_label.show()
            # Start the embedder to search for the new window (will embed it)
            self.embedder.startSearching()
            # Start Exudyn's renderer in background thread
            def run_fresh_docked_renderer():
                debugLog("🧵 [RESTART] Starting fresh exu.StartRenderer() for docked mode...")
                try:
                    self.startRenderer()
                    debugLog("🧵 [RESTART] Fresh exu.StartRenderer() completed successfully")
                except Exception as e:
                    debugLog(f"🧵 [RESTART] Fresh exu.StartRenderer() failed: {e}")
            debugLog("🚀 Creating background thread for fresh docked renderer...")
            renderer_thread = threading.Thread(target=run_fresh_docked_renderer, daemon=True)
            renderer_thread.start()
            debugLog(f"✅ Fresh docked renderer thread started (Thread ID: {renderer_thread.ident})")
            self.renderer_active = True
            self.rendererStarted.emit()           
            debugLog("🔄 Fresh docked renderer started, will be embedded in GUI...")
        except Exception as e:
            debugLog(f"❌ Error starting fresh docked renderer: {e}")
            import traceback
            traceback.print_exc()

    def _startFreshUndockedRenderer(self):
        """Start a fresh renderer that will create an independent window."""
        try:
            debugLog("🚀 Starting fresh undocked renderer...")
            # Set preference to NOT embed the window when it's found
            self._prefer_undocked = True
            self._restart_mode = True  # Flag to indicate this is a restart for undocking
            # Disable resize control for undocked mode
            self.disableResizeControl()
            # Update UI to show we're restarting
            self.placeholder_label.setText("🔄 Restarting Renderer (Undocked Mode)...")
            self.placeholder_label.show()
            # Start the embedder to search for the new window (but won't embed it)
            self.embedder.startSearching()
            # Start Exudyn's renderer in background thread
            def run_fresh_renderer():
                debugLog("🧵 [RESTART] Starting fresh exu.StartRenderer() for undocked mode...")
                try:
                    self.startRenderer()
                    debugLog("🧵 [RESTART] Fresh exu.StartRenderer() completed successfully")
                except Exception as e:
                    debugLog(f"🧵 [RESTART] Fresh exu.StartRenderer() failed: {e}")
            debugLog("🚀 Creating background thread for fresh undocked renderer...")
            renderer_thread = threading.Thread(target=run_fresh_renderer, daemon=True)
            renderer_thread.start()
            debugLog(f"✅ Fresh undocked renderer thread started (Thread ID: {renderer_thread.ident})")
            self.renderer_active = True
            self.rendererStarted.emit()           
            debugLog("🔄 Fresh undocked renderer started, will create independent window...")
        except Exception as e:
            debugLog(f"❌ Error starting fresh undocked renderer: {e}")
            import traceback
            traceback.print_exc()

def restoreRendererAfterPreview():
    """Restore the main OpenGL renderer after preview operations."""
    global _main_window
    try:
        if _main_window and hasattr(_main_window, 'SC'):
            main_SC = _main_window.SC
            
            
            # Step 1: Ensure main renderer is stopped first
            if hasattr(main_SC, 'renderer'):
                try:
                    main_SC.renderer.Stop()
                except Exception as e:
                    pass
            
            # Step 2: Small delay to let any preview renderer finish cleanup
            import time
            time.sleep(0.1)
            
            # Step 3: Restart the renderer
            if hasattr(_main_window, 'solution_viewer'):
                renderer_widget = _main_window.solution_viewer
                
                if hasattr(renderer_widget, 'startRenderer'):
            
                    renderer_widget.startRenderer()
              
                    return True
                else:

                    return False
            else:
          
                return False
                
        else:
        
            return False
            
    except Exception as e:
        return False

def withRendererRestore(preview_operation):
    """Execute a preview operation with proper sequential renderer switching."""
    global _main_window
    main_was_active = False
    
    try:
        # Step 1: Stop main renderer if active
        if _main_window and hasattr(_main_window, 'SC'):
            main_SC = _main_window.SC
            if hasattr(main_SC, 'renderer'):
                try:
                    if hasattr(main_SC.renderer, 'IsActive') and main_SC.renderer.IsActive():
                        main_was_active = True
                        main_SC.renderer.Stop()
                except Exception as e:
                    pass
        
        # Step 2: Execute the preview operation
        result = preview_operation()
        
        # Step 3: Always attempt to restore the main renderer if it was active
        if main_was_active:
            # Use a small delay to ensure preview cleanup is complete
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, restoreRendererAfterPreview)
        
        return result
        
    except Exception as e:
        # Still try to restore renderer even if preview failed
        if main_was_active:
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, restoreRendererAfterPreview)
        raise