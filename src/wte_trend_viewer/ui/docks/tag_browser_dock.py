from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDockWidget,
    QLineEdit,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from ..models.tag_tree_model import TagTreeModel


class TagBrowserDock(QDockWidget):
    """Phase-1 tag browser shell with the right structure for phase 6."""

    def __init__(self, parent=None) -> None:
        super().__init__("Tag Browser", parent)
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.search_box = QLineEdit(container)
        self.search_box.setPlaceholderText("Search tags (phase 6)")
        layout.addWidget(self.search_box)

        self.tree_view = QTreeView(container)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree_view.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.tree_view.setModel(TagTreeModel(parent=self.tree_view))
        self.tree_view.expandAll()
        layout.addWidget(self.tree_view, stretch=1)

        self.setWidget(container)
