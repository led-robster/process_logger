import wmi
import sys
import logging
import threading
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWidgets import QDialog


class Worker(QtCore.QObject):
    process_detected = QtCore.Signal(str)  # Signal to send process names to the UI
    stop_signal = False  # Flag to stop the thread

    def run(self):
        """Thread worker function."""
        c = wmi.WMI()
        process_watcher = c.Win32_Process.watch_for("creation")

        while not self.stop_signal:
            try:
                new_process = process_watcher()
                process_str = str(new_process.Caption)
                self.process_detected.emit(process_str)  # Emit to UI safely
            except Exception as e:
                print(f"Error: {e}")

    def stop(self):
        """Stops the worker thread."""
        self.stop_signal = True


class Searchbar(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.searchField = QtWidgets.QLineEdit("Search for process...")

        self.searchButton = QtWidgets.QPushButton("🔎")

        self.clearButton = QtWidgets.QPushButton("🆑")
        self.clearButton.setToolTip("Clear search bar")

        self.layout = QtWidgets.QHBoxLayout()

        self.layout.addWidget(self.searchField)
        self.layout.addWidget(self.searchButton)
        self.layout.addWidget(self.clearButton)

        self.setLayout(self.layout)

    def getSearchButton(self):
        return self.searchButton
    def getCLButton(self):
        return self.clearButton
    
    def getString(self):
        return self.searchField.text()



# A custom widget that inherits from logging.Handler. Baiscally it is a QPlainTextEdit.
class QTextEditLogger(logging.Handler):
    # self.lineCnt ; counts the emitted lines

    def __init__(self, parent):
        super().__init__()
        self.widget = QtWidgets.QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        self.lineCnt = 0

    def emit(self, record):
        self.lineCnt += 1
        msg = self.format(record)
        self.widget.appendPlainText(msg)

    def getWidget(self):
        return self.widget
    
    def highlightLine(self, searchString):

        highlight_fmt = QtGui.QTextCharFormat()
        highlight_fmt.setBackground(QtGui.QColor("yellow"))

        cursor = self.widget.textCursor()
        # get default text format
        dft_fmt = QtGui.QTextCharFormat()
        dft_fmt.setBackground(QtGui.QColor("white"))

        # move cursor to start
        cursor.movePosition(QtGui.QTextCursor.Start)
        # inspect each line
        for i in range(1, self.widget.blockCount()): ##

            cursor.select(QtGui.QTextCursor.LineUnderCursor)
            line_text = cursor.selectedText()

            if searchString.lower() in line_text.lower().replace(".", " "):
                # highlight
                # print("found")
                cursor.setCharFormat(highlight_fmt)
            else:
                # print(f"line#{i} hasn't the string : {searchString.lower()}\n line#{i} is : {line_text.lower()}")
                pass

            cursor.movePosition(QtGui.QTextCursor.Down)

        # make sure cursor is at the end
        cursor.movePosition(QtGui.QTextCursor.End)
        # double check last line content
        last_line_text = cursor.selectedText()
        if searchString.lower() in line_text.lower().replace(".", " "):
                # highlight
                cursor.setCharFormat(highlight_fmt)

        # reset text format
        cursor.setCharFormat(dft_fmt)
        print("ended search")

    def clearHighlight(self):
        highlight_fmt = QtGui.QTextCharFormat()
        highlight_fmt.setBackground(QtGui.QColor("white"))

        cursor = self.widget.textCursor()
        # move cursor to start
        cursor.movePosition(QtGui.QTextCursor.Start)
        # inspect each line
        for i in range(1, self.lineCnt+1):

            cursor.select(QtGui.QTextCursor.LineUnderCursor)
            cursor.setCharFormat(highlight_fmt)
            cursor.movePosition(QtGui.QTextCursor.Down)

        print("ended clear")


# Dialog-style widget. Contains QTextEditLogger.
class MyDialog(QtWidgets.QDialog, QtWidgets.QPlainTextEdit):

    def __init__(self, parent=None):
        super().__init__(parent)

        # searchbar
        self.searchBar = Searchbar(self)
        self.searchButt = self.searchBar.getSearchButton()
        self.searchButt.clicked.connect(self.search_and_highlight)

        self.CLButton = self.searchBar.getCLButton()
        self.CLButton.clicked.connect(self.clearEditField)

        self.logTextBox = QTextEditLogger(self)
        # You can format what is printed to text box
        self.logTextBox.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(self.logTextBox)
        # You can control the logging level
        logging.getLogger().setLevel(logging.DEBUG)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.searchBar)
        # Add the new logging box widget to the layout
        layout.addWidget(self.logTextBox.widget)
        self.setLayout(layout)

        # initialize worker
        self.worker = Worker()
        self.worker.process_detected.connect(self.post)
        # run worker in separate thread
        self.worker_thread = threading.Thread(target=self.worker.run, daemon=True)
        self.worker_thread.start()


    # log with severity 'info'
    def post(self, text):
        logging.info(text)

    def search_and_highlight(self):
        searchString = self.searchBar.getString()
        self.logTextBox.highlightLine(searchString)

    def clearEditField(self):
        self.logTextBox.clearHighlight()

    def closeEvent(self, event):
        # ensure that thread stops on exit
        self.worker.stop()
        self.worker_thread.join()
        event.accept()

# global function.
# runs when application closes
def cleanup(thread):
    thread.stop()




if __name__ == "__main__":

    stop_flag = False

    # open application
    app = QtWidgets.QApplication([])

    # create widget
    widget = MyDialog()
    widget.resize(800, 600)
    widget.show()

    # add worker function
    # worker = Worker()

    # Create the thread and pass arguments
    # the thread runs the process_watcher and emits on widget
    # worker_thread = threading.Thread(target=worker.do_work, args=(widget,))
    # Start the thread
    # worker_thread.start()

    # wmi instance
    # c = wmi.WMI ()
    # process_watcher = c.Win32_Process.watch_for("creation")
        
    # while not stop_flag:  # Keep working unless stop_flag is set
    #     new_process = process_watcher()
    #     process_str = str(new_process.Caption)
    #     widget.post(process_str)


    # Connect the aboutToQuit signal to the cleanup function
    # from when you tap X to close application, 30 seconds can pass to close thread.
    # app.aboutToQuit.connect(lambda: stop_cycle())

    # widget.raise_()
    # close application
    sys.exit(app.exec())
