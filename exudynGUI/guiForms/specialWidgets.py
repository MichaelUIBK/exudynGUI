# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/graphicsDataEditor.py
#
# Description:
#     Interactive editor for graphicsDataList entries in Exudyn.
#
#     Features:
#       - Visual list of GraphicsData constructor calls (e.g., Sphere, Cylinder)
#       - Supports adding, editing, reordering, and removing entries
#       - Parses argument strings for constructor calls
#       - Integrates with field metadata and validation logic
#       - Exports editable metadata for serialization and code generation
#
# Authors:  Michael Pieber, ExudynGUI Development Team
# Date:     2025-07-03
#
# License:  BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
import exudyn.utilities as exuutils
import tempfile
import os

from exudynGUI.core.qtImports import *
from exudynGUI.functions import userFunctions
from exudynGUI.functions.graphicsVisualizations import graphicsDataRegistry
from exudynGUI.guiForms.userFunctionEditor import UserFunctionEditorDialog
from exudyn.utilities import __dict__ as exuutils_dict

from exudynGUI.guiForms.userFunctionEditor import UserFunctionEditorDialog

from exudyn.utilities import __dict__ as exuutils_dict

# Import debug system - use module-level import for better reliability
import exudynGUI.core.debug as debug

# Legacy compatibility for existing debugLog calls
def debugLog(msg, origin=None, level=None, category=None, **kwargs):
    """Legacy debugLog function - maps to new debug system"""
    # Only output if debug is enabled
    if not debug.isDebugEnabled():
        return
        
    if "⚠️" in msg or "Error" in msg or "Failed" in msg:
        debug.debugWarning(msg, origin=origin or "specialWidgets", category=category or debug.DebugCategory.GUI)
    elif "✅" in msg or "Successfully" in msg:
        debug.debugInfo(msg, origin=origin or "specialWidgets", category=category or debug.DebugCategory.GUI)
    else:
        debug.debugTrace(msg, origin=origin or "specialWidgets", category=category or debug.DebugCategory.GUI)
        
    if "❌" in msg or "Error" in msg or "Failed" in msg:
        debug.debugError(msg, origin=origin, category=debug.DebugCategory.WIDGET)
    elif "⚠️" in msg or "Warning" in msg:
        debug.debugWarning(msg, origin=origin, category=debug.DebugCategory.WIDGET)
    else:
        debug.debugInfo(msg, origin=origin, category=debug.DebugCategory.WIDGET)

import inspect
from PyQt5.QtWidgets import QLabel, QPushButton, QListWidget, QListWidgetItem, QAbstractItemView, QGridLayout, QDoubleSpinBox, QSpinBox, QCheckBox, QLineEdit, QWidget, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import Qt, QEvent, pyqtSignal
import ast

# Used for graphics preview
from exudynGUI.guiForms.graphicsDataDialog import GraphicsDataDialog
from exudynGUI.guiForms.inertiaDataDialog import InertiaDataDialog

  
import math 
# -----------------------------
# UserFunction field widget
# -----------------------------
def buildUserFunctionWidget(fieldName, value=None, parent=None, meta=None, default=None, **kwargs):
    debugLog(f"[buildUserFunctionWidget] 🔍 Creating widget for '{fieldName}' with value={value} (type: {type(value)}), default={default} (type: {type(default)})")
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    combo = QComboBox()
    combo.setEditable(True)

    # Build dropdown: default 0 + all UF* functions
    funcs = ["0"] + [name for name in dir(userFunctions) if name.startswith("UF")]
    combo.addItems(funcs)

    # Select default: treat None, '', '0' all as "0"
    debugLog(f"[buildUserFunctionWidget] 🔍 Setting combo selection for '{fieldName}': default={default} (type: {type(default)})")
    if default in (None, '', 0, '0'):
        combo.setCurrentText("0")
        debugLog(f"[buildUserFunctionWidget] ✅ Set to '0' (empty default)")
    elif isinstance(default, str):
        combo.setCurrentText(default)
        debugLog(f"[buildUserFunctionWidget] ✅ Set to string: '{default}'")
    elif callable(default):
        combo.setCurrentText(getattr(default, '__name__', ''))
        debugLog(f"[buildUserFunctionWidget] ✅ Set to callable name: '{getattr(default, '__name__', '')}'")
    else:
        combo.setCurrentText(str(default))
        debugLog(f"[buildUserFunctionWidget] ✅ Set to string conversion: '{str(default)}'")

    layout.addWidget(combo)

    # Button to open user function editor
    editBtn = QPushButton("Edit userFunctions.py")
    layout.addWidget(editBtn)

    def openEditor():
        from exudynGUI.guiForms.userFunctionEditor import UserFunctionEditorDialog
        dlg = UserFunctionEditorDialog(parent=parent)
        if dlg.exec_():
            import importlib
            import exudynGUI.functions.userFunctions as uf
            importlib.reload(uf)
            combo.clear()
            funcs = ["0"] + [name for name in dir(uf) if name.startswith("UF")]
            combo.addItems(funcs)

    editBtn.clicked.connect(openEditor)

    container.combo = combo
    container.fieldType = "userFunction"

    # Ensure "0" string becomes int 0; everything else is passed through
    def getValue():
        val = container.combo.currentText().strip()
        result = 0 if val in ("0", "") else val
        debugLog(f"[buildUserFunctionWidget] 🔍 getValue() for '{fieldName}': combo text='{val}' → result={result} (type: {type(result)})")
        return result

    container.getValue = getValue    
    return container

    
def getDefaultArgsForInertiaConstructor(constructor):
    import numpy as np
    try:
        sig = inspect.signature(constructor)
        params = sig.parameters
        name = constructor.__name__

        if name == "InertiaTensor2Inertia6D":
            return "np.zeros((3,3))"
        elif name == "InertiaCuboid":
            return "density=1000, sideLengths=[1,1,1]"
        elif name == "InertiaSphere":
            return "mass=1.0, radius=0.1"
        elif name == "InertiaRodX":
            return "density=1000, length=1.0, radius=0.05"
        elif name == "InertiaMassPoint":
            return "mass=1.0"

        # Fallback: generate based on signature
        pieces = []
        for pname, pparam in sig.parameters.items():
            if pparam.default is inspect.Parameter.empty:
                # You can optionally put intelligent guesses here
                if pname == "inertiaTensor":
                    pieces.append(f"{pname}=np.zeros((3,3))")
                else:
                    pieces.append(f"{pname}=…")
            else:
                pieces.append(f"{pname}={repr(pparam.default)}")
        return ", ".join(pieces)

    except Exception as e:
        debugLog(f"[getDefaultArgsForInertiaConstructor] ⚠️ Failed: {e}")
        return ""



# -----------------------------
# GraphicsDataList field widget
# -----------------------------
def buildGraphicsEditorWidget(fieldName, default, meta, parent=None, structure=None):
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    previewLabel = QLabel("0 graphics")
    layout.addWidget(previewLabel)

    editBtn = QPushButton("Edit in Main Window")
    layout.addWidget(editBtn)

    # Get main window (assume parent is the form, whose parent is the main window)
    mainWindow = parent.parent() if parent and hasattr(parent, "parent") else None



    # Set initial graphics list in main window
    if mainWindow and hasattr(mainWindow, "setTemporaryGraphicsList"):
        mainWindow.setTemporaryGraphicsList(default if isinstance(default, list) else [])

    # Normalize malformed graphics entries
    def isValidEntry(e): return isinstance(e, dict) and 'name' in e and 'args' in e
    container.data = [e for e in default if isValidEntry(e)] if isinstance(default, list) else []

    container.previewLabel = previewLabel
    container.fieldType = "graphicsDataList"

    def updatePreview():
        container.previewLabel.setText(f"{len(container.data)} graphics")


    def onEdit():
        if parent is not None and hasattr(parent, "_previewUndo") and parent._previewUndo:
            mainWindow.undoLastAction()
            parent._previewUndo = False
        # Hide the parent form/dialog if possible
        if parent is not None and hasattr(parent, "hide"):
            parent.hide()
        # Show only Analyse and Graphics ribbons if method exists
        if mainWindow and hasattr(mainWindow, "showAnalyseAndGraphicsTabsOnly"):
            mainWindow.showAnalyseAndGraphicsTabsOnly()
        # Pass the form/dialog reference to MainWindow for later
        if mainWindow is not None:
            mainWindow._autoGeneratedForm = parent
        # Trigger graphics edit mode in the main window
        if mainWindow and hasattr(mainWindow, "startGraphicsEdit"):
            mainWindow.startGraphicsEdit(mainWindow.getTemporaryGraphicsList())
            updatePreview()

    editBtn.clicked.connect(onEdit)
    updatePreview()

    # Provide a getValue method for data collection
    def getValue():
        if mainWindow and hasattr(mainWindow, "getTemporaryGraphicsList"):
            return mainWindow.getTemporaryGraphicsList()
        return []

    container.getValue = getValue
    container.previewLabel = previewLabel
    container.fieldType = "graphicsDataList"

    return container


GROUP_NAME_TO_METHOD = {
    "Body": "getAvailableBodies",
    "Node": "getAvailableNodes",
    "Marker": "getAvailableMarkers",
    "Sensor": "getAvailableSensors",
    "Load": "getAvailableLoads",
    "Object": "getAvailableObjects",
}


def buildBodyOrNodeListWidget(fieldName, default=None, meta=None, parent=None, structure=None, **kwargs):
    """
    A multi‐select QListWidget that shows both "Bodies" (Objects) and "Nodes"
    in Model‐Structure format.  Each list‐entry is labeled via formatComponentLabel().

    When the user hits OK, getValue() returns a list of selected integer indices.
    """

    # ─── Delay this import to avoid circular references ───
    from exudynGUI.core.modelManager import formatComponentLabel

    container = QWidget(parent)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    listWidget = QListWidget()
    listWidget.setSelectionMode(QAbstractItemView.MultiSelection)

    # 1) Populate "Bodies" (Objects) and "Nodes"
    if structure is not None:
        try:
            bodies = structure.getAvailableObjects()  # → [(idx, label, objTypeHint), …]
        except Exception:
            bodies = []
        try:
            nodes = structure.getAvailableNodes()      # → [(idx, label, nodeTypeHint), …]
        except Exception:
            nodes = []

        # 2) Add body entries
        for idx, label, objTypeHint in bodies:
            fullType = f"Object{objTypeHint}"
            itemText = formatComponentLabel(
                "objects", idx, None, fullType
            )
            item = QListWidgetItem(itemText)
            # Tag as ("body", idx) so we can ignore the "body" tag in getValue()
            item.setData(Qt.UserRole, ("body", idx))
            listWidget.addItem(item)

        # 3) Add node entries
        for idx, label, nodeTypeHint in nodes:
            fullType = f"Node{nodeTypeHint}"
            itemText = formatComponentLabel(
                "nodes", idx, None, fullType
            )
            item = QListWidgetItem(itemText)
            item.setData(Qt.UserRole, ("node", idx))
            listWidget.addItem(item)

    # 4) Pre‐select any default indices
    if isinstance(default, (list, tuple)):
        defaultSet = set(int(d) for d in default if isinstance(d, int))
    else:
        defaultSet = set()

    for i in range(listWidget.count()):
        it = listWidget.item(i)
        stored = it.data(Qt.UserRole)  # stored is ( "body", idx ) or ( "node", idx )
        if stored is not None and stored[1] in defaultSet:
            it.setSelected(True)

    layout.addWidget(listWidget)

    container.listWidget = listWidget
    container.fieldType = "bodyOrNodeList"

    def getValue():
        # Return a list of (type, idx) tuples, preserving type information
        return [item.data(Qt.UserRole) for item in listWidget.selectedItems()]

    container.getValue = getValue
    return container




