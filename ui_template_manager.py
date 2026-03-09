import sys
from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                             QPushButton, QLabel, QMessageBox, QFileDialog,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QGroupBox, QTextEdit, QSplitter, QWidget,
                             QAbstractItemView, QInputDialog, QComboBox, QTabWidget, QLineEdit, QListWidgetItem, QMenu,
                             QFormLayout)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeySequence
from database import db
import traceback


class KBEditorDialog(QDialog):
    """
    查看测评项 & 知识库维护窗口
    v2.0修改: 允许编辑标准内容
    """

    def __init__(self, template_id, category, item_index, item_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"编辑测评项 & 知识库 - {item_data.get('id', '无编号')}")
        self.resize(900, 750)
        # === 修改1：添加最大化按钮 ===
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)

        self.tpl_id = template_id
        self.cat = category
        self.idx = item_index
        self.item_data = item_data
        self.item_id = item_data.get('id', 'UNKNOWN')

        self.init_ui()
        self.load_kb_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # === 上半部分：标准内容 (可编辑) ===
        content_group = QGroupBox("标准内容编辑")
        content_layout = QVBoxLayout()

        # 1. 风险等级
        risk_layout = QHBoxLayout()
        risk_layout.addWidget(QLabel("风险等级:"))
        self.risk_combo = QComboBox()
        self.risk_combo.addItems(["高", "中", "低"])
        self.risk_combo.setCurrentText(self.item_data.get('risk_level', '中'))
        risk_layout.addWidget(self.risk_combo)
        risk_layout.addStretch()
        content_layout.addLayout(risk_layout)

        # 2. 安全控制点
        content_layout.addWidget(QLabel("安全控制点:"))
        self.point_edit = QLineEdit()
        self.point_edit.setText(self.item_data.get('point', ''))
        # 修改：允许编辑，设置提示
        self.point_edit.setPlaceholderText("请输入安全控制点")
        content_layout.addWidget(self.point_edit)

        # 3. 测评要求
        content_layout.addWidget(QLabel("测评要求:"))
        self.req_edit = QTextEdit()
        self.req_edit.setText(self.item_data.get('requirement', ''))
        self.req_edit.setMaximumHeight(80)
        # 修改：允许编辑
        content_layout.addWidget(self.req_edit)

        # 4. 测评方法
        content_layout.addWidget(QLabel("测评方法:"))
        self.method_edit = QTextEdit()
        self.method_edit.setText(self.item_data.get('method', ''))
        self.method_edit.setMaximumHeight(80)
        # 修改：允许编辑
        content_layout.addWidget(self.method_edit)

        # 保存按钮
        save_btn = QPushButton("保存标准内容修改")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        save_btn.clicked.connect(self.save_content)
        content_layout.addWidget(save_btn)

        content_group.setLayout(content_layout)

        # === 下半部分：知识库维护 ===
        kb_group = QGroupBox("知识库维护 (常用语预设)")
        kb_layout = QHBoxLayout()

        # 左：常用结果
        left_kb = QVBoxLayout()
        left_kb.addWidget(QLabel("常用【结果记录】:"))
        self.list_results = QListWidget()
        btn_add_res = QPushButton("添加记录 (+)")
        btn_add_res.clicked.connect(lambda: self.add_kb('results'))
        btn_del_res = QPushButton("删除选中 (-)")
        btn_del_res.setObjectName("dangerBtn")
        btn_del_res.clicked.connect(lambda: self.del_kb('results'))

        left_kb.addWidget(self.list_results)
        left_kb.addWidget(btn_add_res)
        left_kb.addWidget(btn_del_res)

        # 右：常用建议
        right_kb = QVBoxLayout()
        right_kb.addWidget(QLabel("常用【整改建议】:"))
        self.list_suggestions = QListWidget()
        btn_add_sug = QPushButton("添加建议 (+)")
        btn_add_sug.clicked.connect(lambda: self.add_kb('suggestions'))
        btn_del_sug = QPushButton("删除选中 (-)")
        btn_del_sug.setObjectName("dangerBtn")
        btn_del_sug.clicked.connect(lambda: self.del_kb('suggestions'))

        right_kb.addWidget(self.list_suggestions)
        right_kb.addWidget(btn_add_sug)
        right_kb.addWidget(btn_del_sug)

        kb_layout.addLayout(left_kb)
        kb_layout.addLayout(right_kb)
        kb_group.setLayout(kb_layout)

        layout.addWidget(content_group)
        layout.addWidget(kb_group)

    def save_content(self):
        """保存所有标准内容的修改"""
        new_risk = self.risk_combo.currentText()
        new_point = self.point_edit.text()
        new_req = self.req_edit.toPlainText()
        new_method = self.method_edit.toPlainText()

        try:
            db.update_template_item_text(self.tpl_id, self.cat, self.idx,
                                         new_point, new_req, new_method, new_risk)
            QMessageBox.information(self, "成功", "内容已保存！")
            # 接受改动并关闭，以便主界面刷新
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"数据库错误: {str(e)}")

    def load_kb_data(self):
        entry = db.get_kb_entry(self.item_id, template_id=self.tpl_id)
        self.list_results.clear()
        self.list_suggestions.clear()
        self.list_results.addItems(entry.get('results', []))
        self.list_suggestions.addItems(entry.get('suggestions', []))

    def add_kb(self, kb_type):
        text, ok = QInputDialog.getMultiLineText(self, "添加知识库", "请输入内容:")
        if ok and text:
            db.add_kb_entry(self.item_id, kb_type, text, template_id=self.tpl_id)
            self.load_kb_data()

    def del_kb(self, kb_type):
        target_list = self.list_results if kb_type == 'results' else self.list_suggestions
        item = target_list.currentItem()
        if item:
            db.remove_kb_entry(self.item_id, kb_type, item.text(), template_id=self.tpl_id)
            self.load_kb_data()


class AddItemDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新增测评项")
        self.resize(500, 400)
        self.layout = QFormLayout(self)

        self.id_edit = QLineEdit()
        self.point_edit = QLineEdit()
        self.risk_combo = QComboBox()
        self.risk_combo.addItems(["高", "中", "低"])
        self.risk_combo.setCurrentText("中")
        self.req_edit = QTextEdit()
        self.method_edit = QTextEdit()

        self.btn_ok = QPushButton("确定")
        self.btn_ok.clicked.connect(self.accept)

        self.layout.addRow("编号(ID):", self.id_edit)
        self.layout.addRow("风险等级:", self.risk_combo)
        self.layout.addRow("控制点:", self.point_edit)
        self.layout.addRow("测评要求:", self.req_edit)
        self.layout.addRow("测评方法:", self.method_edit)
        self.layout.addWidget(self.btn_ok)

    def get_data(self):
        return {
            "id": self.id_edit.text(),
            "point": self.point_edit.text(),
            "risk_level": self.risk_combo.currentText(),
            "requirement": self.req_edit.toPlainText(),
            "method": self.method_edit.toPlainText(),
            "status": "不适用",
            "result": "",
            "suggestion": ""
        }


class TemplateManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("测评模板管理中心")
        self.resize(1150, 750)
        # === 修改2：添加最大化按钮 ===
        # 使用 WindowMinMaxButtonsHint 来显示最小化和最大化按钮
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)

        self.current_row_map = []
        self.current_tpl_id = None
        self.is_asset_mode = False
        self.current_data = {}
        # 防止加载数据时触发 itemChanged 信号
        self.loading_data = False

        self.init_ui()
        self.load_standard_templates()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # 1. 标准模板页
        self.tab_standard = QWidget()
        self.init_standard_ui()
        self.tabs.addTab(self.tab_standard, "等保标准模板")

        # 2. 资产模板页
        self.tab_asset = QWidget()
        self.init_asset_ui()
        self.tabs.addTab(self.tab_asset, "资产专用模板（安全计算环境）")

        main_layout.addWidget(self.tabs)

        # 底部提示
        main_layout.addWidget(QLabel(
            "操作提示：\n1. 单击选中 -> 再次单击(或按键)直接编辑。\n2. 双击 -> 打开详细编辑大窗口。\n3. 表格编辑后自动保存。"))

    def init_standard_ui(self):
        layout = QHBoxLayout(self.tab_standard)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("标准模板:"))
        self.std_list = QListWidget()
        self.std_list.itemClicked.connect(lambda item: self.on_template_selected(item, False))

        btn_import = QPushButton("导入数据到当前模板")
        btn_import.clicked.connect(self.import_data_to_current)

        left_layout.addWidget(self.std_list)
        left_layout.addWidget(btn_import)

        self.std_right_widget = QWidget()
        right_layout = QVBoxLayout(self.std_right_widget)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("查看分类:"))
        self.cat_combo = QComboBox()
        self.cat_combo.currentIndexChanged.connect(self.filter_items)
        filter_layout.addWidget(self.cat_combo, 1)

        self.std_table = QTableWidget()
        self.setup_table(self.std_table)

        right_layout.addLayout(filter_layout)
        right_layout.addWidget(self.std_table)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_w = QWidget()
        left_w.setLayout(left_layout)
        splitter.addWidget(left_w)
        splitter.addWidget(self.std_right_widget)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def init_asset_ui(self):
        layout = QHBoxLayout(self.tab_asset)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("资产模板列表:"))

        asset_filter_layout = QHBoxLayout()
        asset_filter_layout.addWidget(QLabel("模板分类:"))
        self.asset_level_combo = QComboBox()
        self.asset_level_combo.addItems(["全部", "二级", "三级"])
        self.asset_level_combo.currentIndexChanged.connect(self.load_asset_templates)
        asset_filter_layout.addWidget(self.asset_level_combo, 1)
        left_layout.addLayout(asset_filter_layout)

        self.asset_list = QListWidget()
        self.asset_list.itemClicked.connect(lambda item: self.on_template_selected(item, True))

        btn_create = QPushButton("新建资产模板")
        btn_create.clicked.connect(self.create_asset_template)

        btn_import = QPushButton("导入数据")
        btn_import.clicked.connect(self.import_data_to_current)

        btn_del = QPushButton("删除选中模板")
        btn_del.setObjectName("dangerBtn")
        btn_del.clicked.connect(self.delete_asset_template)

        left_layout.addWidget(self.asset_list)
        left_layout.addWidget(btn_create)
        left_layout.addWidget(btn_import)
        left_layout.addWidget(btn_del)
        left_layout.addStretch()

        self.asset_table = QTableWidget()
        self.setup_table(self.asset_table)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_w = QWidget()
        left_w.setLayout(left_layout)
        splitter.addWidget(left_w)
        splitter.addWidget(self.asset_table)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def setup_table(self, table):
        """配置表格：允许编辑，允许双击"""
        table.setColumnCount(5)  # ID, 风险, 控制点, 要求, 方法
        table.setHorizontalHeaderLabels(["ID (不可改)", "风险", "控制点", "测评要求", "测评方法"])
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(1, 60)

        # === 修改3：优化触发逻辑 ===
        # SelectedClicked: 点击已选中的项会触发编辑
        # EditKeyPressed: 按F2触发编辑
        # AnyKeyPressed: 按任意键打字触发编辑
        # 注意：这里去掉了 DoubleClicked 触发编辑，因为双击我们要留给弹窗
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.SelectedClicked |
                              QAbstractItemView.EditTrigger.EditKeyPressed |
                              QAbstractItemView.EditTrigger.AnyKeyPressed)

        # 双击事件 -> 弹窗
        table.doubleClicked.connect(self.open_item_editor)

        # 核心：连接数据变更信号，实现表格直接编辑保存
        table.itemChanged.connect(lambda item: self.on_table_cell_changed(table, item))

        # 启用右键菜单
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_context_menu)
        table.installEventFilter(self)

    def eventFilter(self, obj, event):
        if isinstance(obj, QTableWidget) and event.type() == QEvent.Type.KeyPress:
            if event.matches(QKeySequence.StandardKey.Paste):
                if self.handle_multi_paste(obj):
                    return True
        return super().eventFilter(obj, event)

    def handle_multi_paste(self, table):
        """支持风险(1列)和控制点(2列)多选批量粘贴"""
        selected_indexes = table.selectedIndexes()
        if not selected_indexes:
            return False

        allowed_cols = {1, 2}
        if any(index.column() not in allowed_cols for index in selected_indexes):
            return False

        text = QApplication.clipboard().text().strip()
        if not text:
            return False

        # 只在单列多选时处理，避免误覆盖其它列
        selected_cols = {index.column() for index in selected_indexes}
        if len(selected_cols) != 1:
            return False

        target_col = selected_cols.pop()
        selected_rows = sorted({index.row() for index in selected_indexes})

        values = [line.strip() for line in text.splitlines() if line.strip()]
        if not values:
            return False

        # 单值粘贴：应用到所有选中单元格
        if len(values) == 1:
            values = values * len(selected_rows)

        if len(values) != len(selected_rows):
            QMessageBox.warning(
                self,
                "粘贴失败",
                f"选中了 {len(selected_rows)} 行，但粘贴了 {len(values)} 行内容，请保持数量一致。"
            )
            return True

        touched_rows = set()
        self.loading_data = True
        try:
            for row, value in zip(selected_rows, values):
                cell_item = table.item(row, target_col)
                if not cell_item:
                    cell_item = QTableWidgetItem()
                    table.setItem(row, target_col, cell_item)
                cell_item.setText(value)
                touched_rows.add(row)
        finally:
            self.loading_data = False

        for row in touched_rows:
            changed_item = table.item(row, target_col)
            if changed_item:
                self.on_table_cell_changed(table, changed_item)

        return True

    def on_table_cell_changed(self, table, item):
        """表格单元格内容变更时自动保存"""
        # 如果正在加载数据，不触发保存
        if self.loading_data: return
        if not self.current_tpl_id: return

        row = item.row()
        col = item.column()

        # 0列是ID，不处理（或应禁止编辑）
        if col == 0: return

        # 获取该行对应的元数据索引
        if row >= len(self.current_row_map): return
        category, idx, item_data = self.current_row_map[row]

        # 获取当前行的最新数据
        # 注意：这里需要防御性编程，因为可能某些单元格为空
        def get_text(c):
            return table.item(row, c).text() if table.item(row, c) else ""

        new_risk = get_text(1)
        new_point = get_text(2)
        new_req = get_text(3)
        new_method = get_text(4)

        try:
            # 更新数据库
            db.update_template_item_text(self.current_tpl_id, category, idx,
                                         new_point, new_req, new_method, new_risk)

            # 同时更新内存中的缓存数据，防止下次读取时还是旧的
            item_data['risk_level'] = new_risk
            item_data['point'] = new_point
            item_data['requirement'] = new_req
            item_data['method'] = new_method

            # 可选：在控制台打印保存日志
            # print(f"已自动保存: {category} - {new_point}")
        except Exception as e:
            # 避免弹出太多框，这里打印错误
            print(f"自动保存失败: {str(e)}")

    def show_context_menu(self, pos):
        sender_table = self.sender()
        if not sender_table: return

        menu = QMenu()
        add_action = menu.addAction("新增测评项")
        del_action = menu.addAction("删除测评项")
        edit_action = menu.addAction("详细编辑 (双击)")

        action = menu.exec(sender_table.mapToGlobal(pos))

        if action == add_action:
            self.add_new_item()
        elif action == del_action:
            self.delete_selected_item()
        elif action == edit_action:
            self.open_item_editor(sender_table.currentIndex())

    def add_new_item(self):
        if not self.current_tpl_id:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return

        target_cat = "default"
        if not self.is_asset_mode:
            target_cat = self.cat_combo.currentText()
            if not target_cat or target_cat == "全部":
                QMessageBox.warning(self, "提示", "请先在上方下拉框中选择具体的分类（不能是'全部'），以便确定新项的归属。")
                return

        dialog = AddItemDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if db.add_template_item(self.current_tpl_id, target_cat, data):
                self.refresh_current_view()
            else:
                QMessageBox.critical(self, "错误", "添加失败")

    def delete_selected_item(self):
        table = self.asset_table if self.is_asset_mode else self.std_table
        current_row = table.currentRow()

        if current_row < 0 or current_row >= len(self.current_row_map):
            QMessageBox.warning(self, "提示", "请先选择要删除的测评项")
            return

        if QMessageBox.question(self, "确认", "确定删除该测评项？此操作不可恢复！") == QMessageBox.StandardButton.Yes:
            category, idx, _ = self.current_row_map[current_row]
            if db.delete_template_item(self.current_tpl_id, category, idx):
                self.refresh_current_view()
            else:
                QMessageBox.critical(self, "错误", "删除失败")

    def refresh_current_view(self):
        if self.is_asset_mode:
            self.on_template_selected(self.asset_list.currentItem(), True)
        else:
            self.on_template_selected(self.std_list.currentItem(), False)

    def on_tab_changed(self, index):
        if not hasattr(self, 'std_table') or not hasattr(self, 'asset_table'):
            return

        self.current_tpl_id = None
        self.current_data = {}
        self.current_row_map = []

        self.std_table.setRowCount(0)
        self.asset_table.setRowCount(0)

        if index == 0:
            self.load_standard_templates()
            self.is_asset_mode = False
        else:
            self.load_asset_templates()
            self.is_asset_mode = True

    def load_standard_templates(self):
        self.std_list.clear()
        templates = db.get_all_templates()
        for t in templates:
            if t.get('type') == 'asset': continue
            doc_id = getattr(t, 'doc_id', t.get('doc_id'))
            item = QListWidgetItem(t.get('name', '未命名'))
            item.setData(Qt.ItemDataRole.UserRole, doc_id)
            self.std_list.addItem(item)

    def load_asset_templates(self):
        self.asset_list.clear()
        selected_level = self.asset_level_combo.currentText() if hasattr(self, 'asset_level_combo') else "全部"
        templates = db.get_asset_templates(selected_level)
        for t in templates:
            doc_id = getattr(t, 'doc_id', t.get('doc_id'))
            level = t.get('level', '通用')
            item = QListWidgetItem(f"[{level}] {t.get('name', '未命名')}")
            item.setData(Qt.ItemDataRole.UserRole, doc_id)
            self.asset_list.addItem(item)

    def create_asset_template(self):
        level, ok = QInputDialog.getItem(self, "选择分类", "请选择模板分类:", ["二级", "三级"], 0, False)
        if not ok:
            return

        name, ok = QInputDialog.getText(self, "新建", f"请输入{level}资产模板名称 (如: Windows Server 2019):")
        if ok and name:
            db.create_asset_template(name, level)
            self.load_asset_templates()

    def delete_asset_template(self):
        item = self.asset_list.currentItem()
        if item:
            if QMessageBox.question(self, "确认", "确定删除该资产模板？") == QMessageBox.StandardButton.Yes:
                db.delete_template(item.data(Qt.ItemDataRole.UserRole))
                self.load_asset_templates()
                self.asset_table.setRowCount(0)

    def on_template_selected(self, item, is_asset):
        if not item: return
        self.current_tpl_id = item.data(Qt.ItemDataRole.UserRole)
        self.is_asset_mode = is_asset

        tpl = db.get_template_by_id(self.current_tpl_id)
        if not tpl: return

        self.current_data = tpl.get('items', {})

        if not is_asset:
            previous_cat = self.cat_combo.currentText() if hasattr(self, 'cat_combo') else "全部"
            self.cat_combo.blockSignals(True)
            self.cat_combo.clear()
            from database import STD_CATEGORIES
            cats = ["全部"] + [c for c in STD_CATEGORIES if c != "安全计算环境"]
            self.cat_combo.addItems(cats)
            self.cat_combo.blockSignals(False)

            # 刷新列表时尽量保留用户当前的分类筛选，避免关闭详情窗口后跳回“全部”。
            target_cat = previous_cat if previous_cat in cats else "全部"
            self.cat_combo.setCurrentText(target_cat)
            self.filter_items()
        else:
            self.current_row_map = []
            if isinstance(self.current_data, list):
                for idx, val in enumerate(self.current_data):
                    self.current_row_map.append(('default', idx, val))
            self.refresh_table(self.asset_table)

    def filter_items(self):
        if self.is_asset_mode: return
        cat = self.cat_combo.currentText()
        if not cat: return

        self.current_row_map = []
        if cat == "全部":
            from database import STD_CATEGORIES
            for c_name in STD_CATEGORIES:
                if c_name == "安全计算环境": continue
                if c_name in self.current_data:
                    for idx, item in enumerate(self.current_data[c_name]):
                        self.current_row_map.append((c_name, idx, item))
        elif cat in self.current_data:
            for idx, item in enumerate(self.current_data[cat]):
                self.current_row_map.append((cat, idx, item))

        self.refresh_table(self.std_table)

    def refresh_table(self, table):
        """刷新表格数据"""
        self.loading_data = True  # 锁定信号，防止填充数据时触发 itemChanged
        table.setRowCount(len(self.current_row_map))

        for row, (c, idx, item) in enumerate(self.current_row_map):
            # ID 列设为不可编辑 (ItemIsEditable = False)
            id_item = QTableWidgetItem(item.get('id', ''))
            # 移除可编辑标志
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 0, id_item)

            risk_item = QTableWidgetItem(item.get('risk_level', '中'))
            if risk_item.text() == '高':
                risk_item.setForeground(Qt.GlobalColor.red)
            elif risk_item.text() == '低':
                risk_item.setForeground(Qt.GlobalColor.green)
            table.setItem(row, 1, risk_item)

            pt_item = QTableWidgetItem(item.get('point', ''))
            pt_item.setToolTip(item.get('point', ''))
            table.setItem(row, 2, pt_item)

            req_item = QTableWidgetItem(item.get('requirement', ''))
            req_item.setToolTip(item.get('requirement', ''))
            table.setItem(row, 3, req_item)

            method_item = QTableWidgetItem(item.get('method', ''))
            method_item.setToolTip(item.get('method', ''))
            table.setItem(row, 4, method_item)

        self.loading_data = False  # 解锁信号

    def import_data_to_current(self):
        if not self.current_tpl_id:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return

        path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "Excel/CSV Files (*.xlsx *.csv)")
        if not path: return

        success, msg = db.update_template_from_file(self.current_tpl_id, path)
        if success:
            QMessageBox.information(self, "成功", msg)
            self.refresh_current_view()
        else:
            QMessageBox.critical(self, "失败", msg)

    def open_item_editor(self, index):
        """双击打开详细编辑窗口"""
        if not self.current_tpl_id: return

        row = index.row()
        if row < len(self.current_row_map):
            c_name, idx, item_data = self.current_row_map[row]
            dialog = KBEditorDialog(self.current_tpl_id, c_name, idx, item_data, self)

            # 无论是否保存，关闭弹窗后都建议刷新一下表格
            # 因为双击可能也会触发表格的编辑状态，刷新可以清除该状态
            if dialog.exec():
                self.refresh_current_view()
            else:
                self.refresh_current_view()
