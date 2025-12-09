from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication, QGraphicsScene

from request_queue import RequestQueue
from request import Request
from server import Server
from client import Client


# Fixture to ensure QApplication exists (required for Qt widgets)
@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for the test session."""
    # Returns existing OR creates new
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

@pytest.fixture
def scene(qapp):
    """Create a QGraphicsScene for testing."""
    return QGraphicsScene(0, 0, 900, 400)


# ============================================================================
# RequestQueue Tests
# ============================================================================

class TestRequestQueue:
    """Test the priority queue logic."""

    def test_queue_creation(self):
        """Test that a queue is created with correct properties."""
        queue = RequestQueue(100, 100, capacity=5)
        assert queue.capacity == 5
        assert len(queue.queue) == 0
        assert queue.can_bypass is True
        assert queue.paired_server is None

    def test_accept_request_single(self):
        """Test accepting a single request."""
        queue = RequestQueue(100, 100, capacity=5)
        request = Request(priority=2)

        position = queue.accept_request(request)

        assert position == 1
        assert len(queue.queue) == 1
        assert queue.queue[0][1] is request

    def test_accept_request_priority_ordering(self):
        """Test that requests are ordered by priority."""
        queue = RequestQueue(100, 100, capacity=5)

        # Add normal request
        req_normal = Request(priority=2)
        queue.accept_request(req_normal)

        # Add priority request
        req_high = Request(priority=1)
        queue.accept_request(req_high)

        # Add another normal request
        req_normal2 = Request(priority=2)
        queue.accept_request(req_normal2)

        # High priority should be first
        assert len(queue.queue) == 3
        assert queue.queue[0][1] is req_high
        assert queue.queue[1][1] is req_normal
        assert queue.queue[2][1] is req_normal2

    def test_accept_request_fifo_within_priority(self):
        """Test FIFO ordering within same priority level."""
        queue = RequestQueue(100, 100, capacity=5)

        req1 = Request(priority=2)
        req2 = Request(priority=2)
        req3 = Request(priority=2)

        queue.accept_request(req1)
        queue.accept_request(req2)
        queue.accept_request(req3)

        # Should maintain FIFO order
        assert queue.queue[0][1] is req1
        assert queue.queue[1][1] is req2
        assert queue.queue[2][1] is req3

    def test_queue_full_rejection(self):
        """Test that queue rejects requests when full."""
        queue = RequestQueue(100, 100, capacity=2)

        req1 = Request(priority=2)
        req2 = Request(priority=2)
        req3 = Request(priority=2)

        pos1 = queue.accept_request(req1)
        pos2 = queue.accept_request(req2)
        # Should be rejected
        pos3 = queue.accept_request(req3)

        assert pos1 == 1
        assert pos2 == 2
        # capacity + 1 indicates rejection
        assert pos3 == 3
        assert len(queue.queue) == 2

    def test_route_request_to_server(self):
        """Test sending request from queue to server."""
        server = Server(800, 100)
        queue = RequestQueue(100, 100, capacity=5, server=server)

        request = Request(priority=2)
        queue.accept_request(request)

        request.move_to_server = Mock()

        queue.send_request()

        # Queue should be empty
        assert len(queue.queue) == 0
        # Request should be sent to server
        request.move_to_server.assert_called_once_with(server)

    def test_route_request_sets_bypass_true(self):
        """Test that can_bypass is set to True when queue becomes empty."""
        server = Server(800, 100)
        queue = RequestQueue(100, 100, capacity=5, server=server)
        queue.can_bypass = False

        queue.send_request()

        assert queue.can_bypass is True

    def test_route_request_maintains_priority_order(self):
        """Test that highest priority request is sent first."""
        server = Server(800, 100)
        queue = RequestQueue(100, 100, capacity=5, server=server)

        req_normal = Request(priority=2)
        req_priority = Request(priority=1)

        queue.accept_request(req_normal)
        queue.accept_request(req_priority)

        req_priority.move_to_server = Mock()

        queue.send_request()

        # High priority should be sent first
        req_priority.move_to_server.assert_called_once()
        assert len(queue.queue) == 1
        assert queue.queue[0][1] is req_normal


# ============================================================================
# Server Tests
# ============================================================================

class TestServer:
    """Test server request handling."""

    def test_server_creation(self):
        """Test that server is created in idle state."""
        server = Server(800, 100)
        assert server.current_request is None
        assert server.paired_queue is None

    def test_accept_request(self):
        """Test that server accepts and tracks requests."""
        server = Server(800, 100)
        request = Request(priority=2)

        server.accept_request(request)

        assert server.current_request is request

    def test_release_and_notify_without_queue(self):
        """Test releasing request when no queue is paired."""
        server = Server(800, 100)
        request = Request(priority=2)
        server.accept_request(request)

        server.release_and_notify()

        assert server.current_request is None

    def test_release_and_notify_with_queue(self):
        """Test that server notifies queue after releasing request."""
        queue = RequestQueue(100, 100, capacity=5)
        server = Server(800, 100, queue=queue)
        server.paired_queue = queue

        request = Request(priority=2)
        server.accept_request(request)

        queue.send_request = Mock()

        server.release_and_notify()

        assert server.current_request is None
        queue.send_request.assert_called_once()


# ============================================================================
# Client Tests
# ============================================================================

class TestClient:
    """Test client request generation and routing."""

    def test_client_creation_normal_priority(self):
        """Test creating a normal priority client."""
        client = Client(0, 150, priority=2)
        assert client.priority == 2

    def test_client_creation_high_priority(self):
        """Test creating a high priority client."""
        client = Client(0, 0, priority=1)
        assert client.priority == 1

    def test_route_request_to_server_when_no_queues(self, scene):
        """Test that request sends directly to server when no queues exist."""
        client = Client(0, 150)
        scene.addItem(client)

        server = Server(800, 100)
        scene.addItem(server)

        # Create request but mock its movement
        request = Request(priority=2)
        request.move_to_server = Mock()
        scene.addItem(request)

        client._route_request(request)

        # Should send directly to server
        request.move_to_server.assert_called_once_with(server)

    def test_route_request_to_server_when_bypassable_queue(self, scene):
        """Test that request sends to server when queue is bypassable."""
        client = Client(0, 150)
        scene.addItem(client)

        server = Server(800, 100)
        scene.addItem(server)

        queue = RequestQueue(400, 100, capacity=5, server=server)
        queue.can_bypass = True
        scene.addItem(queue)

        # Create request but mock its movement
        request = Request(priority=2)
        request.move_to_server = Mock()
        request.move_to_queue = Mock()
        scene.addItem(request)

        client._route_request(request)

        # Should bypass queue and go directly to server
        request.move_to_server.assert_called_once_with(server)
        request.move_to_queue.assert_not_called()

    def test_route_request_to_non_bypassable_queue(self, scene):
        """Test that request sends to queue when queue is not bypassable."""
        client = Client(0, 150)
        scene.addItem(client)

        server = Server(800, 100)
        scene.addItem(server)

        queue = RequestQueue(400, 100, capacity=5, server=server)
        queue.can_bypass = False
        scene.addItem(queue)

        # Create request but mock its movement
        request = Request(priority=2)
        request.move_to_server = Mock()
        request.move_to_queue = Mock()
        scene.addItem(request)

        client._route_request(request)

        # Should send to queue, not server
        request.move_to_queue.assert_called_once_with(queue)
        request.move_to_server.assert_not_called()

    def test_route_request_to_least_busy_among_multiple_queues(self, scene):
        """Test that request sends to the least busy queue when multiple non-bypassable queues exist."""
        client = Client(0, 150)
        scene.addItem(client)

        # Create three queues with different loads
        busy_queue_with_three = RequestQueue(300, 100, capacity=5)
        busy_queue_with_three.can_bypass = False
        busy_queue_with_three.queue = [(2, Request()), (2, Request()), (2, Request())]
        scene.addItem(busy_queue_with_three)

        least_busy_queue = RequestQueue(500, 100, capacity=5)
        least_busy_queue.can_bypass = False
        least_busy_queue.queue = [(2, Request())]
        scene.addItem(least_busy_queue)

        moderately_busy_queue = RequestQueue(700, 100, capacity=5)
        moderately_busy_queue.can_bypass = False
        moderately_busy_queue.queue = [(2, Request()), (2, Request())]
        scene.addItem(moderately_busy_queue)

        # Create request but mock its movement
        request = Request(priority=2)
        request.move_to_queue = Mock()
        scene.addItem(request)

        client._route_request(request)

        # Should route to least_busy_queue (1 request)
        request.move_to_queue.assert_called_once_with(least_busy_queue)

    def test_route_request_prefers_bypassable_over_empty_queue(self, scene):
        """Test that bypassable queue is preferred even if another queue is empty."""
        client = Client(0, 150)
        scene.addItem(client)

        server = Server(800, 100)
        scene.addItem(server)

        # Empty queue but not bypassable
        empty_queue = RequestQueue(300, 100, capacity=5)
        empty_queue.can_bypass = False
        empty_queue.queue = []
        scene.addItem(empty_queue)

        # Empty queue and bypassable
        bypassable_queue = RequestQueue(500, 100, capacity=5, server=server)
        bypassable_queue.can_bypass = True
        bypassable_queue.queue = []
        scene.addItem(bypassable_queue)

        # Create request but mock its movement
        request = Request(priority=2)
        request.move_to_server = Mock()
        request.move_to_queue = Mock()
        scene.addItem(request)

        client._route_request(request)

        # Should prefer bypassable queue (sends to its server)
        request.move_to_server.assert_called_once_with(server)
        request.move_to_queue.assert_not_called()


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Test interactions between components."""

    def test_client_to_queue_to_server_flow(self, scene):
        """Test complete flow: client -> queue -> server."""
        client = Client(0, 150, priority=2)
        scene.addItem(client)

        server = Server(800, 100)
        scene.addItem(server)

        queue = RequestQueue(400, 100, capacity=5, server=server)
        queue.can_bypass = False
        scene.addItem(queue)

        server.paired_queue = queue

        request = Request(priority=2)
        scene.addItem(request)

        # Step 1: Client routes request to queue
        client._route_request(request)

        # Note: We test _route_request() directly instead of send_request()
        # because send_request() creates the request internally, making it
        # impossible to verify the routing behavior without mocking Request creation.

        # Verify request was added to queue
        assert len(queue.queue) == 1
        assert queue.queue[0][1] is request

        request.move_to_server = Mock()

        # Step 2: Server notifies queue to send request to server
        server.release_and_notify()

        # Verify request was removed from queue
        assert len(queue.queue) == 0

        # Verify request was told to move to server
        request.move_to_server.assert_called_once_with(server)

        # Note: We don't test server.current_request because:
        # - It's only set during animation (server.accept_request() in _check_on_reach_server())
        # - Qt animations require the Qt event loop, making tests slow and complex
        # - This test verifies routing logic, not animation completion