def buildBodyPairSelectorWidget(fieldName=None, default=None, meta=None, parent=None, structure=None):
    from exudynGUI.core.modelManager import formatComponentLabel
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    default = default or [None, None]
    if not isinstance(default, list) or len(default) != 2:
        default = [None, None]

    def createCombo(selectedIndex):
        combo = QComboBox()
        combo.setEditable(True)

        items = structure.get('objects', [])
        for obj in items:
            index = obj['index']
            objTypeHint = obj['data'].get('objectType')
            inferred = obj.get('inferred', None)
            label = formatComponentLabel(
                "objects", index, None, objTypeHint
            )
            combo.addItem(label, userData=index)

        if isinstance(selectedIndex, int):
            combo.setCurrentIndex(combo.findData(selectedIndex))
        return combo

    combo0 = createCombo(default[0])
    combo1 = createCombo(default[1])

    layout.addWidget(combo0)
    layout.addWidget(combo1)

    def getValue():
        def safeGet(combo):
            data = combo.currentData()
            if isinstance(data, int):
                return data
            idx = combo.currentIndex()
            return combo.itemData(idx) if combo.itemData(idx) is not None else idx
        return [safeGet(combo0), safeGet(combo1)]

    container.getValue = getValue
    return container



def buildBodyListWidget(fieldName, default=None, meta=None, parent=None, structure=None, **kwargs):
    """
    A custom widget that lists only "Bodies" (internally called 'Objects') in a
    multi‐select QListWidget.  Each entry is labeled exactly as the Model Structure does:
        [Object <idx>] (Object<objTypeHint>) (Objects (Body)).
    """

    # ─── Delay this import to avoid circular references ───
    from exudynGUI.core.modelManager import formatComponentLabel

    container = QWidget(parent)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    listWidget = QListWidget()
    listWidget.setSelectionMode(QAbstractItemView.MultiSelection)

    # 1) Fetch all "Objects" (bodies) from the structure
    bodies = []
    if structure is not None:
        try:
            # getAvailableObjects() returns a list of (idx, label, objTypeHint)
            bodies = structure.getAvailableObjects()
        except Exception:
            bodies = []

        for idx, label, objTypeHint in bodies:
            # Prepend "Object" to the short type hint, so we get "ObjectGround", "ObjectMassPoint", etc.
            fullType = f"Object{objTypeHint}"
            itemText = formatComponentLabel(
                "objects", idx, None, objTypeHint
            )
            item = QListWidgetItem(itemText)
            # Store just the body‐index in Qt.UserRole
            item.setData(Qt.UserRole, idx)
            listWidget.addItem(item)

    # 2) Pre‐select any defaults (default might be [int, int,…] or a single int)
    if isinstance(default, (list, tuple)):
        defaultSet = {int(x) for x in default if isinstance(x, int)}
    elif isinstance(default, int):
        defaultSet = {default}
    else:
        defaultSet = set()

    for i in range(listWidget.count()):
        it = listWidget.item(i)
        if it.data(Qt.UserRole) in defaultSet:
            it.setSelected(True)

    layout.addWidget(listWidget)

    container.listWidget = listWidget
    container.fieldType = "bodyList"

    def getValue():
        # Return a Python list of the integer indices selected
        return [it.data(Qt.UserRole) for it in listWidget.selectedItems()]

    container.getValue = getValue
    return container







def buildPairSelectorWidget(fieldName, default, meta, parent, structure, groupName):
    """
    A fully‐generic "pair selector" for any component group in the model.
    E.g. groupName="Node", "Object", "Marker", "Load", "Sensor", etc.

    This will produce two side‐by‐side QComboBoxes. Each dropdown is populated
    with all currently‐available items from that group, formatted just as the
    Model‐Structure tree does:

        [<Type> <idx>] (<FullTypeHint>) (<Category>)

    For example, for groupName="Node" you will see entries like:
        [Node 0] (NodePoint)     (Nodes)
        [Node 1] (NodeMassPoint) (Nodes)
        [Node 2] (Node1D)        (Nodes)
        …

    For groupName="Object" (i.e. "body"), you see:
        [Object 0] (ObjectGround)     (Objects (Body))
        [Object 1] (ObjectMassPoint)  (Objects (Body))
        [Object 2] (ObjectRigidBody)  (Objects (Body))
        …

    Once the user picks two items, getValue() returns [ idx0, idx1 ]. 
    "default" should be a length‐2 list or tuple of integers (or None).
    """

    container = QWidget(parent)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    # If `default` is not a length‐2 list of ints, force it to [None, None]
    if isinstance(default, (list, tuple)) and len(default) == 2:
        default0, default1 = default[0], default[1]
    else:
        default0, default1 = None, None

    # Determine which getter to call (e.g., "getAvailableNodes" or "getAvailableObjects", etc.)
    getterName = GROUP_NAME_TO_METHOD.get(groupName)
    # Example: GROUP_NAME_TO_METHOD["Node"] == "getAvailableNodes"
    #          GROUP_NAME_TO_METHOD["Object"] == "getAvailableObjects"
    #          GROUP_NAME_TO_METHOD["Marker"] == "getAvailableMarkers"
    #
    # Make sure you defined GROUP_NAME_TO_METHOD somewhere earlier in this file.

    def createCombo(selectedIndex):
        # Import here to avoid circular import issues
        from exudynGUI.core.modelManager import formatComponentLabel
        
        combo = QComboBox()
        combo.setEditable(False)

        items = []
        if structure is not None and getterName and hasattr(structure, getterName):
            try:
                items = getattr(structure, getterName)()
            except Exception:
                items = []

        # items is now a list of tuples (idx, label, shortTypeHint)
        #   for "Node"  → shortTypeHint might be "Point", "MassPoint", etc.
        #   for "Object"→ shortTypeHint might be "Ground", "MassPoint", etc.
        #   for "Marker"→ shortTypeHint might be "BodyPosition", "BodyMass", etc.
        #   for "Load"  → shortTypeHint might be "LoadMassProportional", etc.
        #   for "Sensor"→ shortTypeHint might be "SensorPosition", etc.

        for idx, label, shortTypeHint in items:
            # 1) Build the "fullType" by prepending groupName (e.g. "NodePoint", "ObjectGround", "MarkerBodyPosition", etc.)
            # Simple fallback formatting instead of using formatComponentLabel
            # 2) Let formatComponentLabel produce exactly:
            #       [<GroupName> <idx>] (<fullTypeHint>) (<Category>)
            itemText = f"[{groupName} {idx}] {label} ({shortTypeHint})"
            combo.addItem(itemText, userData=idx)

        # If the default index is not currently in the combo, add a placeholder
        if isinstance(selectedIndex, int) and combo.findData(selectedIndex) == -1:
            combo.addItem(f"{selectedIndex} - (unknown)", userData=selectedIndex)

        # Restore the default selection if it exists
        if isinstance(selectedIndex, int):
            found = combo.findData(selectedIndex)
            if found >= 0:
                combo.setCurrentIndex(found)

        return combo

    # Build the two combo boxes
    combo1 = createCombo(default0)
    combo2 = createCombo(default1)

    layout.addWidget(combo1)
    layout.addWidget(combo2)

    # Store them on the container so that getValue() can see them
    container.combo1 = combo1
    container.combo2 = combo2
    container.fieldType = f"{groupName}Pair"  # e.g. "NodePair", "ObjectPair", etc.

    def getValue():
        return [combo1.currentData(), combo2.currentData()]

    container.getValue = getValue
    return container



# def buildNodePairSelectorWidget(fieldName, default, meta, parent=None, structure=None):
#     return buildPairSelectorWidget(fieldName, default, meta, parent, structure, "Node")

def setComboBoxIndex(combo, value):
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)

def buildMultiComponentSelectorWidget(fieldName, default, meta, parent=None, structure=None, group="object"):
    container = QWidget(parent)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    listWidget = QListWidget()
    listWidget.setSelectionMode(QAbstractItemView.MultiSelection)

    if structure:
        getterName = f"getAvailable{group.capitalize()}s"
        if hasattr(structure, getterName):
            entries = getattr(structure, getterName)()
            for idx, label, typ in entries:
                item = QListWidgetItem(f"[{idx}] {label} ({typ})")
                item.setData(Qt.UserRole, idx)
                listWidget.addItem(item)

    # Pre-select default values
    if isinstance(default, list):
        for i in range(listWidget.count()):
            item = listWidget.item(i)
            if item.data(Qt.UserRole) in default:
                item.setSelected(True)

    layout.addWidget(listWidget)

    container.listWidget = listWidget
    container.fieldType = f"{group}MultiSelector"
    container.getValue = lambda: [
        item.data(Qt.UserRole) for item in listWidget.selectedItems()
    ]
    return container


def buildMultiIndexSelectorWidget(fieldName, default, meta, parent=None, structure=None, indexType="object", requiredCount=None):
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    edit = QLineEdit()
    edit.setPlaceholderText(f"e.g., [0, 1] for {indexType}s")

    if isinstance(default, list):
        edit.setText(str(default))
    else:
        edit.setText("[]")

    layout.addWidget(edit)
    container.edit = edit
    container.fieldType = "multiIndexSelector"
    container.indexType = indexType
    container.requiredCount = requiredCount

    def getValue():
        try:
            return ast.literal_eval(container.edit.text())
        except:
            return []

    container.getValue = getValue    
    return container


def buildIndexSelectorWidget(fieldName, value, parent=None, meta=None, default=None, structure=None):
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    combo = QComboBox()
    items = []

    if structure is None:
        structure = {}

    if 'node' in fieldName.lower():
        nodes = structure.get('nodes', [])
        items = [f"{i}: {node.get('name', 'Node')}" for i, node in enumerate(nodes)]
    elif 'body' in fieldName.lower() or 'object' in fieldName.lower():
        objs = structure.get('objects', [])
        items = [f"{i}: {obj.get('name', 'Object')}" for i, obj in enumerate(objs)]
    elif 'marker' in fieldName.lower():
        markers = structure.get('markers', [])
        items = [f"{i}: {mk.get('name', 'Marker')}" for i, mk in enumerate(markers)]

    for item in items:
        combo.addItem(item)

    # Try to set initial selection
    try:
        if isinstance(default, int) and 0 <= default < len(items):
            combo.setCurrentIndex(default)
    except:
        pass

    layout.addWidget(combo)
    container.combo = combo
    container.fieldType = "indexSelector"
    
    def getValue():
        return container.combo.currentIndex()
    container.getValue = getValue
    return container
# filepath: c:\Users\piebe\Desktop\ModelBuilderV01\V0\copilotWithGUI\mainExudynGUI_V0.04\exudynGUI\guiForms\specialWidgets.py


