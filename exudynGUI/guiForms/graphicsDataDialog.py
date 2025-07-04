# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/graphicsDataDialog.py
#
# Description:
#     Dialog for managing and previewing entries in the graphicsDataList field.
#     Supports:
#       - Adding/editing visual objects like Sphere, Line, Cuboid, etc.
#       - Parsing and validating constructor call strings
#       - Live preview of individual or all entries using Exudyn's renderer
#       - Background rendering to avoid blocking the main GUI thread
#
# Authors:  Michael Pieber
# Date:     2025-07-03
#
# License:  BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from core.qtImports import *
import exudyn as exu
import exudyn.utilities as exuutils
import numpy as np
import inspect
import exudyn.graphics as gfx
from guiForms.constructorArgsDialog import ConstructorArgsDialog  # assumes you created this
from core.debug import debugLog

def createGraphicsEntry(callStr):
    try:
        obj = eval(f"gfx.{callStr}", {"gfx": gfx})
        if isinstance(obj, dict):
            # wrap in valid graphicsData container - could be a simple dict for preview
            pass  # keep as dict for preview
        setattr(obj, '__guiMetadata__', {'call': callStr})
        return {'call': callStr, 'object': obj}
    except Exception as e:
        debugLog(f"[createGraphicsEntry] ❌ Failed to evaluate gfx.{callStr}: {e}", origin="graphicsDataDialog")
        return {'call': callStr, 'object': None}

def simpleGraphicsReconstruction(entries):
    """Simple graphics reconstruction for preview purposes"""
    graphics_list = []
    for entry in entries:
        if isinstance(entry, dict) and 'name' in entry and 'args' in entry:
            name = entry['name'].removeprefix('GraphicsData')
            args_str = entry['args']
            call_str = f"{name}({args_str})"
            try:
                # Evaluate the graphics call
                graphics_obj = eval(f"gfx.{call_str}", {"gfx": gfx, "np": np})
                graphics_list.append(graphics_obj)
                debugLog(f"[simpleGraphicsReconstruction] ✅ Created: {call_str}", origin="graphicsDataDialog")
            except Exception as e:
                debugLog(f"[simpleGraphicsReconstruction] ❌ Failed: {call_str}: {e}", origin="graphicsDataDialog")
                # Create a simple fallback sphere for failed entries
                fallback = gfx.GraphicsDataSphere(point=[0,0,0], radius=0.1, color=[1,0,0,1])
                graphics_list.append(fallback)
    return graphics_list

    
