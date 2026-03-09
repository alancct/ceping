from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                             QListWidget, QLabel, QComboBox, QTextEdit,
                             QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QFrame, QPushButton, QDialog, QFormLayout, QLineEdit, QMessageBox,
                             QApplication, QMenu)
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtCore import Qt
from database import db
from report_generator import ReportGenerator


class AddAssetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加测评资产")
        self.resize(400, 300)
        self.layout = QFormLayout(self)
        self.name_input = QLineEdit()
        self.model_input = QLineEdit()
        self.ip_input = QLineEdit()
        self.template_combo = QComboBox()

        self.templates = db.get_asset_templates()
        if not self.templates:
            self.template_combo.addItem("无可用模板")
            self.template_combo.setEnabled(False)
        else:
            for t in self.templates:
                doc_id = getattr(t, 'doc_id', t.get('doc_id'))
                self.template_combo.addItem(t.get('name', 'Unknown'), doc_id)

        self.btn_ok = QPushButton("确认添加")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_ok.setEnabled(len(self.templates) > 0)

        self.layout.addRow("资产名称:", self.name_input)
        self.layout.addRow("型号/版本:", self.model_input)
        self.layout.addRow("IP地址:", self.ip_input)
        self.layout.addRow("资产类型:", self.template_combo)
        self.layout.addWidget(self.btn_ok)

    def get_data(self):
        return (self.name_input.text(), self.model_input.text(),
                self.ip_input.text(), self.template_combo.currentData())


