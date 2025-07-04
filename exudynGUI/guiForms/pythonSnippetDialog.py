# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/pythonSnippetDialog.py
#
# Description:
#     Dialog for editing and testing Python code snippets interactively.
#     Features:
#       - Integrated QScintilla-based code editor with syntax highlighting
#       - Optional Jupyter kernel execution backend
#       - Live tooltip inspection using kernel introspection
#       - Manual play (Ctrl+Enter) and tooltip (Shift+Enter) shortcuts
#       - Signal-based snippet return for use in scriptable components
#
# Authors:  Michael Pieber
# Date:     2025-07-03
#
# License:  BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QPlainTextEdit, QPushButton, QTextEdit, QMessageBox, QTextBrowser, QListWidget, QListWidgetItem, QSplitter, QToolTip
)
from PyQt5.QtCore import Qt, pyqtSignal
import threading
from PyQt5.Qsci import QsciScintilla, QsciLexerPython
from PyQt5.QtGui import QFont, QColor

# Jupyter kernel client
try:
    from jupyter_client import KernelManager
except ImportError:
    KernelManager = None

class PythonSnippetDialog(QDialog):
    snippetSaved = pyqtSignal(dict)

    def __init__(self, parent=None, label='', code='', enabled=True, kernel_client=None, console=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Python Snippet")
        self.resize(700, 500)
        self.kernel_manager = None
        self.kernel_client = None
        self.kernel_ready = False
        self.completion_popup = None
        self.console = console
        self.initUI(label, code, enabled)
        if kernel_client is not None:
            self.kernel_client = kernel_client
            self.kernel_ready = True
        elif KernelManager:
            self.start_kernel()

    def initUI(self, label, code, enabled):
        layout = QVBoxLayout(self)

        # Label
        label_layout = QHBoxLayout()
        label_layout.addWidget(QLabel("Label:"))
        self.label_edit = QLineEdit(label)
        label_layout.addWidget(self.label_edit)
        layout.addLayout(label_layout)

        # Enabled checkbox
        self.enabled_checkbox = QCheckBox("Enabled")
        self.enabled_checkbox.setChecked(enabled)
        layout.addWidget(self.enabled_checkbox)

        # Splitter for code/output (now just code editor)
        self.code_edit = QsciScintilla()
        self.code_edit.setText(code)
        self.code_edit.setUtf8(True)
        lexer = QsciLexerPython()
        lexer.setDefaultFont(self.code_edit.font())
        self.code_edit.setLexer(lexer)
        self.code_edit.setMarginLineNumbers(1, True)
        self.code_edit.setMarginsBackgroundColor(Qt.lightGray)
        self.code_edit.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        self.code_edit.setAutoIndent(True)
        self.code_edit.setIndentationGuides(True)
        self.code_edit.setTabWidth(4)
        self.code_edit.setIndentationsUseTabs(False)
        self.code_edit.setCaretLineVisible(True)
        self.code_edit.setCaretLineBackgroundColor(QColor(255,255,200))
        self.code_edit.setFolding(QsciScintilla.BoxedTreeFoldStyle)
        self.code_edit.setMinimumHeight(200)
        layout.addWidget(QLabel("Python Code:"))
        layout.addWidget(self.code_edit, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶️ Play (Ctrl+Enter)")
        self.play_btn.clicked.connect(self.on_play)
        btn_layout.addWidget(self.play_btn)
        btn_layout.addStretch(1)
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # Shortcuts
        self.code_edit.installEventFilter(self)
        self.code_edit.keyPressEvent = self.codeEditorKeyPressEvent
        self.code_edit.cursorPositionChanged.connect(self.clear_error_highlight)
        self.code_edit.setMouseTracking(True)
        self.code_edit.mouseMoveEvent = self.codeEditorMouseMoveEvent
        self.last_tooltip_word = None

    def codeEditorKeyPressEvent(self, event):
        # Minimal version: no completion popup logic
        # Tab should always insert indentation
        if event.key() == Qt.Key_Tab:
            self.code_edit.insert("    ")
            return
        if event.key() == Qt.Key_Return and (event.modifiers() & Qt.ControlModifier):
            self.on_play()
            return
        if event.key() == Qt.Key_Return and (event.modifiers() & Qt.ShiftModifier):
            self.on_play()
            return
        if event.key() == Qt.Key_Escape:
            self.reject()
            return
        if event.key() == Qt.Key_Backtab or (event.key() == Qt.Key_Tab and event.modifiers() & Qt.ShiftModifier):
            self.on_inspect()
            return
        QsciScintilla.keyPressEvent(self.code_edit, event)

    def get_word_at_position(self, pos):
        text = self.code_edit.text()[:pos]
        # Find the start of the word
        start = pos - 1
        while start >= 0 and (text[start].isalnum() or text[start] == '_'):
            start -= 1
        start += 1
        # Find the end of the word
        end = pos
        full_text = self.code_edit.text()
        while end < len(full_text) and (full_text[end].isalnum() or full_text[end] == '_'):
            end += 1
        return full_text[start:end]

    def codeEditorMouseMoveEvent(self, event):
        pos = self.code_edit.SendScintilla(QsciScintilla.SCI_POSITIONFROMPOINT, event.x(), event.y())
        word = self.get_word_at_position(pos)
        if word and word != self.last_tooltip_word:
            self.last_tooltip_word = word
            self.on_inspect(word=word, pos=event.globalPos())
        QsciScintilla.mouseMoveEvent(self.code_edit, event)

    def eventFilter(self, obj, event):
        return False  # Handled in codeEditorKeyPressEvent

    def start_kernel(self):
        self.output_edit.append("Starting Jupyter kernel...")
        self.kernel_manager = KernelManager()
        self.kernel_manager.start_kernel()
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        self.kernel_ready = True
        self.output_edit.append("Kernel started.")

    def stop_kernel(self):
        # Only stop if we started it
        if self.kernel_manager:
            self.kernel_manager.shutdown_kernel(now=True)
            self.kernel_manager = None
            self.kernel_client = None
            self.kernel_ready = False

    def closeEvent(self, event):
        self.stop_kernel()
        super().closeEvent(event)

    def on_play(self):
        code = self.code_edit.text()
        if self.console is not None and hasattr(self.console, 'append_code_and_run'):
            self.console.append_code_and_run(code)
        elif self.kernel_ready:
            # Fallback: just send to kernel (output will go to main console if using same kernel)
            self.kernel_client.execute(code)

    def on_inspect(self, word=None, pos=None):
        if not self.kernel_ready:
            return
        if word is None:
            # Get word at cursor
            pos = self.code_edit.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
            word = self.get_word_at_position(pos)
        if not word:
            return
        code = self.code_edit.text()
        cursor_pos = self.code_edit.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
        msg_id = self.kernel_client.inspect(code=code, cursor_pos=cursor_pos, detail_level=0)
        def run():
            while True:
                try:
                    msg = self.kernel_client.get_shell_msg(timeout=2)
                except Exception:
                    break
                if msg['parent_header'].get('msg_id') != msg_id:
                    continue
                content = msg['content']
                if content.get('status') == 'ok' and content.get('found', False):
                    doc = content.get('data', {}).get('text/plain', '')
                    if doc:
                        QToolTip.showText(pos or self.code_edit.mapToGlobal(self.code_edit.cursorRect().center()), doc, self.code_edit)
                break
        threading.Thread(target=run).start()

    def highlight_error_line(self, line):
        marker = self.code_edit.markerDefine(QsciScintilla.Background)
        self.code_edit.setMarkerBackgroundColor(QColor(255, 200, 200), marker)
        self.code_edit.markerAdd(line, marker)

    def clear_error_highlight(self):
        self.code_edit.markerDeleteAll()

    def accept(self):
        snippet = {
            'type': 'PythonSnippet',
            'label': self.label_edit.text().strip(),
            'enabled': self.enabled_checkbox.isChecked(),
            'code': self.code_edit.text(),
        }
        self.snippetSaved.emit(snippet)
        super().accept() 