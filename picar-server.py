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
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
camera = None
last_face_detected_time = 0
face_detection_cooldown = 2  # seconds between captures
connectionSocket = None  # Global reference for sending images

# Create directory for captured images
if not os.path.exists('captured_faces'):
    os.makedirs('captured_faces')

def initialize_camera():
    """Initialize the camera"""
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        time.sleep(1)  # Allow camera to warm up
        print("Camera initialized")
    return camera

def send_image_to_client(frame, timestamp, num_faces):
    """Send image to client over socket"""
    global connectionSocket
    
    if connectionSocket is None:
        return False
    
    try:
        # Encode image to JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            return False
        
        img_bytes = buffer.tobytes()
        img_size = len(img_bytes)
        
        # Create header
        header = b"IMG" + timestamp.encode('utf-8') + struct.pack('>I', img_size)
        
        # Send header + image data
        connectionSocket.sendall(header + img_bytes)
        print(f"Image sent to client: {timestamp} ({img_size} bytes, {num_faces} face(s))")
        return True
        
    except Exception as e:
        print(f"Error sending image to client: {e}")
        return False

def detect_and_capture_faces():
    """Continuous face detection and capture in a separate thread"""
    global face_detection_enabled, last_face_detected_time
    
    while True:
        if face_detection_enabled and camera is not None:
            ret, frame = camera.read()
            if ret:
                # Convert to grayscale for face detection
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Detect faces
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                
                # If faces detected and cooldown period passed
                if len(faces) > 0:
                    current_time = time.time()
                    if current_time - last_face_detected_time >= face_detection_cooldown:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        # Draw rectangles around faces
                        for (x, y, w, h) in faces:
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        
                        # Send image to client instead of saving locally
                        send_image_to_client(frame, timestamp, len(faces))
                        last_face_detected_time = current_time
        
        time.sleep(0.1)  

# bind the server to the socket
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(("", serverPort))
print("Server started on port: %s" % serverPort)
serverSocket.listen(1)
print('The server is now listening...\n')
connectionSocket, addr = serverSocket.accept()
print('Connected by %s:%d' % (addr[0], addr[1]))

px = Picarx()

# Start face detection thread
face_thread = threading.Thread(target=detect_and_capture_faces, daemon=True)
face_thread.start()

while True:
    print('New connection from %s:%d' % (addr[0], addr[1]))
    data = connectionSocket.recv(1024).decode()
    if not data:
        break
    if 'w' in data:
        px.set_dir_servo_angle(0)
        px.forward(80)
    elif 's' == data:
        px.set_dir_servo_angle(0)
        px.backward(80)
    elif 'a' == data:
        px.set_dir_servo_angle(-35)
        px.forward(80)
    elif 'd' == data:
        px.set_dir_servo_angle(35)
        px.forward(80)
    elif data == 'f':
        # Toggle face detection
        face_detection_enabled = not face_detection_enabled
        if face_detection_enabled:
            initialize_camera()
            response = "Face detection ENABLED"
        else:
            response = "Face detection DISABLED"
        print(response)
        connectionSocket.send(response.encode())
        continue
    elif data == 'q':
        px.stop()
        if camera is not None:
            camera.release()
        sys.exit()
        connectionSocket.close()
    else:
       print(data)

    connectionSocket.send(data.encode())
    
connectionSocket.close()