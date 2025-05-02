##
##    Elecraft P3 w/SVG interface
##    allows control of SPAN and point and click on spectrum
##    rolling the mouse wheel moves frequency up and down.
##
##    Co-developed with ChatGPT
##    May 1, 2025
##    WR9R
##

import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import serial
import time
import re
import json
import os
from serial.tools import list_ports
from ttkthemes import ThemedTk

MY_VERSION = "WR9R  V0.1"
MY_POLL_TIME = 500
CONFIG_FILE = "config.json"

frequency = 0
Scale = 50000

# Load saved settings
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"video_source": 0, "comm_port": "COM4", "comm_rate": "38400"}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

config = load_config()
MY_VIDEO_SOURCE = config.get("video_source", 0)
MY_K3_COMM_PORT = config.get("comm_port", "COM4")
MY_COMM_RATE = config.get("comm_rate", "38400")

K3ser = serial.Serial(MY_K3_COMM_PORT, baudrate=int(MY_COMM_RATE), timeout=0.1)
K3ser.rts = False
K3ser.dtr = False
K3ser.write(b"#SPN001000;")

def extract_fa_string(k):
    match = re.search(r'FA0[^;]*;', k)
    return match.group(0) if match else None

class VideoApp:
    def __init__(self, root):
        self.root = root
        self.root.resizable(False, False)
        self.root.title("Elecraft P3 - WR9R")
        self.root.configure(bg='#2e2e2e')
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.root.after(MY_POLL_TIME, self.periodic_task)

        style = ttk.Style()
        style.theme_use('alt')
        style.configure('TButton', foreground='white', background='#444444')
        style.configure('TLabel', foreground='white', background='#2e2e2e')
        style.configure('TCombobox',
                fieldbackground='#2e2e2e',  # input area background
                background='#2e2e2e',       # arrow button background
                foreground='#ffffff')       # text color

        self.cap = cv2.VideoCapture(MY_VIDEO_SOURCE)
        if not self.cap.isOpened():
            raise RuntimeError("Could not start video capture.")

        self.video_label = tk.Label(self.root, bg='#2e2e2e')
        self.video_label.grid(row=0, column=0, columnspan=7)
        self.video_label.bind("<Motion>", self.mouse_move)
        self.video_label.bind("<Button-1>", self.mouse_click)
        self.video_label.bind("<MouseWheel>", self.on_mouse_wheel)

        self.status_label = ttk.Label(self.root, text="FREQ: ", anchor="w")
        self.status_label.grid(row=1, column=0, columnspan=7, sticky="w")

        self.video_source_var = tk.IntVar(value=MY_VIDEO_SOURCE)
        self.comm_port_var = tk.StringVar(value=MY_K3_COMM_PORT)
        self.comm_rate_var = tk.StringVar(value=MY_COMM_RATE)

        sources = self.detect_video_sources()
        ports = self.detect_serial_ports()
        rates = ["9600", "19200", "38400", "57600", "115200"]

        ttk.Label(self.root, text="Video Source:").grid(row=2, column=0)
        self.source_dropdown = ttk.Combobox(self.root, values=sources, textvariable=self.video_source_var)
        self.source_dropdown.grid(row=2, column=1)

        ttk.Label(self.root, text="COM Port:").grid(row=2, column=2)
        self.port_dropdown = ttk.Combobox(self.root, values=ports, textvariable=self.comm_port_var)
        self.port_dropdown.grid(row=2, column=3)

        ttk.Label(self.root, text="Baud Rate:").grid(row=2, column=4)
        self.rate_dropdown = ttk.Combobox(self.root, values=rates, textvariable=self.comm_rate_var)
        self.rate_dropdown.grid(row=2, column=5)

        ttk.Button(self.root, text="Save", command=self.save_settings).grid(row=2, column=6)

        ttk.Button(self.root, text="10K", command=lambda: self.button_action("10K")).grid(row=3, column=1)
        ttk.Button(self.root, text="50K", command=lambda: self.button_action("50K")).grid(row=3, column=2)
        ttk.Button(self.root, text="100K", command=lambda: self.button_action("100K")).grid(row=3, column=3)
        ttk.Button(self.root, text="200K", command=lambda: self.button_action("200K")).grid(row=3, column=4)
        ttk.Button(self.root, text="Exit", command=self.exit_app).grid(row=3, column=6)

        self.update_video()

    def detect_video_sources(self, max_sources=5):
        available = []
        for i in range(max_sources):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available

    def detect_serial_ports(self):
        return [port.device for port in list_ports.comports()]

    def save_settings(self):
        global MY_VIDEO_SOURCE, MY_K3_COMM_PORT, MY_COMM_RATE, K3ser
        MY_VIDEO_SOURCE = self.video_source_var.get()
        MY_K3_COMM_PORT = self.comm_port_var.get()
        MY_COMM_RATE = self.comm_rate_var.get()

        config['video_source'] = MY_VIDEO_SOURCE
        config['comm_port'] = MY_K3_COMM_PORT
        config['comm_rate'] = MY_COMM_RATE
        save_config(config)

        self.cap.release()
        self.cap = cv2.VideoCapture(MY_VIDEO_SOURCE)
        K3ser.close()
        K3ser = serial.Serial(MY_K3_COMM_PORT, baudrate=int(MY_COMM_RATE), timeout=0.1)
        K3ser.rts = False
        K3ser.dtr = False
        print(f"Saved settings: source {MY_VIDEO_SOURCE}, port {MY_K3_COMM_PORT}, rate {MY_COMM_RATE}")

    def periodic_task(self):
        global frequency
        if K3ser.in_waiting:
            data = K3ser.read(K3ser.in_waiting)
            s = data.decode("utf-8")
            result = extract_fa_string(s)
            if result:
                number_str = result[5:-1]
                frequency = int(number_str)
                print("FREQ:", frequency)
            K3ser.flush()
        else:
            K3ser.write(b"FA;")
            print("Sent: FA;")
        self.root.after(MY_POLL_TIME, self.periodic_task)

    def update_video(self):
        if not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if ret:
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.img = ImageTk.PhotoImage(Image.fromarray(cv2image))
            self.video_label.config(image=self.img)
            self.video_label.image = self.img
        if self.root.winfo_exists():
            self.root.after(10, self.update_video)

    def mouse_move(self, event):
        global frequency, Scale
        pos = (event.x - 320)
        offset = int((Scale/320) * pos)
        newFreq = frequency + offset
        self.status_label.config(text=f"Freq: {newFreq:08d}")

    def mouse_click(self, event):
        global frequency, Scale
        pos = (event.x - 320)
        offset = int((Scale/320) * pos)
        newFreq = frequency + offset
        formatted = f"FA000{newFreq:08d};"
        print(formatted)
        byte_data = bytearray(formatted.encode("utf-8"))
        K3ser.write(byte_data)
        K3ser.write(b"FA;")

    def on_mouse_wheel(self, event):
        if event.delta > 0:
            print("Mouse wheel scrolled up")
            self.on_wheel_up()
            K3ser.write(b"UP3;FA;")
        else:
            print("Mouse wheel scrolled down")
            self.on_wheel_down()
            K3ser.write(b"DN3;FA;")

    def on_wheel_up(self):
        print("Wheel up action")

    def on_wheel_down(self):
        print("Wheel down action")

    def button_action(self, label):
        global Scale
        print(f"Button pressed: {label}")
        match label:
            case "10K":
                Scale = 5000
                K3ser.write(b"#SPN000100;")
            case "50K":
                Scale = 25000
                K3ser.write(b"#SPN000500;")
            case "100K":
                Scale = 50000
                K3ser.write(b"#SPN001000;")
            case "200K":
                Scale = 100000
                K3ser.write(b"#SPN002000;")
            case _:
                print(f"Unknown label: {label}")

    def exit_app(self):
        print("Exiting...")
        self.cap.release()
        self.root.quit()
        self.root.destroy()

if __name__ == "__main__":
    root = ThemedTk(theme="black")
    app = VideoApp(root)
    root.mainloop()
