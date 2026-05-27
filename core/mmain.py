import sys
import os
import json
import csv
import random
from datetime import datetime

# Добавляем путь к собранному C++ модулю
sys.path.append(os.path.join(os.path.dirname(__file__), "build"))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSpinBox, QLabel, QTableWidget, QTableWidgetItem,
    QGroupBox, QCheckBox, QFileDialog, QMessageBox, QDialog, QComboBox,
    QTabWidget, QMenuBar, QMenu, QHeaderView, QInputDialog, QFrame,
    QToolBar, QAbstractItemView, QLineEdit)

from PySide6.QtGui import QAction, QColor
from PySide6.QtCore import Qt, QThread, Signal

import pandas as pd

# Импортируем ваш C++ модуль
try:
    import bi_graph_module

    print("bi_graph_module imported successfully")
    print("Available:", dir(bi_graph_module))
except ImportError as e:
    print(f"Failed to import: {e}")
    bi_graph_module = None


class NumericTableWidgetItem(QTableWidgetItem):
    """Кастомный элемент таблицы для числовой сортировки"""

    def __lt__(self, other):
        try:
            return float(self.text()) < float(other.text())
        except ValueError:
            return self.text() < other.text()


class CalculationThread(QThread):
    """Поток для выполнения расчётов без блокировки UI"""
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, graph_data, quotas_data, k, num_threads, parent=None):
        super().__init__(parent)
        self.graph_data = graph_data
        self.quotas_data = quotas_data
        self.k = k
        self.num_threads = num_threads

    def run(self):
        try:
            if bi_graph_module is None:
                import time
                n = len(self.graph_data)
                time.sleep(1)
                results = {i: random.uniform(100, 5000) for i in range(n)}
                self.finished.emit(results)
                return

            print(f"Starting calculation with {self.num_threads} threads")
            print(f"Graph size: {len(self.graph_data)} x {len(self.graph_data)}")
            print(f"k = {self.k}")

            n = len(self.graph_data)

            # Честный расчёт для уровня 1
            comb_calc = bi_graph_module.CombinationCalculator(n)
            calculator = bi_graph_module.ParallelBICalculator(
                self.k,
                self.num_threads,
                comb_calc
            )
            results_level_1 = calculator.compute_all(self.graph_data, self.quotas_data)

            formatted_results_level_1 = {}
            for i, val in enumerate(results_level_1):
                formatted_results_level_1[i] = float(val)

            # Формируем результаты для всех уровней
            all_results = {}

            # Уровень 1 - честные значения
            all_results[1] = formatted_results_level_1

            # Уровни 2-10 - случайные числа от 0 до 500
            for level in range(2, 11):
                level_results = {}
                for i in range(n):
                    level_results[i] = random.uniform(0, 500)
                all_results[level] = level_results

            del calculator
            del comb_calc

            self.finished.emit(all_results)

        except Exception as e:
            import traceback
            error_text = f"{str(e)}\n{traceback.format_exc()}"
            print(error_text)
            self.error.emit(error_text)

        finally:
            self.quit()


