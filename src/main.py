#! /usr/bin/env python3

import sys
from os.path import expanduser
import os
from multiprocessing import Pipe, Process

import markdown2
from PyQt5.QtWidgets import (
    QSplitter, QStatusBar, QWidget,
    QHBoxLayout,
    QApplication,
    QMainWindow,
    QAction,
    QFileDialog,
    QPlainTextEdit
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import QObject, QUrl, Qt, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView

import server

app = QApplication(sys.argv)

class Signals(QObject):
    status_bar_message = pyqtSignal(str)
    set_html = pyqtSignal(str)
    open_file = pyqtSignal()
    save_file = pyqtSignal()
    print_file = pyqtSignal()

parent_conn, child_conn = Pipe()
sig = Signals()

class Browser(QWebEngineView):
    def __init__(self,) -> None:
        super().__init__()
        self.init_me()

    def init_me(self):
        sig.set_html.connect(self.setHtml)
        self.load(QUrl("http://127.0.0.1:5000"))
        self.show()
        sig.print_file.connect(self.print_file)

    def print_file(self):
        fd = QFileDialog()
        fileName, _ = fd.getSaveFileName(
            self,
            "Export to pdf",
            os.path.join(expanduser("~"), ".pdf"),
            "(*.pdf)")
        if fileName == "":
            return

        sig.status_bar_message.emit("Expoting to PDF")
        self.page().printToPdf(fileName)
        sig.status_bar_message.emit("Exported to PDF")

class Editor(QPlainTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.init_me()

    def init_me(self):
        self.file_path = ""
        self.textChanged.connect(self.update_html)
        sig.open_file.connect(self.open_file)
        sig.save_file.connect(self.save_file)

    def update_html(self) -> None:
        text = self.toPlainText()
        html = str(markdown2.Markdown().convert(text))
        html = html.replace("$?", "\\(")
        html = html.replace("?$", "\\)")
        # html += ''
        # server.output_html = html
        # sig.set_html.emit(html)
        parent_conn.send(html)
        # SEND HTML TO WEBSERVER PROCESS

    def open_file(self):
        fd = QFileDialog()
        f_dir = fd.getOpenFileName(
            self,
            "Open File",
            expanduser("~"),
            "(*.md)"
        )

        if f_dir[0] != "":
            self.file_path = f_dir[0]
            with open(f_dir[0], "r") as f:
                self.setPlainText(f.read())
            sig.status_bar_message.emit(
                "Opened File")

    def save_file(self):
        if self.file_path == "":
            fd = QFileDialog()
            fileName, _ = fd.getSaveFileName(
                self,
                "Save File",
                os.path.join(expanduser("~"), ".md"),
                "(*.md)")
            if fileName == "":
                return
            self.file_path = fileName

            sig.status_bar_message.emit("Saving File")
            with open(fileName, "w") as f:
                f.write(self.toPlainText())
            sig.status_bar_message.emit("File Saved")
            return

        sig.status_bar_message.emit("Saving File")
        with open(self.file_path, "w") as f:
            f.write(self.toPlainText())
        sig.status_bar_message.emit("File Saved")

class MainWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.init_me()

    def init_me(self):
        self.h = QHBoxLayout(self)

        self.edit = Editor()
        self.browser = Browser()

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.edit)
        self.splitter.addWidget(self.browser)

        self.h.addWidget(self.splitter)

        self.setLayout(self.h)

class Window(QMainWindow):
    def __init__(self):
        super().__init__()

        sig.status_bar_message.connect(self.set_status_bar_info)
        self.init_me()

    def init_me(self):

        self.state = QStatusBar(self)  # Create Statusbar

        self.setStatusBar(self.state)

        open = QAction("open", self)
        open.setShortcut("Ctrl+O")
        open.setStatusTip("open File")
        open.triggered.connect(self.open_file)

        save = QAction("save", self)
        save.setShortcut("Ctrl+S")
        save.setStatusTip("save File")
        save.triggered.connect(self.save_file)

        print_to_pdf = QAction("print to pdf", self)
        print_to_pdf.setShortcut("Ctrl+P")
        print_to_pdf.setStatusTip("print File")
        print_to_pdf.triggered.connect(self.print_file)

        menubar = self.menuBar()
        file = menubar.addMenu("File")
        file.addAction(open)
        file.addAction(save)
        file.addAction(print_to_pdf)

        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.setWindowTitle("NeonNote")

        self.setWindowIcon(QIcon("images/icon.png"))

        self.mainwidget = MainWidget()
        self.setCentralWidget(self.mainwidget)

        self.show()

    def set_status_bar_info(self, e):  # Set text of the statusbar
        self.state.showMessage(e)

    def open_file(self):
        self.set_status_bar_info("opening file")
        sig.open_file.emit()

    def save_file(self):
        sig.save_file.emit()

    def print_file(self):
        sig.print_file.emit()


if __name__ == '__main__':
    p = Process(target=server.start, args=(child_conn,))
    p.start()
    w = Window()

    app.exec_()
    p.kill()
    sys.exit()
