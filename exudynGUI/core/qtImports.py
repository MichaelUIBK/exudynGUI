# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: core/qtImports.py
#
# Description:
#     Centralized import file for PyQt5 classes used across the GUI.
#     Ensures consistent and minimal imports throughout the application.
#
# Authors:  Michael Pieber
# Date:     2025-05-12
# Notes:    Avoids redundancy and eases transition between PyQt versions.
#
# License:  BSD-3 license
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
from PyQt5.QtGui import QFont, QColor, QIcon, QIntValidator, QDoubleValidator, QRegExpValidator, QKeySequence
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QEvent, QRegExp, QTimer
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDialogButtonBox, QLabel, QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QMessageBox, QListWidget, QTextEdit, QPushButton, QHBoxLayout, QWidget,
    QMainWindow, QListWidgetItem, QTreeWidget, QDockWidget,
    QTreeWidgetItem, QInputDialog, QGridLayout, QStackedWidget, QAbstractItemView,
    QSizePolicy, QToolButton, QMenu, QAction, QScrollArea, QGroupBox, QTabWidget, QFrame,
    QShortcut, QColorDialog
)

