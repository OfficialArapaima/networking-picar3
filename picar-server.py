import sys
import os
from socket import *
from picarx import Picarx
import cv2
from datetime import datetime
import threading
import time
import struct

serverPort = 12000

# Face detection settings
face_detection_enabled = False
scanning_paused = False  # Pause scanning when face detected
scan_lock = threading.Lock()  # Thread synchronization for scanning_paused

# Load face cascade with cross-platform compatibility
def load_face_cascade():
    """Load Haar cascade with fallback paths for cross-platform support"""
    cascade_paths = []
    
    # Try cv2.data.haarcascades first (cross-platform, works with pip-installed OpenCV)
    if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
        cascade_paths.append(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Fallback paths for system-installed OpenCV on Linux
    cascade_paths.extend([
        '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
        '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml',
        '/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
    ])
    
    for path in cascade_paths:
        if os.path.exists(path):
            cascade = cv2.CascadeClassifier(path)
            if not cascade.empty():
                print(f"Face cascade loaded from: {path}")
                return cascade
    
    print("ERROR: Could not load face cascade classifier!")
    print("Please install opencv-python: pip3 install opencv-python")
    return cv2.CascadeClassifier()  # Return empty classifier

face_cascade = load_face_cascade()
camera = None
last_face_detected_time = 0
face_detection_cooldown = 3  # seconds between captures (give time to resume scanning)
connectionSocket = None

# Scanning settings
SCAN_SPEED = 20  # Slow rotation speed
TILT_MIN = -20   # Camera looks down
TILT_MAX = 20    # Camera looks up
TILT_STEP = 5    # Degrees per step
tilt_direction = 1  # 1 = going up, -1 = going down
current_tilt = 0

px = None  # Global PiCar reference


def initialize_camera():
    """Initialize the camera using V4L2 backend (more reliable on Raspberry Pi)"""
    global camera
    if camera is None:
        # Use V4L2 backend instead of GStreamer to avoid memory issues
        camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
        
        # Set lower resolution for better performance on Pi
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        camera.set(cv2.CAP_PROP_FPS, 15)  # Lower FPS for stability
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to save memory
        
        time.sleep(1)
        
        # Verify camera is actually working
        if camera.isOpened():
            ret, test_frame = camera.read()
            if ret:
                print("Camera initialized successfully (320x240 @ 15fps)")
            else:
                print("WARNING: Camera opened but cannot read frames!")
        else:
            print("ERROR: Failed to open camera!")
    return camera


def send_image_to_client(frame, timestamp, num_faces):
    """Send image to client over socket"""
    global connectionSocket

    if connectionSocket is None:
        return False

    try:
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            return False

        img_bytes = buffer.tobytes()
        img_size = len(img_bytes)

        header = b"IMG" + timestamp.encode('utf-8') + struct.pack('>I', img_size)
        connectionSocket.sendall(header + img_bytes)
        print(f"Image sent to client: {timestamp} ({img_size} bytes, {num_faces} face(s))")
        return True

    except Exception as e:
        print(f"Error sending image to client: {e}")
        return False


def scanning_mode():
    """Rotate slowly and move camera up/down to scan for faces"""
    global face_detection_enabled, scanning_paused, current_tilt, tilt_direction, px

    while True:
        # Thread-safe check of scanning_paused
        with scan_lock:
            is_paused = scanning_paused
            detection_enabled = face_detection_enabled
        
        if detection_enabled and not is_paused and px is not None:
            # Rotate slowly in a circle (turn left)
            px.set_dir_servo_angle(-30)  # Turn wheels left
            px.forward(SCAN_SPEED)       # Move slowly
            
            # Move camera tilt up and down
            current_tilt += TILT_STEP * tilt_direction
            
            # Reverse direction at limits
            if current_tilt >= TILT_MAX:
                current_tilt = TILT_MAX
                tilt_direction = -1
            elif current_tilt <= TILT_MIN:
                current_tilt = TILT_MIN
                tilt_direction = 1
            
            # Apply camera tilt
            px.set_cam_tilt_angle(current_tilt)
            
            time.sleep(0.3)  # Smooth movement
            
        elif is_paused and px is not None:
            # Stop the car when face detected
            px.stop()
            time.sleep(0.1)
        else:
            time.sleep(0.1)


def detect_and_capture_faces():
    """Continuous face detection and capture in a separate thread"""
    global face_detection_enabled, last_face_detected_time, camera, scanning_paused
    
    frame_count = 0
    fail_count = 0
    while True:
        if face_detection_enabled and camera is not None:
            ret, frame = camera.read()
            if ret:
                fail_count = 0
                frame_count += 1
                if frame_count % 50 == 0:  # Print every 50 frames (~5 seconds)
                    print(f"[DEBUG] Scanning... (frame {frame_count})")
                
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                
                if len(faces) > 0:
                    print(f"[DEBUG] Found {len(faces)} face(s)!")
                    current_time = time.time()
                    if current_time - last_face_detected_time >= face_detection_cooldown:
                        # STOP scanning - face detected! (thread-safe)
                        with scan_lock:
                            scanning_paused = True
                        print("Face detected! Stopping to capture...")
                        time.sleep(0.5)  # Let car fully stop
                        
                        # Capture fresh frame after stopping
                        ret, frame = camera.read()
                        if ret:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            
                            # Draw rectangles around faces
                            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                            for (x, y, w, h) in faces:
                                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                            # Send image to client
                            send_image_to_client(frame, timestamp, len(faces))
                            last_face_detected_time = current_time
                        
                        # Wait a moment, then resume scanning (thread-safe)
                        print("Picture taken! Resuming scan in 2 seconds...")
                        time.sleep(2)
                        with scan_lock:
                            scanning_paused = False
            else:
                fail_count += 1
                if fail_count % 10 == 1:
                    print(f"[DEBUG] Camera read failed! (count: {fail_count})")

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
face_thread = threading.Thread(target=detect_and_capture_faces, daemon=True)
face_thread.start()

scan_thread = threading.Thread(target=scanning_mode, daemon=True)
scan_thread.start()

while True:
    print('Waiting for command...')
    data = connectionSocket.recv(1024).decode()
    if not data:
        break

    if data == 'w':
        face_detection_enabled = False  # Disable scanning when manual control
        px.set_dir_servo_angle(0)
        px.forward(80)
    elif data == 's':
        face_detection_enabled = False
        px.set_dir_servo_angle(0)
        px.backward(80)
    elif data == 'a':
        face_detection_enabled = False
        px.set_dir_servo_angle(-35)
        px.forward(80)
    elif data == 'd':
        face_detection_enabled = False
        px.set_dir_servo_angle(35)
        px.forward(80)
    elif data == 'f':
        # Toggle face detection & scanning mode
        face_detection_enabled = not face_detection_enabled
        if face_detection_enabled:
            initialize_camera()
            with scan_lock:
                scanning_paused = False
            px.set_cam_tilt_angle(0)  # Reset camera
            response = "Scanning mode ENABLED - PiCar will rotate and scan for faces"
        else:
            px.stop()
            response = "Scanning mode DISABLED"
        print(response)
        connectionSocket.send(response.encode())
        continue
    elif data == 'q':
        px.stop()
        if camera is not None:
            camera.release()
        connectionSocket.close()
        serverSocket.close()
        sys.exit(0)
    else:
        print(data)

    connectionSocket.send(data.encode())

connectionSocket.close()
serverSocket.close()
