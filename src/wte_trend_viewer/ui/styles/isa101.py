from __future__ import annotations


def build_stylesheet() -> str:
    return """
QMainWindow, QWidget {
    background-color: #E0E0E0;
    color: #2F2F2F;
    font-family: "Segoe UI";
    font-size: 10pt;
}

QDockWidget, QFrame {
    border: 1px solid #747474;
}

QDockWidget::title {
    background-color: #D5D5D5;
    color: #2F2F2F;
    padding: 7px 10px;
    border-bottom: 1px solid #747474;
    font-weight: 600;
}

QTreeView, QTableWidget, QLineEdit {
    background-color: #F2F2F2;
    border: 1px solid #8A8A8A;
    selection-background-color: #6B7F8E;
    selection-color: #FFFFFF;
    alternate-background-color: #ECECEC;
    gridline-color: #B0B0B0;
}

QHeaderView::section {
    background-color: #DCDCDC;
    color: #2F2F2F;
    border: none;
    border-right: 1px solid #A7A7A7;
    border-bottom: 1px solid #A7A7A7;
    padding: 6px;
    font-weight: 600;
}

QToolBar {
    background-color: #D5D5D5;
    border: 1px solid #747474;
    spacing: 6px;
    padding: 4px;
}

QToolButton {
    background-color: #E6E6E6;
    border: 1px solid #8A8A8A;
    padding: 6px 10px;
    margin-right: 4px;
}

QToolButton:hover {
    background-color: #F0F0F0;
}

QSplitter::handle {
    background-color: #B9B9B9;
}

QStatusBar {
    background-color: #D5D5D5;
    border-top: 1px solid #747474;
}
""".strip()