class GraphicsDataDialog(QDialog):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit GraphicsData List")
        self.resize(600, 400)        # Now store just strings
        self.entries = []
        for entry in (data or []):
            if isinstance(entry, dict) and 'name' in entry and 'args' in entry:
                self.entries.append(entry)
            elif isinstance(entry, str):  # fallback: try to split string
                name, args = self.splitCall(entry)
                self.entries.append({'name': name, 'args': args})

        layout = QVBoxLayout(self)
        
        self.listWidget = QListWidget()
        layout.addWidget(self.listWidget)

        btnLayout = QHBoxLayout()
        for text, handler in [
            ("Add", self.addEntry),
            ("Edit", self.editEntry),
            ("Remove", self.removeEntry),
            ("Preview", self.previewSingleEntry),
            ("Preview All", self.previewAllEntries)
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btnLayout.addWidget(btn)
        layout.addLayout(btnLayout)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

        self.refreshList()

    def refreshList(self):
        self.listWidget.clear()
        for entry in self.entries:
            if isinstance(entry, dict) and 'name' in entry and 'args' in entry:
                callStr = f"{entry['name'].removeprefix('GraphicsData')}({entry['args']})"
            else:
                callStr = str(entry)
            self.listWidget.addItem(callStr)

    def addEntry(self):
        name, args = self.promptEntry()
        if name:
            self.entries.append({'name': name, 'args': args})  # ✅ correct
            self.refreshList()

    def editEntry(self):
        row = self.listWidget.currentRow()
        if row < 0:
            return
        old = self.entries[row]
        name = old['name'].removeprefix("GraphicsData")
        args = old['args']
        newName, newArgs = self.promptEntry(name, args)
        if newName:
            self.entries[row] = {'name': f"{newName}", 'args': newArgs}  # ✅ FIXED
            self.refreshList()


    def removeEntry(self):
        row = self.listWidget.currentRow()
        if row >= 0:
            del self.entries[row]
            self.refreshList()

    def promptEntry(self, defaultName='', defaultArgs=''):
        # For new entries (no defaultName), show the selection dialog directly
        if not defaultName:
            from guiForms.addGraphicsDialog import AddGraphicsDialog
            selectionDlg = AddGraphicsDialog(parent=self)
            if selectionDlg.exec_():
                selectedConstructor = selectionDlg.getSelectedConstructor()
                if selectedConstructor:
                    # Now show the arguments dialog with the selected constructor
                    argsDlg = ConstructorArgsDialog(selectedConstructor, "", parent=self)
                    if argsDlg.exec_():
                        return argsDlg.getName(), argsDlg.getArgs()
            return '', ''
        else:
            # For editing existing entries, use the args dialog directly
            dlg = ConstructorArgsDialog(defaultName, defaultArgs, parent=self)
            if dlg.exec_():
                return dlg.getName(), dlg.getArgs()
            return '', ''

    def splitCall(self, callStr):
        """Split call string into name and args"""
        if "(" not in callStr or not callStr.endswith(")"):
            return callStr, ""
        name = callStr[:callStr.index("(")]
        args = callStr[callStr.index("(")+1:-1]
        return name, args

    def getGraphicsDataList(self):
        """Returns pure call strings"""
        return self.entries

    def getData(self):
        result = []
        for entry in self.entries:
            if isinstance(entry, dict) and 'name' in entry and 'args' in entry:
                result.append(entry)
            elif isinstance(entry, str):  # fallback if needed
                name, args = self.splitCall(entry)
                result.append({'name': f"{name}", 'args': args})
        debugLog(f"[GraphicsDataDialog] Returning {len(result)} graphics entries", origin="graphicsDataDialog")
        return result

    def previewSingleEntry(self):
        """Preview the currently selected graphics entry using a temporary ground object"""
        row = self.listWidget.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a graphics entry to preview.")
            return
        
        entry = self.entries[row]
        self._previewGraphics([entry], f"Preview: {entry['name']}")

    def previewAllEntries(self):
        """Preview all graphics entries using a temporary ground object"""
        if not self.entries:
            QMessageBox.warning(self, "No Entries", "No graphics entries to preview.")
            return
        
        self._previewGraphics(self.entries, "Preview All Graphics")

    def _previewGraphics(self, entries, title):
        """Core preview logic: creates temporary system with ground + graphics"""
        try:
            debugLog(f"[_previewGraphics] Starting preview with {len(entries)} entries", origin="graphicsDataDialog")
            
            # Create temporary system
            tempSC = exu.SystemContainer()
            tempMbs = tempSC.AddSystem()
              # Convert entries to graphics objects
            graphicsDataList = simpleGraphicsReconstruction(entries)
            debugLog(f"[_previewGraphics] Reconstructed {len(graphicsDataList)} graphics objects", origin="graphicsDataDialog")
            
            # Create a ground object with the graphics
            groundIndex = tempMbs.CreateGround(graphicsDataList=graphicsDataList)
            debugLog(f"[_previewGraphics] Created ground object with index {groundIndex}", origin="graphicsDataDialog")
            
            # Assemble and visualize
            tempMbs.Assemble()
            debugLog(f"[_previewGraphics] System assembled successfully", origin="graphicsDataDialog")
              # 🧵 Start renderer for preview in background thread to prevent GUI blocking
            import threading
            
            def run_renderer():
                debugLog("🧵 [THREAD] Starting preview exu.StartRenderer() in background...", origin="graphicsDataDialog")
                try:
                    exu.StartRenderer()
                    debugLog("🧵 [THREAD] Preview exu.StartRenderer() completed successfully", origin="graphicsDataDialog")
                except Exception as e:
                    debugLog(f"🧵 [THREAD] Preview exu.StartRenderer() failed: {e}", origin="graphicsDataDialog")
            
            debugLog("🚀 Creating background thread for preview renderer...", origin="graphicsDataDialog")
            renderer_thread = threading.Thread(target=run_renderer, daemon=True)
            renderer_thread.start()
            debugLog(f"✅ Preview renderer thread started (Thread ID: {renderer_thread.ident})", origin="graphicsDataDialog")
            
            # Show message to user
            QMessageBox.information(self, title, 
                                  f"Preview created with {len(entries)} graphics item(s).\n"
                                  f"The preview is now shown in the 3D viewer.\n"
                                  f"Close this dialog when done viewing.")
            
        except Exception as e:
            debugLog(f"[_previewGraphics] ❌ Preview failed: {e}", origin="graphicsDataDialog")
            QMessageBox.critical(self, "Preview Error", 
                               f"Failed to create preview:\n{str(e)}\n\n"                               f"Please check that all graphics entries are valid.")
    
