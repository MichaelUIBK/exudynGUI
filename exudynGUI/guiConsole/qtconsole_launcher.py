#!/usr/bin/env python3
"""
ExudynGUI QtConsole Integration Launcher
=======================================

Quick launcher for QtConsole integration. Run this in the QtConsole
to get access to all GUI manipulation functions.

Usage in QtConsole:
exec(open('qtconsole_launcher.py', encoding='utf-8').read())
"""

print("🚀 ExudynGUI QtConsole Integration Launcher")
print("=" * 45)

# Load the simple integration (recommended)
print("📦 Loading QtConsole integration...")
try:
    exec(open('exudynGUI/guiConsole/qtconsole_simple.py', encoding='utf-8').read())
    print("✅ QtConsole integration loaded successfully!")
    
    print(f"\n💡 Available Functions:")
    print(f"  sync_model_to_exudyn_simple()  - ⭐ KEY: Sync GUI ↔ Exudyn")
    print(f"  get_model_status_simple()      - Check model status")
    print(f"  clear_model_simple()           - Clear the model")
    print(f"  add_ground_node_simple(name, pos)")
    print(f"  add_mass_node_simple(name, pos)")
    print(f"  add_mass_body_simple(name, node, mass)")
    print(f"  demo_simple()                  - Run complete demo")
    print(f"  show_help_simple()             - Show detailed help")
    
    print(f"\n💡 Direct Access (after loading):")
    print(f"  main_window     - The main GUI window")
    print(f"  modelSequence   - The GUI model data")
    print(f"  mbs             - The Exudyn system")
    print(f"  SC              - The Exudyn system container")
    
    print(f"\n🎯 Quick Start:")
    print(f"  demo_simple()  # Run a complete demonstration")
    
    print(f"\n🧪 Testing:")
    print(f"  exec(open('exudynGUI/guiConsole/test_complete_workflow.py', encoding='utf-8').read())")
    print(f"  exec(open('exudynGUI/guiConsole/test_nodetype_fix.py', encoding='utf-8').read())")
    
except Exception as e:
    print(f"❌ Failed to load integration: {e}")
    print(f"\n💡 Try loading manually:")
    print(f"  exec(open('exudynGUI/guiConsole/qtconsole_simple.py', encoding='utf-8').read())")

print("\n🏆 Ready for QtConsole ↔ ExudynGUI integration!")

_integration_already_loaded = False

def auto_inject_qtconsole():
    global _integration_already_loaded
    if _integration_already_loaded:
        return
    _integration_already_loaded = True
    try:
        # Import and run the simple integration logic directly
        import guiConsole.qtconsole_simple  # This will run the integration logic
    except Exception as e:
        print(f'⚠️ QtConsole integration not available: {e}')
        print('💡 To load manually: exec(open("exudynGUI/guiConsole/qtconsole_simple.py", encoding="utf-8").read())')

# If run as a script, do the normal launcher logic
if __name__ == "__main__":
    auto_inject_qtconsole()
