# Queue Simulation

An educational, visual simulation of queueing systems built with PySide6. This application demonstrates how queues handle requests to servers and prevent request drops during peak load.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv

source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Start the application with:
```bash
python main.py
```

## Controls

### Send Requests

**Manual Mode**
- Click on **clients** (colored circles on the left) to send requests:
  - 🟠 **Orange client**: Normal requests (priority 2)
  - 🔵 **Blue client**: High-priority requests (priority 1) - hidden by default, toggle with button

**Auto-Send Mode**
- **Auto Send/Stop Button**: Toggle automatic request generation
- **Speed Slider**: Adjust request generation interval (100-1500 ms per request)

### Scene Configuration

- **Add Queue**: Adds queues in sequence (center → top → bottom)
- **Remove Queue**: Removes queues in reverse order (bottom → top → center)
- **Show/Hide Priority Client**: Toggle the visibility of the priority (blue) client

### Statistics Display

- **Total Dropped**: Cumulative count of all dropped requests
- **Dropped/sec**: Real-time drop rate (only active in Auto-Send mode)

> **Note**: Statistics reset each time Auto-Send mode is started.
