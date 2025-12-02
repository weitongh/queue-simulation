from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from client import Client
from server import Server
from request_queue import RequestQueue


class View(QGraphicsView):
    """
    The viewport for the main scene and items.

    Handles scene setup, rendering options, and initial item placement.
    """

    def __init__(self):
        super().__init__()

        # 0: no queue, 1: center, 2: center + top, 3: center + top + bottom
        self._queue_num = 0

        self._setup_scene()
        self._create_items()
        self._add_initial_items()

    def _setup_scene(self):
        """Configure the graphics scene and view settings."""
        scene = QGraphicsScene(0, 0, 900, 400)
        self.setScene(scene)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setRenderHints(QPainter.Antialiasing)

    def _create_items(self):
        """Create all scene items (client, servers, queues)."""
        top_row_y = 0
        center_row_y = 150
        bottom_row_y = 300

        # Create client
        self.client = Client(0, center_row_y)
        self.priority_client = Client(0, top_row_y, priority=1)

        # Create servers and queues
        self.server_center, self.queue_center = self._create_row(center_row_y)
        self.server_top, self.queue_top = self._create_row(top_row_y)
        self.server_bottom, self.queue_bottom = self._create_row(bottom_row_y)

    def _add_initial_items(self):
        """Add initially visible items to the scene."""
        scene = self.scene()
        scene.addItem(self.client)
        scene.addItem(self.server_center)

    def _create_row(self, row_y):
        """Create and link a server and queue pair."""
        server_x = 800
        queue_capacity = 5
        queue_width = (80 + 10) * queue_capacity + 10
        queue_x = (100 + server_x - queue_width) / 2

        server = Server(server_x, row_y)
        queue = RequestQueue(queue_x, row_y, queue_capacity, server=server)
        server.paired_queue = queue
        return server, queue

    def add_queue(self):
        """Add the next queue in sequence: center -> top -> bottom."""
        scene = self.scene()

        if self._queue_num == 0:
            scene.addItem(self.queue_center)
            self._queue_num = 1

        elif self._queue_num == 1:
            scene.addItem(self.server_top)
            scene.addItem(self.queue_top)
            self._queue_num = 2

        elif self._queue_num == 2:
            scene.addItem(self.server_bottom)
            scene.addItem(self.queue_bottom)
            self._queue_num = 3

        reach_max_queue_num = self._queue_num == 3
        return reach_max_queue_num

    def remove_queue(self):
        """Remove queues in reverse order: bottom -> top -> center."""
        scene = self.scene()

        if self._queue_num == 3:
            scene.removeItem(self.queue_bottom)
            scene.removeItem(self.server_bottom)
            self._queue_num = 2

        elif self._queue_num == 2:
            scene.removeItem(self.queue_top)
            scene.removeItem(self.server_top)
            self._queue_num = 1

        elif self._queue_num == 1:
            scene.removeItem(self.queue_center)
            self._queue_num = 0

        reach_min_queue_num = self._queue_num == 0
        return reach_min_queue_num

    def show_priority_client(self):
        """Add the priority client to the scene."""
        scene = self.scene()
        scene.addItem(self.priority_client)

    def hide_priority_client(self):
        """Remove the priority client from the scene."""
        scene = self.scene()
        scene.removeItem(self.priority_client)
