"""
Renderer state preservation utilities for Exudyn GUI.
Provides unified functions to save and restore renderer/camera state from any parent window.
"""
import time
from exudynGUI.core.debug import debugLog
from PyQt5.QtCore import QTimer

def saveRendererStateFor(parentWindow):
    """Legacy function - saves current view state and returns it directly."""
    # Use the new saveViewState function but return the state directly
    key = "legacy_temp"
    if saveViewState(parentWindow, key):
        # Return the saved state for backward compatibility
        global _saved_view_states
        state = _saved_view_states.get(key)
        # Clean up the temporary key
        clearViewState(key)
        debugLog("✅ Legacy save complete (using new system)", origin="RendererState")
        return state
    
    debugLog("⚠️ Legacy save failed", origin="RendererState")
    return None


def restoreRendererStateFor(parentWindow, state, delay_ms=0):
    """Legacy function - restores view state from direct state object (full or filtered).
    Optionally delays restoration using QTimer.
    """
    if not state:
        debugLog("⚠️ Legacy restore failed - no state provided", origin="RendererState")
        return False

    def do_restore():
        try:
            if hasattr(parentWindow, 'SC') and parentWindow.SC and hasattr(parentWindow.SC, 'renderer'):
                # Check if it's a full state (has extra fields) or filtered state
                if isinstance(state, dict):
                    # For full compatibility, try SetState first with the full state
                    if hasattr(parentWindow.SC.renderer, 'SetState'):
                        try:
                            parentWindow.SC.renderer.SetState(state)
                            debugLog("✅ Legacy restore using SetState() with full state", origin="RendererState")
                        except Exception as e:
                            # If SetState fails, extract view parameters and try individual setting
                            debugLog(f"SetState failed, trying individual properties: {e}", origin="RendererState")
                            if 'centerPoint' in state:
                                parentWindow.SC.renderer.centerPoint = state['centerPoint']
                            if 'zoom' in state:
                                parentWindow.SC.renderer.zoom = state['zoom']
                            if 'modelRotation' in state and state['modelRotation'] is not None:
                                parentWindow.SC.renderer.modelRotation = state['modelRotation']
                            if 'maxSceneSize' in state:
                                parentWindow.SC.renderer.maxSceneSize = state['maxSceneSize']
                            debugLog("✅ Legacy restore using individual properties", origin="RendererState")
                    else:
                        # Fallback: set individual properties
                        if 'centerPoint' in state:
                            parentWindow.SC.renderer.centerPoint = state['centerPoint']
                        if 'zoom' in state:
                            parentWindow.SC.renderer.zoom = state['zoom']
                        if 'modelRotation' in state and state['modelRotation'] is not None:
                            parentWindow.SC.renderer.modelRotation = state['modelRotation']
                        if 'maxSceneSize' in state:
                            parentWindow.SC.renderer.maxSceneSize = state['maxSceneSize']
                        debugLog("✅ Legacy restore using individual properties (no SetState)", origin="RendererState")

                    # Force renderer update
                    if hasattr(parentWindow.SC.renderer, 'DoIdleTasks'):
                        parentWindow.SC.renderer.DoIdleTasks(waitSeconds=0.05)

                    debugLog("✅ Legacy restore complete", origin="RendererState")
                    return True
        except Exception as e:
            debugLog(f"⚠️ Legacy restore failed: {e}", origin="RendererState")
        debugLog("⚠️ Legacy restore failed", origin="RendererState")
        return False

    if delay_ms > 0:
        QTimer.singleShot(delay_ms, do_restore)
        return True
    else:
        return do_restore()

def setupRendererTimer(main_window):
    """Setup periodic renderer refresh to handle DoIdleTasks."""
    if hasattr(main_window, 'renderer_timer') and main_window.renderer_timer is not None:
        return  # Already setup
        
    from PyQt5.QtCore import QTimer
    main_window.renderer_timer = QTimer()
    main_window.renderer_timer.timeout.connect(lambda: refreshRenderer(main_window))
    main_window.renderer_refresh_active = False
    
    debugLog("🔧 Renderer timer initialized", origin="RendererState")

