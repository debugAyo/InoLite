import sys
import os
import serial

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QComboBox, QPlainTextEdit, 
    QLabel, QSplitter, QTabWidget, QLineEdit, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QAction

from arduino_backend import ArduinoCLIWrapper
from syntax_highlighter import ArduinoHighlighter
from code_editor import ArduinoCodeEditor


class SerialReaderThread(QThread):
    data_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, port: str, baudrate: int = 9600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.running = True
        self.ser = None

    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.5)
            self.data_received.emit(f"--- Connected to {self.port} at {self.baudrate} baud ---\n")
            while self.running:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='replace')
                    if line:
                        self.data_received.emit(line)
                else:
                    self.msleep(20)
        except serial.SerialException as e:
            self.error_occurred.emit(f"Serial Error: {e}")
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()
                self.data_received.emit(f"--- Disconnected from {self.port} ---\n")

    def send_data(self, text: str):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((text + '\n').encode('utf-8'))
            except serial.SerialException as e:
                self.error_occurred.emit(f"Write Error: {e}")

    def stop(self):
        self.running = False
        self.wait()


class DeviceWatcherThread(QThread):
    boards_updated = pyqtSignal(list)

    def __init__(self, engine, poll_interval_ms: int = 1500):
        super().__init__()
        self.engine = engine
        self.interval = poll_interval_ms / 1000.0
        self.running = True
        self._last_signature = None

    def run(self):
        while self.running:
            boards = self.engine.detect_boards()
            signature = tuple(sorted((b.get("port", ""), b.get("fqbn", "")) for b in boards))
            if signature != self._last_signature:
                self._last_signature = signature
                self.boards_updated.emit(boards)
            self.msleep(int(self.interval * 1000))

    def stop(self):
        self.running = False
        self.wait()


class WorkerThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, engine, sketch_dir, fqbn, port):
        super().__init__()
        self.engine = engine
        self.sketch_dir = sketch_dir
        self.fqbn = fqbn
        self.port = port

    def run(self):
        self.log_signal.emit(f"Compiling sketch for {self.fqbn}...")
        ok, comp_log = self.engine.compile(self.sketch_dir, self.fqbn)
        self.log_signal.emit(comp_log.strip())

        if not ok:
            self.finished_signal.emit(False, "Compilation failed.")
            return

        self.log_signal.emit(f"\nUploading to {self.port}...")
        up_ok, up_log = self.engine.upload(self.sketch_dir, self.fqbn, self.port)
        self.log_signal.emit(up_log.strip())

        if up_ok:
            self.finished_signal.emit(True, "Upload complete!")
        else:
            self.finished_signal.emit(False, "Upload failed.")


class MiniArduinoIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lightweight Arduino IDE")
        self.resize(950, 700)

        self.engine = ArduinoCLIWrapper(".\\arduino-cli.exe")
        self.detected_boards = []
        
        # File management paths
        self.sketch_dir = os.path.abspath(".\\BlinkTest")
        self.sketch_file = os.path.join(self.sketch_dir, "BlinkTest.ino")

        self.serial_thread = None

        self.init_ui()
        self.init_menus()
        self.load_sketch(self.sketch_file)

        # Hardware watcher
        self.watcher = DeviceWatcherThread(self.engine, poll_interval_ms=1200)
        self.watcher.boards_updated.connect(self.on_boards_detected)
        self.watcher.start()

    def init_menus(self):
        """Creates the File menu with standard shortcuts."""
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")

        # New Sketch (Ctrl+N)
        new_act = QAction("&New Sketch", self)
        new_act.setShortcut(QKeySequence.StandardKey.New)
        new_act.triggered.connect(self.file_new)
        file_menu.addAction(new_act)

        # Open Sketch (Ctrl+O)
        open_act = QAction("&Open Sketch...", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self.file_open)
        file_menu.addAction(open_act)

        # Save Sketch (Ctrl+S)
        save_act = QAction("&Save", self)
        save_act.setShortcut(QKeySequence.StandardKey.Save)
        save_act.triggered.connect(self.file_save)
        file_menu.addAction(save_act)

        # Save As... (Ctrl+Shift+S)
        save_as_act = QAction("Save &As...", self)
        save_as_act.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_act.triggered.connect(self.file_save_as)
        file_menu.addAction(save_as_act)

        file_menu.addSeparator()

        # Exit (Ctrl+Q)
        exit_act = QAction("E&xit", self)
        exit_act.setShortcut(QKeySequence.StandardKey.Quit)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # 1. Top Control Bar
        toolbar_layout = QHBoxLayout()

        self.board_selector = QComboBox()
        self.board_selector.setMinimumWidth(260)
        toolbar_layout.addWidget(self.board_selector)

        self.upload_btn = QPushButton("Upload")
        self.upload_btn.setStyleSheet("font-weight: bold; background-color: #007acc; color: white;")
        self.upload_btn.clicked.connect(self.start_upload)
        toolbar_layout.addWidget(self.upload_btn)

        toolbar_layout.addSpacing(20)

        # Serial Monitor Toolbar Controls
        self.baud_selector = QComboBox()
        self.baud_selector.addItems(["9600", "19200", "38400", "57600", "115200", "230400"])
        self.baud_selector.setCurrentText("9600")
        toolbar_layout.addWidget(QLabel("Baud:"))
        toolbar_layout.addWidget(self.baud_selector)

        self.serial_toggle_btn = QPushButton("Connect Serial")
        self.serial_toggle_btn.clicked.connect(self.toggle_serial)
        toolbar_layout.addWidget(self.serial_toggle_btn)

        toolbar_layout.addStretch()

        self.status_label = QLabel("Scanning hardware...")
        toolbar_layout.addWidget(self.status_label)
        main_layout.addLayout(toolbar_layout)

        # 2. Central Splitter (Editor on top, Tabs on bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Code Editor Pane with Line Numbers and Highlighting
        self.editor = ArduinoCodeEditor()
        self.editor.setFont(QFont("Consolas", 11))
        self.highlighter = ArduinoHighlighter(self.editor.document())
        splitter.addWidget(self.editor)

        # Tab Widget for Bottom Panel
        self.tabs = QTabWidget()

        # Tab 1: Build Output
        self.build_console = QPlainTextEdit()
        self.build_console.setReadOnly(True)
        self.build_console.setFont(QFont("Consolas", 10))
        self.build_console.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        self.tabs.addTab(self.build_console, "Build Output")

        # Tab 2: Serial Monitor
        serial_widget = QWidget()
        serial_layout = QVBoxLayout(serial_widget)
        serial_layout.setContentsMargins(4, 4, 4, 4)

        self.serial_console = QPlainTextEdit()
        self.serial_console.setReadOnly(True)
        self.serial_console.setFont(QFont("Consolas", 10))
        self.serial_console.setStyleSheet("background-color: #121212; color: #4af626;")
        serial_layout.addWidget(self.serial_console)

        send_layout = QHBoxLayout()
        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText("Type message and press Enter...")
        self.serial_input.returnPressed.connect(self.send_serial_message)
        send_layout.addWidget(self.serial_input)

        self.serial_send_btn = QPushButton("Send")
        self.serial_send_btn.clicked.connect(self.send_serial_message)
        send_layout.addWidget(self.serial_send_btn)

        serial_layout.addLayout(send_layout)
        self.tabs.addTab(serial_widget, "Serial Monitor")

        splitter.addWidget(self.tabs)
        splitter.setSizes([450, 200])
        main_layout.addWidget(splitter)

    # --- File Management Methods ---
    def load_sketch(self, file_path: str):
        """Loads sketch text and updates window metadata."""
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                self.editor.setPlainText(f.read())
            self.sketch_file = os.path.abspath(file_path)
            self.sketch_dir = os.path.dirname(self.sketch_file)
            sketch_name = os.path.basename(self.sketch_file)
            self.setWindowTitle(f"Lightweight Arduino IDE - {sketch_name}")
            self.status_label.setText(f"Loaded: {sketch_name}")

    def file_new(self):
        """Initializes a clean template sketch."""
        template = (
            "void setup() {\n"
            "  // put your setup code here, to run once:\n\n"
            "}\n\n"
            "void loop() {\n"
            "  // put your main code here, to run repeatedly:\n\n"
            "}\n"
        )
        self.editor.setPlainText(template)
        self.sketch_file = None
        self.sketch_dir = None
        self.setWindowTitle("Lightweight Arduino IDE - [Untitled]")
        self.status_label.setText("New sketch ready. Use File > Save As to choose a location.")

    def file_open(self):
        """Opens an existing .ino sketch."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Arduino Sketch", "", "Arduino Sketch (*.ino);;All Files (*)"
        )
        if file_path:
            self.load_sketch(file_path)

    def file_save(self):
        """Saves current buffer. Prompts Save As if untitled."""
        if not self.sketch_file:
            self.file_save_as()
            return

        with open(self.sketch_file, "w", encoding="utf-8") as f:
            f.write(self.editor.toPlainText())
        self.status_label.setText(f"Saved: {os.path.basename(self.sketch_file)}")

    def file_save_as(self):
        """Enforces the Arduino folder-matching requirement when saving a new sketch."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Arduino Sketch As", "", "Arduino Sketch (*.ino)"
        )
        if not file_path:
            return

        if not file_path.endswith(".ino"):
            file_path += ".ino"

        sketch_name = os.path.splitext(os.path.basename(file_path))[0]
        chosen_dir = os.path.dirname(file_path)

        # Enforce Arduino CLI directory rule: /SketchName/SketchName.ino
        if os.path.basename(chosen_dir) != sketch_name:
            target_dir = os.path.join(chosen_dir, sketch_name)
            os.makedirs(target_dir, exist_ok=True)
            target_file = os.path.join(target_dir, f"{sketch_name}.ino")
        else:
            target_dir = chosen_dir
            target_file = file_path

        self.sketch_dir = os.path.abspath(target_dir)
        self.sketch_file = os.path.abspath(target_file)

        with open(self.sketch_file, "w", encoding="utf-8") as f:
            f.write(self.editor.toPlainText())

        self.setWindowTitle(f"Lightweight Arduino IDE - {sketch_name}.ino")
        self.status_label.setText(f"Saved as: {sketch_name}.ino")

    # --- Hardware Watcher & Ports ---
    def on_boards_detected(self, boards: list):
        current_data = self.board_selector.currentData()
        current_port = current_data.get("port") if current_data else None

        self.board_selector.clear()
        self.detected_boards = boards

        if not self.detected_boards:
            self.board_selector.addItem("No boards detected", None)
            self.upload_btn.setEnabled(False)
            self.serial_toggle_btn.setEnabled(False)
            self.status_label.setText("No hardware connected")
            return

        reselect_index = 0
        for idx, board in enumerate(self.detected_boards):
            label = f"{board['name']} ({board['port']})"
            self.board_selector.addItem(label, board)
            if current_port and board.get("port") == current_port:
                reselect_index = idx

        self.board_selector.setCurrentIndex(reselect_index)
        self.upload_btn.setEnabled(True)
        self.serial_toggle_btn.setEnabled(True)
        self.status_label.setText(f"Active: {len(self.detected_boards)} board(s)")

    # --- Serial Communication ---
    def toggle_serial(self):
        if self.serial_thread and self.serial_thread.isRunning():
            self.disconnect_serial()
        else:
            self.connect_serial()

    def connect_serial(self):
        current_board = self.board_selector.currentData()
        if not current_board or not current_board.get("port"):
            self.serial_console.appendPlainText("[Error] No active serial port selected.")
            return

        port = current_board["port"]
        baud = int(self.baud_selector.currentText())

        self.watcher.stop()

        self.serial_thread = SerialReaderThread(port, baud)
        self.serial_thread.data_received.connect(self.append_serial_data)
        self.serial_thread.error_occurred.connect(self.handle_serial_error)
        self.serial_thread.start()

        self.serial_toggle_btn.setText("Disconnect")
        self.serial_toggle_btn.setStyleSheet("color: red; font-weight: bold;")
        self.tabs.setCurrentIndex(1)

    def disconnect_serial(self):
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread = None

        self.serial_toggle_btn.setText("Connect Serial")
        self.serial_toggle_btn.setStyleSheet("")

        if not self.watcher.isRunning():
            self.watcher.start()

    def append_serial_data(self, data: str):
        self.serial_console.insertPlainText(data)
        self.serial_console.verticalScrollBar().setValue(
            self.serial_console.verticalScrollBar().maximum()
        )

    def handle_serial_error(self, err_msg: str):
        self.serial_console.appendPlainText(f"\n[Serial Error] {err_msg}")
        self.disconnect_serial()

    def send_serial_message(self):
        if self.serial_thread and self.serial_thread.isRunning():
            text = self.serial_input.text()
            if text:
                self.serial_thread.send_data(text)
                self.serial_input.clear()

    # --- Compile & Upload Workflow ---
    def start_upload(self):
        current_board = self.board_selector.currentData()
        if not current_board or not current_board.get("fqbn"):
            self.build_console.appendPlainText("[Error] Please select a recognized board with a valid FQBN.")
            return

        # Ensure file is saved before uploading
        if not self.sketch_file:
            self.file_save_as()
            if not self.sketch_file:
                return
        else:
            self.file_save()

        if self.serial_thread and self.serial_thread.isRunning():
            self.disconnect_serial()

        self.watcher.stop()

        self.upload_btn.setEnabled(False)
        self.status_label.setText("Working...")
        self.tabs.setCurrentIndex(0)
        self.build_console.clear()

        self.worker = WorkerThread(
            engine=self.engine,
            sketch_dir=self.sketch_dir,
            fqbn=current_board["fqbn"],
            port=current_board["port"]
        )
        self.worker.log_signal.connect(self.build_console.appendPlainText)
        self.worker.finished_signal.connect(self.upload_finished)
        self.worker.start()

    def upload_finished(self, success, summary):
        self.status_label.setText(summary)
        self.upload_btn.setEnabled(True)
        if not self.watcher.isRunning():
            self.watcher.start()

    def closeEvent(self, event):
        self.disconnect_serial()
        self.watcher.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MiniArduinoIDE()
    window.show()
    sys.exit(app.exec())