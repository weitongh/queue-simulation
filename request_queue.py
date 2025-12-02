import bisect
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QGraphicsObject


if TYPE_CHECKING:
    from server import Server
    from request import Request

class RequestQueue(QGraphicsObject):
    def __init__(self, x, y, capacity, server: 'Server | None' = None, parent=None):
        """
        Constructs a Queue with an optional parent item.

        Args:
            x: Position x
            y: Position y
            capactiy: The maximum number of requests in a queue
            server: A server object or None
            parent: QGraphicsItem
        """
        super().__init__(parent)

        # Queue state
        self.queue = []
        self.can_bypass = True
        self.capacity = capacity
        self.paired_server = server

        # Visul properties
        width = (80 + 10) * self.capacity + 10
        self._rect = QRectF(0, 0, width, 100)
        self._color = QColor(230, 230, 230)

        self.setPos(x, y)
        self.setAcceptedMouseButtons(Qt.NoButton)

    def boundingRect(self):
        """
        Defines the smallest rect enclosing the item; used for painting,
        mouse interaction, collision detection, and updates.

        Must be implemented for QGraphicsItem (including QGraphicsObject) subclasses.

        Returns:
            QRectF
        """
        return self._rect

    def paint(self, painter, option, widget=None):
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
        painter.drawRoundedRect(self._rect, 50, 50)

    def accept_request(self, request: 'Request'):
        """
        Add request to the priority queue.
        Requests are ordered by priority first (1 before 2), then by arrival order (FIFO).

        Args:
            request: A Request object

        Returns:
            The position (index + 1) of the added request in the queue.
        """
        queue = self.queue

        if len(queue) < self.capacity:
            entry = (request.priority, request)

            # Insert in sorted position
            index = bisect.bisect_right(queue, entry)
            queue.insert(index, entry)

            # Move backward all requests that are now behind the new one
            for i in range(index + 1, len(queue)):
                request = queue[i][1]
                request.move_backward()

            return index + 1
        else:
            return self.capacity + 1

    def send_request(self):
        """Send the highest priority request to the server."""
        queue = self.queue

        if not queue:
            # Set to True if requests can bypass the queue and go directly to server.
            self.can_bypass = True
            return

        # Pop the first request (highest priority) and send to server
        request = queue.pop(0)[1]
        request.move_to_server(self.paired_server)

        # Move all remaining requests forward one slot
        for _, request in queue:
            request.move_forward()
