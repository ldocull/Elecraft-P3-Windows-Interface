##
##    Elecraft P3 w/SVG interface
##    allows control of SPAN and point and click on spectrum
##    rolling the mouse wheel moves frequency up and down.
##
##    Co-developed with ChatGPT
##    May 1, 2025
##    WR9R
##
##    May 6 -- Added Marker and FVO controls
##    May 12 -- Added Band amd Mode Drop downs
##    May 13 -- Added window scalability
##    May 14 -- Added CW readout
##    May 22 -- Added REF and Scale adjusters
##    May 24 -- changed cursor when in the window for better picking
##    Jun 2 -- improved poll loop format and slider (scale/ref) connection with P3

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

MY_VERSION = "WR9R V1.6"
MY_POLL_TIME = 500
CONFIG_FILE = "config.json"

frequency = 0
checker = 0
Scale = 50000
whichMarker = "N"
L_slider_ready = 0
R_slider_ready = 0

# Load saved settings
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)            
    return {
        "video_source": 0,
        "k3_port": "COM4",
        "baud_rate": "38400",
        "stay_on_top": False,
        "window_x": 100,
        "window_y": 100,
        "window_width": W_WIDTH,
        "window_height": W_HEIGHT,
        "slider_value": -117.0,  # default slider position
        "left_slider_value": 60.0
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)
            
config = load_config()
MY_VIDEO_SOURCE = config.get("video_source", 0)
MY_K3_COMM_PORT = config.get("comm_port", "COM4")
MY_COMM_RATE = config.get("comm_rate", "38400")
STAY_ON_TOP = config.get("stay_on_top", False)
W_WIDTH = 750
W_HEIGHT = 615

K3ser = serial.Serial(MY_K3_COMM_PORT, baudrate=int(MY_COMM_RATE), timeout=0.1)
K3ser.rts = False
K3ser.dtr = False
K3ser.write(b"#SPN001000;")
K3ser.write(b"#SCL;")
K3ser.write(b"#REF;")

def extract_fa_string(k):
    match = re.search(r'FA0[^;]*;', k)
    return match.group(0) if match else None

def extract_bn_string(k):
    match = re.search(r'BN[^;]*;', k)
    return match.group(0) if match else None

def extract_ref_string(k):
    match = re.search(r'#REF[^;]*;', k)
    return match.group(0) if match else None

def extract_scl_string(k):
    match = re.search(r'#SCL[^;]*;', k)
    return match.group(0) if match else None

def extract_md_string(k):
    match = re.search(r'MD[^;]*;', k)
    return match.group(0) if match else None

def extract_tb_data(k):
    match = re.match(r'TB(\d{3})(.*);', k)
    if match:
        byte_count = int(match.group(1))
        data = match.group(2)
        if len(data) >= byte_count:
            return data[:byte_count]
    return None

