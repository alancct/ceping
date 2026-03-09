import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QListWidget, QListWidgetItem,
                             QPushButton, QLabel, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QMessageBox, QInputDialog)
from PyQt6.QtCore import Qt
from database import db
from ui_project import ProjectWindow


# ================= 新建项目对话框 =================
class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建测评项目")
        self.resize(400, 200)
        self.layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.level_combo = QComboBox()
        self.level_combo.addItems(["一级", "二级", "三级", "四级"])
        self.level_combo.setCurrentText("三级")

        self.template_combo = QComboBox()

        # === 关键修复：只获取标准模板，不获取资产模板 ===
        # 调试打印：如果你在控制台没有看到这句话，说明代码没有更新成功或者没重启
        print("DEBUG: 正在加载标准模板列表 (get_standard_templates)...")

        try:
            templates = db.get_standard_templates()
        except AttributeError:
            QMessageBox.critical(self, "代码版本错误",
                                 "database.py 似乎没有更新，找不到 get_standard_templates 方法。\n请检查 database.py 是否已替换为最新版本。")
            templates = []

        if not templates:
            self.template_combo.addItem("无标准模板可用")
            self.template_combo.setEnabled(False)
        else:
            for t in templates:
                # 兼容处理：获取 doc_id
                doc_id = getattr(t, 'doc_id', t.get('doc_id'))
                # 优化显示格式：[级别] 名称 (保持和你截图一样的风格)
                level = t.get('level', '无级别')
                name = t.get('name', 'Unknown')
                self.template_combo.addItem(f"[{level}] {name}", doc_id)

        self.btn_create = QPushButton("创建")
        self.btn_create.clicked.connect(self.accept)
        # 如果没有标准模板，禁用创建按钮
        self.btn_create.setEnabled(len(templates) > 0)

        self.layout.addRow("项目名称:", self.name_input)
        self.layout.addRow("等保级别:", self.level_combo)
        self.layout.addRow("选用标准:", self.template_combo)
        self.layout.addWidget(self.btn_create)

    def get_data(self):
        return (self.name_input.text(), self.level_combo.currentText(),
                self.template_combo.currentData())


# ================= 主窗口 =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("等保测评辅助工具 v2.0")
        self.resize(800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 顶部操作区
        top_layout = QHBoxLayout()
        self.btn_new = QPushButton("新建项目")
        self.btn_new.setStyleSheet("background-color: #2196F3; color: white; padding: 8px;")
        self.btn_new.clicked.connect(self.new_project)

        self.btn_refresh = QPushButton("刷新列表")
        self.btn_refresh.clicked.connect(self.load_projects)

        top_layout.addWidget(self.btn_new)
        top_layout.addWidget(self.btn_refresh)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # 项目列表区
        layout.addWidget(QLabel("项目列表:"))
        self.project_list = QListWidget()
        self.project_list.itemDoubleClicked.connect(self.open_project)
        layout.addWidget(self.project_list)

        # 底部帮助信息
        layout.addWidget(QLabel("双击项目进入测评界面，右键可删除或重命名（暂未实现右键菜单，请参考代码扩展）"))

        self.load_projects()

    def load_projects(self):
        self.project_list.clear()
        projects = db.get_all_projects()
        for p in projects:
            item = QListWidgetItem(f"[{p['level']}] {p['name']}")
            item.setData(Qt.ItemDataRole.UserRole, p.doc_id)
            self.project_list.addItem(item)

    def new_project(self):
        dialog = NewProjectDialog(self)
        if dialog.exec():
            name, level, template_id = dialog.get_data()
            if not name:
                QMessageBox.warning(self, "错误", "项目名称不能为空")
                return

            success, msg = db.create_project(name, level, template_id)
            if success:
                QMessageBox.information(self, "成功", "项目创建成功")
                self.load_projects()
            else:
                QMessageBox.critical(self, "失败", msg)

    def open_project(self, item):
        project_id = item.data(Qt.ItemDataRole.UserRole)
        # 获取项目名称，用于显示
        project_name = item.text().split('] ')[1] if '] ' in item.text() else item.text()

        self.project_window = ProjectWindow(project_id, project_name)
        self.project_window.show()
        # 注意：这里我们不关闭主窗口，而是让子窗口打开


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())