def refreshRenderer(main_window):
    """Refresh the renderer - called by timer."""
    global _auto_restore_target, _auto_restore_until
    import time  # Ensure time module is available in function scope
    
    try:
        if hasattr(main_window, 'SC') and main_window.SC and hasattr(main_window.SC, 'renderer'):
            renderer_is_active = False
            
            # Check if renderer is active
            if (hasattr(main_window, 'solution_viewer') and main_window.solution_viewer):
                if hasattr(main_window.solution_viewer, 'isRendererActive'):
                    renderer_is_active = main_window.solution_viewer.isRendererActive()
                elif hasattr(main_window.solution_viewer, 'renderer_active'):
                    renderer_is_active = getattr(main_window.solution_viewer, 'renderer_active', False)
                else:
                    renderer_is_active = True
            
            if renderer_is_active and main_window.isVisible():
                # 🎯 AUTO-RESTORE MECHANISM: Check if we need to restore view
                current_time = time.time()
                if _auto_restore_target and current_time < _auto_restore_until:
                    # Get current view state
                    current_state = None
                    if hasattr(main_window.SC.renderer, 'GetState'):
                        current_state = main_window.SC.renderer.GetState()
                    
                    # Check if current view is significantly different from target
                    if current_state and _isViewDifferent(current_state, _auto_restore_target):
                        # Restore the target view
                        _performDirectRestore(main_window, _auto_restore_target)
                        debugLog(f"🔄 Auto-restored view (remaining: {_auto_restore_until - current_time:.1f}s)", origin="RendererState")
                
                elif _auto_restore_target and current_time >= _auto_restore_until:
                    # Auto-restore period ended
                    debugLog(f"✅ Auto-restore period ended", origin="RendererState")
                    _auto_restore_target = None
                    _auto_restore_until = 0
                  # Execute DoIdleTasks
                main_window.SC.renderer.DoIdleTasks(waitSeconds=0.1)
                    
    except Exception as e:
        # Don't spam the log with renderer errors
        if not hasattr(main_window, '_last_renderer_error_time'):
            main_window._last_renderer_error_time = 0
        
        current_time = time.time()
        if current_time - main_window._last_renderer_error_time > 5.0:
            debugLog(f"⚠️ Renderer refresh error: {e}", origin="RendererState")
            main_window._last_renderer_error_time = current_time


# Global storage for saved view states
_saved_view_states = {}

# Auto-restore mechanism
_auto_restore_target = None  # The target view state to restore to
_auto_restore_until = 0      # Timestamp until when to keep restoring
_auto_restore_duration = 1.0 # Duration in seconds to keep restoring

def saveViewState(main_window, key="default"):
    """Save current view state with a specific key."""
    global _saved_view_states
    
    try:
        if hasattr(main_window, 'SC') and main_window.SC and hasattr(main_window.SC, 'renderer'):
            if hasattr(main_window.SC.renderer, 'GetState'):
                full_state = main_window.SC.renderer.GetState()
                
                # Extract relevant view parameters
                view_state = {
                    'centerPoint': list(full_state.get('centerPoint', [0, 0, 0])),
                    'rotationCenterPoint': list(full_state.get('rotationCenterPoint', [0, 0, 0])),
                    'zoom': full_state.get('zoom', 1.0),
                    'maxSceneSize': full_state.get('maxSceneSize', 1.0),
                    'modelRotation': full_state.get('modelRotation', None).copy() if full_state.get('modelRotation') is not None else None
                }
                
                _saved_view_states[key] = view_state
                debugLog(f"📌 View state saved with key: '{key}' - zoom={view_state['zoom']:.2f}", origin="RendererState")
                return True
                
    except Exception as e:
        debugLog(f"⚠️ Failed to save view state with key '{key}': {e}", origin="RendererState")
    
    return False

def restoreViewState(main_window, key="default", delay_ms=100):
    """Restore view state with optional delay."""
    global _saved_view_states
    
    if key not in _saved_view_states:
        debugLog(f"⚠️ No saved view state found for key: '{key}'", origin="RendererState")
        return False
    
    if delay_ms > 0:
        # Use QTimer for delayed restoration
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(delay_ms, lambda: _performRestore(main_window, key))
    else:
        _performRestore(main_window, key)
    
    return True

def _performRestore(main_window, key):
    """Internal method to perform the actual restoration."""
    global _saved_view_states
    
    try:
        if key not in _saved_view_states:
            return
            
        target_state = _saved_view_states[key]
        
        if hasattr(main_window, 'SC') and main_window.SC and hasattr(main_window.SC, 'renderer'):
            # Method 1: Try SetState if available
            if hasattr(main_window.SC.renderer, 'SetState'):
                main_window.SC.renderer.SetState(target_state)
                debugLog(f"✅ View restored using SetState() with key: '{key}'", origin="RendererState")
            
            # Method 2: Fallback to individual property setting
            else:
                if 'centerPoint' in target_state:
                    main_window.SC.renderer.centerPoint = target_state['centerPoint']
                if 'rotationCenterPoint' in target_state:
                    main_window.SC.renderer.rotationCenterPoint = target_state['rotationCenterPoint']
                if 'zoom' in target_state:
                    main_window.SC.renderer.zoom = target_state['zoom']
                if 'maxSceneSize' in target_state:
                    main_window.SC.renderer.maxSceneSize = target_state['maxSceneSize']
                if 'modelRotation' in target_state and target_state['modelRotation'] is not None:
                    main_window.SC.renderer.modelRotation = target_state['modelRotation']
                
                debugLog(f"✅ View restored using individual properties with key: '{key}'", origin="RendererState")
            
            # Force renderer update
            if hasattr(main_window.SC.renderer, 'DoIdleTasks'):
                main_window.SC.renderer.DoIdleTasks(waitSeconds=0.05)
                
    except Exception as e:
        debugLog(f"⚠️ Failed to restore view state with key '{key}': {e}", origin="RendererState")

