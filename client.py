from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QGraphicsObject

from request import Request
from server import Server
from request_queue import RequestQueue


class Client(QGraphicsObject):
    def __init__(self, x, y, priority=2, parent=None):
        """
        Constructs a Client with an optional parent item.

        Args:
            x: Position x
            y: Position y
            priority: Priority level for requests sent by this client (1=high, 2=normal)
            parent: QGraphicsItem
        """
        super().__init__(parent)

        self.priority = priority

        # Visual properties
        self._rect = QRectF(0, 0, 100, 100)
        if priority == 1:
            self._color = QColor(0, 114, 178)
        else:
            self._color = QColor(230, 159, 0)

        self.setPos(x, y)
        self.setAcceptedMouseButtons(Qt.LeftButton)

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
        painter.drawEllipse(self._rect)

    def mousePressEvent(self, event):
        """
        Event handler reimplemented to receive mouse press events for this item.

        Args:
            event: QGraphicsSceneMouseEvent
        """
        super().mousePressEvent(event)
        self.send_request()

    def send_request(self):
        """Create a new request and route it to the appropriate destination."""
        request = self._create_request()
        self._route_request(request)

    def _create_request(self):
        """Create and position a new request in the scene."""
        request = Request(priority=self.priority)
        offset = QPointF(
            self._rect.width() + 6,
            (self._rect.height() - request._rect.height()) / 2
        )
        spawn_pos = self.scenePos() + offset
        request.setPos(spawn_pos)
        self.scene().addItem(request)

        # Connect to dropped signal if main window exists
        if hasattr(self.scene().views()[0], 'window'):
            main_window = self.scene().views()[0].window()
            if hasattr(main_window, '_on_request_dropped'):
                request.dropped.connect(main_window._on_request_dropped)

        return request

    def _route_request(self, request: Request):
        """Route a request to the appropriate destination."""
        target_queue = self._find_target_queue()

        if not target_queue:
            # No queues available, try to send directly to server
            server = self._find_server()
            if server:
                request.move_to_server(server)
            return

        # Route based on queue state
        if target_queue.can_bypass:
            request.move_to_server(target_queue.paired_server)
        else:
            request.move_to_queue(target_queue)

    def _find_target_queue(self):
        """
        Find the best queue to send a request to.

        Returns:
            RequestQueue or None
        """
        scene = self.scene()
        queues = [item for item in scene.items() if isinstance(item, RequestQueue)]

        if not queues:
            return None

        # First priority: find a bypassable queue
        bypassable_queue = next((q for q in queues if q.can_bypass), None)
        if bypassable_queue:
            return bypassable_queue

        # Second priority: find the least busy queue
        least_busy_queue = min(queues, key=lambda q: len(q.queue))
        return least_busy_queue

    def _find_server(self):
        """Find any server in the scene."""
        scene = self.scene()
        return next((item for item in scene.items() if isinstance(item, Server)), None)
