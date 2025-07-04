#!/usr/bin/env python3
"""
🎯 PRACTICAL EXAMPLE: CONNECTING JUPYTER TO EXUDYN GUI

This example demonstrates how to connect an external Jupyter QtConsole
to a running Exudyn GUI for bidirectional communication.

SETUP STEPS:

1. Start the Exudyn GUI
2. In the GUI console, run:
   >>> exec(open('gui_console_bridge.py', encoding='utf-8').read())
   >>> export_gui_state()

3. In your external Jupyter QtConsole, run:
   >>> exec(open('jupyter_gui_example.py', encoding='utf-8').read())

This will establish a connection and allow you to:
- View GUI state in Jupyter
- Send code from Jupyter to GUI
- Synchronize variables between environments
"""

def setup_jupyter_gui_connection():
    """
    Set up connection from Jupyter to GUI
    """
    print("🔗 SETTING UP JUPYTER ↔ GUI CONNECTION")
    print("=" * 45)
    
    # Import the bridge module
    try:
        exec(open('gui_console_bridge.py', encoding='utf-8').read())
        print("✅ Bridge module loaded")
    except Exception as e:
        print(f"❌ Failed to load bridge: {e}")
        return False
    
    # Try to connect to GUI
    state = connect_to_gui()
    if not state:
        print("\n💡 SETUP INSTRUCTIONS:")
        print("1. Start the Exudyn GUI application")
        print("2. In GUI console, run:")
        print("   >>> exec(open('gui_console_bridge.py', encoding='utf-8').read())")
        print("   >>> export_gui_state()")
        print("3. Then run this script again")
        return False
    
    print("\n🎉 CONNECTION ESTABLISHED!")
    return True

def jupyter_demo():
    """
    Demonstrate Jupyter ↔ GUI capabilities
    """
    if not setup_jupyter_gui_connection():
        return
    
    print("\n🚀 JUPYTER ↔ GUI DEMO")
    print("=" * 25)
    
    # Load the latest GUI state
    state = connect_to_gui()
    
    print(f"\n📊 GUI STATE SUMMARY:")
    print(f"   Model items: {len(state['model_sequence'])}")
    print(f"   Variables: {list(state['variables'].keys())}")
    print(f"   Last update: {time.ctime(state['timestamp'])}")
    
    # Show model items
    if state['model_sequence']:
        print(f"\n🔧 MODEL ITEMS:")
        for i, item in enumerate(state['model_sequence']):
            item_type = item['itemType']
            return_val = item['returnValue']
            name = item['data'].get('name', 'unnamed')
            legacy = '(Legacy)' if item['isLegacy'] else '(CREATE)'
            print(f"   {i}: {item_type} {legacy} → {return_val} - {name}")
    
    # Try to load GUI modules
    print(f"\n🔄 TESTING MODULE IMPORT:")
    try:
        # Add GUI path
        import sys
        from pathlib import Path
        gui_path = Path.cwd()
        if str(gui_path) not in sys.path:
            sys.path.insert(0, str(gui_path))
        
        # Test imports
        from core.generateCode import generateExudynCodeFromItems
        from model.modelData import modelSequence
        print("   ✅ Core modules imported successfully")
        
        # Try to recreate model sequence
        modelSequence.clear()
        for item in state['model_sequence']:
            modelSequence.sequence.append(item)
        
        print(f"   ✅ Model sequence recreated ({len(modelSequence.sequence)} items)")
        
        # Generate code
        if modelSequence.sequence:
            try:
                code = generateExudynCodeFromItems()
                print(f"\n🎉 GENERATED CODE IN JUPYTER:")
                print("=" * 40)
                print(code)
                print("=" * 40)
            except Exception as e:
                print(f"   ⚠️ Code generation failed: {e}")
        
    except ImportError as e:
        print(f"   ⚠️ Module import failed: {e}")
        print("   💡 This is expected if GUI modules aren't in Python path")
    
    print(f"\n✅ DEMO COMPLETE!")
    print(f"💡 You can now work with GUI data in Jupyter!")

def create_external_script():
    """
    Create a script that can be sent back to the GUI
    """
    script_content = '''
# External script created in Jupyter
print("🎯 SCRIPT EXECUTED IN GUI FROM JUPYTER!")

# Add a new node
from core.modelManager import addItemToModel

# This would need the main window reference
# dialog = addItemToModel('NodePointGround', main_window)
# dialog.values['name'] = 'jupyter_node'
# dialog.accept()

print("✅ External script completed")
'''
    
    script_path = Path('jupyter_to_gui_script.py')
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"📝 Created external script: {script_path}")
    print(f"💡 In GUI, run: import_external_code('{script_path}')")
    
    return script_path

def main():
    """
    Main demonstration
    """
    print("🎯 JUPYTER ↔ GUI CONNECTION EXAMPLE")
    print("=" * 40)
    
    # Check environment
    print("🔍 Checking environment...")
    try:
        import jupyter_client
        print("✅ Jupyter environment detected")
    except ImportError:
        print("⚠️ Jupyter not available, but script will still work")
    
    # Run the demo
    jupyter_demo()
    
    # Create external script example
    print(f"\n📝 CREATING EXTERNAL SCRIPT EXAMPLE...")
    create_external_script()
    
    print(f"\n🎉 SETUP COMPLETE!")
    print(f"💡 You can now:")
    print(f"   • View GUI state in this environment")
    print(f"   • Create scripts to send back to GUI")
    print(f"   • Synchronize data between environments")

if __name__ == "__main__":
    import time
    import sys
    from pathlib import Path
    
    main()