def hasViewState(key="default"):
    """Check if a view state with the given key exists."""
    global _saved_view_states
    return key in _saved_view_states

def clearViewState(key="default"):
    """Clear a specific saved view state."""
    global _saved_view_states
    if key in _saved_view_states:
        del _saved_view_states[key]
        debugLog(f"🗑️ Cleared view state with key: '{key}'", origin="RendererState")
        return True
    return False

def clearAllViewStates():
    """Clear all saved view states."""
    global _saved_view_states
    count = len(_saved_view_states)
    _saved_view_states.clear()
    debugLog(f"�️ Cleared all {count} saved view states", origin="RendererState")

def listViewStates():
    """List all saved view state keys."""
    global _saved_view_states
    keys = list(_saved_view_states.keys())
    debugLog(f"� Saved view states: {keys}", origin="RendererState")
    return keys

def getCurrentViewInfo(main_window):
    """Get current view info for debugging."""
    try:
        if hasattr(main_window, 'SC') and main_window.SC and hasattr(main_window.SC, 'renderer'):
            if hasattr(main_window.SC.renderer, 'GetState'):
                state = main_window.SC.renderer.GetState()
                info = {
                    'zoom': state.get('zoom', 'unknown'),
                    'centerPoint': list(state.get('centerPoint', [0, 0, 0])),
                    'maxSceneSize': state.get('maxSceneSize', 'unknown')
                }
                debugLog(f"📊 Current view: zoom={info['zoom']:.2f}, center={info['centerPoint']}", origin="RendererState")
                return info
    except Exception as e:
        debugLog(f"⚠️ Failed to get current view info: {e}", origin="RendererState")
    return None

def _isViewDifferent(current_state, target_state, tolerance=0.01):
    """Check if current view is significantly different from target."""
    try:
        # Compare zoom
        current_zoom = current_state.get('zoom', 1.0)
        target_zoom = target_state.get('zoom', 1.0)
        if abs(current_zoom - target_zoom) > tolerance:
            return True
        
        # Compare center point
        current_center = current_state.get('centerPoint', [0, 0, 0])
        target_center = target_state.get('centerPoint', [0, 0, 0])
        for i in range(3):
            if abs(current_center[i] - target_center[i]) > tolerance:
                return True
        
        # Views are similar enough
        return False
        
    except Exception as e:
        debugLog(f"⚠️ Error comparing view states: {e}", origin="RendererState")
        return False

def _performDirectRestore(main_window, target_state):
    """Directly restore view state without going through the key system."""
    try:
        if hasattr(main_window, 'SC') and main_window.SC and hasattr(main_window.SC, 'renderer'):
            # Method 1: Try SetState if available
            if hasattr(main_window.SC.renderer, 'SetState'):
                main_window.SC.renderer.SetState(target_state)
            
            # Method 2: Fallback to individual property setting
            else:
                if 'centerPoint' in target_state:
                    main_window.SC.renderer.centerPoint = target_state['centerPoint']
                if 'rotationCenterPoint' in target_state:
                    main_window.SC.renderer.rotationCenterPoint = target_state['rotationCenterPoint']
                if 'zoom' in target_state:
                    main_window.SC.renderer.zoom = target_state['zoom']
                if 'maxSceneSize' in target_state:
                    main_window.SC.renderer.maxSceneSize = target_state['maxSceneSize']
                if 'modelRotation' in target_state and target_state['modelRotation'] is not None:
                    main_window.SC.renderer.modelRotation = target_state['modelRotation']
            
            # Force renderer update
            if hasattr(main_window.SC.renderer, 'DoIdleTasks'):
                main_window.SC.renderer.DoIdleTasks(waitSeconds=0.05)
                
    except Exception as e:
        debugLog(f"⚠️ Failed to perform direct restore: {e}", origin="RendererState")

def saveViewStateWithAutoRestore(main_window, key="auto_restore", duration=1.0):
    """Save view state and enable auto-restore for specified duration."""
    global _auto_restore_target, _auto_restore_until
    import time  # Ensure time module is available in function scope
    
    # First save the view state normally
    if saveViewState(main_window, key):
        # Set up auto-restore
        _auto_restore_target = _saved_view_states[key].copy()  # Make a copy
        _auto_restore_until = time.time() + duration
        
        debugLog(f"🎯 Auto-restore enabled for {duration}s with key: '{key}'", origin="RendererState")
        return True
    
    return False