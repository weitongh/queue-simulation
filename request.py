import math

from PySide6.QtCore import (
    Qt,
    QRectF,
    QPointF,
    QPropertyAnimation,
    QEasingCurve,
    QTimer,
    Property,
    Signal
)
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QGraphicsObject

from server import Server
from request_queue import RequestQueue


class Request(QGraphicsObject):
    # Signal emitted when request is dropped
    dropped = Signal()

    def __init__(self, priority=2, parent=None):
        """
        Constructs a Request with an optional parent item.

        Args:
            priority: Priority level for requests sent by this client (1=high, 2=normal)
            parent: QGraphicsItem
        """
        super().__init__(parent)

        self.priority = priority

        # Visual properties
        self._rect = QRectF(0, 0, 80, 80)
        if priority == 1:
            self._color = QColor(0, 114, 178)
        else:
            self._color = QColor(230, 159, 0)
        self._remaining_angle = 360

        # Target tracking
        self.target_server = None
        self.target_queue = None

        # Animation state
        self._move_anim = None
        self._has_checked_queue = False
        self._has_checked_server = False
        self._has_entered_server = False

        self.setAcceptedMouseButtons(Qt.NoButton)

    def __lt__(self, other):
        """Always return False so requests compare as equal (used by bisect)."""
        return False

    def __gt__(self, other):
        """Always return False so requests compare as equal (used by bisect)."""
        return False

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

        if self._remaining_angle >= 360:
            painter.drawEllipse(self._rect)
        elif self._remaining_angle > 0:
            start_angle = 90 * 16
            span_angle = self._remaining_angle * 16
            painter.drawPie(self._rect, start_angle, span_angle)

    def move_to_server(self, server: Server):
        """
        Initiate animation to move this request to the server.

        Args:
            server: A Server object
        """
        self.target_server = server

        server.paired_queue.can_bypass = False

        server_center_x = server.scenePos().x() + server._rect.width() / 2
        end_x = server_center_x - self._rect.width() / 2

        server_center_y = server.scenePos().y() + server._rect.height() / 2
        end_y = server_center_y - self._rect.height() / 2

        self._move_to(end_x, end_y)

    def move_to_queue(self, queue: RequestQueue):
        """
        Initiate animation to move this request to the queue.

        Args:
            queue: A RequestQueue object
        """
        self.target_queue = queue

        position = queue.accept_request(self)
        if position <= queue.capacity:
            slot_width = self._rect.width() + 10
            self.end_x_in_queue = queue.scenePos().x() + slot_width * (5 - position) + 10
        else:
            self.end_x_in_queue = queue.scenePos().x() - self._rect.width() + 1

        queue_center_y = queue.scenePos().y() + queue._rect.height() / 2
        self.end_y_in_queue = queue_center_y - self._rect.height() / 2

        end_x = self.end_x_in_queue
        end_y = self.end_y_in_queue
        self._move_to(end_x, end_y)

    def move_forward(self):
        """Move this request in queue one slot forward."""
        self.end_x_in_queue += self._rect.width() + 10
        end_x = self.end_x_in_queue
        end_y = self.end_y_in_queue
        self._move_to(end_x, end_y)

    def move_backward(self):
        """Move this request in queue one slot backward."""
        self.end_x_in_queue -= self._rect.width() + 10
        end_x = self.end_x_in_queue
        end_y = self.end_y_in_queue
        self._move_to(end_x, end_y)

    def _move_to(self, end_x, end_y, speed=1200):
        """
        Create a movement animation with fixed speed.

        Args:
            start_pos: QPointF starting position
            end_pos: QPointF ending position
            speed: pixels per second
        """
        if self._move_anim:
            self._move_anim = None

        start_pos = self.pos()
        end_pos = QPointF(end_x, end_y)

        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()
        distance = math.sqrt(dx * dx + dy * dy)

        duration = int(distance / speed * 1000)

        self._move_anim = QPropertyAnimation(self, b"pos")
        self._move_anim.setStartValue(start_pos)
        self._move_anim.setEndValue(end_pos)
        self._move_anim.setDuration(duration)
        self._move_anim.setEasingCurve(QEasingCurve.OutSine)

        self._move_anim.valueChanged.connect(self._check_position)
        self._move_anim.finished.connect(self._move_anim.deleteLater)
        self._move_anim.start()

    def _check_position(self):
        """Check if request has reached key positions during animation."""
        if self.target_queue and not self._has_checked_queue:
            self._check_on_reach_queue()
        elif self.target_server and not self._has_checked_server:
            self._check_on_reach_server()
        elif self.target_server and not self._has_entered_server:
            self._check_on_enter_server()

    def _check_on_reach_queue(self):
        """Check queue capacity and attempt to enter; drop request if queue is full."""
        request_right = self.pos().x() + self._rect.width()
        queue_left = self.target_queue.scenePos().x()

        if request_right >= queue_left:
            self._has_checked_queue = True
            queue = self.target_queue

            # Check if request was successfully added to queue at spawn time, which allows
            # consistent animation speed from spawn position to the final queue slot.
            # Note: The acceptance decision is made when move_to_queue() is called, not when
            # the request visually reaches the queue. If the queue was full at spawn time,
            # the request will be dropped here even if a slot opens up during travel.
            is_in_queue = any(req is self for _, req in queue.queue)
            if not is_in_queue:
                self._drop(blocking_obj=queue)

    def _check_on_reach_server(self):
        """Check server avalibility and attempt to enter; drop request if server is busy."""
        request_right = self.pos().x() + self._rect.width()
        server_left = self.target_server.scenePos().x()

        if request_right >= server_left:
            self._has_checked_server = True
            server = self.target_server
            if server.current_request is None:
                server.accept_request(self)
            elif server.current_request and server.current_request is not self:
                self._drop(blocking_obj=server)

    def _check_on_enter_server(self):
        """Check if request center has reached server center and begin processing animation if so."""
        request_center_x = self.pos().x() + self._rect.width() / 2
        server_center_x = self.target_server.scenePos().x() + self.target_server._rect.width() / 2

        if request_center_x >= server_center_x:
            self._has_entered_center = True
            self._start_processing()

    def _start_processing(self):
        """Create a processing animation with clock-wise disappearing effect."""
        self.processing_anim = QPropertyAnimation(self, b"remaining_angle")
        self.processing_anim.setStartValue(360)
        self.processing_anim.setEndValue(0)
        self.processing_anim.setDuration(1000)
        self.processing_anim.setEasingCurve(QEasingCurve.Linear)

        self.processing_anim.finished.connect(self._on_processing_finished)
        QTimer.singleShot(100, self.processing_anim.start)

    def _on_processing_finished(self):
        """Clean up after drop animation completes."""
        self.processing_anim.deleteLater()
        scene = self.scene()
        if scene:
            scene.removeItem(self)

        if self.target_server:
            self.target_server.release_and_notify()

    def _drop(self, blocking_obj):
        """
        Create a drop animation with bouncing back and falling off screen.

        Args:
            blocking_obj: The object by which the request is rejected
        """
        self.dropped.emit()

        self._move_anim.stop()
        self._move_anim.deleteLater()

        # Due to timing in animations, the request might not stop exactly at the
        # collision position, so it's manually set using the blocking object's position.
        stop_pos_x = blocking_obj.scenePos().x() - self._rect.width()
        stop_pos = QPointF(stop_pos_x, self.pos().y())
        self.setPos(stop_pos)

        end_x = stop_pos_x - self._rect.width() * 1.5
        end_y = self.scene().height() + 50

        # Bounce back (horizontal movement)
        self.bounce_anim = QPropertyAnimation(self, b"x")
        self.bounce_anim.setStartValue(self.pos().x())
        self.bounce_anim.setEndValue(end_x)
        self.bounce_anim.setDuration(500)
        self.bounce_anim.setEasingCurve(QEasingCurve.OutCubic)

        # Drop down (vertical fall)
        self.drop_anim = QPropertyAnimation(self, b"y")
        self.drop_anim.setStartValue(self.pos().y())
        self.drop_anim.setEndValue(end_y)
        self.drop_anim.setDuration(500)
        self.drop_anim.setEasingCurve(QEasingCurve.InQuad)

        self.drop_anim.finished.connect(self._on_drop_finished)
        self.bounce_anim.start()
        self.drop_anim.start()

    def _on_drop_finished(self):
        """Clean up after drop animation completes."""
        self.bounce_anim.deleteLater()
        self.drop_anim.deleteLater()

        scene = self.scene()
        if scene:
            scene.removeItem(self)

    def _get_remaining_angle(self):
        """Get the remaining angle for animation."""
        return self._remaining_angle

    def _set_remaining_angle(self, angle):
        """Set the remaining angle and trigger repaint."""
        self._remaining_angle = angle
        self.update()

    # Define as a Qt property so it can be animated
    remaining_angle = Property(float, _get_remaining_angle, _set_remaining_angle)
