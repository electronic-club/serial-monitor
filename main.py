import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import serial
import serial.tools.list_ports
import threading
import time
import datetime
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re
import json

class SerialMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Serial Monitor")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        # Serial connection variables
        self.serial_port = None
        self.is_connected = False
        self.read_thread = None
        self.stop_thread = False
        self.auto_reconnect = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

        # Data display settings
        self.display_mode = "ASCII"  # ASCII, HEX, or BOTH
        self.auto_scroll = True
        self.timestamp = True
        self.log_to_file = False
        self.log_file = None
        self.plot_data = False
        self.plot_data_points = []
        self.max_plot_points = 100
        self.plot_regex = r"(-?\d+\.?\d*)"  # Default regex to extract numeric data

        # Create the GUI
        self.create_menu()
        self.create_widgets()

        # Initialize port list
        self.update_port_list()

        # Configure style
        self.style = ttk.Style()
        self.style.configure("TButton", padding=6, relief="flat", background="#ccc")
        self.style.configure("TLabel", padding=6)
        self.style.configure("TFrame", background="#f0f0f0")

        # Set up auto-update for port list
        self.root.after(5000, self.auto_update_port_list)

    def create_menu(self):
        menubar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Save Output", command=self.save_output)
        file_menu.add_command(label="Start Logging", command=self.start_logging)
        file_menu.add_command(label="Stop Logging", command=self.stop_logging)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Clear Terminal", command=self.clear_terminal)
        view_menu.add_separator()

        # Display mode submenu
        display_submenu = tk.Menu(view_menu, tearoff=0)
        self.display_var = tk.StringVar(value="ASCII")
        display_submenu.add_radiobutton(label="ASCII", variable=self.display_var, value="ASCII", command=self.set_display_mode)
        display_submenu.add_radiobutton(label="HEX", variable=self.display_var, value="HEX", command=self.set_display_mode)
        display_submenu.add_radiobutton(label="BOTH", variable=self.display_var, value="BOTH", command=self.set_display_mode)
        view_menu.add_cascade(label="Display Mode", menu=display_submenu)

        # Timestamp option
        self.timestamp_var = tk.BooleanVar(value=True)
        view_menu.add_checkbutton(label="Show Timestamps", variable=self.timestamp_var, command=self.toggle_timestamp)

        menubar.add_cascade(label="View", menu=view_menu)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Data Plotter", command=self.show_plotter)
        tools_menu.add_command(label="Line Chart", command=self.show_line_chart)
        tools_menu.add_separator()

        # Auto-reconnect option
        self.auto_reconnect_var = tk.BooleanVar(value=False)
        tools_menu.add_checkbutton(label="Auto-reconnect", variable=self.auto_reconnect_var, command=self.toggle_auto_reconnect)

        menubar.add_cascade(label="Tools", menu=tools_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Help", command=self.show_help)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Top frame for connection settings
        connection_frame = ttk.LabelFrame(main_frame, text="Connection Settings", padding="10")
        connection_frame.pack(fill=tk.X, pady=5)

        # Port selection
        ttk.Label(connection_frame, text="Port:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.port_combo = ttk.Combobox(connection_frame, width=20)
        self.port_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # Refresh ports button
        ttk.Button(connection_frame, text="Refresh", command=self.update_port_list).grid(row=0, column=2, padx=5)

        # Baud rate selection
        ttk.Label(connection_frame, text="Baud Rate:").grid(row=0, column=3, sticky=tk.W, padx=5)
        self.baud_combo = ttk.Combobox(connection_frame, width=10)
        self.baud_combo['values'] = ('9600', '19200', '38400', '57600', '115200', '230400', '460800', '921600')
        self.baud_combo.current(4)  # Default to 115200
        self.baud_combo.grid(row=0, column=4, padx=5, pady=5)

        # Data bits
        ttk.Label(connection_frame, text="Data Bits:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.data_bits_combo = ttk.Combobox(connection_frame, width=5)
        self.data_bits_combo['values'] = ('5', '6', '7', '8')
        self.data_bits_combo.current(3)  # Default to 8
        self.data_bits_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # Parity
        ttk.Label(connection_frame, text="Parity:").grid(row=1, column=2, sticky=tk.W, padx=5)
        self.parity_combo = ttk.Combobox(connection_frame, width=5)
        self.parity_combo['values'] = ('NONE', 'EVEN', 'ODD', 'MARK', 'SPACE')
        self.parity_combo.current(0)  # Default to NONE
        self.parity_combo.grid(row=1, column=3, padx=5, pady=5)

        # Stop bits
        ttk.Label(connection_frame, text="Stop Bits:").grid(row=1, column=4, sticky=tk.W, padx=5)
        self.stop_bits_combo = ttk.Combobox(connection_frame, width=5)
        self.stop_bits_combo['values'] = ('1', '1.5', '2')
        self.stop_bits_combo.current(0)  # Default to 1
        self.stop_bits_combo.grid(row=1, column=5, padx=5, pady=5)

        # Flow control
        ttk.Label(connection_frame, text="Flow Control:").grid(row=1, column=6, sticky=tk.W, padx=5)
        self.flow_combo = ttk.Combobox(connection_frame, width=8)
        self.flow_combo['values'] = ('NONE', 'RTS/CTS', 'XON/XOFF')
        self.flow_combo.current(0)  # Default to NONE
        self.flow_combo.grid(row=1, column=7, padx=5, pady=5)

        # Connect/Disconnect button
        self.connect_button = ttk.Button(connection_frame, text="Connect", command=self.toggle_connection)
        self.connect_button.grid(row=0, column=7, rowspan=1, padx=5, pady=5, sticky=tk.E)

        # Status indicator
        self.status_var = tk.StringVar(value="Disconnected")
        self.status_label = ttk.Label(connection_frame, textvariable=self.status_var, foreground="red")
        self.status_label.grid(row=0, column=6, padx=5, pady=5)

        # Middle frame for terminal output
        terminal_frame = ttk.LabelFrame(main_frame, text="Terminal Output", padding="10")
        terminal_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Terminal controls frame
        terminal_controls_frame = ttk.Frame(terminal_frame)
        terminal_controls_frame.pack(fill=tk.X, side=tk.TOP, padx=5, pady=2)

        # Auto-scroll checkbox in terminal frame
        self.auto_scroll_var = tk.BooleanVar(value=True)
        self.auto_scroll_check = ttk.Checkbutton(
            terminal_controls_frame, 
            text="Auto-scroll", 
            variable=self.auto_scroll_var, 
            command=self.toggle_auto_scroll
        )
        self.auto_scroll_check.pack(side=tk.LEFT, padx=5)

        # Terminal output text area
        self.terminal = scrolledtext.ScrolledText(terminal_frame, wrap=tk.WORD, height=20, background="#1E1E1E", foreground="#D4D4D4")
        self.terminal.pack(fill=tk.BOTH, expand=True)
        self.terminal.config(state=tk.DISABLED)

        # Configure terminal text tags for different message types
        self.terminal.tag_configure("normal", foreground="#D4D4D4")
        self.terminal.tag_configure("input", foreground="#569CD6")  # Blue for user input
        self.terminal.tag_configure("error", foreground="#F14C4C")  # Red for errors
        self.terminal.tag_configure("success", foreground="#6A9955")  # Green for success messages
        self.terminal.tag_configure("info", foreground="#DCDCAA")  # Gold for info messages

        # Bottom frame for input
        input_frame = ttk.LabelFrame(main_frame, text="Send Command", padding="10")
        input_frame.pack(fill=tk.X, pady=5)

        # Input field
        self.input_field = ttk.Entry(input_frame)
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Line ending selection
        ttk.Label(input_frame, text="Line Ending:").pack(side=tk.LEFT, padx=5)
        self.line_ending_combo = ttk.Combobox(input_frame, width=10)
        self.line_ending_combo['values'] = ('None', 'CR', 'LF', 'CR+LF')
        self.line_ending_combo.current(3)  # Default to CR+LF
        self.line_ending_combo.pack(side=tk.LEFT, padx=5)

        # Send button
        self.send_button = ttk.Button(input_frame, text="Send", command=self.send_data)
        self.send_button.pack(side=tk.LEFT, padx=5)

        # Bind Enter key to send data
        self.input_field.bind("<Return>", lambda event: self.send_data())

        # Quick commands frame
        quick_commands_frame = ttk.LabelFrame(main_frame, text="Quick Commands", padding="10")
        quick_commands_frame.pack(fill=tk.X, pady=5)

        # Quick commands
        self.quick_commands = []
        self.create_quick_command_buttons(quick_commands_frame)

        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_quick_command_buttons(self, parent):
        # Default quick commands
        default_commands = [
            {"name": "Reset", "command": "reset"},
            {"name": "Version", "command": "version"},
            {"name": "Help", "command": "help"},
            {"name": "Status", "command": "status"},
            {"name": "Clear", "command": "clear"}
        ]

        # Try to load custom commands from file
        try:
            if os.path.exists("quick_commands.json"):
                with open("quick_commands.json", "r") as f:
                    custom_commands = json.load(f)
                    if isinstance(custom_commands, list):
                        default_commands = custom_commands
        except Exception as e:
            print(f"Error loading quick commands: {e}")

        # Create buttons
        for i, cmd in enumerate(default_commands):
            btn = ttk.Button(
                parent, 
                text=cmd["name"], 
                command=lambda cmd_param=cmd["command"]: self.send_quick_command(cmd_param)
            )
            btn.grid(row=i//5, column=i%5, padx=5, pady=5, sticky=tk.W)
            self.quick_commands.append({"button": btn, "command": cmd["command"]})

        # Add button to add new command
        add_btn = ttk.Button(parent, text="+", width=3, command=self.add_quick_command)
        add_btn.grid(row=(len(default_commands))//5, column=(len(default_commands))%5, padx=5, pady=5, sticky=tk.W)

    def add_quick_command(self):
        # Create a dialog to add a new quick command
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Quick Command")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Button Name:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        name_entry = ttk.Entry(dialog, width=20)
        name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Command:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        cmd_entry = ttk.Entry(dialog, width=20)
        cmd_entry.grid(row=1, column=1, padx=5, pady=5)

        def save_command():
            name = name_entry.get().strip()
            cmd = cmd_entry.get().strip()
            if name and cmd:
                # Add to quick commands
                parent = self.quick_commands[0]["button"].master
                btn = ttk.Button(
                    parent, 
                    text=name, 
                    command=lambda cmd_param=cmd: self.send_quick_command(cmd_param)
                )
                btn.grid(row=(len(self.quick_commands))//5, column=(len(self.quick_commands))%5, padx=5, pady=5, sticky=tk.W)
                self.quick_commands.append({"button": btn, "command": cmd})

                # Save to file
                commands_to_save = [{"name": qc["button"]["text"], "command": qc["command"]} for qc in self.quick_commands]
                try:
                    with open("quick_commands.json", "w") as f:
                        json.dump(commands_to_save, f, indent=2)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save quick commands: {e}")

                dialog.destroy()
            else:
                messagebox.showerror("Error", "Both name and command are required")

        ttk.Button(dialog, text="Save", command=save_command).grid(row=2, column=0, padx=5, pady=10)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).grid(row=2, column=1, padx=5, pady=10)

    def update_port_list(self):
        """Update the list of available serial ports"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports and not self.port_combo.get():
            self.port_combo.current(0)

        # Update status bar
        self.status_bar.config(text=f"Found {len(ports)} serial ports")

    def auto_update_port_list(self):
        """Automatically update the port list every 5 seconds"""
        if not self.is_connected:
            self.update_port_list()
        self.root.after(5000, self.auto_update_port_list)

    def toggle_connection(self):
        """Connect to or disconnect from the serial port"""
        if not self.is_connected:
            self.connect_to_port()
        else:
            self.disconnect_from_port()

    def connect_to_port(self):
        """Connect to the selected serial port"""
        port = self.port_combo.get()
        if not port:
            messagebox.showerror("Error", "No port selected")
            return

        try:
            baud_rate = int(self.baud_combo.get())
            data_bits = int(self.data_bits_combo.get())

            # Convert parity setting
            parity_map = {
                'NONE': serial.PARITY_NONE,
                'EVEN': serial.PARITY_EVEN,
                'ODD': serial.PARITY_ODD,
                'MARK': serial.PARITY_MARK,
                'SPACE': serial.PARITY_SPACE
            }
            parity = parity_map[self.parity_combo.get()]

            # Convert stop bits setting
            stop_bits_map = {
                '1': serial.STOPBITS_ONE,
                '1.5': serial.STOPBITS_ONE_POINT_FIVE,
                '2': serial.STOPBITS_TWO
            }
            stop_bits = stop_bits_map[self.stop_bits_combo.get()]

            # Convert flow control setting
            flow_control = self.flow_combo.get()
            xonxoff = flow_control == 'XON/XOFF'
            rtscts = flow_control == 'RTS/CTS'

            # Open the serial port
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baud_rate,
                bytesize=data_bits,
                parity=parity,
                stopbits=stop_bits,
                xonxoff=xonxoff,
                rtscts=rtscts,
                timeout=0.1
            )

            # Update UI
            self.is_connected = True
            self.connect_button.config(text="Disconnect")
            self.status_var.set("Connected")
            self.status_label.config(foreground="green")
            self.status_bar.config(text=f"Connected to {port} at {baud_rate} baud")

            # Start reading thread
            self.stop_thread = False
            self.read_thread = threading.Thread(target=self.read_from_port)
            self.read_thread.daemon = True
            self.read_thread.start()

            # Reset reconnect attempts
            self.reconnect_attempts = 0

            # Add connection info to terminal
            self.append_to_terminal(f"Connected to {port} at {baud_rate} baud\n", "blue")

        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.status_bar.config(text=f"Connection error: {str(e)}")

    def disconnect_from_port(self):
        """Disconnect from the serial port"""
        if self.serial_port and self.serial_port.is_open:
            # Stop the reading thread
            self.stop_thread = True
            if self.read_thread:
                self.read_thread.join(1.0)  # Wait for thread to finish

            # Close the serial port
            try:
                self.serial_port.close()
            except Exception as e:
                print(f"Error closing port: {e}")

            # Update UI
            self.is_connected = False
            self.connect_button.config(text="Connect")
            self.status_var.set("Disconnected")
            self.status_label.config(foreground="red")
            self.status_bar.config(text="Disconnected")

            # Add disconnection info to terminal
            self.append_to_terminal("Disconnected from serial port\n", "blue")

    def read_from_port(self):
        """Read data from the serial port in a separate thread"""
        while not self.stop_thread and self.serial_port and self.serial_port.is_open:
            try:
                # Read data from the port
                data = self.serial_port.read(1024)
                if data:
                    # Process and display the data
                    self.process_received_data(data)
            except serial.SerialException as e:
                print(f"Serial exception: {e}")
                self.root.after(0, self.handle_connection_error, str(e))
                break
            except Exception as e:
                print(f"Error reading from port: {e}")
                self.root.after(0, self.handle_connection_error, str(e))
                break

            # Small delay to prevent high CPU usage
            time.sleep(0.01)

    def handle_connection_error(self, error_msg):
        """Handle connection errors and attempt to reconnect if enabled"""
        # Update UI to show disconnected state
        self.is_connected = False
        self.connect_button.config(text="Connect")
        self.status_var.set("Error")
        self.status_label.config(foreground="red")
        self.status_bar.config(text=f"Connection error: {error_msg}")

        # Add error info to terminal
        self.append_to_terminal(f"Connection error: {error_msg}\n", "red")

        # Try to close the port if it's still open
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except:
                pass

        # Attempt to reconnect if auto-reconnect is enabled
        if self.auto_reconnect and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            self.append_to_terminal(f"Attempting to reconnect (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})...\n", "blue")
            self.root.after(2000, self.connect_to_port)  # Try to reconnect after 2 seconds

    def process_received_data(self, data):
        """Process and display received data according to display settings"""
        if not data:
            return

        # Convert bytes to string based on display mode
        if self.display_mode == "ASCII":
            try:
                text = data.decode('utf-8', errors='replace')
            except:
                text = data.decode('ascii', errors='replace')
        elif self.display_mode == "HEX":
            text = ' '.join(f"{b:02X}" for b in data)
        else:  # BOTH
            try:
                ascii_text = data.decode('utf-8', errors='replace')
            except:
                ascii_text = data.decode('ascii', errors='replace')
            hex_text = ' '.join(f"{b:02X}" for b in data)
            text = f"{hex_text}\n{ascii_text}"

        # Add timestamp if enabled
        if self.timestamp:
            timestamp = datetime.datetime.now().strftime("[%H:%M:%S.%f")[:-3] + "] "
            text = timestamp + text

        # Append to terminal
        self.append_to_terminal(text, "normal")

        # Log to file if enabled
        if self.log_to_file and self.log_file:
            try:
                self.log_file.write(text)
                self.log_file.flush()
            except Exception as e:
                print(f"Error writing to log file: {e}")

        # Process data for plotting if enabled
        if self.plot_data:
            self.process_data_for_plot(text)

    def append_to_terminal(self, text, color="success"):
        """Append text to the terminal with the specified color tag

        Args:
            text: The text to append
            color: Either a predefined tag name ('normal', 'input', 'error', 'success', 'info')
                   or a legacy color name ('green', 'blue', 'red') which will be mapped to a tag
        """
        # Map legacy color names to new tag names
        color_map = {
            "green": "success",
            "blue": "info",
            "red": "error"
        }

        # Get the appropriate tag name
        tag = color_map.get(color, color)

        # Make sure we have a valid tag, default to 'normal' if not
        if tag not in ["normal", "input", "error", "success", "info"]:
            tag = "normal"

        self.terminal.config(state=tk.NORMAL)
        self.terminal.insert(tk.END, text, tag)

        # Auto-scroll if enabled
        if self.auto_scroll:
            self.terminal.see(tk.END)

        self.terminal.config(state=tk.DISABLED)

    def send_data(self):
        """Send data from the input field to the serial port"""
        if not self.is_connected or not self.serial_port or not self.serial_port.is_open:
            messagebox.showerror("Error", "Not connected to any port")
            return

        # Get the text from the input field
        text = self.input_field.get()
        if not text:
            return

        # Add line ending if selected
        line_ending = self.line_ending_combo.get()
        if line_ending == "CR":
            text += "\r"
        elif line_ending == "LF":
            text += "\n"
        elif line_ending == "CR+LF":
            text += "\r\n"

        try:
            # Send the data
            self.serial_port.write(text.encode('utf-8'))

            # Display in terminal with different color
            if self.timestamp:
                timestamp = datetime.datetime.now().strftime("[%H:%M:%S.%f")[:-3] + "] "
                self.append_to_terminal(f"{timestamp}TX: {text}\n", "input")
            else:
                self.append_to_terminal(f"TX: {text}\n", "input")

            # Clear the input field
            self.input_field.delete(0, tk.END)

        except Exception as e:
            messagebox.showerror("Send Error", str(e))

    def send_quick_command(self, command):
        """Send a quick command to the serial port"""
        if not self.is_connected:
            messagebox.showerror("Error", "Not connected to any port")
            return

        # Set the command in the input field and send it
        self.input_field.delete(0, tk.END)
        self.input_field.insert(0, command)
        self.send_data()

    def clear_terminal(self):
        """Clear the terminal output"""
        self.terminal.config(state=tk.NORMAL)
        self.terminal.delete(1.0, tk.END)
        self.terminal.config(state=tk.DISABLED)

    def save_output(self):
        """Save the terminal output to a file"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.terminal.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Output saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save output: {e}")

    def start_logging(self):
        """Start logging terminal output to a file"""
        if self.log_to_file:
            messagebox.showinfo("Info", "Logging is already active")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            try:
                self.log_file = open(file_path, 'w', encoding='utf-8')
                self.log_to_file = True
                self.append_to_terminal(f"Started logging to {file_path}\n", "blue")
                self.status_bar.config(text=f"Logging to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start logging: {e}")

    def stop_logging(self):
        """Stop logging terminal output"""
        if not self.log_to_file:
            return

        try:
            if self.log_file:
                self.log_file.close()
                self.log_file = None
            self.log_to_file = False
            self.append_to_terminal("Stopped logging\n", "blue")
            self.status_bar.config(text="Logging stopped")
        except Exception as e:
            messagebox.showerror("Error", f"Error while stopping logging: {e}")

    def set_display_mode(self):
        """Set the display mode for received data"""
        self.display_mode = self.display_var.get()
        self.append_to_terminal(f"Display mode set to {self.display_mode}\n", "blue")

    def toggle_auto_scroll(self):
        """Toggle auto-scrolling of the terminal"""
        self.auto_scroll = self.auto_scroll_var.get()
        if self.auto_scroll:
            self.append_to_terminal("Auto-scroll enabled\n", "blue")
            # Scroll to the end when enabling auto-scroll
            self.terminal.see(tk.END)
        else:
            self.append_to_terminal("Auto-scroll disabled - you can now manually scroll through data\n", "blue")

    def toggle_timestamp(self):
        """Toggle timestamp display in the terminal"""
        self.timestamp = self.timestamp_var.get()

    def toggle_auto_reconnect(self):
        """Toggle auto-reconnect feature"""
        self.auto_reconnect = self.auto_reconnect_var.get()
        if self.auto_reconnect:
            self.append_to_terminal("Auto-reconnect enabled\n", "blue")
        else:
            self.append_to_terminal("Auto-reconnect disabled\n", "blue")

    def show_plotter(self):
        """Show the data plotter configuration dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Data Plotter Configuration")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Enable/disable plotting
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        self.plot_data_var = tk.BooleanVar(value=self.plot_data)
        ttk.Checkbutton(frame, text="Enable Data Plotting", variable=self.plot_data_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)

        # Regex pattern for extracting data
        ttk.Label(frame, text="Data Extraction Pattern:").grid(row=1, column=0, sticky=tk.W, pady=5)
        regex_entry = ttk.Entry(frame, width=30)
        regex_entry.insert(0, self.plot_regex)
        regex_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

        # Max data points
        ttk.Label(frame, text="Maximum Data Points:").grid(row=2, column=0, sticky=tk.W, pady=5)
        max_points_var = tk.StringVar(value=str(self.max_plot_points))
        ttk.Spinbox(frame, from_=10, to=1000, increment=10, textvariable=max_points_var, width=5).grid(row=2, column=1, sticky=tk.W, pady=5)

        # Example data
        ttk.Label(frame, text="Example Data Format:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Label(frame, text="temp=23.5, humidity=45%").grid(row=3, column=1, sticky=tk.W, pady=5)

        # Test regex button
        def test_regex():
            pattern = regex_entry.get()
            test_data = "temp=23.5, humidity=45%"
            try:
                matches = re.findall(pattern, test_data)
                if matches:
                    messagebox.showinfo("Regex Test", f"Found values: {matches}")
                else:
                    messagebox.showwarning("Regex Test", "No matches found with this pattern")
            except re.error as e:
                messagebox.showerror("Regex Error", f"Invalid regex pattern: {e}")

        ttk.Button(frame, text="Test Pattern", command=test_regex).grid(row=4, column=0, pady=10)

        # Save button
        def save_settings():
            try:
                # Validate regex
                re.compile(regex_entry.get())

                # Save settings
                self.plot_regex = regex_entry.get()
                self.plot_data = self.plot_data_var.get()
                self.max_plot_points = int(max_points_var.get())

                # Clear existing data points if plotting is enabled
                if self.plot_data:
                    self.plot_data_points = []
                    self.append_to_terminal("Data plotting enabled\n", "blue")
                else:
                    self.append_to_terminal("Data plotting disabled\n", "blue")

                dialog.destroy()
            except re.error as e:
                messagebox.showerror("Error", f"Invalid regex pattern: {e}")
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid number format: {e}")

        ttk.Button(frame, text="Save", command=save_settings).grid(row=5, column=0, pady=10)
        ttk.Button(frame, text="Cancel", command=dialog.destroy).grid(row=5, column=1, pady=10)

    def process_data_for_plot(self, text):
        """Extract numeric data from received text for plotting"""
        try:
            # Extract numbers using regex
            matches = re.findall(self.plot_regex, text)
            if matches:
                # Convert to float and add to data points
                for match in matches:
                    try:
                        value = float(match)
                        timestamp = time.time()
                        self.plot_data_points.append((timestamp, value))

                        # Limit the number of data points
                        if len(self.plot_data_points) > self.max_plot_points:
                            self.plot_data_points.pop(0)
                    except ValueError:
                        # Skip non-numeric matches
                        pass
        except re.error:
            # Invalid regex pattern
            pass

    def show_line_chart(self):
        """Display a line chart of the collected data"""
        if not self.plot_data_points:
            messagebox.showinfo("Info", "No data available for plotting")
            return

        # Create a new window for the chart
        chart_window = tk.Toplevel(self.root)
        chart_window.title("Data Visualization")
        chart_window.geometry("800x600")

        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(10, 6))

        # Extract data
        timestamps = [t for t, _ in self.plot_data_points]
        values = [v for _, v in self.plot_data_points]

        # Convert timestamps to relative time (seconds since start)
        if timestamps:
            start_time = timestamps[0]
            rel_timestamps = [(t - start_time) for t in timestamps]
        else:
            rel_timestamps = []

        # Plot the data
        ax.plot(rel_timestamps, values, 'b-')
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('Value')
        ax.set_title('Serial Data Visualization')
        ax.grid(True)

        # Add statistics
        if values:
            min_val = min(values)
            max_val = max(values)
            avg_val = sum(values) / len(values)
            ax.text(0.02, 0.95, f"Min: {min_val:.2f}\nMax: {max_val:.2f}\nAvg: {avg_val:.2f}", 
                    transform=ax.transAxes, bbox=dict(facecolor='white', alpha=0.7))

        # Create toolbar frame
        toolbar_frame = ttk.Frame(chart_window)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)

        # Add controls
        ttk.Button(toolbar_frame, text="Clear Data", 
                  command=lambda: self.clear_plot_data(chart_window)).pack(side=tk.LEFT, padx=5, pady=5)

        ttk.Button(toolbar_frame, text="Export CSV", 
                  command=self.export_plot_data).pack(side=tk.LEFT, padx=5, pady=5)

        ttk.Button(toolbar_frame, text="Export Image", 
                  command=lambda: self.export_plot_image(fig)).pack(side=tk.LEFT, padx=5, pady=5)

        # Embed the matplotlib figure in the tkinter window
        canvas = FigureCanvasTkAgg(fig, master=chart_window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def clear_plot_data(self, chart_window=None):
        """Clear the collected plot data"""
        self.plot_data_points = []
        if chart_window:
            chart_window.destroy()
        self.append_to_terminal("Plot data cleared\n", "blue")

    def export_plot_data(self):
        """Export the plot data to a CSV file"""
        if not self.plot_data_points:
            messagebox.showinfo("Info", "No data available to export")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', newline='') as f:
                    f.write("Timestamp,Value\n")
                    for timestamp, value in self.plot_data_points:
                        time_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                        f.write(f"{time_str},{value}\n")
                messagebox.showinfo("Success", f"Data exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export data: {e}")

    def export_plot_image(self, fig):
        """Export the plot as an image file"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )
        if file_path:
            try:
                fig.savefig(file_path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("Success", f"Image saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save image: {e}")

    def show_about(self):
        """Show information about the application"""
        about_text = """Advanced Serial Monitor

Version 1.0

A professional serial monitor application designed for electronics engineers 
and embedded hardware specialists. Features include:

- Multiple baud rate and connection settings
- Data visualization
- Logging capabilities
- Multiple display formats (ASCII, HEX)
- Quick commands
- Auto-reconnect functionality

Created with Python and Tkinter.
"""
        messagebox.showinfo("About", about_text)

    def show_help(self):
        """Show help information"""
        help_text = """
Serial Monitor Help

Connection:
- Select the COM port from the dropdown list
- Set the baud rate and other connection parameters
- Click "Connect" to establish a connection
- Use "Refresh" to update the port list

Sending Commands:
- Type your command in the input field
- Select the appropriate line ending
- Press Enter or click "Send"
- Use Quick Commands for frequently used commands

Display Options:
- ASCII: Shows text representation of received data
- HEX: Shows hexadecimal values of received data
- BOTH: Shows both representations
- Auto-scroll: Toggle to automatically scroll to new data or disable to manually browse through data

Data Visualization:
- Configure data extraction in Tools > Data Plotter
- View the chart with Tools > Line Chart
- Export data as CSV or image

Logging:
- Start/Stop logging from the File menu
- Save the current terminal output with File > Save Output

For more information, visit the documentation.
"""
        help_dialog = tk.Toplevel(self.root)
        help_dialog.title("Help")
        help_dialog.geometry("600x500")

        text_widget = scrolledtext.ScrolledText(help_dialog, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)

        ttk.Button(help_dialog, text="Close", command=help_dialog.destroy).pack(pady=10)


# Main entry point
if __name__ == "__main__":
    # Create the root window
    root = tk.Tk()

    # Set application icon (optional)
    try:
        # You can add an icon file to the project and uncomment this
        # root.iconbitmap("icon.ico")
        pass
    except:
        pass

    # Create the serial monitor application
    app = SerialMonitor(root)

    # Start the main event loop
    root.mainloop()
