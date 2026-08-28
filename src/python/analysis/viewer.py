"""Embeddable PySide workspace for completed simulation analysis."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QSplitter,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from .renderers import RENDERERS


ANALYSIS_STYLE = """
QWidget { background: #f4f6f8; color: #18212b; }
QTreeWidget, QTableWidget {
    background: #ffffff; color: #18212b;
    border: 1px solid #cbd3df; gridline-color: #d8dee8;
}
QTreeWidget::item:selected, QTableWidget::item:selected {
    background: #286eff; color: #ffffff;
}
QTreeWidget::item:hover { background: #e8efff; color: #18212b; }
QHeaderView::section, QTableCornerButton::section {
    background: #e8edf4; color: #18212b;
    border: 0; border-right: 1px solid #cbd3df;
    border-bottom: 1px solid #cbd3df; padding: 6px;
}
QToolBar, QToolButton { background: #f4f6f8; color: #18212b; }
QToolButton:hover { background: #dce6f7; }
QLabel#analysisTitle { font-size: 20px; font-weight: 600; padding: 12px 4px; }
"""


def _display_name(value):
    return value.replace("_", " ").strip().title()


class AnalysisWorkspace(QSplitter):
    """Lazy product navigator that keeps only the selected plot instantiated."""

    def __init__(self, catalog, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.catalog = catalog
        self._current_widget = None

        self.navigator = QTreeWidget()
        self.navigator.setHeaderLabel("Analysis Products")
        self.navigator.setMinimumWidth(240)
        self.navigator.currentItemChanged.connect(self._selection_changed)
        self.addWidget(self.navigator)

        self.workspace = QStackedWidget()
        welcome = QLabel("Select an analysis product")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.workspace.addWidget(welcome)
        self.addWidget(self.workspace)
        self.setStretchFactor(1, 1)
        self.setSizes([280, 1000])
        self.setStyleSheet(ANALYSIS_STYLE)

        first_product = self._populate_navigator()
        if first_product is not None:
            self.navigator.setCurrentItem(first_product)

    def _populate_navigator(self):
        owners = {}
        systems = {}
        groups = {}
        first_leaf = None
        owner_order = {
            entity.id: index for index, entity in enumerate(self.catalog.entities)
        }
        products = sorted(
            enumerate(self.catalog.products),
            key=lambda item: (
                owner_order.get(item[1].entity_id, len(owner_order)),
                item[1].display_sort_key,
            ),
        )

        for index, product in products:
            owner = owners.get(product.owner_key)
            if owner is None:
                owner = QTreeWidgetItem([product.owner_name])
                self.navigator.addTopLevelItem(owner)
                owners[product.owner_key] = owner

            system_key = product.owner_key, product.system
            system = systems.get(system_key)
            if system is None:
                system = QTreeWidgetItem(owner, [_display_name(product.system)])
                systems[system_key] = system

            parent = system
            if product.group:
                group_key = product.owner_key, product.system, product.group
                parent = groups.get(group_key)
                if parent is None:
                    parent = QTreeWidgetItem(system, [product.group])
                    groups[group_key] = parent

            leaf = QTreeWidgetItem(parent, [product.name])
            leaf.setData(0, Qt.ItemDataRole.UserRole, index)
            first_leaf = first_leaf or leaf

        self.navigator.expandToDepth(1)
        return first_leaf

    def _selection_changed(self, current, _previous):
        if current is None:
            return
        product_index = current.data(0, Qt.ItemDataRole.UserRole)
        if product_index is None:
            return
        product = self.catalog.products[int(product_index)]
        renderer = RENDERERS.get(product.kind)
        widget = (
            renderer(product)
            if renderer is not None
            else QLabel(f"No renderer is registered for {product.kind!r}")
        )
        self._replace_workspace(widget)

    def _replace_workspace(self, widget: QWidget):
        previous = self._current_widget
        self.workspace.addWidget(widget)
        self.workspace.setCurrentWidget(widget)
        self._current_widget = widget
        if previous is not None:
            self.workspace.removeWidget(previous)
            previous.deleteLater()
