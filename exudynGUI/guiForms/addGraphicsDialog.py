# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/addGraphicsDialog.py
#
# Description:
#     Implements the graphics constructor selection dialog for Exudyn GUI.
#     This dialog allows users to choose a graphical element (e.g., Sphere, Arrow)
#     from categorized and searchable lists of available `exudyn.graphics` functions.
#
#     Features:
#     - Organized categories for constructors (e.g., Basic Shapes, STL Files, etc.)
#     - Integrated search bar for fast filtering of constructors
#     - Live category switching and constructor selection
#     - Tooltips showing descriptions for each constructor
#     - Emits `constructorSelected` signal when a constructor is chosen
#
# Author:    Michael Pieber
# Created:   2025-05-21
# License:   BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Import debug system first
try:
    import exudynGUI.core.debug as debug
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

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QLineEdit, 
    QWidget, QScrollArea, QSizePolicy, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon
import exudyn.graphics as gfx
import inspect

# Graphics constructor categories and descriptions
GRAPHICS_CATEGORIES = {
    "Basic Shapes": {
        "description": "Basic geometric shapes like spheres, cylinders, and boxes",
        "constructors": [
            "Sphere", "Cylinder", "Cuboid", "Brick", "BrickXYZ"
        ]
    },
    "2D Shapes": {
        "description": "Two-dimensional shapes and patterns",
        "constructors": [
            "Circle", "Quad", "CheckerBoard"
        ]
    },
    "Lines & Arrows": {
        "description": "Lines, arrows, and connection elements",
        "constructors": [
            "Arrow", "RigidLink", "Lines"
        ]
    },
    "Complex Shapes": {
        "description": "Advanced shapes and extrusions",
        "constructors": [
            "SolidExtrusion", "SolidOfRevolution"
        ]
    },
    "Text & Annotations": {
        "description": "Text labels and coordinate systems",
        "constructors": [
            "Text", "Basis"
        ]
    },
    "Utilities": {
        "description": "Utility functions for graphics processing",
        "constructors": [
            "Move", "ToPointsAndTrigs", "ExportMergeTriangleLists", 
            "AddEdgesAndSmoothenNormals", "ComputeOrthonormalBasisVectors"
        ]
    },
    "STL Files": {
        "description": "Generate graphics data from STL file",
        "constructors": [
            "FromSTLfileASCII", "FromSTLfile",
            "ExportSTL",
        ]
    }
}

# Constructor descriptions
CONSTRUCTOR_DESCRIPTIONS = {
    "Sphere": "Create a sphere with specified center and radius",
    "Cylinder": "Create a cylinder with specified axis, radius and height",
    "Cuboid": "Create a cuboid (box) with specified dimensions",
    "Brick": "Create a brick shape",
    "BrickXYZ": "Create a brick with specific XYZ dimensions",
    "Circle": "Create a 2D circle",
    "Quad": "Create a quadrilateral surface",
    "CheckerBoard": "Create a checkerboard pattern",
    "Arrow": "Create an arrow for direction visualization",
    "RigidLink": "Create a rigid connection link",
    "Lines": "Create line segments",
    "SolidExtrusion": "Create a 3D solid by extruding a 2D shape",
    "SolidOfRevolution": "Create a 3D solid by rotating a 2D profile",
    "Text": "Create 3D text labels",
    "Basis": "Create a coordinate system visualization",
    "Move": "Move graphics objects by translation",
    "ToPointsAndTrigs": "Convert to points and triangles",
    "ExportMergeTriangleLists": "Merge triangle lists for export",
    "AddEdgesAndSmoothenNormals": "Add edges and smooth normals",
    "ComputeOrthonormalBasisVectors": "Compute orthonormal basis vectors"
}

