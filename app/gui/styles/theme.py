"""
Professional stylesheet for English -> Bangla PDF Translator GUI
"""
STYLE_SHEET = """
QMainWindow {
    background-color: #f5f6f8;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    color: #2c3e50;
}

QPushButton {
    background-color: #2b579a;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
    min-width: 100px;
}

QPushButton:hover {
    background-color: #1e3d6b;
}

QPushButton:disabled {
    background-color: #c0c4cc;
}

QPushButton#cancel_button {
    background-color: #d9534f;
}

QPushButton#cancel_button:hover {
    background-color: #c9302c;
}

QProgressBar {
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    text-align: center;
    background-color: #eef1f6;
    height: 22px;
}

QProgressBar::chunk {
    background-color: #27ae60;
    width: 10px;
}

QTableWidget {
    background-color: #ffffff;
    border: 1px solid #dcdfe6;
    gridline-color: #eef1f6;
}

QHeaderView::section {
    background-color: #f0f2f5;
    padding: 6px;
    font-weight: bold;
    border: 1px solid #dcdfe6;
}
"""
