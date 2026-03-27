import sys
import os
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QCheckBox, QComboBox, QLabel, QFileDialog, 
    QTextEdit, QTabWidget, QGroupBox, QLineEdit, QScrollArea
)
from PyQt6.QtCore import Qt, QProcess, pyqtSignal

class GuiLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Domophone Autotest Launcher")
        self.setGeometry(100, 100, 900, 700)
        
        # Основной виджет и табы
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
      # Создаем вкладки
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        self.init_test_tab()
        self.init_sync_tab()
        self.init_api_sync_tab()  # Новая вкладка
        self.init_param_tab()
        
        # Лог вывода
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas;")
        self.layout.addWidget(QLabel("Output Log:"))
        self.layout.addWidget(self.log_output)
        
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)

    def init_test_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Группа фильтров
        filter_group = QGroupBox("Filters")
        filter_layout = QVBoxLayout()
        
        # Прошивка
        fw_layout = QHBoxLayout()
        fw_layout.addWidget(QLabel("Firmware Version:"))
        self.fw_combo = QComboBox()
        self.fw_combo.addItems(["Auto (from API)", "Auto (from Config)"]) # В будущем подгружать из БД
        fw_layout.addWidget(self.fw_combo)
        filter_layout.addLayout(fw_layout)
        
        # Типы тестов
        type_layout = QHBoxLayout()
        self.cb_positive = QCheckBox("Positive")
        self.cb_positive.setChecked(True)
        self.cb_negative = QCheckBox("Negative")
        self.cb_boundary = QCheckBox("Boundary")
        type_layout.addWidget(self.cb_positive)
        type_layout.addWidget(self.cb_negative)
        type_layout.addWidget(self.cb_boundary)
        filter_layout.addLayout(type_layout)
        
        # Контроль
        control_layout = QHBoxLayout()
        self.cb_api = QCheckBox("API Control")
        self.cb_api.setChecked(True)
        self.cb_web = QCheckBox("Web Control")
        self.cb_config = QCheckBox("Config Control")
        control_layout.addWidget(self.cb_api)
        control_layout.addWidget(self.cb_web)
        control_layout.addWidget(self.cb_config)
        filter_layout.addLayout(control_layout)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Кнопка запуска
        run_btn = QPushButton("Run Selected Tests")
        run_btn.setFixedHeight(40)
        run_btn.setStyleSheet("background-color: #007acc; color: white; font-weight: bold;")
        run_btn.clicked.connect(self.run_tests)
        layout.addWidget(run_btn)
        
        layout.addStretch()
        self.tabs.addTab(tab, "Test Execution")

    def init_sync_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        sync_group = QGroupBox("Configuration Sync")
        sync_layout = QVBoxLayout()
        
        # Выбор файла
        file_layout = QHBoxLayout()
        self.config_file_path = QLineEdit()
        self.config_file_path.setPlaceholderText("Path to decrypted configuration file...")
        file_layout.addWidget(self.config_file_path)
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browse_config_file)
        file_layout.addWidget(btn_browse)
        sync_layout.addLayout(file_layout)
        
        # Версия прошивки
        fw_sync_layout = QHBoxLayout()
        fw_sync_layout.addWidget(QLabel("Target Firmware (Optional):"))
        self.sync_fw_input = QLineEdit()
        self.sync_fw_input.setPlaceholderText("e.g. 2025.05.175445501")
        fw_sync_layout.addWidget(self.sync_fw_input)
        sync_layout.addLayout(fw_sync_layout)
        
        sync_btn = QPushButton("Start Synchronization")
        sync_btn.clicked.connect(self.run_sync)
        sync_layout.addWidget(sync_btn)
        
        sync_group.setLayout(sync_layout)
        layout.addWidget(sync_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "Config Sync")

    def init_api_sync_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        api_group = QGroupBox("API Methods Sync")
        api_layout = QVBoxLayout()
        
        # Версия прошивки
        fw_api_layout = QHBoxLayout()
        fw_api_layout.addWidget(QLabel("Target Firmware:"))
        self.api_fw_input = QLineEdit()
        self.api_fw_input.setPlaceholderText("e.g. 2025.05.175445501")
        fw_api_layout.addWidget(self.api_fw_input)
        api_layout.addLayout(fw_api_layout)
        
        # Выбор коллекции Postman
        coll_layout = QHBoxLayout()
        self.api_coll_path = QLineEdit()
        self.api_coll_path.setPlaceholderText("Path to Postman collection (optional)...")
        coll_layout.addWidget(self.api_coll_path)
        btn_browse_coll = QPushButton("Browse")
        btn_browse_coll.clicked.connect(self.browse_collection)
        coll_layout.addWidget(btn_browse_coll)
        api_layout.addLayout(coll_layout)
        
        api_btn = QPushButton("Launch Interactive API Sync")
        api_btn.clicked.connect(self.run_api_sync)
        api_layout.addWidget(api_btn)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "API Sync")

    def init_param_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Section for manual parameter setup on device (TBD)"))
        layout.addStretch()
        self.tabs.addTab(tab, "Parameter Setup")

    def browse_config_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Config File", "", "Config Files (*.json *.yaml *.yml *.dat);;All Files (*)")
        if file_path:
            self.config_file_path.setText(file_path)

    def browse_collection(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Postman Collection", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            self.api_coll_path.setText(file_path)

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8")
        self.log_output.append(data)

    def handle_stderr(self):
        data = self.process.readAllStandardError().data().decode("utf-8")
        self.log_output.append(f"<span style='color: #f44747;'>{data}</span>")

    def run_tests(self):
        self.log_output.clear()
        args = ["-m"]
        marks = []
        if self.cb_positive.isChecked(): marks.append("positive")
        if self.cb_negative.isChecked(): marks.append("negative")
        if self.cb_boundary.isChecked(): marks.append("boundary")
        
        if not marks:
            self.log_output.append("Error: No test types selected!")
            return
            
        args.append(" or ".join(marks))
        
        controls = []
        if self.cb_api.isChecked(): controls.append("api")
        if self.cb_web.isChecked(): controls.append("web")
        if self.cb_config.isChecked(): controls.append("config")
        
        if controls:
            args.append(f"--control={','.join(controls)}")
            
        self.log_output.append(f"Running command: pytest {' '.join(args)}\n")
        self.process.start("pytest", args)

    def run_sync(self):
        config_path = self.config_file_path.text()
        if not config_path:
            self.log_output.append("Error: Select config file first!")
            return
            
        self.log_output.clear()
        args = ["domophone-tests/tools/config_sync.py", config_path]
        
        fw = self.sync_fw_input.text()
        if fw:
            args.extend(["-fw", fw])
            
        self.log_output.append(f"Running command: python {' '.join(args)}\n")
        # Для интерактивности в будущем нужно будет использовать терминал, 
        # но пока запускаем как процесс
        self.process.start("python", args)

    def run_api_sync(self):
        fw = self.api_fw_input.text()
        if not fw:
            self.log_output.append("Error: Enter firmware version first!")
            return
            
        self.log_output.append(f"Launching interactive API sync for {fw} in a new terminal...\n")
        
        # Запускаем в новом окне терминала для интерактивности
        coll_path = self.api_coll_path.text()
        coll_arg = f' --collection "{coll_path}"' if coll_path else ""
        
        if os.name == 'nt': # Windows
            cmd = f'start cmd /k python domophone-tests/tools/api_sync.py {fw}{coll_arg}'
            os.system(cmd)
        else: # Linux/Mac
            cmd = f"x-terminal-emulator -e 'python3 domophone-tests/tools/api_sync.py {fw}{coll_arg}'"
            os.system(cmd)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GuiLauncher()
    window.show()
    sys.exit(app.exec())
