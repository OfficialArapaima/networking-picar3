import sys
import os
from socket import *
from picarx import Picarx
from vilib import Vilib
from datetime import datetime
import threading
import time
import struct

serverPort = 12000

# Detection settings
detection_enabled = False
scanning_paused = False
scan_lock = threading.Lock()
last_detection_time = 0
detection_cooldown = 3  # seconds between captures

# Detection modes
DETECT_FACE = 'face'
DETECT_COLOR = 'color'
DETECT_QR = 'qr'
current_detect_mode = DETECT_FACE
current_color = 'red'

color_list = ['red', 'orange', 'yellow', 'green', 'blue', 'purple']

connectionSocket = None

# Scanning settings
SCAN_SPEED = 20
TILT_MIN = -20
TILT_MAX = 20
TILT_STEP = 5
tilt_direction = 1
current_tilt = 0

px = None
camera_started = False


def initialize_camera():
    """Initialize the camera using Vilib"""
    global camera_started
    if not camera_started:
        Vilib.camera_start(vflip=False, hflip=False)
        time.sleep(1)
        print("Camera initialized with Vilib")
        camera_started = True


def set_detection_mode(mode, color=None):
    """Set the detection mode (face, color, or qr)"""
    global current_detect_mode, current_color
    
    # Turn off all detection first
    Vilib.face_detect_switch(False)
    Vilib.color_detect('close')
    Vilib.qrcode_detect_switch(False)
    
    current_detect_mode = mode
    
    if mode == DETECT_FACE:
        Vilib.face_detect_switch(True)
        print("Face detection enabled")
    elif mode == DETECT_COLOR:
        if color:
            current_color = color
        Vilib.color_detect(current_color)
        print(f"Color detection enabled: {current_color}")
    elif mode == DETECT_QR:
        Vilib.qrcode_detect_switch(True)
        print("QR code detection enabled")


def take_and_send_photo(reason="detection"):
    """Take a photo and send it to the client"""
    global connectionSocket, last_detection_time
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    username = os.getlogin()
    photo_path = f"/home/{username}/Pictures/"
    photo_name = f"capture_{timestamp}"
    
    # Take photo using Vilib
    Vilib.take_photo(photo_name, photo_path)
    full_path = f"{photo_path}{photo_name}.jpg"
    
    print(f"Photo taken: {full_path} ({reason})")
    
    # Read and send the photo to client
    time.sleep(0.3)  # Wait for file to be written
    
    if os.path.exists(full_path):
        try:
            with open(full_path, 'rb') as f:
                img_bytes = f.read()
            
            img_size = len(img_bytes)
            header = b"IMG" + timestamp.encode('utf-8') + struct.pack('>I', img_size)
            connectionSocket.sendall(header + img_bytes)
            print(f"Image sent to client: {timestamp} ({img_size} bytes)")
            last_detection_time = time.time()
            return True
        except Exception as e:
            print(f"Error sending image: {e}")
            return False
    else:
        print(f"Photo file not found: {full_path}")
        return False


def check_detection():
    """Check if something is detected based on current mode"""
    if current_detect_mode == DETECT_FACE:
        return Vilib.detect_obj_parameter['human_n'] > 0
    elif current_detect_mode == DETECT_COLOR:
        return Vilib.detect_obj_parameter['color_n'] > 0
    elif current_detect_mode == DETECT_QR:
        qr_data = Vilib.detect_obj_parameter['qr_data']
        return qr_data != "None" and qr_data != ""
    return False


def get_detection_info():
    """Get info about what was detected"""
    if current_detect_mode == DETECT_FACE:
        n = Vilib.detect_obj_parameter['human_n']
        x = Vilib.detect_obj_parameter['human_x']
        y = Vilib.detect_obj_parameter['human_y']
        return f"{n} face(s) at ({x}, {y})"
    elif current_detect_mode == DETECT_COLOR:
        n = Vilib.detect_obj_parameter['color_n']
        x = Vilib.detect_obj_parameter['color_x']
        y = Vilib.detect_obj_parameter['color_y']
        return f"{current_color} color at ({x}, {y})"
    elif current_detect_mode == DETECT_QR:
        qr_data = Vilib.detect_obj_parameter['qr_data']
        return f"QR code: {qr_data}"
    return "Unknown"


def scanning_mode():
    """Rotate slowly and move camera up/down to scan"""
    global detection_enabled, scanning_paused, current_tilt, tilt_direction, px

    while True:
        with scan_lock:
            is_paused = scanning_paused
            enabled = detection_enabled
        
        if enabled and not is_paused and px is not None:
            px.set_dir_servo_angle(-30)
            px.forward(SCAN_SPEED)
            
            current_tilt += TILT_STEP * tilt_direction
            
            if current_tilt >= TILT_MAX:
                current_tilt = TILT_MAX
                tilt_direction = -1
            elif current_tilt <= TILT_MIN:
                current_tilt = TILT_MIN
                tilt_direction = 1
            
            px.set_cam_tilt_angle(current_tilt)
            time.sleep(0.3)
            
        elif is_paused and px is not None:
            px.stop()
            time.sleep(0.1)
        else:
            time.sleep(0.1)


