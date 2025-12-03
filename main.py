import sys
from PySide6.QtCore import Qt, QTimer, QElapsedTimer
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QSlider,
    QLabel
)
from view import View


class MainWindow(QMainWindow):
    """Main application window for the request queue simulation."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Queue Simulation")
        self.resize(1000, 600)

        self._setup_timer()
        self._setup_ui()

    def _setup_timer(self):
        """Set up the auto-send timer and updating stats timer."""
        # Timer for auto-sending requests
        self.send_timer = QTimer()
        self.send_timer.setInterval(10)
        self.send_timer.timeout.connect(self._check_last_send_time)
        self.is_playing = False
        self.last_send_timer = QElapsedTimer()

        # Timer for updating stats display
        self.stats_timer = QTimer()
        self.stats_timer.setInterval(1000)
        self.stats_timer.timeout.connect(self._update_stats_display)
        self.total_dropped = 0
        self.session_timer = QElapsedTimer()

    def _setup_ui(self):
        """Set up the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.addLayout(self._create_control_buttons())

        self.view = View()
        layout.addWidget(self.view)

        layout.addLayout(self._create_stats_display())

    def _create_control_buttons(self):
        """Create and return the control buttons layout."""
        hbox_layout = QHBoxLayout()

        # Add or remove queue buttons
        self.add_queue_btn = QPushButton("Add Queue")
        self.add_queue_btn.setFixedWidth(150)
        self.add_queue_btn.clicked.connect(self.add_queue)

        self.remove_queue_btn = QPushButton("Remove Queue")
        self.remove_queue_btn.setFixedWidth(150)
        self.remove_queue_btn.setDisabled(True)
        self.remove_queue_btn.clicked.connect(self.remove_queue)

        # Toggle priority client button
        self.toggle_priority_client_btn = QPushButton("Show Priority Client")
        self.toggle_priority_client_btn.setFixedWidth(180)
        self.toggle_priority_client_btn.setCheckable(True)
        self.toggle_priority_client_btn.clicked.connect(self.toggle_priority_client)

        # Play/Pause button
        self.play_btn = QPushButton("Auto Send")
        self.play_btn.setFixedWidth(100)
        self.play_btn.clicked.connect(self.toggle_play)

        # Interval slider
        slider_label = QLabel("Interval:")
        self.interval_label = QLabel("1500 ms/request")
        self.interval_label.setFixedWidth(150)

        self.interval_slider = QSlider(Qt.Horizontal)
        self.interval_slider.setMinimum(100)
        self.interval_slider.setMaximum(1500)
        self.interval_slider.setValue(1500)
        self.interval_slider.setFixedWidth(200)
        self.interval_slider.valueChanged.connect(self._update_interval_label)

        hbox_layout.addWidget(self.add_queue_btn)
        hbox_layout.addWidget(self.remove_queue_btn)
        hbox_layout.addWidget(self.toggle_priority_client_btn)
        hbox_layout.addWidget(self.play_btn)
        hbox_layout.addWidget(slider_label)
        hbox_layout.addWidget(self.interval_slider)
        hbox_layout.addWidget(self.interval_label)
        hbox_layout.addStretch()

        return hbox_layout

    def _create_stats_display(self):
        """Create and return the statistics display layout."""
        hbox_layout = QHBoxLayout()

        # Total dropped requests
        total_label = QLabel("Total Dropped:")
        self.total_dropped_label = QLabel("0")
        self.total_dropped_label.setFixedWidth(60)

        # Dropped per second
        rate_label = QLabel("Dropped/sec:")
        self.dropped_rate_label = QLabel("0.00")
        hint_label = QLabel("(Auto Send mode only)")

        hbox_layout.addStretch()
        hbox_layout.addWidget(total_label)
        hbox_layout.addWidget(self.total_dropped_label)
        hbox_layout.addWidget(rate_label)
        hbox_layout.addWidget(self.dropped_rate_label)
        hbox_layout.addWidget(hint_label)

        return hbox_layout

    def add_queue(self):
        """Add the next queue in sequence."""
        reach_max_queue_num = self.view.add_queue()
        if reach_max_queue_num:
            self.add_queue_btn.setDisabled(True)
        self.remove_queue_btn.setEnabled(True)

    def remove_queue(self):
        """Remove the last added queue."""
        reach_min_queue_num = self.view.remove_queue()
        if reach_min_queue_num:
            self.remove_queue_btn.setDisabled(True)
        self.add_queue_btn.setEnabled(True)

    def toggle_priority_client(self):
        """Toggle visibility of the priority client."""
        if self.toggle_priority_client_btn.isChecked():
            self.view.show_priority_client()
            self.toggle_priority_client_btn.setText("Hide Priority Client")
        else:
            self.view.hide_priority_client()
            self.toggle_priority_client_btn.setText("Show Priority Client")

    def toggle_play(self):
        """Toggle auto-sending requests on/off."""
        if self.is_playing:
            self.send_timer.stop()
            self.stats_timer.stop()
            self.play_btn.setText("Auto Send")
            self.is_playing = False
        else:
            self._auto_send_request()
            self.last_send_timer.restart()
            self.send_timer.start()

            self.total_dropped = 0
            self.total_dropped_label.setText("0")
            self.session_timer.restart()
            self.stats_timer.start()

            self.play_btn.setText("Stop")
            self.is_playing = True

    def _update_interval_label(self, value):
        """Update the timer interval and label display."""
        self.interval_label.setText(f"{value} ms/request")

    def _check_last_send_time(self):
        """Check if enough time has elapsed and send request."""
        interval_ms = self.interval_slider.value()
        if self.last_send_timer.elapsed() >= interval_ms:
            self._auto_send_request()
            self.last_send_timer.restart()

    def _auto_send_request(self):
        """Automatically send a request from the client."""
        if self.view.client:
            self.view.client.send_request()

    def _on_request_dropped(self):
        """Handle when a request is dropped."""
        self.total_dropped += 1
        self.total_dropped_label.setText(str(self.total_dropped))

    def _update_stats_display(self):
        """Update the statistics display."""
        self.total_dropped_label.setText(str(self.total_dropped))

        elapsed_seconds = self.session_timer.elapsed() / 1000.0
        if elapsed_seconds > 0:
            rate = self.total_dropped / elapsed_seconds
            self.dropped_rate_label.setText(f"{rate:.2f}")
        else:
            self.dropped_rate_label.setText("0.00")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
