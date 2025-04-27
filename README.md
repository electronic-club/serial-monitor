# Advanced Serial Monitor

A professional serial monitor application designed for electronics engineers and embedded hardware specialists. This application provides a
modern GUI interface for communicating with serial devices like Arduino, Raspberry Pi Pico, and other microcontrollers.

## Features

- **Modern Tkinter GUI** with a clean, professional interface
- **Comprehensive connection settings**:
  - COM port selection with auto-refresh
  - Configurable baud rate, data bits, parity, stop bits, and flow control
  - Auto-reconnect functionality
- **Advanced data display options**:
  - ASCII, HEX, or combined display modes
  - Timestamp display
  - Auto-scrolling
- **Data visualization**:
  - Real-time data plotting
  - Configurable data extraction using regular expressions
  - Export data as CSV or images
- **Logging capabilities**:
  - Save terminal output to file
  - Continuous logging to file
- **Quick commands**:
  - Predefined command buttons
  - Custom command creation and persistence

## Requirements

- Python 3.6 or higher
- Required Python packages:
  - tkinter (usually included with Python)
  - pyserial
  - matplotlib

## Installation

1. Clone or download this repository
2. Install the required packages:

```bash
# Option 1: Install packages individually
pip install pyserial matplotlib

# Option 2: Install using requirements.txt
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
python main.py
```

### Connecting to a Device

1. Select the COM port from the dropdown list
2. Configure the connection parameters (baud rate, etc.)
3. Click "Connect"

### Sending Commands

1. Type your command in the input field
2. Select the appropriate line ending (None, CR, LF, CR+LF)
3. Press Enter or click "Send"

### Using Quick Commands

1. Click on any of the predefined command buttons
2. Add custom commands by clicking the "+" button

### Data Visualization

1. Configure data extraction in Tools > Data Plotter
2. View the chart with Tools > Line Chart
3. Export data as CSV or image

### Logging

1. Start logging: File > Start Logging
2. Stop logging: File > Stop Logging
3. Save current terminal output: File > Save Output

## Customization

### Quick Commands

The application saves custom quick commands to a `quick_commands.json` file. You can edit this file directly to add or modify commands.

### Display Settings

Configure display preferences in the View menu:
- Display Mode (ASCII, HEX, BOTH)
- Auto-scroll
- Show Timestamps

## Troubleshooting

### Common Issues

- **No ports available**: Make sure your device is connected and drivers are installed
- **Connection errors**: Check that no other application is using the selected port
- **Data not displaying correctly**: Try different display modes or baud rates