class VideoApp:
    def __init__(self, root):
        self.root = root
        self.root.resizable(True, True)
        self.root.title("Elecraft P3 " + MY_VERSION)
        self.root.configure(bg='#2e2e2e')
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.root.after(MY_POLL_TIME, self.periodic_task)
        # Set window position and size
        window_width = config.get("window_width", W_WIDTH)
        window_height = config.get("window_height", W_HEIGHT)
        window_x = config.get("window_x", 100)
        window_y = config.get("window_y", 100)
        self.root.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")


        style = ttk.Style()
        style.theme_use('clam')  ## 'alt'
        style.configure('TButton', foreground='white', background='#444444')
        style.configure('Dark.TCheckbutton',
                foreground='white',
                background='#444444',
                focuscolor=style.configure(".")["background"])  # optional to match look
        
        style.configure('TLabel', foreground='white', background='#2e2e2e')
        style.configure('TCombobox',
                foreground='white',       # text color
                background='#444444',       # arrow button background
                fieldbackground='#2e2e2e')  # input area background

        self.stay_on_top_var = tk.BooleanVar(value=STAY_ON_TOP)
        self.stay_on_top_cb = tk.Checkbutton(
            self.root,
            text="Stay on Top",
            variable=self.stay_on_top_var,
            command=self.toggle_stay_on_top,
            bg="#444444",
            fg="white",
            selectcolor="#444444",
            activebackground="#555555"
        )

        self.stay_on_top_cb.grid(row=5, column=0, columnspan=1)

        self.root.attributes('-topmost', self.stay_on_top_var.get())

        self.cap = cv2.VideoCapture(MY_VIDEO_SOURCE)
        if not self.cap.isOpened():
            raise RuntimeError("Could not start video capture.")

        # set up mouse configuration -- point / target zones
        self.video_label = tk.Label(self.root, bg='#2e2e2e', cursor="target")
        self.video_label.grid(row=0, column=1, columnspan=6, sticky="nsew")
        self.video_label.bind("<Motion>", self.mouse_move)
        self.video_label.bind("<Button-1>", self.mouse_click)
        self.video_label.bind("<MouseWheel>", self.on_mouse_wheel)

        # add slider to scale the RF display (left side)
        self.left_slider = ttk.Scale(
            self.root,
            from_=10,
            to=80,
            orient='vertical',
            command=self.on_left_slider_change
        )
        self.left_slider.set(config.get("left_slider_value", 60))
        # Place the left slider in column -1 (or 0 if video starts at 1)
        self.left_slider.grid(row=0, column=0, rowspan=1, sticky='ns', padx=(10, 10))

        self.slider_var = tk.IntVar(value=0)  # Initial value can be set here
        # Create a frame to contain the right slider (same size as button)
        self.slider_frame = tk.Frame(self.root, width=80, bg="#2e2e2e")  # Set bg to black
        self.slider_frame.grid(row=0, column=7, rowspan=6, sticky='ns', padx=(5, 10))

        # add slider to set reference the RF display (right side)
        self.slider = ttk.Scale(
            self.root,
            from_=10,
            to=-170,
            orient='vertical',
            command=self.on_slider_change
        )
        self.slider.set(config.get("slider_value", -117.0))
        self.slider.grid(row=0, column=7, rowspan=1, sticky='ns', padx=(10, 10))

        # drop downs to select video source, comm port, and baud rate
        self.video_source_var = tk.IntVar(value=MY_VIDEO_SOURCE)
        self.comm_port_var = tk.StringVar(value=MY_K3_COMM_PORT)
        self.comm_rate_var = tk.StringVar(value=MY_COMM_RATE)

        sources = self.detect_video_sources()
        ports = self.detect_serial_ports()
        rates = ["9600", "19200", "38400", "57600", "115200"]

        # Band selector (this must be BEFORE self.band_var.set(...))
        self.band_var = tk.StringVar()
        self.band_mapping = {
            "160 M": 0,
            "80 M": 1,
            "60 M": 2,
            "40 M": 3,
            "30 M": 4,
            "20 M": 5,
            "17 M": 6,
            "15 M": 7,
            "12 M": 8,
            "10 M": 9,
            "6 M": 10
        }
        # Band select setup
        self.band_var = tk.StringVar(value="20 M")  # Set the variable first
        self.band_dropdown = ttk.Combobox(
            self.root,
            textvariable=self.band_var,
            values=list(self.band_mapping.keys()),
            state="normal",
            style='TCombobox',
            width=9
        )
        self.band_dropdown.grid(row=4, column=5)
        self.band_dropdown.bind("<<ComboboxSelected>>", self.on_band_select)

        # Mode select setup
        self.mode_mapping = {
            "LSB": 1,
            "USB": 2,
            "CW": 3,
            "FM": 4,
            "AM": 5
        }
        self.mode_var = tk.StringVar(value="USB")
        mode_options = list(self.mode_mapping.keys())

        self.mode_dropdown = ttk.Combobox(
            self.root,
            values=mode_options,
            state="normal",
            style='TCombobox',
            width=9,
            textvariable=self.mode_var
        )
        self.mode_dropdown.grid(row=5, column=5)
        self.mode_dropdown.bind("<<ComboboxSelected>>", self.on_mode_select)
        
        ttk.Label(self.root, text="VID Input:").grid(row=2, column=0)
        self.source_dropdown = ttk.Combobox(self.root, values=sources, textvariable=self.video_source_var, style='TCombobox', width=9)
        self.source_dropdown.grid(row=2, column=1)

        ttk.Label(self.root, text="COM Port:").grid(row=2, column=2)
        self.port_dropdown = ttk.Combobox(self.root, values=ports, textvariable=self.comm_port_var, style='TCombobox', width=9)
        self.port_dropdown.grid(row=2, column=3)

        ttk.Label(self.root, text="Baud Rate:").grid(row=2, column=4)
        self.rate_dropdown = ttk.Combobox(self.root, values=rates, textvariable=self.comm_rate_var, style='TCombobox', width=9)
        self.rate_dropdown.grid(row=2, column=5)


        # setup buttons for predefined span, marker and vfo controls
        ttk.Button(self.root, text="2K", command=lambda: self.button_action("2K")).grid(row=3, column=0)
        ttk.Button(self.root, text="10K", command=lambda: self.button_action("10K")).grid(row=3, column=1)
        ttk.Button(self.root, text="50K", command=lambda: self.button_action("50K")).grid(row=3, column=2)
        ttk.Button(self.root, text="100K", command=lambda: self.button_action("100K")).grid(row=3, column=3)
        ttk.Button(self.root, text="200K", command=lambda: self.button_action("200K")).grid(row=3, column=4)

        ttk.Button(self.root, text="MKR A", command=lambda: self.marker_action("MKR A")).grid(row=4, column=1)
        ttk.Button(self.root, text="MKR B", command=lambda: self.marker_action("MKR B")).grid(row=4, column=2)
        ttk.Button(self.root, text="QSY", command=lambda: self.marker_action("QSY")).grid(row=4, column=3)
        ttk.Button(self.root, text="MKR OFF", command=lambda: self.marker_action("OFF")).grid(row=4, column=4)

        ttk.Button(self.root, text="A/B", command=lambda: self.VFO_action("A/B")).grid(row=5, column=1)
        ttk.Button(self.root, text="A>B", command=lambda: self.VFO_action("A>B")).grid(row=5, column=2)
        ttk.Button(self.root, text="SPLIT", command=lambda: self.VFO_action("SPLIT")).grid(row=5, column=3)
        ttk.Button(self.root, text="SUB", command=lambda: self.VFO_action("SUB")).grid(row=5, column=4)

        ttk.Button(self.root, text="Save", command=self.save_settings).grid(row=2, column=6)
        ttk.Button(self.root, text="Exit", command=self.exit_app).grid(row=5, column=6)

        # Spacer label to force extra space to the right of the buttons for looks
        spacer = tk.Label(self.root, text="", width=2, bg='#2e2e2e')
        spacer.grid(row=3, column=7, rowspan=3)
        self.root.columnconfigure(7, weight=1)

        # Allow window to resize widgets
        for i in range(7):  # Columns 0 to 5
            self.root.columnconfigure(i, weight=1)

        for i in range(5):  # Rows 0 to 5
            self.root.rowconfigure(i, weight=1)
            
        self.update_video()

    def on_left_slider_change(self, val):   # adjust RF scales
        global L_slider_ready
        
        if L_slider_ready:
            value = int(float(val))
            print(f"L_Slider: {value}")
            formatted = f"#SCL{value:03d};"
            print(formatted)
            byte_data = bytearray(formatted.encode("utf-8"))
            K3ser.write(byte_data)
        
    def on_slider_change(self, val):        # adjust RF offset (REF)
        global R_slider_ready
        
        if R_slider_ready:
            value = int(float(val))
            print(f"R_Slider: {value}")
            formatted = f"#REF{value:03d};"
            print(formatted)
            byte_data = bytearray(formatted.encode("utf-8"))
            K3ser.write(byte_data)

    def set_left_slider_value(self, value):
        """
        Sets the left_slider (RF scale) value within its defined range (10 to 80).
        """
        clamped_value = max(10, min(value, 80))
        self.left_slider.set(clamped_value)


    def set_right_slider_value(self, value):
        """
        Sets the right slider (RF reference) value within its defined range (from 10 to -170).
        """
        clamped_value = max(-170, min(value, 10))
        self.slider.set(clamped_value)

    def on_band_select(self, event):
        selected_band = self.band_dropdown.get()
        print(f"BAND selected: {selected_band}")
        
        # You can reverse lookup the band_map if needed
        band_id = self.band_mapping.get(selected_band)
        if band_id is not None:
            # Set band_var to the selected band name, not band_id
            self.band_var.set(selected_band)
            formatted = f"BN{band_id:02d};"
            print(formatted)
            byte_data = bytearray(formatted.encode("utf-8"))
            K3ser.write(byte_data)
        
    def on_mode_select(self, event):
        selected_mode = self.mode_var.get()
        mode_code = self.mode_mapping[selected_mode]
        print(f"Selected MODE: {selected_mode} → Code: {mode_code}")
        # Send command to device, e.g.:
        K3ser.write(f"MD{mode_code};".encode())

    def set_mode_by_id(self, mode_id):
        for mode_label, mode_value in self.mode_mapping.items():
            if mode_value == mode_id:
                self.mode_var.set(mode_label)
                break

    def set_band_by_id(self, band_id):
        for band_label, band_value in self.band_mapping.items():
            if band_value == band_id:
                self.band_var.set(band_label)
                break
            
    def toggle_stay_on_top(self):
        is_on_top = self.stay_on_top_var.get()
        self.root.attributes('-topmost', is_on_top)
        config['stay_on_top'] = is_on_top
        global STAY_ON_TOP
        STAY_ON_TOP = is_on_top  # keep in sync
        save_config(config)

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
        config['stay_on_top'] = self.stay_on_top_var.get()
        config['mode'] = self.mode_var.get()
        config["band"] = self.band_var.get()
        config["slider_value"] = self.slider.get()
        config["left_slider_value"] = self.left_slider.get()
        save_config(config)

        self.cap.release()
        self.cap = cv2.VideoCapture(MY_VIDEO_SOURCE)
        K3ser.close()
        K3ser = serial.Serial(MY_K3_COMM_PORT, baudrate=int(MY_COMM_RATE), timeout=0.1)
        K3ser.rts = False
        K3ser.dtr = False
        print(f"Saved settings: source {MY_VIDEO_SOURCE}, port {MY_K3_COMM_PORT}, rate {MY_COMM_RATE}")


    def update_video(self):
        ret, frame = self.cap.read()
        if ret:
            # Resize to current label size
            w = self.video_label.winfo_width()
            h = self.video_label.winfo_height()
            if w > 0 and h > 0:
                frame = cv2.resize(frame, (w, h))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)
        self.root.after(10, self.update_video)

    def mouse_move(self, event):
        global frequency, Scale

        widget_width = self.video_label.winfo_width()
        center_x = widget_width / 2  # Current center of the widget

        # Scale per pixel (Scale is total width in Hz)
        scale_per_pixel = Scale / widget_width

        offset = int(scale_per_pixel * (event.x - center_x)) * 2
        newFreq = frequency + offset

        # Optional: Update UI or status bar
        # self.status_label.config(text=f"Freq: {newFreq:08d}")

    # mouse click will move VFO-A or MARKER-A or MARKER-B, depending on what is active
    def mouse_click(self, event):
        global frequency, Scale, whichMarker

        widget_width = self.video_label.winfo_width()
        center_x = widget_width / 2

        scale_per_pixel = Scale / widget_width
        offset = int(scale_per_pixel * (event.x - center_x)) * 2
        newFreq = frequency + offset

        if whichMarker == "A":
            formatted = f"#MFA 000{newFreq:08d};"
        elif whichMarker == "B":
            formatted = f"#MFB 000{newFreq:08d};"
        else:
            formatted = f"FA000{newFreq:08d};"

        print(formatted)
        byte_data = bytearray(formatted.encode("utf-8"))
        K3ser.write(byte_data)
        K3ser.write(b"FA;")  # Trigger display update

    
    def on_mouse_wheel(self, event):  # MOUSE UP/DOWN ACTIVE VFO (A)
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
            case "2K":
                Scale = 1000
                K3ser.write(b"#SPN000020;")
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

    def marker_action(self, label):
        global whichMarker
        print(f"Button pressed: {label}")
        match label:
            case "MKR A":
                print("Marker A action triggered")
                K3ser.write(b"#MKA1;#MKB0;")
                whichMarker = "A"
            case "MKR B":
                print("Marker B action triggered")
                K3ser.write(b"#MKA0;#MKB1;")
                whichMarker = "B"
            case "QSY":
                print("QSY action triggered")
                K3ser.write(b"#QSY1;")             
            case "OFF":
                print("Markers OFF action triggered")
                K3ser.write(b"#MKA0;#MKB0;#QSY0;")
                whichMarker = "N"
            case _:
                print(f"Unknown marker button: {label}")

    def VFO_action(self, label):
        print(f"Button pressed: {label}")
        match label:
            case "A/B":
                print("VFO A/B action triggered")
                K3ser.write(b"SWT11;")
            case "SUB":
                print("VFO REV action triggered")
                K3ser.write(b"SWT48;")
            case "A>B":
                print("VFO A=B action triggered")
                K3ser.write(b"SWT13;")
            case "SPLIT":
                print("SPLIT action triggered")
                K3ser.write(b"SWH13;")
            case _:
                print(f"Unknown marker button: {label}")

    def periodic_task(self):
        """
        Polls the K3 for status of Freq, band, mode, pan-ref, and pan-scale
        Frequency gets sampled more frequently than anything else -- for feel
        """        
        global frequency, checker, L_slider_ready, R_slider_ready

        if K3ser.in_waiting:
            data = K3ser.read(K3ser.in_waiting)
            s = data.decode("utf-8")

            match True:
                case _ if (result := extract_fa_string(s)):
                    number_str = result[5:-1]
                    try:
                        frequency = int(number_str)
                        print("FREQ:", frequency)
                    except ValueError:
                        print(f"Ignored bad Freq: '{number_str}'")

                case _ if (result := extract_bn_string(s)):
                    number_str = result[2:-1]
                    try:
                        bandid = int(number_str)
                        print("BAND:", bandid)
                        self.set_band_by_id(bandid)
                    except ValueError:
                        print(f"Ignored bad band data: '{number_str}'")

                case _ if (result := extract_md_string(s)):
                    number_str = result[2:-1]
                    try:
                        mode_id = int(number_str)
                        self.set_mode_by_id(mode_id)
                        print("MODE:", mode_id)
                    except ValueError:
                        print(f"Ignored bad mode data: '{number_str}'")

                case _ if (result := extract_scl_string(s)):
                    number_str = result[4:-1]
                    try:
                        sclval = int(number_str)
                        self.set_left_slider_value(sclval)      # Sets left slider safely
                        print("SCALE:", sclval)
                        L_slider_ready = 1
                    except ValueError:
                        print(f"Ignored bad scale data: '{number_str}'")

                case _ if (result := extract_ref_string(s)):
                    number_str = result[4:-1]
                    try:
                        refval = int(number_str)
                        self.set_right_slider_value(refval)   # Sets right slider safely
                        print("REF:", refval)
                        R_slider_ready = 1
                    except ValueError:
                        print(f"Ignored bad ref data: '{number_str}'")
                        
            K3ser.flush()
        else:
            checker += 1
            match checker:
                case 2:
                    K3ser.write(b"#REF;")
                    print("Sent: ;")
                case 4:
                    K3ser.write(b"#SCL;")
                    print("Sent: #SCL;")
                case 6:
                    K3ser.write(b"BN;")
                    print("Sent: BN;")
                case 8:
                    K3ser.write(b"MD;")
                    print("Sent: MD;")
                    checker = 0
                case _:
                    K3ser.write(b"FA;")
                    print("Sent: FA;")
            
        self.root.after(MY_POLL_TIME, self.periodic_task)

        
    def exit_app(self):
        print("Exiting...")
        # Save window position and size
        config['window_x'] = self.root.winfo_x()
        config['window_y'] = self.root.winfo_y()
        config['window_width'] = self.root.winfo_width()
        config['window_height'] = self.root.winfo_height()
        config["slider_value"] = self.slider.get()
        config["left_slider_value"] = self.left_slider.get()
        save_config(config)
        self.cap.release()
        self.root.quit()
        self.root.destroy()


if __name__ == "__main__":
    root = ThemedTk(theme="black")
    app = VideoApp(root)
    root.mainloop()
