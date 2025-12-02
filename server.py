from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QGraphicsObject


if TYPE_CHECKING:
    from request_queue import RequestQueue

class Server(QGraphicsObject):
    def __init__(self, x, y, queue: 'RequestQueue | None' = None, parent=None):
        """
        Constructs a Client with an optional parent item.

        Args:
            x: Position x
            y: Position y
            queue: A RequestQueue object or None
            parent: QGraphicsItem
        """
        super().__init__(parent)

        # Server state
        self.current_request = None
        self.paired_queue = queue

        # Visual properties
        self._rect = QRectF(0, 0, 100, 100)
        self._color = QColor(0, 0, 0)

        self.setPos(x, y)

    def boundingRect(self):
        """
        Defines the smallest rect enclosing the item; used for painting,
        mouse interaction, collision detection, and updates.

        Must be implemented for QGraphicsItem (including QGraphicsObject) subclasses.

        Returns:
            QRectF
        """
        return self._rect

    def paint(self, painter, option, widegt=None):
        """
        This function is called by QGraphicsView to paint the item using local
        coordinates. Reimplement it in a QGraphicsItem subclass to define how
        the item is drawn using the provided QPainter.

        Args:
            painter: QPainter
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._color))
        painter.drawRoundedRect(self._rect, 25, 25)

    def accept_request(self, request):
        """Accept request and mark server as busy."""
        if request:
            self.current_request = request

    def release_and_notify(self):
        """Release request, mark server as free, and notify queue to send next."""
        self.current_request = None
        if self.paired_queue:
            self.paired_queue.send_request()