class EnhancedInt6Widget(QWidget):
    """
    A widget for a 6-element integer vector.
    - Top: a QLineEdit for literal entry like "[1,0,1,0,1,0]"
    - Bottom: six QSpinBoxes (each ∈ ℤ, default from input)
    """
    valueChanged = pyqtSignal()

    def __init__(self, default=[1,1,1,1,1,1], parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)

        # 1) Expression line edit
        self.exprField = QLineEdit()
        self.exprField.setPlaceholderText("Type int6 list, e.g. [1,0,1,0,1,0]")
        self.exprField.setText(str(default))
        self.layout.addWidget(self.exprField)

        # 2) Six spin boxes
        self.spinBoxes = []
        spinRow = QWidget()
        h = QHBoxLayout(spinRow)
        h.setContentsMargins(0,0,0,0)
        for i in range(6):
            sb = QSpinBox()
            sb.setRange(-9999, 9999)
            sb.setValue(default[i] if isinstance(default, (list,tuple)) and len(default)==6 else 0)
            sb.valueChanged.connect(self._onSpinChanged)
            h.addWidget(sb)
            self.spinBoxes.append(sb)
        self.layout.addWidget(spinRow)

        # When user edits "[a,b,c,d,e,f]" in the text field:
        self.exprField.textChanged.connect(self._onExprChanged)

    def _onSpinChanged(self, newVal):
        arr = [sb.value() for sb in self.spinBoxes]
        self.exprField.setText(str(arr))
        self.valueChanged.emit()

    def _onExprChanged(self, text):
        txt = text.strip()
        if txt.startswith("[") and txt.endswith("]"):
            try:
                candidate = eval(txt, {}, {})   # (you could use ast.literal_eval(txt) if you prefer)
                if isinstance(candidate, (list,tuple)) and len(candidate)==6 and all(isinstance(x,int) for x in candidate):
                    for i,sb in enumerate(self.spinBoxes):
                        sb.setValue(candidate[i])
                    self.exprField.setStyleSheet("")  # valid → clear error highlight
                    self.valueChanged.emit()
                    return
            except Exception:
                pass
        # Invalid expression → highlight background in red
        self.exprField.setStyleSheet("background-color: #ffdddd;")

    def getValue(self):
        txt = self.exprField.text().strip()
        if txt.startswith("[") and txt.endswith("]"):
            try:
                candidate = eval(txt, {}, {})
                if isinstance(candidate, (list,tuple)) and len(candidate)==6 and all(isinstance(x,int) for x in candidate):
                    return candidate
            except:
                pass
        # Otherwise, just read directly from spinBoxes:
        return [sb.value() for sb in self.spinBoxes]


def buildInt6Widget(fieldName, default=None, meta=None, parent=None, structure=None):
    """
    Build an EnhancedInt6Widget for a 6-element integer vector.
    """
    d = default if (isinstance(default, list) and len(default)==6) else [1,1,1,1,1,1]
    return EnhancedInt6Widget(default=d, parent=parent)


def extractSpecialWidgetValue(widget):

    if hasattr(widget, "data") and getattr(widget, "fieldType", "") == "inertiaList":
        if widget.data:
            value = widget.data[0]
            valueStr = f"{value['name']}({value['args']})"
            debugLog(f"[extractSpecialWidgetValue] inertiaList → {valueStr}", origin="specialWidgets")
            return valueStr

    elif hasattr(widget, "data") and getattr(widget, "fieldType", "") == "inertiaList":
        if widget.data:
            value = widget.data[0]  # First entry
            valueStr = f"{value['name']}({value['args']})"
            debugLog(f"[extractSpecialWidgetValue] inertiaList → {valueStr}", origin="specialWidgets")
            return valueStr
    
    elif hasattr(widget, "data") and hasattr(widget, "previewLabel"):
        # Graphics editor widget
        debugLog(f"[extractSpecialWidgetValue] graphicsDataList → {len(widget.data)} entries", origin="specialWidgets")
        return list(widget.data)

    elif hasattr(widget, "combo") and isinstance(widget.combo, QComboBox):
        # UserFunction selector
        value = widget.combo.currentText()
        debugLog(f"[extractSpecialWidgetValue] userFunction → {value}", origin="specialWidgets")
        return value

    elif hasattr(widget, "edit") and getattr(widget, "fieldType", None) == "multiIndexSelector":
        try:
            value = ast.literal_eval(widget.edit.text())
            debugLog(f"[extractSpecialWidgetValue] multiIndexSelector → {value}", origin="specialWidgets")
            return value
        except Exception as e:
            debugLog(f"[extractSpecialWidgetValue] ❌ Error parsing multiIndex: {e}", origin="specialWidgets")
            return []

    elif hasattr(widget, "getValue") and callable(widget.getValue):
        try:
            value = widget.getValue()
            debugLog(f"[extractSpecialWidgetValue] fallback → {value}", origin="specialWidgets")
            return value
        except Exception as e:
            debugLog(f"[extractSpecialWidgetValue] ❌ getValue() failed: {e}", origin="specialWidgets")

    debugLog(f"[extractSpecialWidgetValue] ❌ Unknown widget type: {widget}", origin="specialWidgets")
    return None







import numpy as np

# from PyQt5.QtWidgets import QWidget, QGridLayout, QDoubleSpinBox, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox

class Matrix3x3Widget(QWidget):
    def __init__(self, default=None, parent=None, symbolDict=None, default_value=None):
        super().__init__(parent)
        self.symbolDict = symbolDict or {}
        
        # Support both 'default' and 'default_value' parameters for compatibility
        if default_value is not None:
            default = default_value

        self.layout = QVBoxLayout(self)
        self.grid = QGridLayout()
        self.spinBoxes = []

        if isinstance(default, np.ndarray):
            default = default.tolist()
        for i in range(3):
            row = []
            for j in range(3):
                spin = QDoubleSpinBox()
                spin.setDecimals(6)
                spin.setRange(-1e4, 1e4)
                spin.setAlignment(Qt.AlignRight)
                spin.setSingleStep(1.0)
                val = default[i][j] if default is not None else (1.0 if i == j else 0.0)
                spin.setValue(val)
                self.grid.addWidget(spin, i, j)
                row.append(spin)
            self.spinBoxes.append(row)

        # Presets + angle
        self.presetCombo = QComboBox()
        self.presetCombo.addItems([
            "Identity", "Diagonal (2.0)", "RotationX", "RotationY", "RotationZ"
        ])

        self.angleInput = QLineEdit("90")  # degrees or variable
        self.angleInput.setPlaceholderText("angle (deg or variable)")
        self.applyButton = QPushButton("Apply Preset")
        self.applyButton.clicked.connect(self.applyPreset)

        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel("Preset:"))
        hlayout.addWidget(self.presetCombo)
        hlayout.addWidget(QLabel("Angle:"))
        hlayout.addWidget(self.angleInput)
        hlayout.addWidget(self.applyButton)

        self.layout.addLayout(self.grid)
        self.layout.addLayout(hlayout)

    def getValue(self):
        return [[sb.value() for sb in row] for row in self.spinBoxes]

    def text(self):
        """Get the current matrix as a string representation for the constructor dialog"""
        matrix = self.getValue()
        # Ensure all values are standard Python floats for valid syntax
        clean_matrix = [[float(matrix[i][j]) for j in range(3)] for i in range(3)]
        return str(clean_matrix)

    def setMatrix(self, matrix):
        for i in range(3):
            for j in range(3):
                self.spinBoxes[i][j].setValue(matrix[i][j])

    def parseAngleInput(self):
        text = self.angleInput.text().strip()
        try:
            return float(text) * np.pi / 180  # degrees → radians
        except ValueError:
            # Try resolving symbolic variable
            if text in self.symbolDict:
                return float(self.symbolDict[text]) * np.pi / 180
            raise ValueError(f"Invalid angle input: '{text}'")

    def applyPreset(self):
        preset = self.presetCombo.currentText()
        try:
            angle = self.parseAngleInput()
        except ValueError as e:
            debugLog(str(e))
            return
    
        if preset == "Identity":
            matrix = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
        elif preset == "Diagonal (2.0)":
            matrix = [[2.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
        elif preset == "RotationX":
            matrix = exuutils.RotationMatrixX(angle)
        elif preset == "RotationY":
            matrix = exuutils.RotationMatrixY(angle)
        elif preset == "RotationZ":
            matrix = exuutils.RotationMatrixZ(angle)
        else:
            return
    
        if isinstance(matrix, np.ndarray):
            matrix = matrix.tolist()
    
        self.setMatrix(matrix)
        

def createEulerXYZWidget(self, initial_matrix=None):
    from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QDoubleSpinBox
    import numpy as np
    import ast
    import exudyn.utilities as ut
    import math

    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0,0,0,0)

    # three spinboxes in degrees
    rotX = QDoubleSpinBox(); rotY = QDoubleSpinBox(); rotZ = QDoubleSpinBox()
    for sb in (rotX, rotY, rotZ):
        sb.setRange(-360, 360)
        sb.setSingleStep(1)
        sb.setSuffix("°")
    for sb, lbl in ((rotX,'X:'), (rotY,'Y:'), (rotZ,'Z:')):
        lay.addWidget(QLabel(lbl))
        lay.addWidget(sb)

    # if we already have a matrix, decompose it to XYZ angles (rad) and convert to deg
    if initial_matrix:
        try:
            mat = np.array(ast.literal_eval(initial_matrix)
                            if isinstance(initial_matrix, str) else initial_matrix)
            angles_rad = ut.RotationMatrix2RotXYZ(mat)
            rotX.setValue( math.degrees(angles_rad[0]) )
            rotY.setValue( math.degrees(angles_rad[1]) )
            rotZ.setValue( math.degrees(angles_rad[2]) )
        except:
            pass

    # override .text() to export a 3×3 matrix (in radians!) as JSON list
    def text():
        degs = [rotX.value(), rotY.value(), rotZ.value()]
        rads = [math.radians(d) for d in degs]
        A = ut.RotXYZ2RotationMatrix(rads)
        return repr(A.tolist())
    w.text = text

    return w        

def buildMatrix3x3Widget(fieldName, value=None, parent=None, meta=None, default=None, **kwargs):
    """
    Create a 3×3‐matrix editor.  Behavior:
      • If the incoming `value` (or `default`) is the exact string 
        "EXUmath::unitMatrix3D", fill with the identity matrix.
      • If it's any other string (e.g. a user‐function expression), 
        start with all zeros so the user can type in something.
      • If it's already a 3×3 list/tuple/ndarray of numbers (or a flat list of 9 floats),
        prefill with those numeric values.
      • Otherwise, fall back to zeros.

    This way, a default of "EXUmath::unitMatrix3D" becomes identity, not zeros.
    """
    # 1) Decide which "matrix candidate" to use: prefer `value` over `default`
    matrix_candidate = value if (value not in (None, "")) else default

    # 2) If the candidate is exactly the unit‐matrix string, use identity
    if isinstance(matrix_candidate, str) and matrix_candidate.strip() == "EXUmath::unitMatrix3D":
        identity = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]
        return Matrix3x3Widget(default=identity, parent=parent)

    # 3) If it's any other string, we intentionally do NOT prefill numerically.
    #    Just give the user a blank (zero) grid to enter whatever they want.
    if isinstance(matrix_candidate, str):
        return Matrix3x3Widget(parent=parent)

    # 4) If it's a NumPy array, convert to nested lists
    if isinstance(matrix_candidate, np.ndarray):
        try:
            matrix_candidate = matrix_candidate.tolist()
        except Exception:
            matrix_candidate = None

    # 5) If it's a flat list/tuple of length 9, reshape to 3×3
    if isinstance(matrix_candidate, (list, tuple)) and len(matrix_candidate) == 9 \
       and all(isinstance(x, (int, float)) for x in matrix_candidate):
        flat = matrix_candidate
        numeric = [
            [float(flat[0]), float(flat[1]), float(flat[2])],
            [float(flat[3]), float(flat[4]), float(flat[5])],
            [float(flat[6]), float(flat[7]), float(flat[8])]
        ]
        return Matrix3x3Widget(default=numeric, parent=parent)

    # 6) If it's already a nested 3×3 list/tuple, convert each to float
    if isinstance(matrix_candidate, (list, tuple)) and len(matrix_candidate) == 3 \
       and all(isinstance(row, (list, tuple)) and len(row) == 3 for row in matrix_candidate):
        try:
            nested = [[float(matrix_candidate[i][j]) for j in range(3)] for i in range(3)]
            return Matrix3x3Widget(default=nested, parent=parent)
        except Exception:
            # Something was not numeric; fall through to zeros
            pass

    # 7) Fallback: anything else → blank (all‐zeros) widget
    return Matrix3x3Widget(parent=parent)


