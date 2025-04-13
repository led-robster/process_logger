import wmi
import sys
import logging
import threading
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWidgets import QDialog
import random


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
        self.searchButton.setToolTip("Search matching pattern")

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
    # self.high_lines = number of entry lines CURRENTLY highlighted; gets **resetted** by clear_highlight(), increments when highlighting

    def __init__(self, parent):
        super().__init__()
        self.widget = QtWidgets.QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        self.lineCnt = 0
        self.high_lines = 0
        # yellow tones
        self.user_color = QtGui.QColor('yellow') # default highlight color
        self.color_tones = []
        self.update_color_tones()
        self.yellow_tones = [QtGui.QColor(255, 255, 204, 255), QtGui.QColor(255, 247, 0, 255), QtGui.QColor(255, 215, 0, 255), QtGui.QColor(204, 153, 0, 255), QtGui.QColor(184, 134, 11, 255)]
        self.tone_cnt = 0

    def emit(self, record):
        self.lineCnt += 1
        msg = self.format(record)
        self.widget.appendPlainText(msg)

    def getWidget(self):
        return self.widget
    
    def setUserColor(self, picked_color: QtGui.QColor):
        self.user_color = picked_color
        self.update_color_tones()

    def update_color_tones(self):

        base_h, base_s, base_l, _ = self.user_color.getHsl()

        self.color_tones = []
        for i in range(5):
            # Slightly tweak hue, saturation, and lightness
            hue_variation = (base_h + random.randint(-10, 10)) % 360
            sat_variation = max(0, min(255, base_s + random.randint(-30, 30)))
            light_variation = max(0, min(255, base_l + random.randint(-40, 40)))

            variant = QtGui.QColor()
            variant.setHsl(hue_variation, sat_variation, light_variation)
            self.color_tones.append(variant)

        return
    
    def highlightLine(self, searchString):

        highlight_fmt = QtGui.QTextCharFormat()
        # highlight_fmt.setBackground(QtGui.QColor("yellow"))
        highlight_fmt.setBackground(self.color_tones[self.tone_cnt])
        self.tone_cnt += 1
        self.tone_cnt %= len(self.color_tones)

        cursor = self.widget.textCursor()
        # get default text format
        dft_fmt = QtGui.QTextCharFormat()
        dft_fmt.setBackground(QtGui.QColor("white"))

        # move cursor to start
        cursor.movePosition(QtGui.QTextCursor.Start)
        # inspect each line
        for i in range(1, self.widget.blockCount()+1): ##

            cursor.select(QtGui.QTextCursor.LineUnderCursor)
            line_text = cursor.selectedText()

            if searchString.lower() in line_text.lower().replace(".", " "):
                # if line was already highlighted, then ignore incrementing counter
                if cursor.charFormat().background().color().name() in [i.name() for i in self.color_tones]:
                    #"#ffff00":
                    pass
                else:
                    # print(cursor.charFormat().background().color().name())
                    self.high_lines += 1

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
        # last_line_text = cursor.selectedText()
        # if searchString.lower() in line_text.lower().replace(".", " "):
        #         # highlight
        #         cursor.setCharFormat(highlight_fmt)

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

        # reset highlighted lines counter
        self.high_lines = 0

        print("ended clear")

    def getHighlightedLines(self):
        return self.high_lines


