from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Sequence

from PySide6.QtCore import QAbstractItemModel, QMimeData, QModelIndex, Qt


SEPARATOR_PATTERN = re.compile(r"[\\/.:]+")


@dataclass
class TagTreeNode:
    name: str
    full_tag: str | None = None
    parent: TagTreeNode | None = None
    children: list["TagTreeNode"] = field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        return self.full_tag is not None

    def child(self, row: int) -> "TagTreeNode | None":
        if 0 <= row < len(self.children):
            return self.children[row]
        return None

    def row(self) -> int:
        if self.parent is None:
            return 0
        return self.parent.children.index(self)


class TagTreeModel(QAbstractItemModel):
    def __init__(self, tags: Sequence[str] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._root = TagTreeNode("root")
        if tags:
            self.set_tags(tags)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: ARG002
        return 1

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None

        node = self._node_from_index(index)
        if role == Qt.DisplayRole:
            return node.name
        if role == Qt.ToolTipRole and node.full_tag:
            return node.full_tag
        if role == Qt.UserRole:
            return node.full_tag
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags

        node = self._node_from_index(index)
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if node.is_leaf:
            flags |= Qt.ItemIsDragEnabled
        return flags

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole,
    ):
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

        parent_node = self._node_from_index(parent)
        child_node = parent_node.child(row)
        if child_node is None:
            return QModelIndex()
        return self.createIndex(row, column, child_node)

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        node = self._node_from_index(index)
        parent_node = node.parent
        if parent_node is None or parent_node.parent is None:
            return QModelIndex()
        return self.createIndex(parent_node.row(), 0, parent_node)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.column() > 0:
            return 0
        parent_node = self._node_from_index(parent)
        return len(parent_node.children)

    def mimeTypes(self) -> list[str]:
        return ["text/plain"]

    def mimeData(self, indexes) -> QMimeData:
        mime_data = QMimeData()
        for index in indexes:
            if not index.isValid():
                continue
            node = self._node_from_index(index)
            if node.full_tag:
                mime_data.setText(node.full_tag)
                break
        return mime_data

    def supportedDragActions(self) -> Qt.DropActions:
        return Qt.CopyAction

    def set_tags(self, tags: Sequence[str]) -> None:
        self.beginResetModel()
        self._root = TagTreeNode("root")
        for full_tag in sorted(set(tags), key=str.casefold):
            self._insert_tag(full_tag)
        self.endResetModel()

    def tag_for_index(self, index: QModelIndex) -> str | None:
        if not index.isValid():
            return None
        return self._node_from_index(index).full_tag

    def _insert_tag(self, full_tag: str) -> None:
        segments = self._split_tag(full_tag)
        node = self._root
        for segment in segments[:-1]:
            existing = next(
                (child for child in node.children if child.name == segment and child.full_tag is None),
                None,
            )
            if existing is None:
                existing = TagTreeNode(segment, parent=node)
                node.children.append(existing)
            node = existing

        leaf_name = segments[-1]
        if any(child.full_tag == full_tag for child in node.children):
            return
        node.children.append(TagTreeNode(leaf_name, full_tag=full_tag, parent=node))

    def _node_from_index(self, index: QModelIndex) -> TagTreeNode:
        if index.isValid():
            return index.internalPointer()
        return self._root

    def _split_tag(self, tag_name: str) -> list[str]:
        if SEPARATOR_PATTERN.search(tag_name):
            parts = [part for part in SEPARATOR_PATTERN.split(tag_name) if part]
            if len(parts) > 1:
                return parts

        underscore_parts = [part for part in tag_name.split("_") if part]
        if len(underscore_parts) > 1:
            return underscore_parts

        return [tag_name]