def detect_and_capture():
    """Continuous detection and capture in a separate thread"""
    global detection_enabled, last_detection_time, scanning_paused
    
    frame_count = 0
    while True:
        if detection_enabled:
            frame_count += 1
            if frame_count % 50 == 0:
                print(f"[DEBUG] Scanning... (check {frame_count}, mode: {current_detect_mode})")
            
            if check_detection():
                current_time = time.time()
                if current_time - last_detection_time >= detection_cooldown:
                    info = get_detection_info()
                    print(f"[DEBUG] Detected: {info}")
                    
                    # Stop scanning
                    with scan_lock:
                        scanning_paused = True
                    print("Detection! Stopping to capture...")
                    time.sleep(0.5)
                    
                    # Take and send photo
                    take_and_send_photo(info)
                    
                    # Resume scanning
                    print("Photo taken! Resuming scan in 2 seconds...")
                    time.sleep(2)
                    with scan_lock:
                        scanning_paused = False

        time.sleep(0.1)


# Bind the server to the socket
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(("", serverPort))
print("Server started on port: %s" % serverPort)
serverSocket.listen(1)
print('The server is now listening...\n')
connectionSocket, addr = serverSocket.accept()
print('Connected by %s:%d' % (addr[0], addr[1]))

px = Picarx()

# Reset camera position
px.set_cam_tilt_angle(0)
px.set_cam_pan_angle(0)

# Start threads
detect_thread = threading.Thread(target=detect_and_capture, daemon=True)
detect_thread.start()

scan_thread = threading.Thread(target=scanning_mode, daemon=True)
scan_thread.start()

print("""
Controls:
  w/a/s/d - Manual movement
  f - Toggle face detection scanning
  c - Toggle color detection (cycles through colors)
  r - Toggle QR code detection
  q - Quit
""")

while True:
    print('Waiting for command...')
    data = connectionSocket.recv(1024).decode()
    if not data:
        break

    if data == 'w':
        detection_enabled = False
        px.set_dir_servo_angle(0)
        px.forward(80)
    elif data == 's':
        detection_enabled = False
        px.set_dir_servo_angle(0)
        px.backward(80)
    elif data == 'a':
        detection_enabled = False
        px.set_dir_servo_angle(-35)
        px.forward(80)
    elif data == 'd':
        detection_enabled = False
        px.set_dir_servo_angle(35)
        px.forward(80)
    elif data == 'f':
        # Toggle face detection scanning
        detection_enabled = not detection_enabled
        if detection_enabled:
            initialize_camera()
            set_detection_mode(DETECT_FACE)
            with scan_lock:
                scanning_paused = False
            px.set_cam_tilt_angle(0)
            response = "Face detection scanning ENABLED"
        else:
            px.stop()
            Vilib.face_detect_switch(False)
            response = "Face detection scanning DISABLED"
        print(response)
        connectionSocket.send(response.encode())
        continue
    elif data == 'c':
        # Toggle/cycle color detection
        detection_enabled = not detection_enabled
        if detection_enabled:
            initialize_camera()
            # Cycle to next color
            current_idx = color_list.index(current_color) if current_color in color_list else -1
            next_color = color_list[(current_idx + 1) % len(color_list)]
            set_detection_mode(DETECT_COLOR, next_color)
            with scan_lock:
                scanning_paused = False
            px.set_cam_tilt_angle(0)
            response = f"Color detection ({next_color}) scanning ENABLED"
        else:
            px.stop()
            Vilib.color_detect('close')
            response = "Color detection scanning DISABLED"
        print(response)
        connectionSocket.send(response.encode())
        continue
    elif data == 'r':
        # Toggle QR code detection
        detection_enabled = not detection_enabled
        if detection_enabled:
            initialize_camera()
            set_detection_mode(DETECT_QR)
            with scan_lock:
                scanning_paused = False
            px.set_cam_tilt_angle(0)
            response = "QR code detection scanning ENABLED"
        else:
            px.stop()
            Vilib.qrcode_detect_switch(False)
            response = "QR code detection scanning DISABLED"
        print(response)
        connectionSocket.send(response.encode())
        continue
    elif data == 'p':
        # Manual photo
        initialize_camera()
        take_and_send_photo("manual")
        response = "Photo taken!"
        connectionSocket.send(response.encode())
        continue
    elif data == 'q':
        px.stop()
        Vilib.camera_close()
        connectionSocket.close()
        serverSocket.close()
        sys.exit(0)
    else:
        print(data)

    connectionSocket.send(data.encode())

connectionSocket.close()
serverSocket.close()
