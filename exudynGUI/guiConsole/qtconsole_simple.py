#!/usr/bin/env python3
"""
ExudynGUI QtConsole Simple Integration
=====================================

Simple integration functions for QtConsole to interact with the ExudynGUI.
This provides easy access to model manipulation and synchronization.

Usage in QtConsole:
exec(open('exudynGUI/guiConsole/qtconsole_simple.py', encoding='utf-8').read())
"""

import sys
import traceback
from pathlib import Path

def get_main_window():
    """
    Get the main GUI window reference.
    """
    try:
        # Try to get from global namespace
        if 'main_window' in globals():
            return globals()['main_window']
        
        # Try to import from GUI modules
        try:
            from exudynGUI.guiForms.mainWindow import MainWindow
            # Look for existing instance
            for obj in gc.get_objects():
                if isinstance(obj, MainWindow):
                    return obj
        except ImportError:
            pass
        
        # Try to get from sys.modules
        for module_name in sys.modules:
            if 'mainWindow' in module_name:
                module = sys.modules[module_name]
                if hasattr(module, 'MainWindow'):
                    # Look for instance
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if hasattr(attr, '__class__') and 'MainWindow' in str(attr.__class__):
                            return attr
        
        return None
    except Exception as e:
        print(f"⚠️ Could not get main window: {e}")
        return None

def get_model_sequence():
    """
    Get the model sequence from the GUI.
    """
    try:
        # Try direct import
        from exudynGUI.model.modelData import modelSequence
        print(f"🔍 [DEBUG] Successfully imported modelSequence: {type(modelSequence)}, length: {len(modelSequence)}")
        return modelSequence
    except ImportError as e:
        print(f"🔍 [DEBUG] Direct import failed: {e}")
        # Try alternative paths
        try:
            import exudynGUI.model.modelData as modelData
            print(f"🔍 [DEBUG] Alternative import successful: {type(modelData.modelSequence)}, length: {len(modelData.modelSequence)}")
            return modelData.modelSequence
        except ImportError as e2:
            print(f"🔍 [DEBUG] Alternative import also failed: {e2}")
            print("❌ Could not import modelSequence")
            return None

def get_exudyn_system():
    """
    Get the Exudyn system (mbs) from the GUI.
    """
    try:
        # Try to get from global namespace
        if 'mbs' in globals():
            return globals()['mbs']
        
        # Try to get from main window
        main_win = get_main_window()
        if main_win and hasattr(main_win, 'mbs'):
            return main_win.mbs
        
        return None
    except Exception as e:
        print(f"⚠️ Could not get Exudyn system: {e}")
        return None

def sync_model_to_exudyn_simple():
    """
    Sync the GUI model to the Exudyn system.
    """
    try:
        print("🔄 Syncing GUI model to Exudyn system...")
        
        # Get the main window
        main_win = get_main_window()
        if not main_win:
            print("❌ Could not find main window")
            return False
        
        # Get the model sequence
        model_seq = get_model_sequence()
        if not model_seq:
            print("❌ Could not get model sequence")
            return False
        
        # Call the sync method
        if hasattr(main_win, 'syncModelToExudyn'):
            main_win.syncModelToExudyn()
            print("✅ Model synced successfully")
            return True
        else:
            print("❌ Main window has no syncModelToExudyn method")
            return False
            
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        traceback.print_exc()
        return False

def get_model_status_simple():
    """
    Get the current status of the model.
    """
    try:
        status = {}
        
        # Get model sequence
        model_seq = get_model_sequence()
        if model_seq:
            status['modelSequence_length'] = len(model_seq)
            
            # Sample some items
            sample_items = []
            for i, item in enumerate(model_seq[:5]):  # First 5 items
                sample_items.append({
                    'index': i,
                    'type': item.get('type', 'unknown'),
                    'name': item.get('data', {}).get('name', 'unnamed'),
                    'objIndex': item.get('data', {}).get('objIndex', None)
                })
            status['sample_items'] = sample_items
        
        # Get Exudyn system status
        mbs = get_exudyn_system()
        if mbs:
            try:
                status['mbs_nodes'] = mbs.GetNumberOfNodes()
                status['mbs_objects'] = mbs.GetNumberOfObjects()
                status['mbs_markers'] = mbs.GetNumberOfMarkers()
                status['mbs_loads'] = mbs.GetNumberOfLoads()
            except Exception as e:
                print(f"⚠️ Could not get MBS status: {e}")
                status['mbs_nodes'] = 0
                status['mbs_objects'] = 0
                status['mbs_markers'] = 0
                status['mbs_loads'] = 0
        else:
            status['mbs_nodes'] = 0
            status['mbs_objects'] = 0
            status['mbs_markers'] = 0
            status['mbs_loads'] = 0
        
        return status
        
    except Exception as e:
        print(f"❌ Could not get model status: {e}")
        return {'error': str(e)}

def clear_model_simple():
    """
    Clear the current model.
    """
    try:
        print("🧹 Clearing model...")
        
        # Get model sequence
        model_seq = get_model_sequence()
        if not model_seq:
            print("❌ Could not get model sequence")
            return False
        
        # Clear the sequence
        model_seq.clear()
        
        # Also clear the Exudyn system if available
        global SC, mbs
        mbs = get_exudyn_system()
        if mbs:
            try:
                # Create a new system container
                import exudyn as exu
                SC = exu.SystemContainer()
                mbs = SC.AddSystem()
                print("✅ Exudyn system cleared")
            except Exception as e:
                print(f"⚠️ Could not clear Exudyn system: {e}")
        
        print("✅ Model cleared successfully")
        return True
        
    except Exception as e:
        print(f"❌ Clear failed: {e}")
        return False