class BoolWidget(QCheckBox):
    def __init__(self, fieldName, default=False, parent=None):
        label = "Show" if fieldName.lower() == "show" else fieldName
        super().__init__(label, parent)
        self.setChecked(bool(default))

    def getValue(self):
        return self.isChecked()
    
def buildBoolWidget(fieldName, value=None, parent=None, meta=None, default=None, **kwargs):
    return BoolWidget(fieldName, default=default, parent=parent)



class EnhancedVector3Widget(QWidget):
    valueChanged = pyqtSignal()

    def __init__(self, default=None, parent=None, symbolDict=None):
        super().__init__(parent)
        self.symbolDict = symbolDict or {}

        # ─── Build layout ─────────────────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 1) Three spin‐boxes on top (always enabled)
        self.vectorWidget = Vector3Widget(default=default, parent=parent)
        layout.addWidget(self.vectorWidget)

        # 2) Expression‐box below, start "read‐only gray"
        self.exprField = QLineEdit()
        self.exprField.setPlaceholderText("Type vector expression, e.g. [l, 0, 0]")

        # Make it read‐only so it looks "grayed‐out" but still takes focus
        self.exprField.setReadOnly(True)

        # Give it a gray‐text, gray‐background style
        self.exprField.setStyleSheet("""
            QLineEdit {
                color: gray;
                background-color: #f0f0f0;
            }
        """)
        layout.addWidget(self.exprField)

        # Whenever the user actually types something, we switch to normal mode
        self.exprField.textChanged.connect(self._onTextChanged)

        # ─── Install an event filter so we catch FocusIn and FocusOut on exprField ─
        self.exprField.installEventFilter(self)

    def eventFilter(self, obj, event):
        """
        Catch FocusIn on exprField → make it editable;
        Catch FocusOut on exprField → if text is still empty, revert to read‐only gray.
        """
        if obj is self.exprField:
            # 1) When exprField receives focus: clear read‐only gray style
            if event.type() == QEvent.FocusIn:
                if self.exprField.isReadOnly():
                    self.exprField.setReadOnly(False)
                    self.exprField.setStyleSheet("")  # back to default look
                return False  # let Qt continue handling focus

            # 2) When exprField loses focus: if its text is empty, revert to read‐only gray
            if event.type() == QEvent.FocusOut:
                txt = self.exprField.text().strip()
                if txt == "":
                    # Put it back into read‐only gray mode
                    self.exprField.setReadOnly(True)
                    self.exprField.setStyleSheet("""
                        QLineEdit {
                            color: gray;
                            background-color: #f0f0f0;
                        }
                    """)
                return False  # let Qt continue handling focusOut

        # For all other events / objects, fallback to default:
        return super().eventFilter(obj, event)

    def _onTextChanged(self, text):
        """
        Once the user types something (i.e. textChanged fires),
        ensure the field remains editable and disable spin‐boxes if valid.
        """
        if self.exprField.isReadOnly():
            # In case textChanged came in before we switched off readOnly, do it now:
            self.exprField.setReadOnly(False)
            self.exprField.setStyleSheet("")

        stripped = text.strip()
        if stripped == "":
            # If the expression is now empty, re‐enable spin‐boxes:
            self.vectorWidget.setEnabled(True)
            return

        try:
            val = evaluateExpression(stripped, self.symbolDict)
            if isinstance(val, list) and len(val) == 3:
                # Valid 3D vector → disable spin‐boxes
                self.vectorWidget.setEnabled(False)
                self.exprField.setToolTip(f"✅ Resolved to: {val}")
            else:
                raise ValueError("Not a 3D vector")
        except Exception as e:
            # Invalid expression → highlight red background
            self.exprField.setToolTip(f"❌ {e}")
            self.exprField.setStyleSheet("background-color: #ffe0e0;")
            self.vectorWidget.setEnabled(False)

    def getValue(self):
        """
        If the user provided a non‐empty expression, evaluate it;
        otherwise, return the three spin‐box values.
        """
        txt = self.exprField.text().strip()
        if txt:
            try:
                return evaluateExpression(txt, self.symbolDict)
            except:
                pass
        return self.vectorWidget.getValue()






class Vector3Widget(QWidget):
    valueChanged = pyqtSignal()  # ✅ Add this line

    def __init__(self, default=[0.0, 0.0, 0.0], parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.spinBoxes = []
        for i in range(3):
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(-1e12, 1e12)
            spin.setSingleStep(0.1)
            if isinstance(default, list) and i < len(default):
                spin.setValue(float(default[i]))
            layout.addWidget(spin)
            spin.valueChanged.connect(self.valueChanged.emit)  # ✅ Connect signal
            self.spinBoxes.append(spin)

        self.fieldType = "vector3"

    def getValue(self):
        return [sb.value() for sb in self.spinBoxes]

def buildVec3Widget(fieldName, value=None, parent=None, meta=None, default=None, **kwargs):
    variables = kwargs.get("userVariables", {})
    initial = value if value not in (None, '') else default
    return EnhancedVector3Widget(default=initial, parent=parent, symbolDict=variables)




# --- Node/Body/Marker Selectors ---
from PyQt5.QtWidgets import QComboBox

def setComboBoxIndex(combo, value):
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)



def buildNodeNumberWidget(fieldName, value=None, parent=None, meta=None, default=None, **kwargs):
    structure = kwargs.get("structure", None)
    combo = QComboBox()
    combo.setEditable(True)

    defaultIndex = None
    if isinstance(default, int):
        defaultIndex = default
    elif isinstance(default, str):
        try:
            defaultIndex = int(default.split()[0])
        except:
            pass

    addedIndices = set()
    if structure:
        allNodes = structure.get('nodes', [])
        for node in allNodes:
            idx = node['index']
            label = node.get('label', f"Node_{idx}")
            display = f"{idx} - {label}"
            combo.addItem(display, userData=idx)
            addedIndices.add(idx)

    if defaultIndex is not None and defaultIndex not in addedIndices:
        combo.addItem(f"{defaultIndex} - (unknown)", userData=defaultIndex)

    if defaultIndex is not None:
        idx = combo.findData(defaultIndex)
        if idx != -1:
            combo.setCurrentIndex(idx)

    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(combo)

    container.combo = combo
    container.fieldType = "nodeNumber"
    container.getValue = lambda: combo.currentData()
    return container







def buildBodyNumberWidget(fieldName, value=None, parent=None, meta=None, default=None, **kwargs):
    structure = kwargs.get("structure", None)
    combo = QComboBox()
    combo.setEditable(True)

    defaultIndex = None
    if isinstance(default, int):
        defaultIndex = default
    elif isinstance(default, str):
        try:
            defaultIndex = int(default.split()[0])
        except:
            pass

    addedIndices = set()
    if structure:
        allObjects = structure.get('objects', [])
        for obj in allObjects:
            if not str(obj['data'].get('objectType', '')).startswith("Ground"):
                idx = obj['index']
                label = obj.get('label', f"Object_{idx}")
                display = f"{idx} - {label}"
                combo.addItem(display, userData=idx)
                addedIndices.add(idx)

    # 🔧 Add placeholder if missing
    if defaultIndex is not None and defaultIndex not in addedIndices:
        combo.addItem(f"{defaultIndex} - (unknown)", userData=defaultIndex)    # 🧠 Restore selection
    if defaultIndex is not None:
        idx = combo.findData(defaultIndex)
        if idx != -1:
            combo.setCurrentIndex(idx)
    
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(combo)

    # Toggle Highlight button
    from PyQt5.QtWidgets import QPushButton
    highlightBtn = QPushButton("Highlight")
    highlightBtn.setToolTip("Highlight selected body in the OpenGL window")
    highlightBtn.setMaximumWidth(80)
    highlightBtn.setCheckable(True)
    layout.addWidget(highlightBtn)

    # Persistent slot for connection/disconnection
    def do_highlight():
        selected_index = combo.currentData()
        setupRendererHighlighting(parent, selected_index)

    def clear_highlight():
        SC = None
        if hasattr(parent, 'SC') and parent.SC:
            SC = parent.SC
        elif hasattr(parent, 'parent') and parent.parent and hasattr(parent.parent, 'SC'):
            SC = parent.parent.SC
        if SC and hasattr(SC, 'visualizationSettings') and hasattr(SC.visualizationSettings, 'interactive'):
            from exudyn import ItemType
            SC.visualizationSettings.interactive.highlightItemType = ItemType._None
            SC.visualizationSettings.interactive.highlightItemIndex = -1
            if hasattr(parent, '_refreshOpenGLRenderer'):
                parent._refreshOpenGLRenderer()
            elif hasattr(parent, 'parent') and hasattr(parent.parent, '_refreshOpenGLRenderer'):
                parent.parent._refreshOpenGLRenderer()

    def on_combo_changed():
        if highlightBtn.isChecked():
            do_highlight()

    def on_highlight_toggled(checked):
        if checked:
            do_highlight()
            combo.currentIndexChanged.connect(on_combo_changed)
        else:
            try:
                combo.currentIndexChanged.disconnect(on_combo_changed)
            except Exception:
                pass
            setupRendererHighlighting(parent, None)

    highlightBtn.toggled.connect(on_highlight_toggled)

    container.combo = combo
    container.fieldType = "bodyNumber"
    container.getValue = lambda: combo.currentData()
    container.highlightBtn = highlightBtn
    container._clear_highlight = clear_highlight  # for form close/reject
    return container



def buildMarkerPairSelectorWidget(fieldName, value=None, parent=None, meta=None, default=None, **kwargs):
    debugLog("[DEBUG] 🔥 buildMarkerPairSelectorWidget called!")
    structure = kwargs.get("structure", None)
    markerList = structure.get('markers', []) if structure else []

    default0 = (default[0] if isinstance(default, list) and len(default) > 0 else None)
    default1 = (default[1] if isinstance(default, list) and len(default) > 1 else None)

    combo1 = QComboBox()
    combo2 = QComboBox()

    def populateCombo(combo, selected):
        addedIndices = set()
        for marker in markerList:
            idx = marker['index']
            label = marker.get('label', f"Marker_{idx}")
            combo.addItem(f"{idx} - {label}", userData=idx)
            addedIndices.add(idx)

        if selected is not None and selected not in addedIndices:
            combo.addItem(f"{selected} - (unknown)", userData=selected)

        if selected is not None:
            i = combo.findData(selected)
            if i >= 0:
                combo.setCurrentIndex(i)

    populateCombo(combo1, default0)
    populateCombo(combo2, default1)

    # Assemble container
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(combo1)
    layout.addWidget(combo2)

    container.combo1 = combo1
    container.combo2 = combo2
    container.fieldType = "markerNumbers"
    container.getValue = lambda: [combo1.currentData(), combo2.currentData()]
    return container




