#!/usr/bin/env python3
"""
OSC Mapper GUI with external JSON config and debug log.

- Listen IP is fixed to host IP (auto-detected).
- User configures:
    * Listen Port
    * Target IP
    * Target Port
- Mappings are loaded from config.json in the same folder.
- All incoming OSC messages are shown in a scrollable debug log.
"""

import threading
import logging
import socket
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import os
import sys
import json

from pythonosc import dispatcher, osc_server, udp_client

# ============================================================
# CONFIG
# ============================================================

VERSION = "1.0.0"
CONFIG_FILENAME = "config.json"
VALUE_MAP = {}
FORWARD_UNMAPPED = True

# ============================================================
# GLOBALS
# ============================================================

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

osc_client = None
osc_server_obj = None
server_thread = None
app_instance = None

# ============================================================
# UTILITIES
# ============================================================

def log_gui(text: str):
    """Append logs to the GUI debug window (or print if GUI not ready)."""
    global app_instance
    if app_instance and hasattr(app_instance, "log_text"):
        app_instance.log_text.configure(state="normal")
        app_instance.log_text.insert(tk.END, text + "\n")
        app_instance.log_text.see(tk.END)
        app_instance.log_text.configure(state="disabled")
    else:
        print(text)


def get_app_dir() -> str:
    """
    Directory where the script/EXE lives.
    Works both in dev and in PyInstaller EXE.
    """
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def get_local_ip() -> str:
    """Try to detect the primary local IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # No packets are actually sent to 8.8.8.8; this is just for routing.
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def load_config():
    """Load VALUE_MAP and FORWARD_UNMAPPED from JSON config file."""
    global VALUE_MAP, FORWARD_UNMAPPED

    config_path = os.path.join(get_app_dir(), CONFIG_FILENAME)

    # If config does not exist, create a default one
    if not os.path.exists(config_path):
        default = {
            "forward_unmapped": True,
            "mappings": []
        }
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2)
            log_gui(f"Config file not found. Created default at: {config_path}")
            data = default
        except Exception as e:
            log_gui(f"ERROR writing default config: {e}")
            return
    else:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            log_gui(f"Loaded config from: {config_path}")
        except Exception as e:
            log_gui(f"ERROR reading config {config_path}: {e}")
            return

    # forward_unmapped flag
    FORWARD_UNMAPPED = bool(data.get("forward_unmapped", False))

    # Build VALUE_MAP dict: (in_address, in_value) -> (out_address, out_args)
    mappings_dict = {}
    for m in data.get("mappings", []):
        in_addr = m.get("in_address")
        # in_value can be None (for matching messages with no args or we don't care)
        in_val = m.get("in_value")
        out_addr = m.get("out_address")
        out_args = m.get("out_args", [])

        if not in_addr or not out_addr:
            continue

        mappings_dict[(in_addr, in_val)] = (out_addr, out_args)

    VALUE_MAP = mappings_dict
    log_gui(f"Loaded {len(VALUE_MAP)} mappings (forward_unmapped={FORWARD_UNMAPPED})")


# ============================================================
# OSC LOGIC
# ============================================================

def send_osc(address: str, out_args):
    """Send OSC message to current target."""
    global osc_client
    if osc_client is None:
        log_gui("WARN: OSC client not initialized, cannot send.")
        return

    if out_args is None:
        args = []
    elif isinstance(out_args, (list, tuple)):
        args = out_args
    else:
        args = [out_args]

    log_gui(f"SEND → {address} {args}")
    osc_client.send_message(address, args)


def osc_handler(address, *args):
    """
    Default handler for all incoming OSC messages.
    Uses (address, first_arg) as key in VALUE_MAP.
    """
    log_gui(f"RECV ← {address} {list(args)}")

    first_arg = args[0] if args else None
    key = (address, first_arg)

    if key in VALUE_MAP:
        out_address, out_args = VALUE_MAP[key]
        send_osc(out_address, out_args)
    elif FORWARD_UNMAPPED:
        send_osc(address, list(args))
    else:
        log_gui(f"Ignored (no mapping for {key})")


def start_osc_server(listen_ip: str, listen_port: int, target_ip: str, target_port: int):
    """Start OSC server in a background thread."""
    global osc_client, osc_server_obj, server_thread

    osc_client = udp_client.SimpleUDPClient(target_ip, target_port)

    disp = dispatcher.Dispatcher()
    disp.set_default_handler(osc_handler)

    osc_server_obj = osc_server.ThreadingOSCUDPServer(
        (listen_ip, listen_port),
        disp
    )

    log_gui(f"Server starting on {listen_ip}:{listen_port}")
    log_gui(f"Forwarding mapped messages to {target_ip}:{target_port}")

    server_thread = threading.Thread(
        target=osc_server_obj.serve_forever,
        kwargs={"poll_interval": 0.1},
        daemon=True
    )
    server_thread.start()


def stop_osc_server():
    """Stop OSC server if running."""
    global osc_server_obj, server_thread
    if osc_server_obj is not None:
        log_gui("Stopping OSC server...")
        osc_server_obj.shutdown()
        osc_server_obj.server_close()
        osc_server_obj = None
    server_thread = None
    log_gui("OSC server stopped.")

def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource (works for dev and for PyInstaller EXE)
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# ============================================================
# GUI
# ============================================================

class OSCMapperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        global app_instance
        app_instance = self

        self.title("OTM • OSC Routing v{VERSION}")
        self.resizable(False, False)
        try:
            self.iconbitmap(resource_path("favicon.ico"))
        except Exception as e:
            print("Could not set window icon:", e)

        # Fixed host IP (auto-detected)
        self.host_ip = get_local_ip()

        # User-editable vars
        self.listen_port_var = tk.StringVar(value="7000")
        self.target_ip_var = tk.StringVar(value="127.0.0.1")
        self.target_port_var = tk.StringVar(value="7000")

        self.running = False

        self.entry_listen_port = None
        self.entry_target_ip = None
        self.entry_target_port = None

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="nsew", **pad)

        # Fixed listen IP
        ttk.Label(frame, text="Listen IP (fixed):").grid(row=0, column=0, sticky="e")
        ttk.Label(frame, text=self.host_ip).grid(row=0, column=1, sticky="w")

        # Listen Port
        ttk.Label(frame, text="Listen Port:").grid(row=0, column=2, sticky="e")
        self.entry_listen_port = ttk.Entry(frame, textvariable=self.listen_port_var, width=10)
        self.entry_listen_port.grid(row=0, column=3, **pad)

        # Target IP
        ttk.Label(frame, text="Target IP:").grid(row=1, column=0, sticky="e")
        self.entry_target_ip = ttk.Entry(frame, textvariable=self.target_ip_var, width=15)
        self.entry_target_ip.grid(row=1, column=1, **pad)

        # Target Port
        ttk.Label(frame, text="Target Port:").grid(row=1, column=2, sticky="e")
        self.entry_target_port = ttk.Entry(frame, textvariable=self.target_port_var, width=10)
        self.entry_target_port.grid(row=1, column=3, **pad)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=4, pady=10)

        self.start_button = ttk.Button(btn_frame, text="Start", command=self.on_start)
        self.start_button.grid(row=0, column=0, padx=5)

        self.stop_button = ttk.Button(btn_frame, text="Stop", command=self.on_stop, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5)

        # Debug Log
        ttk.Label(frame, text="Debug Log:").grid(row=3, column=0, columnspan=4, sticky="w")
        self.log_text = ScrolledText(frame, width=70, height=20, state="disabled")
        self.log_text.grid(row=4, column=0, columnspan=4, pady=4)

        # Status
        self.status_var = tk.StringVar(value="Status: Stopped")
        ttk.Label(frame, textvariable=self.status_var).grid(row=5, column=0, columnspan=4, sticky="w", **pad)

    def on_start(self):
        if self.running:
            return

        try:
            listen_port = int(self.listen_port_var.get().strip())
            target_ip = self.target_ip_var.get().strip()
            target_port = int(self.target_port_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Ports must be integers.")
            return

        try:
            start_osc_server(self.host_ip, listen_port, target_ip, target_port)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start OSC server:\n{e}")
            return

        self.running = True
        self._toggle_inputs(False)
        self.status_var.set(f"Running on {self.host_ip}:{listen_port}")
        log_gui("OSC Mapper started.")

    def on_stop(self):
        if not self.running:
            return

        stop_osc_server()
        self.running = False
        self._toggle_inputs(True)
        self.status_var.set("Status: Stopped")

    def _toggle_inputs(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.entry_listen_port.config(state=state)
        self.entry_target_ip.config(state=state)
        self.entry_target_port.config(state=state)
        self.start_button.config(state=state)
        self.stop_button.config(state="normal" if not enabled else "disabled")

    def on_close(self):
        if self.running:
            stop_osc_server()
        self.destroy()


# ============================================================
# ENTRY POINT
# ============================================================

def main():
    # Load mapping config before GUI starts
    load_config()

    app = OSCMapperApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
