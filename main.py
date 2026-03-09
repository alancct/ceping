import sys
import traceback

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QListWidget, QPushButton, QLabel,
                             QInputDialog, QMessageBox, QDialog, QFormLayout, QComboBox, QLineEdit)
from PyQt6.QtCore import Qt
import styles
from database import db
from ui_project import ProjectWindow

# 尝试导入模板管理，如果失败给出提示
try:
    from ui_template_manager import TemplateManagerDialog
except ImportError as e:
    print(f"!!! 导入 ui_template_manager 失败: {e}")
    TemplateManagerDialog = None


# === 全局异常捕获 (关键：防止程序无响应) ===
def exception_hook(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    print("!!! 捕获到未处理异常:\n", error_msg)

    app = QApplication.instance()
    if app:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("程序严重错误")
        msg_box.setText("发生了一个未捕获的错误。")
        msg_box.setDetailedText(error_msg)
        msg_box.exec()
    else:
        sys.__excepthook__(exctype, value, tb)


sys.excepthook = exception_hook


class CreateProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建测评项目")
        self.resize(450, 250)
        self.layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.template_combo = QComboBox()

        try:
            self.templates = db.get_all_templates()
        except Exception as e:
            print(f"获取模板失败: {e}")
            self.templates = []

        if not self.templates:
            self.template_combo.addItem("无可用模板，请先去导入")
            self.template_combo.setEnabled(False)
        else:
            for t in self.templates:
                level = t.get('level', '未知')
                name = t.get('name', '未命名')
                # 兼容处理 doc_id
                doc_id = getattr(t, 'doc_id', None)
                if doc_id is None: doc_id = t.get('doc_id')

                if doc_id is not None:
                    self.template_combo.addItem(f"[{level}] {name}", doc_id)

        self.submit_btn = QPushButton("创建")
        self.submit_btn.clicked.connect(self.accept)
        self.submit_btn.setEnabled(len(self.templates) > 0)

        self.layout.addRow("项目名称:", self.name_input)
        self.layout.addRow("选择模板:", self.template_combo)
        self.layout.addWidget(self.submit_btn)

    def get_data(self):
        if self.template_combo.isEnabled():
            tpl_id = self.template_combo.currentData()
            # 简单回查等级
            current_level = "未知"
            for t in self.templates:
                tid = getattr(t, 'doc_id', t.get('doc_id'))
                if tid == tpl_id:
                    current_level = t.get('level', '未知')
                    break
            return self.name_input.text(), current_level, tpl_id
        return None, None, None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("等保测评辅助工具 v2.1 (稳定版)")
        self.resize(1000, 650)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        self.init_ui()
        self.load_projects()

    def init_ui(self):
        # 左侧：项目列表
        list_layout = QVBoxLayout()
        header_label = QLabel("我的项目")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #FF9800; margin-bottom: 10px;")

        self.project_list = QListWidget()
        self.project_list.itemDoubleClicked.connect(self.open_project)

        list_layout.addWidget(header_label)
        list_layout.addWidget(self.project_list)

        # 右侧：操作按钮
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(15)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        grp_proj = QLabel("项目操作")
        grp_proj.setStyleSheet("color: #888; font-size: 12px; margin-top: 10px;")

        self.btn_create = QPushButton("新建项目 (+)")
        self.btn_create.clicked.connect(self.create_project)

        self.btn_rename = QPushButton("重命名")
        self.btn_rename.clicked.connect(self.rename_project)

        self.btn_delete = QPushButton("删除项目")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.clicked.connect(self.delete_project)

        grp_sys = QLabel("系统设置")
        grp_sys.setStyleSheet("color: #888; font-size: 12px; margin-top: 30px;")

        self.btn_templates = QPushButton("模板与知识库管理")
        self.btn_templates.setStyleSheet("background-color: #2D2D2D; border: 1px solid #FF9800; color: #FF9800;")
        self.btn_templates.clicked.connect(self.open_template_manager)

        btn_layout.addWidget(grp_proj)
        btn_layout.addWidget(self.btn_create)
        btn_layout.addWidget(self.btn_rename)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(grp_sys)
        btn_layout.addWidget(self.btn_templates)
        btn_layout.addStretch()

        self.main_layout.addLayout(list_layout, stretch=3)
        self.main_layout.addLayout(btn_layout, stretch=1)

    def load_projects(self):
        try:
            self.project_list.clear()
            projects = db.get_all_projects()
            for p in projects:
                level = p.get('level', '未知')
                name = p.get('name', '未命名')
                template_name = p.get('template_name', 'Unknown')
                created_at = p.get('created_at', '')

                doc_id = getattr(p, 'doc_id', None)
                if doc_id is None: doc_id = p.get('doc_id')

                display_text = f"[{level}] {name}"
                from PyQt6.QtWidgets import QListWidgetItem
                item_widget = QListWidgetItem(display_text)
                if doc_id is not None:
                    item_widget.setData(Qt.ItemDataRole.UserRole, doc_id)

                item_widget.setToolTip(f"模板: {template_name}\n创建时间: {created_at}")
                self.project_list.addItem(item_widget)
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "加载失败", f"加载项目列表时出错: {str(e)}")

    def create_project(self):
        try:
            dialog = CreateProjectDialog(self)
            if dialog.exec():
                name, level, tpl_id = dialog.get_data()
                if not name or not tpl_id:
                    return

                success, msg = db.create_project(name, level, tpl_id)
                if success:
                    self.load_projects()
                else:
                    QMessageBox.critical(self, "错误", msg)
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "运行错误", f"创建项目时发生错误:\n{str(e)}")

    def delete_project(self):
        try:
            current_item = self.project_list.currentItem()
            if not current_item:
                QMessageBox.information(self, "提示", "请先选择一个项目")
                return

            proj_id = current_item.data(Qt.ItemDataRole.UserRole)
            confirm = QMessageBox.question(self, "确认删除",
                                           f"确定要删除项目 '{current_item.text()}' 吗？\n删除后无法恢复！",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            if confirm == QMessageBox.StandardButton.Yes:
                db.delete_project(proj_id)
                self.load_projects()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def rename_project(self):
        try:
            current_item = self.project_list.currentItem()
            if not current_item:
                QMessageBox.information(self, "提示", "请先选择一个项目")
                return

            proj_id = current_item.data(Qt.ItemDataRole.UserRole)
            old_name_full = current_item.text()
            old_name = old_name_full.split('] ')[1] if '] ' in old_name_full else old_name_full

            new_name, ok = QInputDialog.getText(self, "重命名", "请输入新项目名称:", text=old_name)
            if ok and new_name:
                db.rename_project(proj_id, new_name)
                self.load_projects()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"重命名失败: {str(e)}")

    def open_template_manager(self):
        if not TemplateManagerDialog:
            QMessageBox.critical(self, "错误", "模板管理模块未正确加载。")
            return

        try:
            mgr = TemplateManagerDialog(self)
            mgr.exec()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"打开模板管理失败:\n{str(e)}")

    def open_project(self, item):
        try:
            proj_id = item.data(Qt.ItemDataRole.UserRole)
            proj_name = item.text()
            self.project_window = ProjectWindow(proj_id, proj_name)
            self.project_window.show()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"打开项目失败:\n{str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(styles.DARK_THEME)
    app.setWindowIcon(QIcon("doge.ico"))
    window = MainWindow()
    window.show()

    sys.exit(app.exec())