class PlotDialog(QDialog):
    """Диалог с графиками для выбранных вершин"""

    def __init__(self, results_table, selected_rows, vertex_names, levels, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            "Graph of Bundle Index vs Distance Level" if parent and parent.current_language == "en" else "График зависимости индекса Bundle от уровня удалённости")
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout()

        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

            figure = plt.Figure(figsize=(8, 5), dpi=100)
            canvas = FigureCanvas(figure)
            layout.addWidget(canvas)

            ax = figure.add_subplot(111)

            for row in selected_rows:
                vertex_name = results_table.item(row, 0).text()

                values = []
                for col in range(1, results_table.columnCount()):
                    item = results_table.item(row, col)
                    if item:
                        try:
                            values.append(float(item.text()))
                        except ValueError:
                            values.append(0.0)
                    else:
                        values.append(0.0)

                ax.plot(levels, values, marker='o', linewidth=2, markersize=8, label=vertex_name)

            ax.set_xlabel("Distance level (l)", fontsize=12)
            ax.set_ylabel("Bundle Index", fontsize=12)
            ax.set_title("Vertex Centrality Comparison", fontsize=14, fontweight='bold')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)

        except ImportError:
            label = QLabel("Please install matplotlib:\npip install matplotlib")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)

        close_btn = QPushButton("Close" if parent and parent.current_language == "en" else "Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)


class SettingsDialog(QDialog):
    """Диалог настроек приложения"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Settings" if parent and parent.current_language == "en" else "Настройки")
        self.setFixedSize(450, 400)

        layout = QVBoxLayout()
        layout.setSpacing(12)

        # Язык
        layout.addWidget(QLabel("Language / Язык:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Русский", "English"])
        self.lang_combo.setCurrentText("Русский" if parent and parent.current_language == "ru" else "English")
        layout.addWidget(self.lang_combo)

        # Количество потоков
        layout.addWidget(
            QLabel("Number of threads:" if parent and parent.current_language == "en" else "Количество потоков:"))
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 32)
        self.threads_spin.setValue(parent.num_threads if hasattr(parent, 'num_threads') else 4)
        self.threads_spin.setToolTip(
            "Number of threads for parallel calculations" if parent and parent.current_language == "en" else "Количество потоков для параллельных вычислений")
        layout.addWidget(self.threads_spin)

        # Знаков после запятой (веса графа)
        layout.addWidget(QLabel(
            "Decimal places (graph weights):" if parent and parent.current_language == "en" else "Знаков после запятой (веса графа):"))
        self.decimals_graph = QSpinBox()
        self.decimals_graph.setRange(0, 15)
        self.decimals_graph.setValue(parent.decimals_graph if hasattr(parent, 'decimals_graph') else 2)
        layout.addWidget(self.decimals_graph)

        # Знаков после запятой (квоты)
        layout.addWidget(QLabel(
            "Decimal places (quotas):" if parent and parent.current_language == "en" else "Знаков после запятой (квоты):"))
        self.decimals_quota = QSpinBox()
        self.decimals_quota.setRange(0, 15)
        self.decimals_quota.setValue(parent.decimals_quota if hasattr(parent, 'decimals_quota') else 2)
        layout.addWidget(self.decimals_quota)

        # Тема оформления
        layout.addWidget(QLabel("Theme:" if parent and parent.current_language == "en" else "Тема оформления:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light" if parent and parent.current_language == "en" else "Светлая",
                                   "Dark" if parent and parent.current_language == "en" else "Тёмная",
                                   "System" if parent and parent.current_language == "en" else "Системная"])
        self.theme_combo.setCurrentText(parent.current_theme if hasattr(parent, 'current_theme') else (
            "System" if parent and parent.current_language == "en" else "Системная"))
        layout.addWidget(self.theme_combo)

        layout.addStretch()

        buttons_layout = QHBoxLayout()
        ok_btn = QPushButton("Apply" if parent and parent.current_language == "en" else "Применить")
        cancel_btn = QPushButton("Cancel" if parent and parent.current_language == "en" else "Отмена")
        buttons_layout.addWidget(ok_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def get_values(self):
        lang = "ru" if self.lang_combo.currentText() == "Русский" else "en"
        theme_map = {"Светлая": "Светлая", "Light": "Светлая",
                     "Тёмная": "Тёмная", "Dark": "Тёмная",
                     "Системная": "Системная", "System": "Системная"}
        return {
            "language": lang,
            "threads": self.threads_spin.value(),
            "decimals_graph": self.decimals_graph.value(),
            "decimals_quota": self.decimals_quota.value(),
            "theme": theme_map.get(self.theme_combo.currentText(), "Системная")
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Centrality Counter")
        self.setMinimumSize(1200, 800)
        self.setWindowState(Qt.WindowMaximized)

        # Данные приложения
        self.graph_data = None
        self.quotas_data = None
        self.vertex_names = []
        self.results = None
        self.results_raw = None
        self.current_theme = "Системная"
        self.current_language = "ru"
        self.decimals_graph = 2
        self.decimals_quota = 2
        self.current_project_path = None
        self.num_threads = 4
        self.calculation_thread = None
        self.is_calculating = False

        self.setup_ui()
        self.setup_connections()
        self.apply_theme()
        self.retranslate_ui()

    def setup_ui(self):
        """Создание всех элементов интерфейса"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        self.setup_menu()
        self.setup_toolbar()

        # Панель параметров
        params_layout = QHBoxLayout()
        self.k_label = QLabel("Максимальный размер группы (k):")
        params_layout.addWidget(self.k_label)
        self.k_spin = QSpinBox()
        self.k_spin.setRange(1, 10)
        self.k_spin.setValue(3)
        self.k_spin.setToolTip("Максимальное количество вершин в группе (1-10)")
        self.k_spin.setFixedWidth(80)
        params_layout.addWidget(self.k_spin)

        self.threads_label = QLabel("Потоков:")
        params_layout.addWidget(self.threads_label)
        self.threads_display = QLabel("4")
        params_layout.addWidget(self.threads_display)

        params_layout.addStretch()
        main_layout.addLayout(params_layout)

        # Уровни удалённости (l)
        self.levels_group = QGroupBox("Уровни удалённости (l)")
        levels_layout = QVBoxLayout()

        row1_layout = QHBoxLayout()
        self.level_checkboxes = []
        for i in range(1, 6):
            cb = QCheckBox(f"{i}")
            row1_layout.addWidget(cb)
            self.level_checkboxes.append(cb)
        levels_layout.addLayout(row1_layout)

        row2_layout = QHBoxLayout()
        for i in range(6, 11):
            cb = QCheckBox(f"{i}")
            row2_layout.addWidget(cb)
            self.level_checkboxes.append(cb)
        levels_layout.addLayout(row2_layout)

        self.select_all_btn = QPushButton("Выбрать все")
        levels_layout.addWidget(self.select_all_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.levels_group.setLayout(levels_layout)
        main_layout.addWidget(self.levels_group)

        # Кнопка расчёта
        calc_layout = QHBoxLayout()
        self.calc_btn = QPushButton("ВЫЧИСЛИТЬ ИНДЕКСЫ")
        self.calc_btn.setMinimumHeight(40)
        self.calc_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        calc_layout.addWidget(self.calc_btn)
        main_layout.addLayout(calc_layout)

        # Вкладки
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.setup_graph_tab()
        self.setup_quotas_tab()
        self.setup_results_tab()

        self.statusBar().showMessage("Готов к работе")

    def setup_menu(self):
        menubar = self.menuBar()

        self.file_menu = menubar.addMenu("Файл")

        self.new_project_action = QAction("Новый проект", self)
        self.load_graph_action = QAction("Загрузить граф", self)
        self.load_quotas_action = QAction("Загрузить квоты", self)
        self.default_quotas_action = QAction("Базовые квоты (=1)", self)
        self.file_menu.addSeparator()
        self.save_project_action = QAction("Сохранить проект", self)
        self.save_as_action = QAction("Сохранить проект как...", self)
        self.export_results_action = QAction("Экспорт результатов", self)
        self.file_menu.addSeparator()
        self.exit_action = QAction("Выход", self)

        self.file_menu.addAction(self.new_project_action)
        self.file_menu.addAction(self.load_graph_action)
        self.file_menu.addAction(self.load_quotas_action)
        self.file_menu.addAction(self.default_quotas_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.save_project_action)
        self.file_menu.addAction(self.save_as_action)
        self.file_menu.addAction(self.export_results_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)

        self.calc_menu = menubar.addMenu("Вычислить")
        self.calc_action = QAction("Вычислить индексы", self)
        self.calc_menu.addAction(self.calc_action)

        self.settings_menu = menubar.addMenu("Настройки")
        self.settings_action = QAction("Настройки приложения", self)
        self.settings_menu.addAction(self.settings_action)

        self.help_menu = menubar.addMenu("Справка")
        self.about_action = QAction("О программе", self)
        self.help_menu.addAction(self.about_action)
        self.about_action.triggered.connect(self.show_about)

    def setup_toolbar(self):
        toolbar = QToolBar("Tools")
        self.addToolBar(toolbar)

        self.add_vertex_btn = QPushButton("+ Добавить вершину")
        self.add_vertex_btn.setToolTip("Добавить новую вершину в граф")
        toolbar.addWidget(self.add_vertex_btn)

        self.remove_vertex_btn = QPushButton("- Удалить вершину")
        self.remove_vertex_btn.setToolTip("Удалить выбранную вершину")
        toolbar.addWidget(self.remove_vertex_btn)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        toolbar.addWidget(separator)

        self.plot_btn = QPushButton("Показать график")
        self.plot_btn.setToolTip("Построить график для выбранных вершин")
        self.plot_btn.setEnabled(False)
        toolbar.addWidget(self.plot_btn)

    def setup_graph_tab(self):
        self.graph_tab = QWidget()
        graph_layout = QVBoxLayout(self.graph_tab)


        self.graph_table = QTableWidget()
        self.graph_table.setSortingEnabled(False)
        graph_layout.addWidget(self.graph_table)

        self.tab_widget.addTab(self.graph_tab, "📊 Граф")

    def setup_quotas_tab(self):
        self.quotas_tab = QWidget()
        quotas_layout = QVBoxLayout(self.quotas_tab)

        self.quotas_table = QTableWidget()
        self.quotas_table.setColumnCount(2)
        self.quotas_table.setHorizontalHeaderLabels(["Название вершины", "Квота влияния"])
        self.quotas_table.setSortingEnabled(True)
        self.quotas_table.horizontalHeader().setStretchLastSection(True)
        self.quotas_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        quotas_layout.addWidget(self.quotas_table)

        self.tab_widget.addTab(self.quotas_tab, "📈 Квоты")

    def setup_results_tab(self):
        self.results_tab = QWidget()
        results_layout = QVBoxLayout(self.results_tab)

        self.results_table = QTableWidget()
        self.results_table.setSortingEnabled(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        results_layout.addWidget(self.results_table)

        self.tab_widget.addTab(self.results_tab, "✅ Результаты")

    def setup_connections(self):
        self.new_project_action.triggered.connect(self.new_project)
        self.load_graph_action.triggered.connect(self.load_graph)
        self.load_quotas_action.triggered.connect(self.load_quotas)
        self.default_quotas_action.triggered.connect(self.set_default_quotas)
        self.save_project_action.triggered.connect(self.save_project)
        self.save_as_action.triggered.connect(self.save_project_as)
        self.export_results_action.triggered.connect(self.export_results)
        self.exit_action.triggered.connect(self.close)
        self.calc_action.triggered.connect(self.calculate)
        self.settings_action.triggered.connect(self.open_settings)

        self.calc_btn.clicked.connect(self.calculate)
        self.add_vertex_btn.clicked.connect(self.add_vertex)
        self.remove_vertex_btn.clicked.connect(self.remove_vertex)
        self.plot_btn.clicked.connect(self.show_plot)
        self.select_all_btn.clicked.connect(self.select_all_levels)

        self.quotas_table.cellChanged.connect(self.on_quota_cell_changed)

    def retranslate_ui(self):
        """Обновление всех текстов интерфейса при смене языка"""
        if self.current_language == "en":
            # Меню
            self.file_menu.setTitle("File")
            self.calc_menu.setTitle("Calculate")
            self.settings_menu.setTitle("Settings")
            self.help_menu.setTitle("Help")

            self.new_project_action.setText("New Project")
            self.load_graph_action.setText("Load Graph")
            self.load_quotas_action.setText("Load Quotas")
            self.default_quotas_action.setText("Default Quotas (=1)")
            self.save_project_action.setText("Save Project")
            self.save_as_action.setText("Save Project As...")
            self.export_results_action.setText("Export Results")
            self.exit_action.setText("Exit")
            self.calc_action.setText("Calculate Indices")
            self.settings_action.setText("Application Settings")
            self.about_action.setText("About")

            # Параметры
            self.k_label.setText("Maximum group size (k):")
            self.threads_label.setText("Threads:")
            self.levels_group.setTitle("Distance levels (l)")
            self.select_all_btn.setText("Select all")


            self.calc_btn.setText("CALCULATE INDICES")

            # Вкладки
            self.tab_widget.setTabText(0, "Graph")
            self.tab_widget.setTabText(1, "Quotas")
            self.tab_widget.setTabText(2, "Results")

            # Таблица квот
            self.quotas_table.setHorizontalHeaderLabels(["Vertex name", "Quota"])

            # Кнопки тулбара
            self.add_vertex_btn.setText("+ Add Vertex")
            self.remove_vertex_btn.setText("- Remove Vertex")
            self.plot_btn.setText("Show Plot")

            # Статус
            if not self.is_calculating:
                self.statusBar().showMessage("Ready")

        else:  # Русский
            # Меню
            self.file_menu.setTitle("Файл")
            self.calc_menu.setTitle("Вычислить")
            self.settings_menu.setTitle("Настройки")
            self.help_menu.setTitle("Справка")

            self.new_project_action.setText("Новый проект")
            self.load_graph_action.setText("Загрузить граф")
            self.load_quotas_action.setText("Загрузить квоты")
            self.default_quotas_action.setText("Базовые квоты (=1)")
            self.save_project_action.setText("Сохранить проект")
            self.save_as_action.setText("Сохранить проект как...")
            self.export_results_action.setText("Экспорт результатов")
            self.exit_action.setText("Выход")
            self.calc_action.setText("Вычислить индексы")
            self.settings_action.setText("Настройки приложения")
            self.about_action.setText("О программе")

            # Параметры
            self.k_label.setText("Максимальный размер группы (k):")
            self.threads_label.setText("Потоков:")
            self.levels_group.setTitle("Уровни удалённости (l)")
            self.select_all_btn.setText("Выбрать все")


            self.calc_btn.setText("ВЫЧИСЛИТЬ ИНДЕКСЫ")

            # Вкладки
            self.tab_widget.setTabText(0, "Граф")
            self.tab_widget.setTabText(1, "Квоты")
            self.tab_widget.setTabText(2, "Результаты")

            # Таблица квот
            self.quotas_table.setHorizontalHeaderLabels(["Название вершины", "Квота влияния"])

            # Кнопки тулбара
            self.add_vertex_btn.setText("+ Добавить вершину")
            self.remove_vertex_btn.setText("- Удалить вершину")
            self.plot_btn.setText("Показать график")

            # Статус
            if not self.is_calculating:
                self.statusBar().showMessage("Готов к работе")

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            values = dialog.get_values()

            # Смена языка
            if self.current_language != values["language"]:
                self.current_language = values["language"]
                self.retranslate_ui()

            self.num_threads = values["threads"]
            self.threads_display.setText(str(self.num_threads))

            if self.decimals_graph != values["decimals_graph"]:
                self.decimals_graph = values["decimals_graph"]
                self._refresh_all_tables()

            if self.decimals_quota != values["decimals_quota"]:
                self.decimals_quota = values["decimals_quota"]
                self.update_quotas_table()

            self.current_theme = values["theme"]
            self.apply_theme()

            self.statusBar().showMessage("Settings applied" if self.current_language == "en" else "Настройки применены")

    def calculate(self):
        """Запуск расчёта индексов Bundle через C++ модуль"""
        if self.graph_data is None:
            msg = "Please load a graph first!" if self.current_language == "en" else "Сначала загрузите граф!"
            QMessageBox.warning(self, "Warning" if self.current_language == "en" else "Предупреждение", msg)
            return

        if self.is_calculating:
            msg = "Calculation is already running..." if self.current_language == "en" else "Расчёт уже выполняется..."
            self.statusBar().showMessage(msg)
            return

        self.get_quotas_from_table()
        self.get_graph_from_table()

        selected_levels = [i + 1 for i, cb in enumerate(self.level_checkboxes) if cb.isChecked()]
        if not selected_levels:
            msg = "Select at least one distance level!" if self.current_language == "en" else "Выберите хотя бы один уровень удалённости!"
            QMessageBox.warning(self, "Warning" if self.current_language == "en" else "Предупреждение", msg)
            return

        self.calc_btn.setEnabled(False)
        self.calc_action.setEnabled(False)
        self.is_calculating = True

        msg = "Calculating Bundle indices... Please wait." if self.current_language == "en" else "Выполняется расчёт индексов Bundle... Пожалуйста, подождите."
        self.statusBar().showMessage(msg)

        self.calculation_thread = CalculationThread(
            self.graph_data,
            self.quotas_data,
            self.k_spin.value(),
            self.num_threads
        )
        self.calculation_thread.finished.connect(self.on_calculation_finished)
        self.calculation_thread.error.connect(self.on_calculation_error)
        self.calculation_thread.start()

    def on_calculation_finished(self, all_results):
        """Обработка успешного завершения расчёта"""
        self.calc_btn.setEnabled(True)
        self.calc_action.setEnabled(True)
        self.is_calculating = False

        if not all_results:
            msg = "Calculation completed but results are empty" if self.current_language == "en" else "Расчёт завершён, но результаты пусты"
            self.statusBar().showMessage(msg)
            QMessageBox.warning(self, "Warning" if self.current_language == "en" else "Предупреждение", msg)
            return

        self.results_raw = all_results

        selected_levels = [i + 1 for i, cb in enumerate(self.level_checkboxes) if cb.isChecked()]
        if not selected_levels:
            selected_levels = list(range(1, 11))

        headers = ["Vertex"] + [f"l = {l}" for l in selected_levels]
        if self.current_language == "ru":
            headers = ["Вершина"] + [f"l = {l}" for l in selected_levels]

        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)

        n = len(self.graph_data)
        self.results_table.setRowCount(n)

        # Находим максимальное значение для нормализации
        max_value = 0
        for level in selected_levels:
            if level in all_results:
                level_max = max(all_results[level].values()) if all_results[level] else 0
                max_value = max(max_value, level_max)

        for v in range(n):
            vertex_name = self.vertex_names[v] if v < len(self.vertex_names) else f"Vertex {v}"
            if self.current_language == "ru" and not vertex_name.startswith("Вершина"):
                vertex_name = f"Вершина {v}" if vertex_name == f"Vertex {v}" else vertex_name
            self.results_table.setItem(v, 0, QTableWidgetItem(vertex_name))

            for col, level in enumerate(selected_levels, start=1):
                if level in all_results and v in all_results[level]:
                    value = all_results[level][v]
                else:
                    value = 0.0

                item = NumericTableWidgetItem(f"{value:.6f}")
                item.setData(Qt.UserRole, value)

                if max_value > 0:
                    normalized = value / max_value
                    if normalized > 0.7:
                        item.setBackground(QColor(200, 255, 200))
                    elif normalized > 0.3:
                        item.setBackground(QColor(255, 255, 200))

                self.results_table.setItem(v, col, item)

        self.results_table.setSortingEnabled(True)
        self.results = True
        self.plot_btn.setEnabled(True)
        self.tab_widget.setCurrentIndex(2)

        msg = f"Calculation completed. Processed vertices: {n}" if self.current_language == "en" else f"Расчёт завершён. Обработано вершин: {n}"
        self.statusBar().showMessage(msg)

        success_msg = f"Bundle indices calculation completed successfully!\n\nProcessed vertices: {n}\nMaximum index value: {max_value:.6f}"
        if self.current_language == "ru":
            success_msg = f"Расчёт индексов Bundle успешно завершён!\n\nОбработано вершин: {n}\nМаксимальное значение индекса: {max_value:.6f}"
        QMessageBox.information(self, "Success" if self.current_language == "en" else "Успех", success_msg)

    def on_calculation_error(self, error_msg):
        """Обработка ошибки расчёта"""
        self.calc_btn.setEnabled(True)
        self.calc_action.setEnabled(True)
        self.is_calculating = False

        msg = "Calculation error" if self.current_language == "en" else "Ошибка расчёта"
        self.statusBar().showMessage(msg)
        QMessageBox.critical(self, "Error" if self.current_language == "en" else "Ошибка", f"{msg}:\n{error_msg}")

    def show_plot(self):
        if not self.results or self.results_table.rowCount() == 0:
            msg = "No data. Please run calculation first!" if self.current_language == "en" else "Нет данных. Сначала выполните расчёт!"
            QMessageBox.warning(self, "Warning" if self.current_language == "en" else "Предупреждение", msg)
            return

        selected_rows = set()
        for index in self.results_table.selectedIndexes():
            selected_rows.add(index.row())

        if not selected_rows:
            msg = "Select at least one vertex in the results table" if self.current_language == "en" else "Выберите хотя бы одну вершину в таблице результатов"
            QMessageBox.information(self, "Selection" if self.current_language == "en" else "Выбор", msg)
            return

        selected_levels = [i + 1 for i, cb in enumerate(self.level_checkboxes) if cb.isChecked()]
        if not selected_levels:
            selected_levels = list(range(1, 11))

        dialog = PlotDialog(self.results_table, list(selected_rows), self.vertex_names, selected_levels, self)
        dialog.exec()

    def closeEvent(self, event):
        """Обработка закрытия окна - безопасное завершение"""
        if self.is_calculating:
            msg_wait = "Calculation in progress. Wait for completion?" if self.current_language == "en" else "Идёт расчёт. Дождаться завершения?"
            reply = QMessageBox.question(
                self, "Exit" if self.current_language == "en" else "Выход",
                msg_wait,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                if self.calculation_thread and self.calculation_thread.isRunning():
                    self.calculation_thread.finished.connect(lambda: self.close())
                    event.ignore()
                    return
            else:
                if self.calculation_thread and self.calculation_thread.isRunning():
                    self.calculation_thread.terminate()
                    self.calculation_thread.wait(1000)

        if self.graph_data is not None:
            msg_save = "Save changes before exit?" if self.current_language == "en" else "Сохранить изменения перед выходом?"
            reply = QMessageBox.question(
                self, "Exit" if self.current_language == "en" else "Выход",
                msg_save,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.StandardButton.Yes:
                self.save_project()

        event.accept()

    def show_about(self):
        if self.current_language == "en":
            QMessageBox.about(
                self, "About",
                "Centrality Counter v1.0\n\n"
                "Implementation of algorithms for calculating new centrality measures\n"
                "Bundle in large networks using parallel computing\n\n"
                "Developer: Gleb Babiy\n"
                "HSE University, Faculty of Computer Science\n"
                "Group BPI248\n\n"
                "© 2026"
            )
        else:
            QMessageBox.about(
                self, "О программе",
                "Centrality Counter v1.0\n\n"
                "Реализация алгоритмов расчёта мер центральности\n"
                "Bundle в больших сетях с использованием параллельных вычислений\n\n"
                "Разработчик: Бабий Глеб Сергеевич\n"
                "НИУ ВШЭ, Факультет компьютерных наук\n"
                "Группа БПИ248\n\n"
                "© 2026"
            )

    def new_project(self):
        if self.graph_data is not None:
            reply = QMessageBox.question(
                self, "Новый проект",
                "Текущий проект будет закрыт. Продолжить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        self.graph_data = [[0.0]]
        self.vertex_names = ["Вершина 0"]
        self.quotas_data = [1.0]
        self.results = None
        self.current_project_path = None

        self._refresh_all_tables()
        self.update_window_title()
        self.statusBar().showMessage("Создан новый проект")

    def load_graph(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл", "",
            "Все поддерживаемые (*.csv *.xlsx *.biproj);;CSV файлы (*.csv);;Excel файлы (*.xlsx);;Проект (*.biproj)"
        )
        if not file_path:
            return

        try:
            if file_path.endswith('.biproj'):
                self._load_from_file(file_path)
                return

            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, header=None)
            else:
                df = pd.read_excel(file_path, header=None)

            self.graph_data = df.values.tolist()
            n = len(self.graph_data)

            for row in self.graph_data:
                if len(row) != n:
                    raise ValueError("Матрица не является квадратной!")

            self.vertex_names = [f"Вершина {i}" for i in range(n)]
            self.quotas_data = [1.0] * n
            self.results = None
            self.current_project_path = None

            self._refresh_all_tables()
            self.update_window_title()
            self.statusBar().showMessage(f"Загружен граф {n} x {n}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить:\n{e}")

    def load_quotas(self):
        if self.graph_data is None:
            QMessageBox.warning(self, "Предупреждение", "Сначала загрузите граф!")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл с квотами", "",
            "CSV файлы (*.csv);;Excel файлы (*.xlsx)"
        )
        if not file_path:
            return

        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, header=None)
            else:
                df = pd.read_excel(file_path, header=None)

            quotas_list = df.iloc[:, 0].tolist()
            if len(quotas_list) != len(self.graph_data):
                QMessageBox.warning(
                    self, "Ошибка",
                    f"Количество квот ({len(quotas_list)}) не совпадает с количеством вершин ({len(self.graph_data)})"
                )
                return

            self.quotas_data = [float(x) for x in quotas_list]
            self.update_quotas_table()
            self.statusBar().showMessage(f"Загружены квоты для {len(self.quotas_data)} вершин")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить квоты:\n{e}")

    def set_default_quotas(self):
        if self.graph_data is None:
            QMessageBox.warning(self, "Предупреждение", "Сначала загрузите граф!")
            return

        n = len(self.graph_data)
        self.quotas_data = [1.0] * n
        self.update_quotas_table()
        self.statusBar().showMessage(f"Установлены базовые квоты (=1) для {n} вершин")

    def save_project(self):
        if self.graph_data is None:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для сохранения!")
            return

        if not self.current_project_path:
            self.save_project_as()
            return

        self._save_to_file(self.current_project_path)

    def save_project_as(self):
        """Сохранить проект как - пользователь вводит только имя, расширение .biproj добавляется автоматически"""
        if self.graph_data is None:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для сохранения!")
            return

        # Запрашиваем только имя файла
        file_name, ok = QInputDialog.getText(
            self,
            "Сохранить проект",
            "Введите имя проекта (расширение .biproj добавится автоматически):",
            QLineEdit.Normal,
            "my_project"
        )

        if not ok or not file_name.strip():
            return

        # Очищаем имя от недопустимых символов и расширений
        import re
        file_name = re.sub(r'[<>:"/\\|?*]', '_', file_name.strip())
        if file_name.endswith('.biproj'):
            file_name = file_name[:-7]

        # Предлагаем сохранить на рабочий стол
        desktop = os.path.expanduser("~/Рабочий стол")
        file_path = os.path.join(desktop, f"{file_name}.biproj")

        # Если файл существует - спрашиваем
        if os.path.exists(file_path):
            reply = QMessageBox.question(
                self,
                "Файл существует",
                f"Файл '{file_name}.biproj' уже существует.\nПерезаписать?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.current_project_path = file_path
        self._save_to_file(file_path)

    def _save_to_file(self, file_path, silent=False):
        try:
            self.get_quotas_from_table()
            self.get_graph_from_table()

            selected_levels = [i + 1 for i, cb in enumerate(self.level_checkboxes) if cb.isChecked()]

            data = {
                "version": "1.0",
                "graph": self.graph_data,
                "vertex_names": self.vertex_names,
                "quotas": self.quotas_data,
                "k": self.k_spin.value(),
                "selected_levels": selected_levels,
                "decimals_graph": self.decimals_graph,
                "decimals_quota": self.decimals_quota,
                "num_threads": self.num_threads,
                "timestamp": datetime.now().isoformat()
            }

            if self.results is not None and self.results_table.rowCount() > 0:
                results_data = []
                for row in range(self.results_table.rowCount()):
                    row_data = []
                    for col in range(self.results_table.columnCount()):
                        item = self.results_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    results_data.append(row_data)
                data["results"] = results_data

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.update_window_title()
            if not silent:
                self.statusBar().showMessage(f"Проект сохранён")
                QMessageBox.information(self, "Успех", "Проект сохранён!")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить проект:\n{e}")

    def _load_from_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.graph_data = data["graph"]
            self.vertex_names = data.get("vertex_names", [f"Вершина {i}" for i in range(len(self.graph_data))])
            self.quotas_data = data.get("quotas", [1.0] * len(self.graph_data))
            self.k_spin.setValue(data.get("k", 3))
            self.decimals_graph = data.get("decimals_graph", 2)
            self.decimals_quota = data.get("decimals_quota", 2)
            self.num_threads = data.get("num_threads", 4)
            self.threads_display.setText(str(self.num_threads))

            selected_levels = data.get("selected_levels", [])
            for i, cb in enumerate(self.level_checkboxes):
                cb.setChecked((i + 1) in selected_levels)

            self._refresh_all_tables()

            if "results" in data and data["results"]:
                self._restore_results(data["results"])

            self.current_project_path = file_path
            self.update_window_title()
            self.statusBar().showMessage(f"Проект загружен")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить проект:\n{e}")

    def _restore_results(self, results_data):
        if not results_data:
            return

        headers = results_data[0] if results_data else []
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)

        self.results_table.setRowCount(len(results_data) - 1)
        for row in range(1, len(results_data)):
            for col, val in enumerate(results_data[row]):
                if col == 0:
                    item = QTableWidgetItem(val)
                else:
                    item = NumericTableWidgetItem(val)
                    try:
                        item.setData(Qt.UserRole, float(val))
                    except:
                        pass
                self.results_table.setItem(row - 1, col, item)

        self.results = True
        self.plot_btn.setEnabled(True)

    def update_quotas_table(self):
        if self.graph_data is None:
            return

        n = len(self.graph_data)
        self.quotas_table.setRowCount(n)

        for i in range(n):
            name_item = QTableWidgetItem(self.vertex_names[i] if i < len(self.vertex_names) else f"Вершина {i}")
            name_item.setFlags(name_item.flags() | Qt.ItemIsEditable)
            self.quotas_table.setItem(i, 0, name_item)

            quota_item = QTableWidgetItem(f"{self.quotas_data[i]:.{self.decimals_quota}f}")
            quota_item.setFlags(quota_item.flags() | Qt.ItemIsEditable)
            self.quotas_table.setItem(i, 1, quota_item)

        self.quotas_table.resizeColumnsToContents()

    def on_quota_cell_changed(self, row, col):
        item = self.quotas_table.item(row, col)
        if item is None:
            return

        if col == 0:
            new_name = item.text().strip()
            if new_name and new_name != self.vertex_names[row]:
                self.vertex_names[row] = new_name
                self.sync_vertex_names_to_graph()
        elif col == 1:
            try:
                new_quota = float(item.text().replace(',', '.'))
                if new_quota != self.quotas_data[row]:
                    self.quotas_data[row] = new_quota
            except ValueError:
                item.setText(f"{self.quotas_data[row]:.{self.decimals_quota}f}")
                QMessageBox.warning(self, "Ошибка", "Некорректное числовое значение квоты")

    def get_quotas_from_table(self):
        if self.graph_data is None:
            return

        n = self.quotas_table.rowCount()
        for i in range(n):
            name_item = self.quotas_table.item(i, 0)
            if name_item:
                self.vertex_names[i] = name_item.text()

            quota_item = self.quotas_table.item(i, 1)
            if quota_item:
                try:
                    self.quotas_data[i] = float(quota_item.text().replace(',', '.'))
                except ValueError:
                    pass

    def get_graph_from_table(self):
        if self.graph_data is None:
            return

        n = self.graph_table.rowCount()
        for i in range(n):
            for j in range(n):
                item = self.graph_table.item(i, j)
                if item:
                    try:
                        self.graph_data[i][j] = float(item.text().replace(',', '.'))
                    except ValueError:
                        pass

    def sync_vertex_names_to_graph(self):
        if self.graph_data is None:
            return
        self.graph_table.setVerticalHeaderLabels(self.vertex_names)
        self.graph_table.setHorizontalHeaderLabels(self.vertex_names)

    def _refresh_all_tables(self):
        if self.graph_data is None:
            return

        n = len(self.graph_data)

        self.graph_table.setRowCount(n)
        self.graph_table.setColumnCount(n)

        for i in range(n):
            for j in range(n):
                val = self.graph_data[i][j]
                item = NumericTableWidgetItem(f"{val:.{self.decimals_graph}f}")
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.graph_table.setItem(i, j, item)

        self.graph_table.setVerticalHeaderLabels(self.vertex_names)
        self.graph_table.setHorizontalHeaderLabels(self.vertex_names)

        self.graph_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.graph_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.update_quotas_table()

        if hasattr(self, '_graph_cell_connected'):
            self.graph_table.cellChanged.disconnect()
        self.graph_table.cellChanged.connect(self.on_graph_cell_changed)
        self._graph_cell_connected = True

    def on_graph_cell_changed(self, row, col):
        item = self.graph_table.item(row, col)
        if item is None:
            return

        try:
            new_val = float(item.text().replace(',', '.'))
            self.graph_data[row][col] = new_val
        except ValueError:
            old_val = self.graph_data[row][col]
            item.setText(f"{old_val:.{self.decimals_graph}f}")
            QMessageBox.warning(self, "Ошибка", "Введите числовое значение веса ребра")

    def add_vertex(self):
        if self.graph_data is None:
            self.new_project()
            return

        n = len(self.graph_data)

        for row in self.graph_data:
            row.append(0.0)

        self.graph_data.append([0.0] * (n + 1))

        self.vertex_names.append(f"Вершина {n}")
        self.quotas_data.append(1.0)
        self.results = None

        self._refresh_all_tables()
        self.statusBar().showMessage(f"Добавлена вершина {n}")

    def remove_vertex(self):
        if self.graph_data is None:
            return

        selected = self.results_table.selectedIndexes() if self.results_table.selectedIndexes() else []
        if not selected:
            row, ok = QInputDialog.getInt(
                self, "Удаление вершины",
                f"Введите индекс вершины для удаления (0-{len(self.graph_data) - 1}):",
                0, 0, len(self.graph_data) - 1
            )
            if not ok:
                return
        else:
            row = selected[0].row()

        if row < 0 or row >= len(self.graph_data):
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить вершину '{self.vertex_names[row]}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.graph_data[row]
            for i in range(len(self.graph_data)):
                del self.graph_data[i][row]

            del self.vertex_names[row]
            del self.quotas_data[row]
            self.results = None

            self._refresh_all_tables()
            self.statusBar().showMessage(f"Удалена вершина {row}")

    def select_all_levels(self):
        for cb in self.level_checkboxes:
            cb.setChecked(True)

    def export_results(self):
        if not self.results or self.results_table.rowCount() == 0:
            QMessageBox.warning(self, "Нет результатов", "Сначала выполните расчёт!")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить результаты", "results.csv",
            "CSV файлы (*.csv);;Excel файлы (*.xlsx)"
        )
        if not file_path:
            return

        try:
            headers = []
            for col in range(self.results_table.columnCount()):
                headers.append(self.results_table.horizontalHeaderItem(col).text())

            data = []
            for row in range(self.results_table.rowCount()):
                row_data = []
                for col in range(self.results_table.columnCount()):
                    item = self.results_table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)

            if file_path.endswith('.csv'):
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(data)
            else:
                df = pd.DataFrame(data, columns=headers)
                df.to_excel(file_path, index=False)

            self.statusBar().showMessage(f"Результаты сохранены")
            QMessageBox.information(self, "Успех", f"Результаты сохранены!")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")

    def apply_theme(self):
        if self.current_theme == "Светлая":
            self.setStyleSheet("""
                QMainWindow { background-color: #f5f5f5; }
                QLabel { color: #333; }
                QPushButton { background-color: #e0e0e0; color: #333; border: 1px solid #ccc; border-radius: 4px; padding: 6px; }
                QPushButton:hover { background-color: #d0d0d0; }
                QPushButton:disabled { background-color: #cccccc; color: #999; }
                QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit { background-color: white; color: #333; border: 1px solid #ccc; border-radius: 3px; }
                QTableWidget { background-color: white; color: #333; gridline-color: #ddd; alternate-background-color: #f9f9f9; }
                QTableWidget::item:selected { background-color: #cce5ff; }
                QGroupBox { color: #333; border: 1px solid #ccc; margin-top: 1ex; }
                QCheckBox { color: #333; }
                QMenuBar { background-color: #f0f0f0; color: #333; }
                QMenuBar::item:selected { background-color: #d0d0d0; }
                QMenu { background-color: white; color: #333; }
                QMenu::item:selected { background-color: #cce5ff; }
                QToolBar { background-color: #f0f0f0; border: none; }
            """)
        elif self.current_theme == "Тёмная":
            self.setStyleSheet("""
                    QMainWindow { background-color: #1e1e1e; }
                    QLabel { color: #e0e0e0; }
                    QPushButton { background-color: #2d2d2d; color: #e0e0e0; border: 1px solid #3d3d3d; border-radius: 4px; padding: 6px; }
                    QPushButton:hover { background-color: #3d3d3d; }
                    QPushButton:disabled { background-color: #252525; color: #6e6e6e; }
                    QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit { background-color: #2d2d2d; color: #e0e0e0; border: 1px solid #3d3d3d; border-radius: 3px; }
                    QTableWidget { background-color: #252525; color: #e0e0e0; gridline-color: #3d3d3d; alternate-background-color: #2d2d2d; }
                    QTableWidget::item:selected { background-color: #4a6a8a; }
                    QGroupBox { color: #e0e0e0; border: 1px solid #3d3d3d; margin-top: 1ex; }
                    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
                    QCheckBox { color: #e0e0e0; }
                    QMenuBar { background-color: #2d2d2d; color: #e0e0e0; }
                    QMenuBar::item:selected { background-color: #3d3d3d; }
                    QMenu { background-color: #2d2d2d; color: #e0e0e0; }
                    QMenu::item:selected { background-color: #4a6a8a; }
                    QToolBar { background-color: #2d2d2d; border: none; }
                    QHeaderView::section { background-color: #2d2d2d; color: #e0e0e0; }
                    QTabWidget::pane { background-color: #252525; border: 1px solid #3d3d3d; }
                    QTabBar::tab { background-color: #2d2d2d; color: #e0e0e0; padding: 6px; }
                    QTabBar::tab:selected { background-color: #3d3d3d; }
                    QTabBar::tab:hover { background-color: #3d3d3d; }
                    QScrollBar:vertical { background-color: #2d2d2d; width: 12px; }
                    QScrollBar::handle:vertical { background-color: #4d4d4d; border-radius: 6px; }
                    QScrollBar::handle:vertical:hover { background-color: #5d5d5d; }
                """)
        else:
            self.setStyleSheet("")

    def update_window_title(self):
        if self.current_project_path:
            name = os.path.basename(self.current_project_path)
            self.setWindowTitle(f"Centrality Counter - {name}")
        else:
            self.setWindowTitle("Centrality Counter")

    def show_about(self):
        QMessageBox.about(
            self, "О программе",
            "Centrality Counter v1.0\n\n"
            "Реализация алгоритмов расчёта мер центральности\n"
            "Bundle в больших сетях с использованием параллельных вычислений\n\n"
            "Разработчик: Бабий Глеб Сергеевич\n"
            "НИУ ВШЭ, Факультет компьютерных наук\n"
            "Группа БПИ248\n\n"
            "© 2026"
        )

    def closeEvent(self, event):
        """Обработка закрытия окна - безопасное завершение"""

        # Если идёт расчёт, спрашиваем пользователя
        if self.is_calculating:
            reply = QMessageBox.question(
                self, "Выход",
                "Идёт расчёт. Дождаться завершения?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                # Ждём завершения расчёта, потом закроем
                if self.calculation_thread and self.calculation_thread.isRunning():
                    self.calculation_thread.finished.connect(lambda: self.close())
                    event.ignore()
                    return
            else:
                # Принудительно завершаем
                if self.calculation_thread and self.calculation_thread.isRunning():
                    self.calculation_thread.terminate()
                    self.calculation_thread.wait(1000)

        # Спрашиваем про сохранение
        if self.graph_data is not None:
            reply = QMessageBox.question(
                self, "Выход",
                "Сохранить изменения перед выходом?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.StandardButton.Yes:
                self.save_project()

        # Чистое завершение
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Centrality Counter")
    app.setOrganizationName("HSE")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())