def buildMarkerNumberWidget(fieldName, value=None, parent=None, meta=None, default=None, **kwargs):
    structure = kwargs.get("structure", None)
    combo = QComboBox()
    combo.setEditable(True)

    defaultIndex = None
    if isinstance(default, int):
        defaultIndex = default
    elif isinstance(default, str):
        try:
            defaultIndex = int(default.split()[0])
        except:
            pass

    addedIndices = set()
    if structure:
        allMarkers = structure.get('markers', [])
        for marker in allMarkers:
            idx = marker['index']
            label = marker.get('label', f"Marker_{idx}")
            display = f"{idx} - {label}"
            combo.addItem(display, userData=idx)
            addedIndices.add(idx)

    if defaultIndex is not None and defaultIndex not in addedIndices:
        combo.addItem(f"{defaultIndex} - (unknown)", userData=defaultIndex)

    if defaultIndex is not None:
        idx = combo.findData(defaultIndex)
        if idx != -1:
            combo.setCurrentIndex(idx)

    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(combo)

    container.combo = combo
    container.fieldType = "markerNumber"
    container.getValue = lambda: combo.currentData()
    return container


def buildSensorNumberWidget(fieldName, value=None, default=None, meta=None, parent=None, structure=None, **kwargs):
    combo = QComboBox(parent)
    items = structure.getAvailableSensors() if structure else []
    for idx, label, typ in items:
        combo.addItem(f"[{idx}] {label} ({typ})", idx)
    
    selected = value if value is not None else default
    setComboBoxIndex(combo, selected)
    return combo

def buildLoadNumberWidget(fieldName, default, meta, parent=None, structure=None, **kwargs):
    combo = QComboBox(parent)
    items = structure.getAvailableItems("load") if structure else []
    for idx, label, typ in items:
        combo.addItem(f"[{idx}] {label} ({typ})", idx)
    
    selected = value if value is not None else default
    setComboBoxIndex(combo, selected)
    return combo


class Int3Widget(QWidget):
    """
    A simple 3‐element integer row. Uses three QSpinBox for
    picking integers. Default values come from a length‐3 list, if provided.
    """
    valueChanged = pyqtSignal()

    def __init__(self, default=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.spinBoxes = []
        for i in range(3):
            spin = QSpinBox()
            spin.setRange(-999999, 999999)
            if isinstance(default, (list, tuple)) and len(default) == 3:
                try:
                    spin.setValue(int(default[i]))
                except:
                    spin.setValue(0)
            layout.addWidget(spin)
            spin.valueChanged.connect(self.valueChanged.emit)
            self.spinBoxes.append(spin)

        self.fieldType = "int3"

    def getValue(self):
        return [sb.value() for sb in self.spinBoxes]


class EnhancedInt3Widget(QWidget):
    """
    Like EnhancedVector3Widget, but for three integers.
    Top row: QLineEdit (allows expressions like [0, k, 1]).
    Bottom row: an Int3Widget (three spinboxes).
    If the expression parses to [int, int, int], disables spinboxes.
    Otherwise disables spinboxes until the expression is clear.
    """
    valueChanged = pyqtSignal()

    def __init__(self, default=None, parent=None, symbolDict=None):
        super().__init__(parent)
        self.symbolDict = symbolDict or {}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.exprField = QLineEdit()
        self.exprField.setPlaceholderText("Type integer-vector expression, e.g. [1, 0, k]")
        outer.addWidget(self.exprField)

        prefill = None
        if isinstance(default, (list, tuple)) and len(default) == 3:
            try:
                prefill = [int(default[i]) for i in range(3)]
            except:
                prefill = None

        self.int3Widget = Int3Widget(default=prefill, parent=parent)
        outer.addWidget(self.int3Widget)

        self.exprField.textChanged.connect(self.onTextChanged)
        self.int3Widget.valueChanged.connect(self.onSpinChanged)

    def onSpinChanged(self):
        # If they clicked a spinbox, clear out any expression on top
        if self.exprField.text().strip() != "":
            self.exprField.blockSignals(True)
            self.exprField.clear()
            self.exprField.blockSignals(False)
        self.valueChanged.emit()

    def onTextChanged(self, text):
        text = text.strip()
        if not text:
            self.int3Widget.setEnabled(True)
            return

        try:
            from ..core.fieldValidation import evaluateExpression
            candidate = evaluateExpression(text, self.symbolDict)
            if (
                isinstance(candidate, (list, tuple))
                and len(candidate) == 3
                and all(isinstance(x, int) for x in candidate)
            ):
                self.int3Widget.setEnabled(False)
                self.exprField.setToolTip(f"✅ Resolved to: {candidate}")
            else:
                raise ValueError("Not a 3-element int list")
        except Exception as e:
            self.int3Widget.setEnabled(False)
            self.exprField.setToolTip(f"❌ {e}")
            self.exprField.setStyleSheet("background-color: #ffe0e0;")

        self.valueChanged.emit()

    def getValue(self):
        text = self.exprField.text().strip()
        if text:
            try:
                from ..core.fieldValidation import evaluateExpression
                candidate = evaluateExpression(text, self.symbolDict)
                if (
                    isinstance(candidate, (list, tuple))
                    and len(candidate) == 3
                    and all(isinstance(x, int) for x in candidate)
                ):
                    return [int(candidate[i]) for i in range(3)]
            except:
                pass
        return self.int3Widget.getValue()


def buildInt3Widget(fieldName, default=None, meta=None, parent=None, structure=None, **kwargs):
    """
    Called by specialFields.dispatchSpecialFieldBuilder whenever
    typeHint contains 'IntVector'+'3'. We simply hand off to
    EnhancedInt3Widget so that users can type either [1,2,3] or pick
    3 spinboxes.
    """
    return EnhancedInt3Widget(
        default=default,
        parent=parent,
        symbolDict=kwargs.get("userVariables", {})
    )


class MultiComponentSelectorWidget(QWidget):
    def __init__(self, fieldName, default, meta, parent=None, structure=None):
        super().__init__(parent)
        self.fieldType = "multiComponent"
        self.label = QLabel(fieldName)
        self.listWidget = QListWidget()

        # Ensure multi-selection
        self.listWidget.setSelectionMode(QAbstractItemView.MultiSelection)

        # Populate the list if structure is provided
        self.structure = structure or {}
        self.group = self.inferGroupFromField(fieldName)

        items = self.structure.get(self.group, [])
        for idx in items:
            item = QListWidgetItem(f"[{self.group[:-1]} {idx}]")
            item.setData(Qt.UserRole, idx)
            self.listWidget.addItem(item)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.listWidget)
        self.setLayout(layout)

        # Preselect defaults if applicable
        if isinstance(default, list):
            self.setSelectedIndices(default)

    def inferGroupFromField(self, fieldName):
        """Heuristically maps field name to group type (objects, nodes, etc)."""
        if "node" in fieldName.lower():
            return "nodes"
        if "object" in fieldName.lower() or "body" in fieldName.lower():
            return "objects"
        if "marker" in fieldName.lower():
            return "markers"
        if "sensor" in fieldName.lower():
            return "sensors"
        if "load" in fieldName.lower():
            return "loads"
        return "objects"  # fallback

    def getSelectedIndices(self):
        return [item.data(Qt.UserRole) for item in self.listWidget.selectedItems()]

    def setSelectedIndices(self, indices):
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if item.data(Qt.UserRole) in indices:
                item.setSelected(True)
            else:
                item.setSelected(False)

class EnhancedIntNWidget(QWidget):
    """
    A widget for an N-element integer vector.
    - Top: a QLineEdit for literal entry like "[1,0,1,0,1,0]"
    - Bottom: N QSpinBoxes (each ∈ ℤ, default from input)
    """
    valueChanged = pyqtSignal()

    def __init__(self, N=6, default=None, parent=None):
        super().__init__(parent)
        self.N = N
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)

        # 1) Expression line edit
        self.exprField = QLineEdit()
        self.exprField.setPlaceholderText(f"Type int{N} list, e.g. {[1]*N}")
        if isinstance(default, (list, tuple)) and len(default) == N:
            self.exprField.setText(str(default))
        else:
            self.exprField.setText(str([1]*N))
        self.layout.addWidget(self.exprField)

        # 2) N spin boxes
        self.spinBoxes = []
        spinRow = QWidget()
        h = QHBoxLayout(spinRow)
        h.setContentsMargins(0,0,0,0)
        for i in range(N):
            sb = QSpinBox()
            sb.setRange(-9999, 9999)
            if isinstance(default, (list,tuple)) and len(default)==N:
                sb.setValue(default[i])
            else:
                sb.setValue(1)
            sb.valueChanged.connect(self._onSpinChanged)
            h.addWidget(sb)
            self.spinBoxes.append(sb)
        self.layout.addWidget(spinRow)

        self.exprField.textChanged.connect(self._onExprChanged)

    def _onSpinChanged(self, newVal):
        arr = [sb.value() for sb in self.spinBoxes]
        self.exprField.setText(str(arr))
        self.valueChanged.emit()

    def _onExprChanged(self, text):
        txt = text.strip()
        if txt.startswith("[") and txt.endswith("]"):
            try:
                candidate = eval(txt, {}, {})
                if isinstance(candidate, (list,tuple)) and len(candidate)==self.N and all(isinstance(x,int) for x in candidate):
                    for i,sb in enumerate(self.spinBoxes):
                        sb.setValue(candidate[i])
                    self.exprField.setStyleSheet("")
                    self.valueChanged.emit()
                    return
            except Exception:
                pass
        self.exprField.setStyleSheet("background-color: #ffdddd;")

    def getValue(self):
        txt = self.exprField.text().strip()
        if txt.startswith("[") and txt.endswith("]"):
            try:
                candidate = eval(txt, {}, {})
                if isinstance(candidate, (list,tuple)) and len(candidate)==self.N and all(isinstance(x,int) for x in candidate):
                    return candidate
            except:
                pass
        return [sb.value() for sb in self.spinBoxes]

def buildIntNWidget(fieldName, default=None, meta=None, parent=None, structure=None, N=6):
    d = default if (isinstance(default, list) and len(default)==N) else [1]*N
    return EnhancedIntNWidget(N=N, default=d, parent=parent)

def buildMatrix6x6Widget(fieldName, value=None, parent=None, meta=None, default=None, **kwargs):
    # Widget for editing a 6x6 matrix (list of lists or np.array)
    import numpy as np
    container = QWidget(parent)
    layout = QGridLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    spinBoxes = []
    # Use default or zeros
    arr = np.zeros((6,6))
    if default is not None:
        try:
            arr = np.array(default, dtype=float)
            if arr.shape != (6,6):
                arr = np.zeros((6,6))
        except Exception:
            arr = np.zeros((6,6))
    for i in range(6):
        row = []
        for j in range(6):
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(-1e12, 1e12)
            spin.setSingleStep(0.1)
            spin.setValue(float(arr[i][j]))
            layout.addWidget(spin, i, j)
            row.append(spin)
        spinBoxes.append(row)
    container.spinBoxes = spinBoxes
    container.fieldType = "matrix6x6"
    def getValue():
        return [[sb.value() for sb in row] for row in spinBoxes]
    container.getValue = getValue
    return container