# Dialog-style widget. Contains QTextEditLogger.
class MyDialog(QtWidgets.QDialog, QtWidgets.QPlainTextEdit):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.posted_lines_cnt = 0

        self.user_color = QtGui.QColor()

        # menubar
        self.menubar = QtWidgets.QMenuBar()
        self.menubar.setMinimumWidth(self.width())

        self.tools_menu = self.menubar.addMenu('Tools')

        color_action = QtGui.QAction('Choose highlight color...', self)
        color_action.triggered.connect(self.color_palette_picker)

        self.tools_menu.addAction(color_action)

        # searchbar
        self.searchBar = Searchbar(self)
        self.searchButt = self.searchBar.getSearchButton()
        self.searchButt.clicked.connect(self.search_and_highlight)

        self.CLButton = self.searchBar.getCLButton()
        self.CLButton.clicked.connect(self.clearEditField)

        self.ctrlAButt = QtWidgets.QPushButton("🗒️", self)
        self.ctrlAButt.setToolTip("Copy to clipboard")
        self.ctrlAButt.clicked.connect(self.copyAll)

        self.logTextBox = QTextEditLogger(self)
        # You can format what is printed to text box
        self.logTextBox.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(self.logTextBox)
        # You can control the logging level
        logging.getLogger().setLevel(logging.DEBUG)

        self.layout = QtWidgets.QVBoxLayout()
        # First add menubar
        self.layout.setMenuBar(self.menubar)

        self.top_hbox = QtWidgets.QHBoxLayout()
        self.top_hbox.addWidget(self.searchBar)
        self.top_hbox.addWidget(self.ctrlAButt)
        self.layout.addLayout(self.top_hbox)
        # Add the new logging box widget to the layout
        self.layout.addWidget(self.logTextBox.widget)

        # bottom hbox
        self.bottom_hbox = QtWidgets.QHBoxLayout()
        self.layout.addLayout(self.bottom_hbox)

        # Add stats line at the end
        self.stats_line = QtWidgets.QLabel("0 entries. 0 selected.", self) # initialized at Zero
        self.bottom_hbox.addWidget(self.stats_line)

        # QLabel for actions
        self.action_label = QtWidgets.QLabel("", self) # blank init
        self.action_label.setAlignment(QtCore.Qt.AlignRight)
        self.bottom_hbox.addWidget(self.action_label)


        self.setLayout(self.layout)

        # initialize worker
        self.worker = Worker()
        self.worker.process_detected.connect(self.post)
        # run worker in separate thread
        self.worker_thread = threading.Thread(target=self.worker.run, daemon=True)
        self.worker_thread.start()

    # capture resize event
    def resizeEvent(self, event):
        self.menubar.setMinimumWidth(self.width())
        super().resizeEvent(event)


    def color_palette_picker(self):
        self.user_color = QtWidgets.QColorDialog.getColor()
        if self.user_color.isValid():
            hex_color = self.user_color.name()  # Gets hex code like "#ff5733"
            print("Selected Color", f"You picked: {hex_color}")
        # update QTextEditLogger
        self.logTextBox.setUserColor(self.user_color)

    # log with severity 'info'
    def post(self, text):
        # update number of entries and the associated QLabel
        self.posted_lines_cnt += 1
        stats_line_text = f"{self.posted_lines_cnt} entries. {self.getHighlightedLines()} selected." 
        self.stats_line.setText(stats_line_text)
        logging.info(text)

    def search_and_highlight(self):
        searchString = self.searchBar.getString()
        self.logTextBox.highlightLine(searchString)
        # update highlighted lines
        self.stats_line.setText(f"{self.posted_lines_cnt} entries. {self.getHighlightedLines()} selected.")

    def getHighlightedLines(self):
        return self.logTextBox.getHighlightedLines()

    def clearEditField(self):
        self.logTextBox.clearHighlight()
        # update highlighted lines	
        self.stats_line.setText(f"{self.posted_lines_cnt} entries. {self.getHighlightedLines()} selected.")

    def copyAll(self):
        all_text = self.logTextBox.getWidget().toPlainText()
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(all_text)
        # update comment status
        self.set_command_status("Copied to clipboard")

    def set_command_status(self, stringa):
        self.action_label.setText(stringa)


    def closeEvent(self, event):
        # ensure that thread stops on exit
        self.action_label.setText("Closing...")
        bold_font = QtGui.QFont()
        bold_font.setBold(True)
        self.action_label.setFont(bold_font)
        # Force UI update
        QtWidgets.QApplication.processEvents()  # ✅ Ensures label updates immediately
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
    # sys.argv required for clipboarding
    app = QtWidgets.QApplication(sys.argv)

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