def add_ground_node_simple(name, position):
    """
    Add a ground node to the model.
    """
    try:
        print(f"➕ Adding ground node '{name}' at {position}...")
        
        # Get model sequence
        model_seq = get_model_sequence()
        if not model_seq:
            print("❌ Could not get model sequence")
            return False
        
        # Create ground node item
        ground_node = {
            'type': 'NodePointGround',
            'data': {
                'name': name,
                'nodeType': 'NodePointGround',
                'referenceCoordinates': position,
                'graphicsDataList': []
            }
        }
        
        # Add to sequence
        model_seq.append(ground_node)
        print(f"✅ Ground node '{name}' added")
        return True
        
    except Exception as e:
        print(f"❌ Failed to add ground node: {e}")
        return False

def add_mass_node_simple(name, position):
    """
    Add a mass node to the model.
    """
    try:
        print(f"➕ Adding mass node '{name}' at {position}...")
        
        # Get model sequence
        model_seq = get_model_sequence()
        if not model_seq:
            print("❌ Could not get model sequence")
            return False
        
        # Create mass node item
        mass_node = {
            'type': 'NodePoint',
            'data': {
                'name': name,
                'nodeType': 'NodePoint',
                'referenceCoordinates': position,
                'initialCoordinates': [0.0, 0.0, 0.0],
                'initialVelocities': [0.0, 0.0, 0.0],
                'graphicsDataList': []
            }
        }
        
        # Add to sequence
        model_seq.append(mass_node)
        print(f"✅ Mass node '{name}' added")
        return True
        
    except Exception as e:
        print(f"❌ Failed to add mass node: {e}")
        return False

def add_mass_body_simple(name, node_name, mass):
    """
    Add a mass body to the model.
    """
    try:
        print(f"➕ Adding mass body '{name}' with mass {mass}...")
        
        # Get model sequence
        model_seq = get_model_sequence()
        if not model_seq:
            print("❌ Could not get model sequence")
            return False
        
        # Create mass body item
        mass_body = {
            'type': 'ObjectMassPoint',
            'data': {
                'name': name,
                'nodeNumber': f'n{node_name}',
                'physicsMass': mass,
                'graphicsDataList': []
            }
        }
        
        # Add to sequence
        model_seq.append(mass_body)
        print(f"✅ Mass body '{name}' added")
        return True
        
    except Exception as e:
        print(f"❌ Failed to add mass body: {e}")
        return False

def demo_simple():
    """
    Run a simple demonstration of the integration.
    """
    print("🎯 Running Simple QtConsole Demo")
    print("=" * 35)
    
    # Clear model
    if not clear_model_simple():
        return False
    
    # Add ground node
    if not add_ground_node_simple("DemoGround", [0.0, 0.0, 0.0]):
        return False
    
    # Add mass node
    if not add_mass_node_simple("DemoMass", [1.0, 0.0, 0.0]):
        return False
    
    # Add mass body
    if not add_mass_body_simple("DemoBody", "DemoMass", 2.0):
        return False
    
    # Sync to Exudyn
    if not sync_model_to_exudyn_simple():
        return False
    
    # Check status
    status = get_model_status_simple()
    print(f"\n📊 Demo Results:")
    print(f"   GUI items: {status.get('modelSequence_length', 0)}")
    print(f"   MBS nodes: {status.get('mbs_nodes', 0)}")
    print(f"   MBS objects: {status.get('mbs_objects', 0)}")
    
    print("✅ Demo completed successfully!")
    return True

def show_help_simple():
    """
    Show help information for the simple integration.
    """
    help_text = """
🎯 QtConsole Simple Integration Help
====================================

Available Functions:
-------------------
• sync_model_to_exudyn_simple()  - Sync GUI model to Exudyn system
• get_model_status_simple()      - Get current model status
• clear_model_simple()           - Clear the current model
• add_ground_node_simple(name, position)  - Add ground node
• add_mass_node_simple(name, position)    - Add mass node  
• add_mass_body_simple(name, node, mass)  - Add mass body
• demo_simple()                  - Run complete demonstration
• show_help_simple()             - Show this help

Direct Access:
--------------
• modelSequence  - The GUI model data (from model.modelData)
• main_window    - The main GUI window (if available)
• mbs            - The Exudyn system (if available)
• SC             - The Exudyn system container (if available)

Quick Start:
------------
1. demo_simple()  # Run a complete demonstration
2. Check results with get_model_status_simple()
3. Add your own items using the add_*_simple() functions
4. Sync changes with sync_model_to_exudyn_simple()

Example:
--------
clear_model_simple()
add_ground_node_simple("MyGround", [0, 0, 0])
add_mass_node_simple("MyMass", [1, 0, 0])
add_mass_body_simple("MyBody", "MyMass", 5.0)
sync_model_to_exudyn_simple()
"""
    print(help_text)

# Initialize global references
try:
    import gc
    main_window = get_main_window()
    modelSequence = get_model_sequence()
    mbs = get_exudyn_system()
    
    # Try to get SC if available
    SC = None
    try:
        if mbs and hasattr(mbs, 'systemContainer'):
            SC = mbs.systemContainer
        elif main_window and hasattr(main_window, 'SC'):
            SC = main_window.SC
        elif 'SC' in globals():
            SC = globals()['SC']
    except:
        SC = None
    
    print("✅ QtConsole integration initialized")
    print(f"   Main window: {'✅' if main_window else '❌'}")
    print(f"   Model sequence: {'✅' if modelSequence is not None else '❌'}")
    print(f"   Exudyn system: {'✅' if mbs else '❌'}")
    print(f"   System container: {'✅' if SC else '❌'}")
    
except Exception as e:
    print(f"⚠️ Initialization warning: {e}")
    main_window = None
    modelSequence = None
    mbs = None
    SC = None