class Vector6Widget(QWidget):
    valueChanged = pyqtSignal()
    def __init__(self, default=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.spinBoxes = []
        for i in range(6):
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(-1e12, 1e12)
            spin.setSingleStep(0.1)
            if isinstance(default, list) and i < len(default):
                spin.setValue(float(default[i]))
            layout.addWidget(spin)
            spin.valueChanged.connect(self.valueChanged.emit)
            self.spinBoxes.append(spin)
        self.fieldType = "vector6"
    def getValue(self):
        return [sb.value() for sb in self.spinBoxes]

class EnhancedVector6Widget(QWidget):
    valueChanged = pyqtSignal()
    def __init__(self, default=None, parent=None, symbolDict=None):
        super().__init__(parent)
        self.symbolDict = symbolDict or {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.vectorWidget = Vector6Widget(default=default, parent=parent)
        layout.addWidget(self.vectorWidget)
        self.exprField = QLineEdit()
        self.exprField.setPlaceholderText("Type 6D vector expression, e.g. [l, 0, 0, 0, 0, 0]")
        self.exprField.setReadOnly(True)
        self.exprField.setStyleSheet("""
            QLineEdit {
                color: gray;
                background-color: #f0f0f0;
            }
        """)
        layout.addWidget(self.exprField)
        self.exprField.textChanged.connect(self._onTextChanged)
        self.exprField.installEventFilter(self)
    def eventFilter(self, obj, event):
        if obj is self.exprField:
            if event.type() == QEvent.FocusIn:
                if self.exprField.isReadOnly():
                    self.exprField.setReadOnly(False)
                    self.exprField.setStyleSheet("")
                return False
            if event.type() == QEvent.FocusOut:
                txt = self.exprField.text().strip()
                if txt == "":
                    self.exprField.setReadOnly(True)
                    self.exprField.setStyleSheet("""
                        QLineEdit {
                            color: gray;
                            background-color: #f0f0f0;
                        }
                    """)
                return False
        return super().eventFilter(obj, event)
    def _onTextChanged(self, text):
        if self.exprField.isReadOnly():
            self.exprField.setReadOnly(False)
            self.exprField.setStyleSheet("")
        stripped = text.strip()
        if stripped == "":
            self.vectorWidget.setEnabled(True)
            return
        try:
            from ..core.fieldValidation import evaluateExpression
            val = evaluateExpression(stripped, self.symbolDict)
            if isinstance(val, list) and len(val) == 6:
                self.vectorWidget.setEnabled(False)
                self.exprField.setToolTip(f"✅ Resolved to: {val}")
            else:
                raise ValueError("Not a 6D vector")
        except Exception as e:
            self.exprField.setToolTip(f"❌ {e}")
            self.exprField.setStyleSheet("background-color: #ffe0e0;")
            self.vectorWidget.setEnabled(False)
    def getValue(self):
        txt = self.exprField.text().strip()
        if txt:
            try:
                from ..core.fieldValidation import evaluateExpression
                return evaluateExpression(txt, self.symbolDict)
            except:
                pass
        return self.vectorWidget.getValue()

def buildVec6Widget(fieldName, value=None, parent=None, meta=None, default=None, **kwargs):
    variables = kwargs.get("userVariables", {})
    initial = value if value not in (None, '') else default
    return EnhancedVector6Widget(default=initial, parent=parent, symbolDict=variables)

# --- File browser widget for file paths ---
class FileBrowserWidget(QWidget):
    """Widget with line edit and browse button for file selection"""
    
    def __init__(self, default_value="", file_filter="All Files (*)", parent=None):
        super().__init__(parent)
        self.file_filter = file_filter
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Line edit for file path
        self.lineEdit = QLineEdit()
        self.lineEdit.setText(str(default_value))
        layout.addWidget(self.lineEdit)
        
        # Browse button
        self.browseButton = QPushButton("Browse...")
        self.browseButton.setFixedWidth(80)
        self.browseButton.clicked.connect(self._browse)
        layout.addWidget(self.browseButton)
    
    def _browse(self):
        """Open file dialog to select a file"""
        from PyQt5.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getOpenFileName(
            self, 
            "Select File", 
            self.lineEdit.text(), 
            self.file_filter        )
        if filename:
            self.lineEdit.setText(filename)
    
    def text(self):
        """Get the current file path as a quoted string for constructor dialog"""
        path = self.lineEdit.text()
        if path:
            # Use repr() for proper escaping of backslashes and quotes
            return repr(path)
        return "''"
    
    def setText(self, text):
        """Set the file path"""
        self.lineEdit.setText(text)

def buildFileBrowserWidget(fieldName, value=None, parent=None, meta=None, default="", file_filter="All Files (*)", **kwargs):
    """Build a file browser widget for file path selection"""
    if value is None:
        value = default
    
    # Determine file filter based on field name
    field_lower = fieldName.lower()
    if 'stl' in field_lower or field_lower == 'filename':
        if 'stl' in field_lower:
            file_filter = "STL Files (*.stl);;All Files (*)"
        else:
            file_filter = "STL Files (*.stl);;Text Files (*.txt);;All Files (*)"
    
    widget = FileBrowserWidget(default_value=str(value), file_filter=file_filter, parent=parent)
    return widget

# --- Vector3D widget for 3D offsets ---
class Vector3DWidget(QWidget):
    """Widget for editing 3D vectors (position offsets, etc.)"""
    
    def __init__(self, default_value=[0.0, 0.0, 0.0], parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
          # Parse default value
        if isinstance(default_value, str):
            try:
                default_value = ast.literal_eval(default_value)
            except:
                default_value = [0.0, 0.0, 0.0]
        
        # Handle numpy arrays properly
        import numpy as np
        if isinstance(default_value, np.ndarray):
            if default_value.shape == (3,):
                default_value = default_value.tolist()
            else:
                default_value = [0.0, 0.0, 0.0]
        elif not isinstance(default_value, (list, tuple)):
            default_value = [0.0, 0.0, 0.0]
        elif len(default_value) != 3:
            default_value = [0.0, 0.0, 0.0]
        
        # Create three spin boxes for x, y, z
        self.spinBoxes = []
        labels = ['X:', 'Y:', 'Z:']
        for i, label in enumerate(labels):
            layout.addWidget(QLabel(label))
            spinBox = QDoubleSpinBox()
            spinBox.setDecimals(6)
            spinBox.setRange(-999999.0, 999999.0)
            spinBox.setValue(float(default_value[i]))
            spinBox.setFixedWidth(80)
            layout.addWidget(spinBox)
            self.spinBoxes.append(spinBox)
    
    def text(self):
        """Get the current vector as a string representation"""
        values = [spinBox.value() for spinBox in self.spinBoxes]
        return str(values)
    
    def setText(self, text):
        """Set the vector from a string representation"""
        try:
            values = ast.literal_eval(text)
            if isinstance(values, (list, tuple)) and len(values) == 3:
                for i, spinBox in enumerate(self.spinBoxes):
                    spinBox.setValue(float(values[i]))
        except:
            pass

def buildVector3DWidget(fieldName, value=None, parent=None, meta=None, default=[0.0, 0.0, 0.0], **kwargs):
    """Build a 3D vector widget for position/rotation offsets"""
    # Handle None values properly
    if value is None:
        value = default
    
    widget = Vector3DWidget(default_value=value, parent=parent)
    return widget

# --- Matrix3x3 widget for rotation matrices ---
# Removed duplicate basic Matrix3x3Widget - using the advanced version with presets instead

# --- Enhanced rotation widget specifically for STL file positioning ---
class STLRotationWidget(QWidget):
    """User-friendly rotation widget for STL file positioning using Euler angles"""
    
    def __init__(self, default_value=None, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("Rotation (degrees)")
        title.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(title)
        
        # Euler angle inputs (more intuitive for users)
        angles_layout = QHBoxLayout()
        
        # X, Y, Z rotation angles
        self.angleSpinBoxes = []
        labels = ['X-axis:', 'Y-axis:', 'Z-axis:']
        
        for i, label in enumerate(labels):
            angles_layout.addWidget(QLabel(label))
            spinBox = QDoubleSpinBox()
            spinBox.setDecimals(1)
            spinBox.setRange(-360.0, 360.0)
            spinBox.setValue(0.0)
            spinBox.setSuffix("°")
            spinBox.setFixedWidth(80)
            spinBox.valueChanged.connect(self._updateMatrix)
            angles_layout.addWidget(spinBox)
            self.angleSpinBoxes.append(spinBox)
        
        layout.addLayout(angles_layout)
        
        # Quick rotation buttons
        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("Quick rotations:"))
        
        quick_buttons = [
            ("0°", [0, 0, 0]),
            ("90° Z", [0, 0, 90]),
            ("180° Z", [0, 0, 180]),
            ("90° Y", [0, 90, 0]),
            ("90° X", [90, 0, 0])
        ]
        
        for label, angles in quick_buttons:
            btn = QPushButton(label)
            btn.setFixedWidth(60)
            btn.clicked.connect(lambda checked, a=angles: self._setAngles(a))
            quick_layout.addWidget(btn)
        
        layout.addLayout(quick_layout)
        
        # Matrix display (read-only, for verification)
        matrix_label = QLabel("Resulting rotation matrix:")
        matrix_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(matrix_label)
        
        self.matrixDisplay = QLabel()
        self.matrixDisplay.setStyleSheet("""
            background-color: #f0f0f0; 
            border: 1px solid #ccc; 
            padding: 5px; 
            font-family: monospace; 
            font-size: 9pt;
        """)
        self.matrixDisplay.setWordWrap(True)
        layout.addWidget(self.matrixDisplay)
        
        # Initialize with default value
        if default_value:
            self._setFromMatrix(default_value)
        else:
            self._updateMatrix()
    
    def _setAngles(self, angles):
        """Set the Euler angles"""
        for i, angle in enumerate(angles):
            self.angleSpinBoxes[i].setValue(angle)
    
    def _updateMatrix(self):
        """Update the matrix display when angles change"""
        try:
            import numpy as np
            import exudyn.utilities as exuutils
            
            # Get angles in radians
            x_rad = np.radians(self.angleSpinBoxes[0].value())
            y_rad = np.radians(self.angleSpinBoxes[1].value())
            z_rad = np.radians(self.angleSpinBoxes[2].value())
            
            # Create rotation matrix (ZYX order - common for orientation)
            matrix = exuutils.RotXYZ2RotationMatrix([x_rad, y_rad, z_rad])
            
            # Display the matrix
            self._displayMatrix(matrix)
            
        except Exception as e:
            self.matrixDisplay.setText(f"Error: {e}")
    
    def _displayMatrix(self, matrix):
        """Display the rotation matrix in a readable format"""
        if isinstance(matrix, np.ndarray):
            matrix = matrix.tolist()
        
        # Format matrix with proper alignment
        lines = []
        for row in matrix:
            formatted_row = "[" + ", ".join(f"{val:8.4f}" for val in row) + "]"
            lines.append(formatted_row)
        
        matrix_text = "[\n  " + ",\n  ".join(lines) + "\n]"
        self.matrixDisplay.setText(matrix_text)
    
    def _setFromMatrix(self, matrix_value):
        """Set the spin-boxes from a rotation matrix by decomposing to RotXYZ angles."""
        try:
            import numpy as np
            import exudyn.utilities as exuutils

            # if string, parse it
            if isinstance(matrix_value, str):
                import ast
                matrix_value = ast.literal_eval(matrix_value)

            # ensure ndarray
            M = np.array(matrix_value, dtype=float)

            # decompose to [rotX, rotY, rotZ] in radians
            rot = exuutils.RotationMatrix2RotXYZ(M)  

            # convert to degrees and populate spin-boxes
            deg = np.degrees(rot)
            for i, angle in enumerate(deg):
                self.angleSpinBoxes[i].setValue(angle)

            # update the matrix display
            self._updateMatrix()

        except Exception as e:
            # fallback: leave default and show error matrix
            self._displayMatrix(np.eye(3))
            debugLog(f"STLRotationWidget: failed to decompose matrix: {e}")
    
    def text(self):
        """Get the current rotation matrix as a string"""
        try:
            return str(self.getMatrix().tolist())
        except Exception:
            return "[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]"

    def getMatrix(self):
        """Compute and return the 3×3 rotation matrix as an ndarray."""
        import numpy as np
        import exudyn.utilities as exuutils

        x_rad = np.radians(self.angleSpinBoxes[0].value())
        y_rad = np.radians(self.angleSpinBoxes[1].value())
        z_rad = np.radians(self.angleSpinBoxes[2].value())

        # Build individual rotations
        rx = exuutils.RotationMatrixX(x_rad)
        ry = exuutils.RotationMatrixY(y_rad)
        rz = exuutils.RotationMatrixZ(z_rad)

        # Combined Z * Y * X
        return rz @ ry @ rx

# --- Color Widget for RGBA color fields ---
class ColorWidget(QWidget):
    """Advanced color picker widget for RGBA color values"""
    
    valueChanged = pyqtSignal()
    
    def __init__(self, default=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(200)  # Set a reasonable height for the widget
        
        # Parse default color
        if isinstance(default, list) and len(default) >=  3:
            self.color = default[:4] if len(default) >= 4 else default + [1.0]
        elif isinstance(default, str):
            try:
                # Try to parse string like "[0.5, 0.5, 0.5, 1.0]"
                import ast
                parsed = ast.literal_eval(default)
                if isinstance(parsed, list) and len(parsed) >= 3:
                    self.color = parsed[:4] if len(parsed) >= 4 else parsed + [1.0]
                else:
                    self.color = [0.5, 0.5, 0.5, 1.0]
            except:
                self.color = [0.5, 0.5, 0.5, 1.0]
        else:
            self.color = [0.5, 0.5, 0.5, 1.0]
        
        # Ensure color values are in [0, 1] range
        self.color = [max(0.0, min(1.0, float(c))) for c in self.color]
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Color preview
        self.colorPreview = QLabel()
        self.colorPreview.setFixedHeight(30)
        self.colorPreview.setStyleSheet("border: 1px solid gray;")
        layout.addWidget(self.colorPreview)
        
        # RGB sliders
        sliders_layout = QVBoxLayout()
        
        # Create sliders for R, G, B, A
        self.sliders = {}
        self.spinboxes = {}
        labels = ['R', 'G', 'B', 'A']
        colors = ['Red', 'Green', 'Blue', 'Alpha']
        
        for i, (label, color_name) in enumerate(zip(labels, colors)):
            # Container for each color component
            row_layout = QHBoxLayout()
            
            # Label
            label_widget = QLabel(f"{label}:")
            label_widget.setFixedWidth(20)
            row_layout.addWidget(label_widget)
            
            # Slider
            slider = QDoubleSpinBox()
            slider.setRange(0.0, 1.0)
            slider.setDecimals(3)
            slider.setSingleStep(0.01)
            slider.setValue(self.color[i])
            slider.valueChanged.connect(lambda val, idx=i: self.updateColorFromSpinbox(idx, val))
            self.spinboxes[label] = slider
            row_layout.addWidget(slider)
            
            sliders_layout.addLayout(row_layout)
        
        layout.addLayout(sliders_layout)
        
        # Preset colors section
        presets_layout = QHBoxLayout()
        presets_layout.addWidget(QLabel("Presets:"))
        
        # Common color presets
        preset_colors = [
            ("Red", [1.0, 0.0, 0.0, 1.0]),
            ("Green", [0.0, 1.0, 0.0, 1.0]),
            ("Blue", [0.0, 0.0, 1.0, 1.0]),
            ("Yellow", [1.0, 1.0, 0.0, 1.0]),
            ("Cyan", [0.0, 1.0, 1.0, 1.0]),
            ("Magenta", [1.0, 0.0, 1.0, 1.0]),
            ("White", [1.0, 1.0, 1.0, 1.0]),
            ("Black", [0.0, 0.0, 0.0, 1.0]),
            ("Gray", [0.5, 0.5, 0.5, 1.0])
        ]
        
        for name, color in preset_colors:
            btn = QPushButton(name)
            btn.setMaximumWidth(60)
            btn.clicked.connect(lambda checked, c=color: self.setColor(c))
            presets_layout.addWidget(btn)
        
        layout.addLayout(presets_layout)
        
        # Update the preview
        self.updatePreview()
        
        self.fieldType = "color"
    
    def updateColorFromSpinbox(self, index, value):
        """Update color when spinbox value changes"""
        self.color[index] = value
        self.updatePreview()
        self.valueChanged.emit()
    
    def setColor(self, color):
        """Set the color and update all controls"""
        if isinstance(color, list) and len(color) >= 3:
            self.color = color[:4] if len(color) >= 4 else color + [1.0]
            # Ensure values are in [0, 1] range
            self.color = [max(0.0, min(1.0, float(c))) for c in self.color]
            
            # Update spinboxes
            labels = ['R', 'G', 'B', 'A']
            for i, label in enumerate(labels):
                self.spinboxes[label].blockSignals(True)
                self.spinboxes[label].setValue(self.color[i])
                self.spinboxes[label].blockSignals(False)
            
            self.updatePreview()
            self.valueChanged.emit()
    
    def updatePreview(self):
        """Update the color preview"""
        # Convert to 0-255 range for Qt
        r, g, b, a = [int(c * 255) for c in self.color]
        self.colorPreview.setStyleSheet(f"""
            background-color: rgba({r}, {g}, {b}, {a});
            border: 1px solid gray;
            border-radius: 3px;
        """)
        self.colorPreview.setText(f"RGBA({r}, {g}, {b}, {a})")
        self.colorPreview.setAlignment(Qt.AlignCenter)
    
    def getValue(self):
        """Return the current color as a list [R, G, B, A]"""
        return self.color.copy()


def buildColorWidget(fieldName, value=None, parent=None, meta=None, default=None, **kwargs):
    """Build a color widget for RGBA color selection"""
    color_value = value if value is not None else (default if default is not None else [0.5, 0.5, 0.5, 1.0])
    return ColorWidget(default=color_value, parent=parent)

def buildOutputVariableTypeWidget(fieldName, default=None, meta=None, parent=None, structure=None, value=None):
    """Build an intelligent widget for selecting OutputVariableType values based on actual object capabilities"""
    # Try to import the robust output discovery functionality
    has_discovery = False
    discover_sensor_body_outputs = None
    discover_sensor_node_outputs = None
    discover_sensor_marker_outputs = None
    try:
        # First try direct relative import
        import sys
        import os

        # Get absolute path to the core directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        core_path = os.path.join(parent_dir, 'core')

        if core_path not in sys.path:
            sys.path.insert(0, core_path)

        # Try import, but handle if not found
        try:
            from outputDiscovery import (
                discover_sensor_body_outputs,
                discover_sensor_node_outputs,
                discover_sensor_marker_outputs,
            )
            has_discovery = True
        except ImportError:
            has_discovery = False
    except Exception:
        has_discovery = False

    def update_output_options():
        """Update the combo box by probing against a fresh save/load cycle."""

        # 1) figure out entity_type & body_number
        body_number = None
        entity_type = 'object'
        if parent and hasattr(parent, 'fields'):
            for fname, fw in parent.fields.items():
                if fname in ('bodyNumber','nodeNumber','markerNumber') and hasattr(fw, 'getValue'):
                    body_number = fw.getValue()
                    if fname == 'nodeNumber':    entity_type = 'node'
                    elif fname == 'markerNumber': entity_type = 'marker'
                    break

        # # 2) save the project
        # tmp = os.path.join(tempfile.gettempdir(), "__sensor_discovery.exu")
    
        # # Climb up from the widget until we find the MainWindow (has saveProject2)
        # mw = parent
        # while mw is not None and not hasattr(mw, "saveProject2"):
        #     mw = mw.parent() if hasattr(mw, "parent") else None
        # # If that failed, try all top-level widgets
        # if mw is None:
        #     from PyQt5.QtWidgets import QApplication
        #     for w in QApplication.instance().topLevelWidgets():
        #         if hasattr(w, "saveProject2"):
        #             mw = w
        #             break
        # if mw is None:
        #     raise RuntimeError("Could not locate MainWindow for saveProject2()")
    
        # mw.saveProject2(tmp)
        # mw.SC.renderer.Stop()
        # # remember current body selection (an integer)
        # prevBody = None
        # try:
        #     prevBody = combo.currentData()
        # except Exception:
        #     pass
   

        from core.outputDiscovery import discover_supported_outputs_via_assembly_test
        try:
            if entity_type in ('object','body'):
                outs = discover_supported_outputs_via_assembly_test('object', body_number or 0, 'SensorBody')
            elif entity_type == 'node':
                outs = discover_supported_outputs_via_assembly_test('node', body_number or 0, 'SensorNode')
            else:
                outs = discover_supported_outputs_via_assembly_test('marker', body_number or 0, 'SensorMarker')

        except Exception:
            # discovery failed → fall back
            #outs = get_supported_outputs_for_entity(entity_type, body_number or 0)
            debugLog("⚠️ [Highlighting] Discovery failed", origin="specialWidgets")

        # finally:
            # always delete the temp file and restore the real project

            # mw.newModel()
            # mw.loadProject2(tmp)
            # mw.solution_viewer.restartRendererDocked()
            # # Re-apply highlight state after renderer restart
            # if hasattr(parent, '_replayHighlightState'):
            #     try:
            #         parent._replayHighlightState()
            #     except Exception as e:
            #         debugLog(f"⚠️ [Highlighting] Failed to replay highlight state after renderer restart: {e}", origin="specialWidgets")

            # from PyQt5.QtCore import QTimer
            # QTimer.singleShot(0, mw.solution_viewer.restartRendererDocked)


            # 3) now that we've reloaded, delete the temp file
            # try: os.remove(tmp)
            # except: pass

        # 4) populate the combo with whatever we got, but remember old selection
        prev = combo.currentData()
        combo.clear()
        for o in outs or []:
            combo.addItem(o, o)

        # 5) restore previous selection if still valid
        if prev is not None:
            idx = combo.findData(prev)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    # Create the combo box
    combo = QComboBox(parent)
    oldValue = value
    # Initial population
    update_output_options()
    # Set up monitoring for body number changes
    def setup_auto_update():
        """Set up auto-update when bodyNumber changes"""
        try:
            if parent and hasattr(parent, 'fields'):
                # Look for bodyNumber widget
                for field_name, field_widget in parent.fields.items():
                    if field_name == 'bodyNumber':
                        if hasattr(field_widget, 'combo') and hasattr(field_widget.combo, 'currentIndexChanged'):
                            # Disconnect first to prevent multiple connections
                            try:
                                field_widget.combo.currentIndexChanged.disconnect(update_output_options)
                            except Exception:
                                pass
                            field_widget.combo.currentIndexChanged.connect(update_output_options)
                        elif hasattr(field_widget, 'bodySelectionChanged'):
                            # Disconnect first to prevent multiple connections
                            try:
                                field_widget.bodySelectionChanged.disconnect(update_output_options)
                            except Exception:
                                pass
                            field_widget.bodySelectionChanged.connect(update_output_options)
                        break

            # Alternative approach: search through all child widgets
            if parent:
                for child in parent.findChildren(QWidget):
                    if hasattr(child, 'fieldType') and child.fieldType == 'bodyNumber':
                        if hasattr(child, 'combo'):
                            # Disconnect first to prevent multiple connections
                            try:
                                child.combo.currentIndexChanged.disconnect(update_output_options)
                            except Exception:
                                pass
                            child.combo.currentIndexChanged.connect(update_output_options)
                            break
        except Exception:
            pass

    try:
        from core.qtImports import QTimer
        QTimer.singleShot(100, setup_auto_update)
    except ImportError:
        setup_auto_update()

    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(combo)

    container.combo = combo
    container.fieldType = "outputVariableType"
    container.getValue = lambda: combo.currentData()
    container.update_options = update_output_options  # Expose for manual updates

    return container
    


def buildConfigurationTypeWidget(fieldName, default=None, meta=None, parent=None, structure=None, value=None):
    """Build a widget for selecting ConfigurationType values"""
    try:
        from core.outputDiscovery import get_all_configuration_types
        config_types = get_all_configuration_types()
    except ImportError:
        # Fallback to common configuration types
        config_types = ['Current', 'Initial', 'Reference', 'Visualization']
    
    combo = QComboBox(parent)
    for config_type in config_types:
        combo.addItem(config_type, config_type)
    
    # Set current value
    selected = value if value is not None else (default if default is not None else 'Current')
    if isinstance(selected, str):
        # Handle string values
        index = combo.findData(selected)
        if index >= 0:
            combo.setCurrentIndex(index)
    
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(combo)
    
    container.combo = combo
    container.fieldType = "configurationType"
    container.getValue = lambda: combo.currentData()
    return container


def buildSmartOutputTypeWidget(fieldName, default=None, meta=None, parent=None, structure=None, value=None):
    """
    Build an intelligent output type widget that shows only supported outputs
    for the referenced entity (when available)
    """
    container = QWidget(parent)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    
    # Output type selection
    output_combo = QComboBox()
    
    # Configuration type selection
    config_combo = QComboBox()
    
    # Try to get smart recommendations if we have context
    output_types = ['Position', 'Velocity', 'Displacement', 'Force']  # Default fallback
    config_types = ['Current', 'Initial', 'Reference']  # Default fallback
    
    try:
        from exudynGUI.core.outputDiscovery import (
            get_all_output_variable_types, 
            get_all_configuration_types
        )
        output_types = get_all_output_variable_types()
        config_types = get_all_configuration_types()
    except ImportError:
        pass
    
    # Populate output types
    for output_type in output_types:
        output_combo.addItem(output_type, output_type)
    
    # Populate configuration types
    for config_type in config_types:
        config_combo.addItem(config_type, config_type)
    
    # Set defaults
    if value and isinstance(value, dict):
        output_val = value.get('outputVariableType', 'Position')
        config_val = value.get('configurationType', 'Current')
    else:
        output_val = default if default else 'Position'
        config_val = 'Current'
    
    # Set current selections
    output_idx = output_combo.findData(output_val)
    if output_idx >= 0:
        output_combo.setCurrentIndex(output_idx)
    
    config_idx = config_combo.findData(config_val)
    if config_idx >= 0:
        config_combo.setCurrentIndex(config_idx)
    
    # Layout
    output_layout = QHBoxLayout()
    output_layout.addWidget(QLabel("Output Type:"))
    output_layout.addWidget(output_combo)
    
    config_layout = QHBoxLayout()
    config_layout.addWidget(QLabel("Configuration:"))
    config_layout.addWidget(config_combo)
    
    layout.addLayout(output_layout)
    layout.addLayout(config_layout)
    
    # Store references
    container.output_combo = output_combo
    container.config_combo = config_combo
    container.fieldType = "smartOutputType"
    
    def get_value():
        return {
            'outputVariableType': output_combo.currentData(),
            'configurationType': config_combo.currentData()
        }
    
    container.getValue = get_value
    return container


def buildFileNameWidget(fieldName, default, meta=None, parent=None, structure=None):
    """Build a widget for fileName fields that allows None/empty values"""
    line_edit = QLineEdit(parent)
    
    if default is not None:
        line_edit.setText(str(default))
    else:
        line_edit.setPlaceholderText("Auto-generated if empty (sensor + outputType)")
    
    # Make it clear this is optional
    line_edit.setToolTip("Leave empty for auto-generated filename based on sensor name and output type")
    
    container = QWidget(parent)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(line_edit)
    
    container.line_edit = line_edit
    container.fieldType = "fileName"
    container.getValue = lambda: line_edit.text().strip() if line_edit.text().strip() else ""
    
    return container

def buildEnhancedSensorWidget(fieldName, default, meta=None, parent=None, structure=None):
    """
    Build an enhanced sensor widget that combines entity selection with smart output types
    This creates a comprehensive sensor configuration widget
    """
    from exudynGUI.core.qtImports import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton, QTextEdit
    
    container = QWidget(parent)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(5, 5, 5, 5)
    
    # Entity Selection Section
    entity_group = QGroupBox("Target Entity")
    entity_layout = QVBoxLayout(entity_group)
    
    # This will be populated based on sensor type
    entity_selector = None
    if parent and hasattr(parent, 'objectType'):
        sensor_type = getattr(parent, 'objectType', '')
        if 'SensorBody' in sensor_type or 'SensorObject' in sensor_type:
            entity_selector = buildBodyNumberWidget(fieldName, default, meta, parent, structure=structure)
        elif 'SensorNode' in sensor_type:
            entity_selector = buildNodeNumberWidget(fieldName, default, meta, parent, structure=structure)
        elif 'SensorMarker' in sensor_type:
            entity_selector = buildMarkerNumberWidget(fieldName, default, meta, parent, structure=structure)
    
    if entity_selector:
        entity_layout.addWidget(QLabel("Select Entity:"))
        entity_layout.addWidget(entity_selector)
    
    layout.addWidget(entity_group)
    
    # Output Type Selection Section  
    output_group = QGroupBox("Output Configuration")
    output_layout = QVBoxLayout(output_group)
    
    # Use our smart output type widget
    output_widget = buildSmartOutputTypeWidget(
        "outputVariableType", default, meta, parent, structure
    )
    output_layout.addWidget(output_widget)
    
    layout.addWidget(output_group)
    
    # Preview Section
    preview_group = QGroupBox("Live Preview")
    preview_layout = QVBoxLayout(preview_group)
    
    preview_text = QTextEdit()
    preview_text.setMaximumHeight(60)
    preview_text.setPlainText("Configure entity and output type to see preview...")
    preview_text.setReadOnly(True)
    
    refresh_button = QPushButton("Refresh Preview")
    
    preview_layout.addWidget(preview_text)
    preview_layout.addWidget(refresh_button)
    
    layout.addWidget(preview_group)
    
    # Store references for later access
    container.entity_selector = entity_selector
    container.output_widget = output_widget  
    container.preview_text = preview_text
    container.refresh_button = refresh_button
    container.fieldType = "enhancedSensor"
    
    def get_value():
        """Get the combined sensor configuration"""
        result = {}
        if entity_selector and hasattr(entity_selector, 'getValue'):
            result['entityIndex'] = entity_selector.getValue()
        if output_widget and hasattr(output_widget, 'getValue'):
            output_config = output_widget.getValue()
            if isinstance(output_config, dict):
                result.update(output_config)
            else:
                result['outputVariableType'] = output_config
        return result
    
    container.getValue = get_value
    
    # Connect refresh button (this would need actual implementation)
    def refresh_preview():
        try:
            config = get_value()
            preview_text.setPlainText(f"Config: {config}")
        except Exception as e:
            preview_text.setPlainText(f"Error: {e}")
    
    refresh_button.clicked.connect(refresh_preview)
    
    return container

from PyQt5.QtWidgets import QApplication

def getCurrentMainWindow():
    # Try to get the most up-to-date main window reference
    for widget in QApplication.topLevelWidgets():
        if widget.objectName() == "MainWindow" or widget.__class__.__name__ == "MainWindow":
            return widget
    return None

def setupRendererHighlighting(parentWindow, index, elementType="body", _retry=0):
    """
    Highlight an element (body, marker, node, load, sensor, etc.) in the OpenGL renderer.
    Pass index=None or index < 0 to clear highlight.
    """
    try:
        from PyQt5.QtWidgets import QApplication
        from exudyn import ItemType
        from PyQt5.QtCore import QTimer

        # Always get the most up-to-date main window
        mainWindow = None
        for widget in QApplication.topLevelWidgets():
            if widget.objectName() == "MainWindow" or widget.__class__.__name__ == "MainWindow":
                mainWindow = widget
                break
        if not mainWindow:
            mainWindow = parentWindow

        # Always get the current SC
        SC = getattr(mainWindow, 'SC', None)

        if not SC or not hasattr(SC, 'visualizationSettings') or not hasattr(SC.visualizationSettings, 'interactive'):
            # Retry up to 15 times with 300ms delay (total ~4.5s)
            if _retry < 15:
                debugLog(f"[Highlighting][RETRY {_retry}] SC or visualizationSettings not available, retrying...")
                QTimer.singleShot(300, lambda: setupRendererHighlighting(parentWindow, index, elementType, _retry=_retry+1))
            else:
                debugLog(f"[Highlighting][FAIL] Could not get SC/visualizationSettings after retries. Highlight state may be stale.")
            return

        # Map elementType to ItemType
        type_map = {
            "body": ItemType.Object,
            "object": ItemType.Object,
            "marker": ItemType.Marker,
            "node": ItemType.Node,
            "load": ItemType.Load,
            "sensor": ItemType.Sensor,
        }
        itemType = type_map.get(elementType, ItemType._None)

        if index is None or (isinstance(index, int) and index < 0):
            # CLEAR highlight
            SC.visualizationSettings.interactive.highlightItemType = ItemType._None
            SC.visualizationSettings.interactive.highlightItemIndex = -1
            if hasattr(SC.visualizationSettings.interactive, 'highlightColor'):
                SC.visualizationSettings.interactive.highlightColor = [0, 0, 0, 0]
            debugLog(f"[Highlighting] CLEAR highlight (OFF) sent to SC id: {id(SC)}")
        else:
            # SET highlight
            SC.visualizationSettings.interactive.highlightItemType = itemType
            SC.visualizationSettings.interactive.highlightItemIndex = index
            if hasattr(SC.visualizationSettings.interactive, 'highlightColor'):
                SC.visualizationSettings.interactive.highlightColor = [0.8, 0.05, 0.05, 0.75]
            debugLog(f"[Highlighting] SET highlight (ON) for {elementType} {index} sent to SC id: {id(SC)}")

        # Force OpenGL window refresh
        if hasattr(mainWindow, '_refreshOpenGLRenderer'):
            mainWindow._refreshOpenGLRenderer()
        elif hasattr(mainWindow, 'parent') and hasattr(mainWindow.parent, '_refreshOpenGLRenderer'):
            mainWindow.parent._refreshOpenGLRenderer()

    except Exception as e:
        debugLog(f"[Highlighting][EXCEPTION] {e}")
        pass