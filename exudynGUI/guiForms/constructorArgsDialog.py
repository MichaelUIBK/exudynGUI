# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/constructorArgsDialog.py
#
# Description:
#     Dialog for editing arguments of Exudyn graphics constructors in a form.
#     Dynamically generates argument fields for constructors like Sphere, Arrow,
#     Basis, FromSTLfile, etc., using introspection (inspect.signature).
#
#     Features:
#       - Supports custom widgets for special types (colors, vectors, matrices)
#       - Handles syntax validation and preview capability
#       - Adapts to constructor-specific logic (e.g., STL, Basis, Arrow)
#       - Integrates with AddGraphicsDialog for constructor selection
#       - Supports argument restoration from string representation
#
# Authors:  Michael Pieber
# Date:     2025-05-22
#
# License:  BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Import debug system first
try:
    import core.debug as debug
    # Legacy compatibility for existing debugLog calls
    def debugLog(msg, origin=None):
        if "Warning" in msg or "Error" in msg:
            debug.debugWarning(msg, origin=origin, category=debug.DebugCategory.GUI)
        else:
            debug.debugInfo(msg, origin=origin, category=debug.DebugCategory.GUI)
    def debugInfo(msg, origin=None, category=None):
        return debug.debugInfo(msg, origin, category)
    def debugWarning(msg, origin=None, category=None):
        return debug.debugWarning(msg, origin, category)
except ImportError:
    # Fallback if debug module not available
    def debugLog(msg, origin=None):
        pass
    def debugInfo(msg, origin=None, category=None):
        pass
    def debugWarning(msg, origin=None, category=None):
        pass

from core.qtImports import *
from PyQt5.QtWidgets import QWidget, QFormLayout, QLineEdit, QLabel, QMessageBox, QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QCheckBox, QDoubleSpinBox, QPushButton, QHBoxLayout
import exudyn as exu
import exudyn.graphics as gfx
import inspect
import ast
from guiForms.addGraphicsDialog import AddGraphicsDialog
def split_args(arg_string):
    parts = []
    bracket_level = 0
    current = ''
    for c in arg_string:
        if c == ',' and bracket_level == 0:
            parts.append(current.strip())
            current = ''
        else:
            current += c
            if c == '[':
                bracket_level += 1
            elif c == ']':
                bracket_level -= 1
    if current:
        parts.append(current.strip())
    return parts        




