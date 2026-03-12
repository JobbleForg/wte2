from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt


@dataclass
class TagNode:
    name: str
    parent: "TagNode | None" = None
    children: list["TagNode"] = field(default_factory=list)

    def child(self, row: int) -> "TagNode | None":
        if 0 <= row < len(self.children):
            return self.children[row]
        return None

    def row(self) -> int:
        if self.parent is None:
            return 0
        return self.parent.children.index(self)


class TagTreeModel(QAbstractItemModel):
    """Small placeholder model that mirrors the future phase-6 direction."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._root = self._build_placeholder_tree()

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: ARG002
        return 1

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        node = self._node(index)
        if role == Qt.DisplayRole:
            return node.name
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole and section == 0:
            return "Tags"
        return None

    def index(
        self,
        row: int,
        column: int,
        parent: QModelIndex = QModelIndex(),
    ) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parent_node = self._node(parent)
        child_node = parent_node.child(row)
        if child_node is None:
            return QModelIndex()
        return self.createIndex(row, column, child_node)

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()
        node = self._node(index)
        parent_node = node.parent
        if parent_node is None or parent_node.parent is None:
            return QModelIndex()
        return self.createIndex(parent_node.row(), 0, parent_node)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.column() > 0:
            return 0
        return len(self._node(parent).children)

    def _node(self, index: QModelIndex) -> TagNode:
        if index.isValid():
            return index.internalPointer()
        return self._root

    def _build_placeholder_tree(self) -> TagNode:
        root = TagNode("root")
        area = TagNode("Imported Workbook", parent=root)
        root.children.append(area)
        area.children.extend(
            [
                TagNode("Phase 2 will populate real workbook tags", parent=area),
                TagNode("Phase 6 will enable drag and drop", parent=area),
            ]
        )
        return root
