# 现代化黑橙配色方案
# 主色调：黑色/深灰 (#1E1E1E, #2D2D2D)
# 强调色：橙色 (#FF9800, #F57C00)
# 文字色：白色/浅灰 (#FFFFFF, #B0B0B0)

DARK_THEME = """
QMainWindow, QDialog {
    background-color: #1E1E1E;
    color: #FFFFFF;
}

QWidget {
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 14px;
    color: #E0E0E0;
}

/* 列表和表格样式 */
QListWidget, QTableWidget {
    background-color: #2D2D2D;
    border: 1px solid #3E3E3E;
    border-radius: 4px;
    outline: none;
    padding: 5px;
}

QListWidget::item {
    height: 40px;
    padding-left: 10px;
    border-bottom: 1px solid #3E3E3E;
}

QListWidget::item:selected, QTableWidget::item:selected {
    background-color: #FF9800;
    color: #000000;
    border-radius: 2px;
}

QListWidget::item:hover {
    background-color: #3E3E3E;
}

/* 按钮样式 */
QPushButton {
    background-color: #FF9800;
    color: #000000;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #FFA726;
}

QPushButton:pressed {
    background-color: #F57C00;
}

QPushButton#dangerBtn {
    background-color: #D32F2F;
    color: white;
}
QPushButton#dangerBtn:hover {
    background-color: #E53935;
}

/* 输入框样式 */
QLineEdit, QTextEdit, QComboBox {
    background-color: #2D2D2D;
    border: 1px solid #444;
    border-radius: 4px;
    padding: 5px;
    color: #FFF;
    selection-background-color: #FF9800;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #FF9800;
}

/* 分割器手柄 */
QSplitter::handle {
    background-color: #3E3E3E;
}

/* 表头 */
QHeaderView::section {
    background-color: #1E1E1E;
    color: #FF9800;
    padding: 5px;
    border: none;
    border-bottom: 2px solid #FF9800;
    font-weight: bold;
}

/* 分组框 */
QGroupBox {
    border: 1px solid #FF9800;
    border-radius: 5px;
    margin-top: 20px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #FF9800;
}
"""