class AddGraphicsDialog(QDialog):
    constructorSelected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Graphics Constructor")
        self.resize(700, 500)
        self.selectedCategory = None
        self._selectedConstructor = None
        
        # Verify available constructors
        self.availableConstructors = [k for k in dir(gfx) if callable(getattr(gfx, k)) and not k.startswith("_")]
        debugLog(f"[AddGraphicsDialog] Found {len(self.availableConstructors)} graphics constructors")
        
        # Filter categories to only include available constructors
        self.filteredCategories = {}
        for category, data in GRAPHICS_CATEGORIES.items():
            available = [c for c in data["constructors"] if c in self.availableConstructors]
            if available:
                self.filteredCategories[category] = {
                    "description": data["description"],
                    "constructors": available
                }
        
        self.setupUI()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Select Graphics Constructor")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Search box
        self.searchEdit = QLineEdit()
        self.searchEdit.setPlaceholderText("Search graphics constructors...")
        self.searchEdit.textChanged.connect(self.filterConstructors)
        layout.addWidget(self.searchEdit)
        
        # Main content area
        contentWidget = QWidget()
        contentLayout = QHBoxLayout(contentWidget)
        
        # Left panel - Categories
        self.setupCategoryPanel(contentLayout)
        
        # Right panel - Constructors
        self.setupConstructorPanel(contentLayout)
        
        layout.addWidget(contentWidget)
        
        # Button box
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)
        
        # Initialize with first category
        if self.filteredCategories:
            first_category = list(self.filteredCategories.keys())[0]
            self.selectCategory(first_category)
    
    def setupCategoryPanel(self, parentLayout):
        # Category panel
        categoryPanel = QWidget()
        categoryPanel.setFixedWidth(200)
        categoryLayout = QVBoxLayout(categoryPanel)
        
        categoryTitle = QLabel("Categories")
        categoryTitle.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        categoryLayout.addWidget(categoryTitle)
        
        # Category buttons
        self.categoryButtons = {}
        for category in self.filteredCategories:
            btn = QPushButton(category)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, cat=category: self.selectCategory(cat))
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px;
                    margin: 2px;
                }
                QPushButton:checked {
                    background-color: #0078d4;
                    color: white;
                }
            """)
            self.categoryButtons[category] = btn
            categoryLayout.addWidget(btn)
        
        categoryLayout.addStretch()
        parentLayout.addWidget(categoryPanel)
    
    def setupConstructorPanel(self, parentLayout):
        # Constructor panel
        constructorPanel = QWidget()
        constructorLayout = QVBoxLayout(constructorPanel)
        
        # Category description
        self.categoryDescLabel = QLabel()
        self.categoryDescLabel.setWordWrap(True)
        self.categoryDescLabel.setStyleSheet("font-style: italic; margin-bottom: 10px;")
        constructorLayout.addWidget(self.categoryDescLabel)
          # Scroll area for constructor buttons
        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.constructorWidget = QWidget()
        self.constructorLayout = QGridLayout(self.constructorWidget)
        self.constructorLayout.setSpacing(5)
        
        scrollArea.setWidget(self.constructorWidget)
        constructorLayout.addWidget(scrollArea)
        
        parentLayout.addWidget(constructorPanel)
    
    def selectCategory(self, category):
        # Update category selection
        for cat, btn in self.categoryButtons.items():
            btn.setChecked(cat == category)
        
        self.selectedCategory = category
        
        # Update description
        if category in self.filteredCategories:
            self.categoryDescLabel.setText(self.filteredCategories[category]["description"])
        
        # Update constructor buttons
        self.updateConstructorButtons()
    
    def updateConstructorButtons(self):
        # Clear existing buttons
        for i in reversed(range(self.constructorLayout.count())):
            self.constructorLayout.itemAt(i).widget().setParent(None)
        
        if not self.selectedCategory:
            return
        
        # Get search text
        searchText = self.searchEdit.text().lower()
        
        # Get constructors for selected category
        constructors = self.filteredCategories[self.selectedCategory]["constructors"]
        
        # Filter by search text if provided
        if searchText:
            constructors = [c for c in constructors if searchText in c.lower()]
        
        # Create constructor buttons
        self.constructorButtons = {}
        row, col = 0, 0
        cols = 2  # Two columns of buttons
        
        for constructor in constructors:
            btn = QPushButton(constructor)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, name=constructor: self.selectConstructor(name))
            
            # Add description as tooltip
            if constructor in CONSTRUCTOR_DESCRIPTIONS:
                btn.setToolTip(CONSTRUCTOR_DESCRIPTIONS[constructor])
            
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    margin: 2px;
                    min-height: 30px;
                }
                QPushButton:checked {
                    background-color: #0078d4;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                    color: white;
                }
            """)
            
            self.constructorButtons[constructor] = btn
            self.constructorLayout.addWidget(btn, row, col)
            
            col += 1
            if col >= cols:
                col = 0
                row += 1
    
    def selectConstructor(self, constructor):
        # Update constructor selection
        for name, btn in self.constructorButtons.items():
            btn.setChecked(name == constructor)
        
        self._selectedConstructor = constructor
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
        
        debugLog(f"[AddGraphicsDialog] Selected constructor: {constructor}")
    
    def filterConstructors(self, searchText):
        """Filter constructors based on search text"""
        if not searchText:
            # Show all constructors for selected category
            self.updateConstructorButtons()
            return
        
        searchText = searchText.lower()
        
        # Find categories that contain matching constructors
        matchingCategories = []
        for category, data in self.filteredCategories.items():
            matching = [c for c in data["constructors"] if searchText in c.lower()]
            if matching:
                matchingCategories.append(category)
        
        # If current category has matches, just update the buttons
        if self.selectedCategory in matchingCategories:
            self.updateConstructorButtons()
        elif matchingCategories:
            # Switch to first matching category
            self.selectCategory(matchingCategories[0])
        else:
            # No matches - clear constructor area
            for i in reversed(range(self.constructorLayout.count())):
                self.constructorLayout.itemAt(i).widget().setParent(None)
    
    def getSelectedConstructor(self):
        """Return the selected constructor name"""
        return self._selectedConstructor
    
    def accept(self):
        if self._selectedConstructor:
            self.constructorSelected.emit(self._selectedConstructor)
            debugLog(f"[AddGraphicsDialog] Emitting constructor selection: {self._selectedConstructor}")
        super().accept()