class ConstructorArgsDialog(QDialog):
    graphicsDataAccepted = pyqtSignal(dict)  # or list, if you want to support multiple
    def __init__(self, constructorName="", argsString="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Graphics Constructor")
        self.resize(500, 400)

        # Make dialog non-modal and always on top
        self.setModal(False)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.result = {"name": constructorName, "args": argsString}
        self.selectedConstructor = constructorName

        layout = QVBoxLayout(self)        # Constructor name display (compact)
        self.constructorHeaderLabel = None
        if constructorName:
            constructorHeaderLayout = QHBoxLayout()
            self.constructorHeaderLabel = QLabel(f"Graphics Constructor: {constructorName}")
            constructorHeaderLayout.addWidget(self.constructorHeaderLabel)
            constructorHeaderLayout.addStretch()
            
            changeBtn = QPushButton("Change...")
            changeBtn.setMaximumWidth(80)
            changeBtn.clicked.connect(self.selectConstructor)
            constructorHeaderLayout.addWidget(changeBtn)
            
            layout.addLayout(constructorHeaderLayout)
        
        # Dynamic argument fields
        self.argsWidget = QWidget()
        self.argsLayout = QFormLayout(self.argsWidget)
        layout.addWidget(self.argsWidget)
        self.argFields = {}  # name: widget        # Initialize fields if we have a constructor
        if constructorName:
            self.setWindowTitle(f"Add Graphics Constructor - {constructorName}")
            self.updateArgsFromConstructor(argsString)

        # Buttons layout with Preview button
        buttonsLayout = QHBoxLayout()
        
        # Preview button
        self.previewBtn = QPushButton("Preview")
        self.previewBtn.clicked.connect(self.previewCurrentGraphics)
        buttonsLayout.addWidget(self.previewBtn)
        
        # Spacer to push OK/Cancel to the right
        buttonsLayout.addStretch()
        
        # OK/Cancel
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.onAccepted)
        self.buttonBox.rejected.connect(self.reject)
        buttonsLayout.addWidget(self.buttonBox)
        
        layout.addLayout(buttonsLayout)

    def onAccepted(self):
        funcName = self.selectedConstructor
        argsList = []
        for name, field in self.argFields.items():
            val = field.text().strip()
            if val != '':
                # Special handling for fileName argument
                if name == 'fileName':
                    # Remove any existing quotes
                    val = val.strip("'\"")
                    # Always wrap in single quotes for eval
                    argsList.append(f"{name}='{val}'")
                else:
                    argsList.append(f"{name}={val}")
        # Validate syntax
        fullExpr = f"gfx.{funcName}({', '.join(argsList)})"
        try:
            import ast
            ast.parse(fullExpr, mode="eval")
        except Exception as e:
            QMessageBox.warning(self, "Syntax Error", f"Invalid input:\n{e}")
            return
        self.result = {
            "name": funcName,
            "args": ', '.join(argsList)
        }
        self.graphicsDataAccepted.emit(self.result)  # <-- emit here
        self.accept()

    def selectConstructor(self):
        """Open the graphics constructor selection dialog"""
        dialog = AddGraphicsDialog(self)
        if dialog.exec_():
            constructor = dialog.getSelectedConstructor()
            if constructor:
                self.selectedConstructor = constructor
                # Update window title to show selected constructor
                self.setWindowTitle(f"Add Graphics Constructor - {constructor}")
                # Update header label if it exists
                if self.constructorHeaderLabel:
                    self.constructorHeaderLabel.setText(f"Graphics Constructor: {constructor}")
                self.updateArgsFromConstructor("")
                debugLog(f"[ConstructorArgsDialog] Selected constructor: {constructor}")
                return True
        return False

    def onConstructorChanged(self, constructorName):
        """Handle when the user changes the graphics function"""
        # This method is now replaced by selectConstructor
        self.selectedConstructor = constructorName
        self.updateArgsFromConstructor("")

    

    def updateArgsFromConstructor(self, argsString=None):
        # Properly delete all old fields
        while self.argsLayout.count():
            item = self.argsLayout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        self.argFields.clear()
        funcName = self.selectedConstructor
        if not funcName:
            return
        try:
            func = getattr(gfx, funcName)
            try:
                sig = inspect.signature(func)
            except ValueError as e:
                if "ambiguous" in str(e):
                    # Handle numpy array defaults by creating a basic signature
                    # This is a workaround for functions with numpy array defaults
                    sig = None
                    # Create basic fields for known functions like Basis
                    if funcName == 'Basis':
                        self.createBasicBasisFields()
                        return
                else:
                    raise e
            
            # Parse provided argsString if present and is a string
            argValues = {}
            if argsString and isinstance(argsString, str):
                for arg in split_args(argsString):
                    if '=' in arg:
                        k, v = arg.split('=', 1)
                        k = k.strip()
                        v = v.strip()
                        if k == 'fileName':
                            v = v.strip("'\"")
                        argValues[k] = v
            
            for name, param in sig.parameters.items():
                if name == 'kwargs' or name.startswith('**'):
                    continue
                default = param.default if param.default is not inspect.Parameter.empty else ''
                val = argValues.get(name, default)
                
                # Handle numpy arrays to prevent "ambiguous truth value" errors
                import numpy as np
                if isinstance(val, np.ndarray):
                    val = val.tolist()  # Convert numpy array to list
                
                lname = name.lower()
                
                # Special handling for Quad pList parameter
                if funcName == 'Quad' and name == 'pList':
                    # Create a specialized widget for 4 points
                    field = self.createQuadPointsWidget(val)
                # Special handling for other point list parameters                elif name.lower() in ['plist', 'pointlist', 'points'] and funcName in ['Quad', 'QuadMesh']:
                    # Create a specialized widget for multiple points
                    field = self.createPointListWidget(name, val, funcName)                # Special handling for STL file parameters
                elif funcName == 'FromSTLfile':
                    if name == 'fileName':
                        import os
                        if isinstance(val, str) and val:
                            val = os.path.abspath(os.path.expanduser(val))
                        # File browser widget for STL file selection
                        from .specialWidgets import buildFileBrowserWidget
                        field = buildFileBrowserWidget(name, value=val, parent=self, 
                                                     file_filter="STL Files (*.stl);;All Files (*)")
                        
                    elif name == 'pOff':
                        from .specialWidgets import buildVector3DWidget
                        default_val = [0.0, 0.0, 0.0]
                        use_val = val if (not isinstance(val, str) or val.strip()) else default_val
                        field = buildVector3DWidget(name, value=use_val, parent=self)
                    elif name == 'Aoff':
                        # for STL “Aoff” use the new angle‐spinner widget
                        from guiForms.specialWidgets import STLRotationWidget
        
                        # parse any existing matrix literal (or fall back to identity)
                        try:
                            mat = ast.literal_eval(val) if isinstance(val, str) else val
                        except:
                            mat = None
        
                        field = STLRotationWidget(default_value=mat, parent=self)
                        # override text() so onAccepted() emits the 3×3 literal
                        field.text = lambda w=field: str(w.getMatrix().tolist())
        
                        # immediately after Aoff, insert the CS‐toggle
                        self.showCS = QCheckBox("Show local coordinate system")
                        self.showCS.setChecked(False)
                        # empty label to align under the name column
                        self.argsLayout.addRow(QLabel(""), self.showCS)
                        # now add the Aoff row and continue to the next parameter
                        self.argsLayout.addRow(QLabel(name), field)
                        self.argFields[name] = field
                        continue






                    elif 'color' in name.lower():
                        # Use the new color widget for all color fields
                        from exudynGUI.guiForms.specialWidgets import buildColorWidget
                        
                        # Parse the color value
                        color_value = val
                        if isinstance(val, str):
                            if val.strip() == '' or val == '[]':
                                color_value = [0.5, 0.5, 0.5, 1.0]  # Default gray
                            else:
                                try:
                                    import ast
                                    parsed = ast.literal_eval(val)
                                    if isinstance(parsed, list) and len(parsed) >= 3:
                                        color_value = parsed
                                    else:
                                        color_value = [0.5, 0.5, 0.5, 1.0]
                                except:
                                    color_value = [0.5, 0.5, 0.5, 1.0]
                        elif isinstance(val, list) and len(val) >= 3:
                            color_value = val
                        else:
                            color_value = [0.5, 0.5, 0.5, 1.0]
                        
                        field = buildColorWidget(name, value=color_value, parent=self)
                        
                        # Override text() method to return the color as a string
                        def color_text(widget=field):
                            color = widget.getValue()
                            return str(color)
                        field.text = color_text
                    elif name in ['verbose', 'invertNormals', 'invertTriangles']:
                        # Checkbox for boolean parameters
                        field = QCheckBox()
                        if isinstance(val, bool):
                            field.setChecked(val)
                        elif str(val).lower() in ['true', '1']:
                            field.setChecked(True)
                        # Override text() method for checkbox
                        def checkbox_text(cb=field):
                            return str(cb.isChecked())
                        field.text = checkbox_text
                    elif name in ['density', 'scale']:
                        # Spin box for numeric parameters
                        field = QDoubleSpinBox()
                        field.setDecimals(6)
                        field.setRange(-999999.0, 999999.0)
                        try:
                            field.setValue(float(val) if val != '' else (0.0 if name == 'density' else 1.0))
                        except ValueError:
                            field.setValue(0.0 if name == 'density' else 1.0)
                        # Override text() method for spin box
                        def spinbox_text(sb=field):
                            return str(sb.value())
                        field.text = spinbox_text
                    else:
                        field = QLineEdit(str(val))
                # Special handling for Basis function parameters
                elif funcName == 'Basis':
                    if name == 'origin':
                        # 3D point widget for origin
                        from exudynGUI.guiForms.specialWidgets import buildVector3DWidget
                        default_val = [0.0, 0.0, 0.0]
                        # Handle numpy array or empty values properly
                        if val is None or (isinstance(val, str) and (val == '' or val.strip() == '')):
                            use_val = default_val
                        else:
                            use_val = val
                        field = buildVector3DWidget(name, value=use_val, parent=self)
                    elif name == 'rotationMatrix':
                        # 3x3 rotation matrix widget
                        from exudynGUI.guiForms.specialWidgets import buildMatrix3x3Widget
                        field = buildMatrix3x3Widget(name, value=val, parent=self)
                    elif name == 'colors':
                        # Specialized widget for 3 colors (red, green, blue)
                        field = self.createBasisColorsWidget(val)
                    elif name in ['length', 'headFactor', 'headStretch', 'radius']:
                        # Numeric parameters with appropriate defaults
                        field = QDoubleSpinBox()
                        field.setDecimals(6)
                        field.setRange(0.001, 999999.0)
                        default_value = 1.0 if name == 'length' else (2.0 if name == 'headFactor' else (4.0 if name == 'headStretch' else 0.01))
                        try:
                            field.setValue(float(val) if val != '' else default_value)
                        except ValueError:
                            field.setValue(default_value)
                        # Override text() method for spin box
                        def spinbox_text(sb=field):
                            return str(sb.value())
                        field.text = spinbox_text
                    elif name == 'nTiles':
                        # Integer spin box for nTiles (minimum 3)
                        from PyQt5.QtWidgets import QSpinBox
                        field = QSpinBox()
                        field.setRange(3, 999)
                        try:
                            field.setValue(int(val) if val != '' else 12)
                        except ValueError:
                            field.setValue(12)
                        # Override text() method for spin box
                        def int_spinbox_text(sb=field):
                            return str(sb.value())
                        field.text = int_spinbox_text
                    else:
                        field = QLineEdit(str(val))
                elif lname == 'constrainedaxes':
                    from exudynGUI.guiForms.specialWidgets import buildIntNWidget  # moved import here to avoid circular import
                    # --- Unified logic for SphericalJoint: always N=3, default [1,1,1] ---
                    N = 6
                    # Try to get N from annotation, name, or default
                    if '3' in name or '3' in str(param.annotation):
                        N = 3
                    elif '6' in name or '6' in str(param.annotation):
                        N = 6
                    elif isinstance(default, (list, tuple)):
                        N = len(default)
                    elif isinstance(default, str) and default.startswith("["):
                        try:
                            arr = ast.literal_eval(default)
                            if isinstance(arr, (list, tuple)):
                                N = len(arr)
                        except Exception:
                            pass
                    # --- Force N=3 and default [1,1,1] for SphericalJoint (robust) ---
                    funcNameLower = funcName.lower()
                    if 'sphericaljoint' in funcNameLower or 'createsphericaljoint' in funcNameLower or 'objectjointspherical' in funcNameLower:
                        N = 3
                        val = [1,1,1]
                    field = buildIntNWidget(name, default=val, meta=None, parent=self, N=N)
                # Special handling for Arrow function parameters                elif funcName == 'Arrow':
                    if name in ['pAxis', 'vAxis']:                        # 3D vector widgets for arrow position and direction
                        from exudynGUI.guiForms.specialWidgets import buildVector3DWidget
                        default_val = [0.0, 0.0, 0.0] if name == 'pAxis' else [0.0, 0.0, 1.0]
                        # Handle numpy array or empty values properly
                        if val is None or (isinstance(val, str) and (val == '' or val.strip() == '')):
                            use_val = default_val
                        else:
                            use_val = val
                        field = buildVector3DWidget(name, value=use_val, parent=self)
                    elif name in ['radius', 'headFactor', 'headStretch']:
                        # Numeric parameters
                        field = QDoubleSpinBox()
                        field.setDecimals(6)
                        field.setRange(0.001, 999999.0)
                        default_value = 0.05 if name == 'radius' else (2.0 if name == 'headFactor' else 4.0)
                        try:
                            field.setValue(float(val) if val != '' else default_value)
                        except ValueError:
                            field.setValue(default_value)
                        def spinbox_text(sb=field):
                            return str(sb.value())
                        field.text = spinbox_text
                    elif name == 'nTiles':
                        # Integer spin box for nTiles
                        from PyQt5.QtWidgets import QSpinBox
                        field = QSpinBox()
                        field.setRange(3, 999)
                        try:
                            field.setValue(int(val) if val != '' else 12)
                        except ValueError:
                            field.setValue(12)
                        def int_spinbox_text(sb=field):
                            return str(sb.value())
                        field.text = int_spinbox_text
                    elif name == 'color':
                        # Use the new color widget for color fields
                        from exudynGUI.guiForms.specialWidgets import buildColorWidget
                        
                        # Parse the color value
                        color_value = val
                        if isinstance(val, str):
                            if val.strip() == '' or val == '[]':
                                color_value = [0.0, 0.0, 1.0, 1.0]  # Default blue for Arrow
                            else:
                                try:
                                    import ast
                                    parsed = ast.literal_eval(val)
                                    if isinstance(parsed, list) and len(parsed) >= 3:
                                        color_value = parsed
                                    else:
                                        color_value = [0.0, 0.0, 1.0, 1.0]
                                except:
                                    color_value = [0.0, 0.0, 1.0, 1.0]
                        elif isinstance(val, list) and len(val) >= 3:
                            color_value = val
                        else:
                            color_value = [0.0, 0.0, 1.0, 1.0]
                        
                        field = buildColorWidget(name, value=color_value, parent=self)
                        
                        # Override text() method to return the color as a string
                        def color_text(widget=field):
                            color = widget.getValue()
                            return str(color)
                        field.text = color_text
                    else:
                        field = QLineEdit(str(val))                # Special handling for Sphere/Cylinder common parameters
                elif funcName in ['Sphere', 'Cylinder'] and name in ['point', 'pAxis']:                    # 3D point/position widgets
                    from exudynGUI.guiForms.specialWidgets import buildVector3DWidget
                    default_val = [0.0, 0.0, 0.0]
                    # Handle numpy array or empty values properly
                    if val is None or (isinstance(val, str) and (val == '' or val.strip() == '')):
                        use_val = default_val
                    else:
                        use_val = val
                    field = buildVector3DWidget(name, value=use_val, parent=self)
                elif funcName == 'Cylinder' and name == 'vAxis':
                    # 3D direction vector for cylinder
                    from exudynGUI.guiForms.specialWidgets import buildVector3DWidget
                    default_val = [0.0, 0.0, 1.0]  # Default Z direction
                    # Handle numpy array or empty values properly
                    if val is None or (isinstance(val, str) and (val == '' or val.strip() == '')):
                        use_val = default_val
                    else:
                        use_val = val
                    field = buildVector3DWidget(name, value=use_val, parent=self)
                # General handling for any color field that wasn't caught above
                elif 'color' in name.lower():
                    # Use the new color widget for all color fields
                    from exudynGUI.guiForms.specialWidgets import buildColorWidget
                    
                    # Parse the color value
                    color_value = val
                    if isinstance(val, str):
                        if val.strip() == '' or val == '[]':
                            color_value = [0.5, 0.5, 0.5, 1.0]  # Default gray
                        else:
                            try:
                                import ast
                                parsed = ast.literal_eval(val)
                                if isinstance(parsed, list) and len(parsed) >= 3:
                                    color_value = parsed
                                else:
                                    color_value = [0.5, 0.5, 0.5, 1.0]
                            except:
                                color_value = [0.5, 0.5, 0.5, 1.0]
                    elif isinstance(val, list) and len(val) >= 3:
                        color_value = val
                    else:
                        color_value = [0.5, 0.5, 0.5, 1.0]
                    
                    field = buildColorWidget(name, value=color_value, parent=self)
                    
                    # Override text() method to return the color as a string
                    def color_text(widget=field):
                        color = widget.getValue()
                        return str(color)
                    field.text = color_text
                else:
                    field = QLineEdit(str(val))
                self.argsLayout.addRow(QLabel(name), field)
                self.argFields[name] = field

            # ─── for STL imports only: show/hide a Basis ──────────────────
            if funcName=="FromSTLfile" and name=="Aoff":
               self.showCS = QCheckBox("Show local coordinate system")
               # make it on by default if you like:
               self.showCS.setChecked(False)
               self.argsLayout.addRow(QLabel(""), self.showCS)

        except Exception as e:
            self.argsLayout.addRow(QLabel("Error"), QLabel(str(e)))

    def accepted(self):
        funcName = self.selectedConstructor
        argsList = []
        for name, field in self.argFields.items():
            val = field.text().strip()
            if val != '':
                argsList.append(f"{name}={val}")
        # Validate syntax
        fullExpr = f"gfx.{funcName}({', '.join(argsList)})"
        try:
            ast.parse(fullExpr, mode="eval")
        except Exception as e:
            QMessageBox.warning(self, "Syntax Error", f"Invalid input:\n{e}")
            return
        self.result = {
            "name": funcName,
            "args": ', '.join(argsList)
        }
        self.accept()

    def getName(self):
        return self.selectedConstructor

    def getArgs(self):
        return self.result.get("args", "")

    def getResult(self):
        return self.result

    def previewCurrentGraphics(self):
        """Preview the current graphics function configuration in the main GUI."""
        try:
            funcName = self.selectedConstructor
            if not funcName:
                QMessageBox.warning(self, "No Constructor", "Please select a graphics constructor first.")
                return
            argsList = []
            for name, field in self.argFields.items():
                val = field.text().strip()
                if val != '':
                    argsList.append(f"{name}={val}")

            # Validate syntax first
            fullExpr = f"gfx.{funcName}({', '.join(argsList)})"
            try:
                ast.parse(fullExpr, mode="eval")
            except Exception as e:
                QMessageBox.warning(self, "Syntax Error", f"Cannot preview - Invalid input:\n{e}")
                return

            # Build the new graphics object
            import exudyn.graphics as gfx
            graphics_obj = eval(f"gfx.{funcName}({', '.join(argsList)})", {"gfx": gfx})

            # Get main system (mbs) from parent or pass it explicitly
            mbs = getattr(self.parent(), "mbs", None)
            if mbs is None:
                QMessageBox.warning(self, "Preview Error", "Main system (mbs) not found in parent.")
                return

            # Remove previous preview ground if it exists
            if hasattr(self, "_previewGroundId"):
                try:
                    mbs.RemoveObject(self._previewGroundId)
                except Exception:
                    pass


            # ─── Prepare preview state ───────────────────────────────────────
            editIndex       = getattr(self, "_editIndex", None)
            gfxLocals       = {"gfx": gfx}
            graphicsDataList = []

            # ─── if user asked for local CS, prepend a Basis ───────────────
            if getattr(self, 'showCS', False) and self.showCS.isChecked():
                p = ast.literal_eval(self.argFields['pOff'].text())
                A = ast.literal_eval(self.argFields['Aoff'].text())
                graphicsDataList.append(gfx.Basis(origin=p, rotationMatrix=A))

            # ─── now include all the other entries ─────────────────────────
            if hasattr(self.parent(), "_temporaryGraphicsList"):
                for i, entry in enumerate(self.parent()._temporaryGraphicsList):
                    if editIndex is not None and i == editIndex:
                        continue
                    try:
                        graphicsDataList.append(
                            eval(f"gfx.{entry['name']}({entry['args']})", gfxLocals)
                        )
                    except Exception as e:
                        debugLog(f"Preview: failed to evaluate entry {i}: {e}")

            # Append the new graphics object
            graphicsDataList.append(graphics_obj)

            # Reset and preview all graphics
            mbs.Reset()
            self._previewGroundId = mbs.CreateGround(referencePosition=[0,0,0], graphicsDataList=graphicsDataList)
            mbs.Assemble()
            if hasattr(self.parent(), "refreshModelView"):
                self.parent().refreshModelView()

            # Force Qt to process events (helps update OpenGL window)
            QApplication.processEvents()

            # Force Exudyn renderer to do idle tasks if possible
            if hasattr(mbs, "renderer") and hasattr(mbs.renderer, "DoIdleTasks"):
                mbs.renderer.DoIdleTasks(waitSeconds=0.05)

        except Exception as e:
            QMessageBox.critical(self, "Preview Error", f"Failed to create preview:\n{str(e)}")

    def _previewSingleGraphics(self, entry, title):
        """Create preview of a single graphics entry"""
        try:
            # Create temporary system
            tempSC = exu.SystemContainer()
            tempMbs = tempSC.AddSystem()
            
            # Simple graphics reconstruction for single entry
            graphics_data = self._reconstructSingleGraphics(entry)
            if graphics_data is None:
                QMessageBox.warning(self, "Preview Error", 
                                  f"Failed to create graphics object from {entry['name']}")
                return
            
            # Create a ground object with the graphics
            groundIndex = tempMbs.CreateGround(graphicsDataList=[graphics_data])
              # Assemble and visualize
            tempMbs.Assemble()
              # 🧵 Start renderer for preview in background thread to prevent GUI blocking
            import threading
            
            def run_renderer():
                debugLog("🧵 [THREAD] Starting constructor preview exu.StartRenderer() in background...")
                try:
                    exu.StartRenderer()
                    debugLog("🧵 [THREAD] Constructor preview exu.StartRenderer() completed successfully")
                except Exception as e:
                    debugLog(f"🧵 [THREAD] Constructor preview exu.StartRenderer() failed: {e}")
            
            debugLog("🚀 Creating background thread for constructor preview renderer...")
            renderer_thread = threading.Thread(target=run_renderer, daemon=True)
            renderer_thread.start()
            debugLog(f"✅ Constructor preview renderer thread started (Thread ID: {renderer_thread.ident})")
            
            # Show message to user
            QMessageBox.information(self, title, 
                                  f"Preview created for {entry['name']}.\n"
                                  f"The preview is now shown in the 3D viewer.\n"
                                  f"Close this dialog when done viewing.")
            
        except Exception as e:
            QMessageBox.critical(self, "Preview Error", 
                               f"Failed to create preview:\n{str(e)}")

    def _reconstructSingleGraphics(self, entry):
        """Reconstruct a single graphics object from entry data"""
        try:
            func_name = entry['name']
            args_str = entry['args']
            
            # Remove 'GraphicsData' prefix if present
            if func_name.startswith('GraphicsData'):
                func_name = func_name[12:]  # Remove 'GraphicsData' prefix
            
            # Build the call string
            if args_str:
                call_str = f"gfx.{func_name}({args_str})"
            else:
                call_str = f"gfx.{func_name}()"
            
            # Evaluate the graphics function
            graphics_obj = eval(call_str, {"gfx": gfx})
            return graphics_obj
            
        except Exception as e:
            debugLog(f"Failed to reconstruct graphics {entry}: {e}")
            return None

    def createQuadPointsWidget(self, initial_value=""):
        """Create a specialized widget for Quad pList parameter (4 points)"""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("Quad Points (4 corners, counter-clockwise):")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)
        
        # Create 4 point input rows
        self.point_fields = []
        point_labels = ["P0 (bottom-left):", "P1 (bottom-right):", "P2 (top-right):", "P3 (top-left):"]
        default_points = ["[0,0,0]", "[1,0,0]", "[1,1,0]", "[0,1,0]"]
        
        # Try to parse initial value if provided
        if initial_value and initial_value != "":
            try:
                if isinstance(initial_value, str) and initial_value.startswith('['):
                    points_list = ast.literal_eval(initial_value)
                    if len(points_list) == 4:
                        default_points = [str(point) for point in points_list]
            except:
                pass  # Use default if parsing fails
        
        for i, (label, default) in enumerate(zip(point_labels, default_points)):
            row_layout = QHBoxLayout()
            
            # Label
            label_widget = QLabel(label)
            label_widget.setMinimumWidth(120)
            row_layout.addWidget(label_widget)
            
            # Point input field
            point_field = QLineEdit(default)
            point_field.setPlaceholderText("[x,y,z]")
            self.point_fields.append(point_field)
            row_layout.addWidget(point_field)
            
            layout.addLayout(row_layout)
        
        # Add helpful buttons
        button_layout = QHBoxLayout()
        
        # Reset to default button
        reset_btn = QPushButton("Reset to Default")
        reset_btn.clicked.connect(self.resetQuadToDefault)
        button_layout.addWidget(reset_btn)
        
        # Create XY plane button
        xy_plane_btn = QPushButton("XY Plane (1x1)")
        xy_plane_btn.clicked.connect(self.setQuadXYPlane)
        button_layout.addWidget(xy_plane_btn)
        
        layout.addLayout(button_layout)
        
        # Override text() method to return the properly formatted pList
        def get_quad_text():
            points = []
            for field in self.point_fields:
                try:
                    point_str = field.text().strip()
                    if point_str:
                        # Ensure it's a valid point format
                        if not point_str.startswith('['):
                            point_str = f"[{point_str}]"
                        points.append(point_str)
                except:
                    points.append("[0,0,0]")
            
            return f"[{','.join(points)}]"
        
        widget.text = get_quad_text
        return widget
    
    def resetQuadToDefault(self):
        """Reset quad points to default values"""
        defaults = ["[0,0,0]", "[1,0,0]", "[1,1,0]", "[0,1,0]"]
        for field, default in zip(self.point_fields, defaults):
            field.setText(default)
    
    def setQuadXYPlane(self):
        """Set quad points to form a 1x1 square in XY plane"""
        xy_points = ["[0,0,0]", "[1,0,0]", "[1,1,0]", "[0,1,0]"]
        for field, point in zip(self.point_fields, xy_points):
            field.setText(point)
    
    def createPointListWidget(self, name, initial_value, func_name):
        """Create a widget for general point lists (fallback)"""
        field = QLineEdit(str(initial_value) if initial_value else "[[0,0,0],[1,0,0],[1,1,0],[0,1,0]]")
        field.setPlaceholderText("[[x1,y1,z1],[x2,y2,z2],...]")
        return field
    
    def createBasisColorsWidget(self, initial_value=""):
        """Create a specialized widget for Basis colors parameter (3 colors for X, Y, Z axes)"""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from .specialWidgets import buildColorWidget
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("Basis Colors (X, Y, Z axes):")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)
        
        # Create 3 color input rows using color widgets
        self.color_widgets = []
        color_labels = ["X-axis (Red):", "Y-axis (Green):", "Z-axis (Blue):"]
        default_colors = [[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0], [0.0, 0.0, 1.0, 1.0]]
        
        # Try to parse initial value if provided
        if initial_value and initial_value != "":
            try:
                if isinstance(initial_value, str) and initial_value.startswith('['):
                    colors_list = ast.literal_eval(initial_value)
                    if len(colors_list) == 3:
                        default_colors = colors_list
            except:
                pass  # Use default if parsing fails
        
        for i, (label, default_color) in enumerate(zip(color_labels, default_colors)):
            row_layout = QHBoxLayout()
            
            # Label with color indicator
            label_widget = QLabel(label)
            label_widget.setMinimumWidth(120)
            row_layout.addWidget(label_widget)
            
            # Color widget
            color_widget = buildColorWidget(f"color_{i}", value=default_color, parent=widget)
            self.color_widgets.append(color_widget)
            row_layout.addWidget(color_widget)
            
            layout.addLayout(row_layout)
        
        # Add helpful buttons
        button_layout = QHBoxLayout()
        
        # Reset to default colors button
        reset_btn = QPushButton("Reset to RGB")
        reset_btn.clicked.connect(self.resetBasisColorsToRGB)
        button_layout.addWidget(reset_btn)
        
        # Monochrome option
        mono_btn = QPushButton("Use Monochrome")
        mono_btn.clicked.connect(self.setBasisColorsMonochrome)
        button_layout.addWidget(mono_btn)
        
        layout.addLayout(button_layout)
          # Override text() method to return the properly formatted colors list
        def get_colors_text():
            colors = []
            for color_widget in self.color_widgets:
                try:
                    color = color_widget.getValue()
                    colors.append(str(color))
                except:
                    colors.append("[0.5, 0.5, 0.5, 1.0]")
            
            return f"[{','.join(colors)}]"
        
        widget.text = get_colors_text
        return widget

    def resetBasisColorsToRGB(self):
        """Reset basis colors to standard RGB (red, green, blue)"""
        rgb_colors = [[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0], [0.0, 0.0, 1.0, 1.0]]
        if hasattr(self, 'color_widgets'):
            for widget, color in zip(self.color_widgets, rgb_colors):
                widget.setColor(color)
    
    def setBasisColorsMonochrome(self):
        """Set all basis colors to the same monochrome color"""
        mono_color = [0.8, 0.8, 0.8, 1.0]
        if hasattr(self, 'color_widgets'):
            for widget in self.color_widgets:                
                widget.setColor(mono_color)