class ProjectWindow(QWidget):
    clipboard_data = []

    def __init__(self, project_id, project_name):
        super().__init__()
        self.project_id = project_id
        self.setWindowTitle(f"等保测评工具 - {project_name}")
        self.resize(1300, 850)

        self.current_category = None
        self.current_asset_id = None
        # 现在列表行对应的是 assessments 表中的 doc_id
        self.current_assessment_doc_id = None

        self.init_ui()
        self.load_categories()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        left_layout = QVBoxLayout()
        self.left_sidebar = QListWidget()
        self.left_sidebar.currentRowChanged.connect(self.on_category_changed)
        self.left_sidebar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.left_sidebar.customContextMenuRequested.connect(self.show_category_menu)

        btn_report = QPushButton("生成整改报告")
        btn_report.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
        btn_report.clicked.connect(self.generate_report)

        left_layout.addWidget(self.left_sidebar)
        left_layout.addWidget(btn_report)
        left_container = QWidget()
        left_container.setLayout(left_layout)
        left_container.setFixedWidth(200)

        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)

        self.asset_panel = QGroupBox("资产列表")
        asset_layout = QHBoxLayout()
        self.asset_list_combo = QComboBox()
        self.asset_list_combo.currentIndexChanged.connect(self.on_asset_changed)
        btn_add = QPushButton("添加")
        btn_add.clicked.connect(self.add_asset)
        btn_del = QPushButton("删除")
        btn_del.setObjectName("dangerBtn")
        btn_del.clicked.connect(self.delete_asset)
        asset_layout.addWidget(QLabel("当前资产:"))
        asset_layout.addWidget(self.asset_list_combo, 1)
        asset_layout.addWidget(btn_add)
        asset_layout.addWidget(btn_del)
        self.asset_panel.setLayout(asset_layout)
        self.asset_panel.setVisible(False)
        self.right_layout.addWidget(self.asset_panel)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.top_container = QGroupBox("测评详情")
        top_layout = QHBoxLayout()
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        top_bar = QHBoxLayout()
        self.lbl_id = QLabel("ID: -")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["不适用", "符合", "不符合", "部分符合"])
        self.status_combo.currentIndexChanged.connect(self.save_current_edit)
        top_bar.addWidget(QLabel("符合情况:"))
        top_bar.addWidget(self.status_combo)
        top_bar.addStretch()
        top_bar.addWidget(self.lbl_id)

        self.result_edit = QTextEdit()
        self.result_edit.setPlaceholderText("结果记录...")
        self.result_edit.textChanged.connect(self.save_current_edit)
        self.result_edit.focusInEvent = self.on_result_focus

        self.suggestion_edit = QTextEdit()
        self.suggestion_edit.setPlaceholderText("整改建议...")
        self.suggestion_edit.setMaximumHeight(80)
        self.suggestion_edit.textChanged.connect(self.save_current_edit)
        self.suggestion_edit.focusInEvent = self.on_suggestion_focus

        form_layout.addLayout(top_bar)
        form_layout.addWidget(QLabel("结果记录:"))
        form_layout.addWidget(self.result_edit)
        form_layout.addWidget(QLabel("整改建议:"))
        form_layout.addWidget(self.suggestion_edit)

        kb_group = QGroupBox("知识库")
        kb_group.setFixedWidth(250)
        kb_layout = QVBoxLayout()
        self.lbl_kb_hint = QLabel("点击文本框加载...")
        self.kb_list = QListWidget()
        self.kb_list.itemDoubleClicked.connect(self.apply_kb_item)
        kb_layout.addWidget(self.lbl_kb_hint)
        kb_layout.addWidget(self.kb_list)
        kb_group.setLayout(kb_layout)

        top_layout.addWidget(form_widget)
        top_layout.addWidget(kb_group)
        self.top_container.setLayout(top_layout)
        self.top_container.setEnabled(False)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(4)
        self.items_table.setHorizontalHeaderLabels(["状态", "控制点", "测评要求", "测评方法"])
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.items_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.items_table.cellClicked.connect(self.on_item_selected)

        # 快捷键
        QShortcut(QKeySequence.StandardKey.Copy, self.items_table).activated.connect(self.copy_items)
        QShortcut(QKeySequence.StandardKey.Paste, self.items_table).activated.connect(self.paste_items)

        splitter.addWidget(self.top_container)
        splitter.addWidget(self.items_table)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        self.right_layout.addWidget(splitter)
        main_layout.addWidget(left_container)
        main_layout.addWidget(self.right_container)
        self.current_focus_field = None

        # === 核心逻辑修改：基于 assessments 表 ===

    def refresh_items_table(self):
        """从 assessments 表加载数据"""
        self.items_table.setRowCount(0)
        self.current_records = []  # 缓存当前页面的记录对象

        if self.current_category == "安全计算环境" and not self.current_asset_id:
            return  # 未选资产不显示

        # 查询数据库
        records = db.get_assessments(self.project_id, self.current_category, self.current_asset_id)
        self.current_records = records

        self.items_table.setRowCount(len(records))
        for row, rec in enumerate(records):
            status = rec.get('status', '不适用')
            status_item = QTableWidgetItem(status)
            if status == '符合':
                status_item.setForeground(Qt.GlobalColor.green)
            elif status == '不符合':
                status_item.setForeground(Qt.GlobalColor.red)
            else:
                status_item.setForeground(Qt.GlobalColor.gray)

            # 存储 doc_id 到第一列 item 中
            status_item.setData(Qt.ItemDataRole.UserRole, rec.doc_id)

            self.items_table.setItem(row, 0, status_item)
            self.items_table.setItem(row, 1, QTableWidgetItem(rec.get('point', '')))

            req_item = QTableWidgetItem(rec.get('requirement', ''))
            req_item.setToolTip(rec.get('requirement', ''))
            self.items_table.setItem(row, 2, req_item)

            method_item = QTableWidgetItem(rec.get('method', ''))
            method_item.setToolTip(rec.get('method', ''))
            self.items_table.setItem(row, 3, method_item)

    def on_item_selected(self, row, col):
        if row >= len(self.current_records): return

        self.top_container.setEnabled(True)
        rec = self.current_records[row]
        self.current_assessment_doc_id = rec.doc_id

        # 知识库ID
        self.current_item_id = rec.get('tpl_item_id')
        self.lbl_id.setText(f"ID: {self.current_item_id}")

        self.block_signals_ui(True)
        self.status_combo.setCurrentText(rec.get('status', '不适用'))
        self.result_edit.setText(rec.get('result', ''))
        self.suggestion_edit.setText(rec.get('suggestion', ''))
        self.block_signals_ui(False)

        self.load_kb('results')

    def save_current_edit(self):
        if not self.current_assessment_doc_id: return

        new_data = {
            "status": self.status_combo.currentText(),
            "result": self.result_edit.toPlainText(),
            "suggestion": self.suggestion_edit.toPlainText()
        }

        # 更新数据库
        db.update_assessment_record(self.current_assessment_doc_id, new_data)

        # 刷新当前行UI
        row = self.items_table.currentRow()
        if row >= 0:
            st_item = self.items_table.item(row, 0)
            st_item.setText(new_data['status'])
            if new_data['status'] == '符合':
                st_item.setForeground(Qt.GlobalColor.green)
            elif new_data['status'] == '不符合':
                st_item.setForeground(Qt.GlobalColor.red)
            else:
                st_item.setForeground(Qt.GlobalColor.gray)

            # 同时更新缓存
            self.current_records[row].update(new_data)

    def copy_items(self):
        indexes = self.items_table.selectedIndexes()
        if not indexes: return
        rows = sorted(set(idx.row() for idx in indexes))

        data = []
        for r in rows:
            if r < len(self.current_records):
                item = self.current_records[r]
                data.append({
                    "status": item.get('status'),
                    "result": item.get('result'),
                    "suggestion": item.get('suggestion')
                })
        ProjectWindow.clipboard_data = data

    def paste_items(self):
        if not ProjectWindow.clipboard_data: return
        indexes = self.items_table.selectedIndexes()
        if not indexes: return
        rows = sorted(set(idx.row() for idx in indexes))

        src_data = ProjectWindow.clipboard_data
        if len(src_data) == 1:
            src_data = [src_data[0]] * len(rows)

        count = 0
        for i, r in enumerate(rows):
            if i >= len(src_data): break
            if r >= len(self.current_records): continue

            rec = self.current_records[r]
            doc_id = rec.doc_id
            paste_data = src_data[i]

            db.update_assessment_record(doc_id, paste_data)

            # 刷新UI
            item = self.items_table.item(r, 0)
            item.setText(paste_data['status'])
            if paste_data['status'] == '符合':
                item.setForeground(Qt.GlobalColor.green)
            elif paste_data['status'] == '不符合':
                item.setForeground(Qt.GlobalColor.red)
            else:
                item.setForeground(Qt.GlobalColor.gray)

            # 更新缓存
            rec.update(paste_data)
            count += 1

        # 刷新编辑器
        if self.items_table.currentRow() in rows:
            self.on_item_selected(self.items_table.currentRow(), 0)


    # === 辅助逻辑 ===
    def load_categories(self):
        self.left_sidebar.clear()
        from database import STD_CATEGORIES
        proj = db.get_project_data(self.project_id)
        disabled = proj.get('disabled_categories', [])
        for c in STD_CATEGORIES:
            if c not in disabled: self.left_sidebar.addItem(c)

    def on_category_changed(self, row):
        item = self.left_sidebar.item(row)
        if not item: return
        self.current_category = item.text()

        if self.current_category == "安全计算环境":
            self.asset_panel.setVisible(True)
            self.load_assets()
        else:
            self.asset_panel.setVisible(False)
            self.current_asset_id = None
            self.refresh_items_table()

        self.top_container.setEnabled(False)
        self.clear_editor()

    def load_assets(self):
        self.asset_list_combo.blockSignals(True)
        self.asset_list_combo.clear()
        proj = db.get_project_data(self.project_id)
        assets = proj.get('assets', [])
        for a in assets:
            self.asset_list_combo.addItem(f"{a['name']} ({a['ip']})", a['id'])
        self.asset_list_combo.blockSignals(False)

        if assets:
            self.asset_list_combo.setCurrentIndex(0)
            self.on_asset_changed(0)
        else:
            self.items_table.setRowCount(0)

    def on_asset_changed(self, index):
        self.current_asset_id = self.asset_list_combo.itemData(index)
        self.refresh_items_table()

    def add_asset(self):
        dialog = AddAssetDialog(self)
        if dialog.exec():
            name, model, ip, tpl_id = dialog.get_data()
            if not name or not tpl_id: return
            if db.add_asset_to_project(self.project_id, name, model, ip, tpl_id):
                self.load_assets()

    def delete_asset(self):
        if self.asset_list_combo.count() == 0: return
        aid = self.asset_list_combo.currentData()
        if QMessageBox.question(self, "确认", "删除资产及记录？") == QMessageBox.StandardButton.Yes:
            db.remove_asset_from_project(self.project_id, aid)
            self.load_assets()

    def show_category_menu(self, pos):
        item = self.left_sidebar.itemAt(pos)
        menu = QMenu()
        if item:
            action = menu.addAction(f"隐藏 '{item.text()}'")
            if menu.exec(self.left_sidebar.mapToGlobal(pos)) == action:
                db.remove_project_category(self.project_id, item.text())
                self.load_categories()
        else:
            restore_menu = menu.addMenu("恢复分类")
            proj = db.get_project_data(self.project_id)
            for c in proj.get('disabled_categories', []):
                restore_menu.addAction(c).triggered.connect(lambda ch, cat=c: self.restore_cat(cat))
            menu.exec(self.left_sidebar.mapToGlobal(pos))

    def restore_cat(self, cat):
        db.restore_project_category(self.project_id, cat)
        self.load_categories()

    def generate_report(self):
        ReportGenerator(self, self.project_id).generate()

    # 知识库相关
    def on_result_focus(self, e):
        self.current_focus_field = 'result'
        self.load_kb('results')
        QTextEdit.focusInEvent(self.result_edit, e)

    def on_suggestion_focus(self, e):
        self.current_focus_field = 'suggestion'
        self.load_kb('suggestions')
        QTextEdit.focusInEvent(self.suggestion_edit, e)

    def load_kb(self, ftype):
        if not self.current_item_id: return
        data = db.get_kb_entry(self.current_item_id)
        items = data.get(ftype, [])
        self.kb_list.clear()
        if not items:
            self.kb_list.addItem("暂无...")
        else:
            self.kb_list.addItems(items)
        self.lbl_kb_hint.setText("常用记录" if ftype == 'results' else "常用建议")

    def apply_kb_item(self, item):
        txt = item.text()
        if txt == "暂无...": return
        if self.current_focus_field == 'result':
            self.result_edit.setText(txt)
        elif self.current_focus_field == 'suggestion':
            self.suggestion_edit.setText(txt)

    def clear_editor(self):
        self.block_signals_ui(True)
        self.result_edit.clear()
        self.suggestion_edit.clear()
        self.lbl_id.setText("-")
        self.kb_list.clear()
        self.block_signals_ui(False)

    def block_signals_ui(self, b):
        self.result_edit.blockSignals(b)
        self.suggestion_edit.blockSignals(b)
        self.status_combo.blockSignals(b)