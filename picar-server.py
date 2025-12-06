#!/usr/bin/env python3

import sys
import os
from socket import *
from picarx import Picarx
from vilib import Vilib
from datetime import datetime
from time import sleep, time, strftime, localtime
import threading

# Server settings
SERVER_PORT = 12000

# Detection state
color_list = ['red', 'orange', 'yellow', 'green', 'blue', 'purple']
current_color_idx = 0
detection_running = False
face_detection_on = True

# Camera state
camera_started = False

# Car state
current_speed = 50
pan_angle = 0
tilt_angle = 0

# Connection
connection_socket = None
px = None


def initialize_camera():
    """Start camera with web streaming and enable all detection"""
    global camera_started, detection_running
    if not camera_started:
        try:
            print("Initializing camera...")
            Vilib.camera_start(vflip=False, hflip=False)
            sleep(0.5)
            # web=True enables Flask web server, local=False for headless operation
            Vilib.display(local=False, web=True)
            sleep(1)  # Give camera time to start
            camera_started = True
            print("Camera started successfully!")
            print("  http:0.0.0.0:9000/mjpg")
            
            # Auto-start face detection
            print("Enabling face detection...")
            Vilib.face_detect_switch(True)
            
            # Auto-start all-color detection loop
            print("Enabling color detection (all colors)...")
            if not detection_running:
                detection_running = True
                thread = threading.Thread(target=color_detection_loop, daemon=True)
                thread.start()
            
        except Exception as e:
            print(f"Camera error: {e}")
            camera_started = False


def send_response(msg):
    """Send text response to client"""
    global connection_socket
    try:
        if connection_socket:
            connection_socket.send(msg.encode())
    except Exception as e:
        print(f"Error sending response: {e}")


def take_photo():
    """Take and save photo locally on Pi"""
    initialize_camera()
    _time = strftime('%Y-%m-%d-%H-%M-%S', localtime(time()))
    name = f'photo_{_time}'
    username = os.getlogin()
    path = f"/home/{username}/Pictures/"
    
    # Create directory if needed
    os.makedirs(path, exist_ok=True)
    
    Vilib.take_photo(name, path)
    full_path = f"{path}{name}.jpg"
    print(f"Photo saved: {full_path}")
    return full_path


def color_detection_loop():
    """Background thread that cycles through all colors for detection"""
    global detection_running, current_color_idx
    
    while detection_running:
        for i, color in enumerate(color_list):
            if not detection_running:
                break
            
            current_color_idx = i
            Vilib.color_detect(color)
            
            # Check for detection - if found, stay on this color longer
            sleep(0.08)
            n = Vilib.detect_obj_parameter.get('color_n', 0)
            if n > 0:
                # Color detected - stay on it a bit longer
                sleep(0.15)
            else:
                sleep(0.02)


def toggle_face_detection():
    """Toggle face detection on/off"""
    global face_detection_on
    
    face_detection_on = not face_detection_on
    Vilib.face_detect_switch(face_detection_on)
    
    status = "ON" if face_detection_on else "OFF"
    msg = f"Face detection: {status}"
    print(msg)
    return msg


def toggle_all_detection():
    """Toggle all detection (face + color) on/off"""
    global detection_running, face_detection_on
    
    if detection_running or face_detection_on:
        # Turn everything off
        detection_running = False
        face_detection_on = False
        Vilib.face_detect_switch(False)
        Vilib.color_detect('close')
        sleep(0.1)
        msg = "All detection: OFF"
    else:
        # Turn everything on
        face_detection_on = True
        Vilib.face_detect_switch(True)
        detection_running = True
        thread = threading.Thread(target=color_detection_loop, daemon=True)
        thread.start()
        msg = "All detection: ON (face + all colors)"
    
    print(msg)
    return msg




def get_detection_info():
    """Get current detection information"""
    info_parts = []
    
    # Face detection info
    if face_detection_on:
        n = Vilib.detect_obj_parameter.get('human_n', 0)
        if n > 0:
            x = Vilib.detect_obj_parameter.get('human_x', 0)
            y = Vilib.detect_obj_parameter.get('human_y', 0)
            w = Vilib.detect_obj_parameter.get('human_w', 0)
            h = Vilib.detect_obj_parameter.get('human_h', 0)
            info_parts.append(f"Faces: {n} at ({x},{y}) size:{w}x{h}")
        else:
            info_parts.append("Faces: none")
    else:
        info_parts.append("Faces: OFF")
    
    # Color detection info
    if detection_running:
        n = Vilib.detect_obj_parameter.get('color_n', 0)
        if n > 0:
            x = Vilib.detect_obj_parameter.get('color_x', 0)
            y = Vilib.detect_obj_parameter.get('color_y', 0)
            current_color = color_list[current_color_idx] if current_color_idx < len(color_list) else "unknown"
            info_parts.append(f"Color({current_color}): at ({x},{y})")
        else:
            info_parts.append("Color: none")
    else:
        info_parts.append("Color: OFF")
    
    return " | ".join(info_parts)


def clamp(value, min_val, max_val):
    """Clamp value between min and max"""
    return max(min_val, min(max_val, value))


def handle_command(cmd):
    """Process a command from the client"""
    global current_speed, pan_angle, tilt_angle, px
    
    response = ""
    
    # Movement commands
    if cmd == 'w':
        px.set_dir_servo_angle(0)
        px.forward(current_speed)
        response = f"Forward (speed: {current_speed})"
        
    elif cmd == 's':
        px.set_dir_servo_angle(0)
        px.backward(current_speed)
        response = f"Backward (speed: {current_speed})"
        
    elif cmd == 'a':
        px.set_dir_servo_angle(-35)
        px.forward(current_speed)
        response = f"Turn left (speed: {current_speed})"
        
    elif cmd == 'd':
        px.set_dir_servo_angle(35)
        px.forward(current_speed)
        response = f"Turn right (speed: {current_speed})"
    
    elif cmd == 'x':
        px.stop()
        response = "Stopped"
    
    # Speed control
    elif cmd == '+' or cmd == '=':
        current_speed = clamp(current_speed + 10, 0, 100)
        response = f"Speed: {current_speed}"
        
    elif cmd == '-' or cmd == '_':
        current_speed = clamp(current_speed - 10, 0, 100)
        response = f"Speed: {current_speed}"
    
    # Camera pan/tilt
    elif cmd == 'i':
        tilt_angle = clamp(tilt_angle + 5, -35, 35)
        px.set_cam_tilt_angle(tilt_angle)
        response = f"Tilt: {tilt_angle}"
        
    elif cmd == 'k':
        tilt_angle = clamp(tilt_angle - 5, -35, 35)
        px.set_cam_tilt_angle(tilt_angle)
        response = f"Tilt: {tilt_angle}"
        
    elif cmd == 'j':
        pan_angle = clamp(pan_angle - 5, -35, 35)
        px.set_cam_pan_angle(pan_angle)
        response = f"Pan: {pan_angle}"
        
    elif cmd == 'l':
        pan_angle = clamp(pan_angle + 5, -35, 35)
        px.set_cam_pan_angle(pan_angle)
        response = f"Pan: {pan_angle}"
    
    # Detection toggles
    elif cmd == 'f':
        response = toggle_face_detection()
    
    elif cmd == 'o':
        response = toggle_all_detection()
    
    # Info/utility
    elif cmd == 'n':
        response = get_detection_info()
        
    elif cmd == 'p':
        path = take_photo()
        response = f"Photo saved: {path}"
    
    elif cmd == 'h':
        response = "Commands: wasd=move, x=stop, +-=speed, ijkl=cam, f=face, o=all detect, p=photo, n=info, q=quit"
    
    elif cmd == 'q':
        response = "Shutting down..."
        return response, True  # Signal to quit
    
    else:
        response = f"Unknown command: {cmd}"
    
    print(f"[{cmd}] {response}")
    return response, False


def cleanup():
    """Clean up resources"""
    global px, camera_started, detection_running, face_detection_on
    
    print("\nCleaning up...")
    
    # Stop detection thread
    detection_running = False
    face_detection_on = False
    
    # Turn off detection features
    try:
        Vilib.face_detect_switch(False)
        Vilib.color_detect('close')
    except:
        pass
    
    if px:
        px.set_cam_tilt_angle(0)
        px.set_cam_pan_angle(0)
        px.set_dir_servo_angle(0)
        px.stop()
    
    if camera_started:
        Vilib.camera_close()
    
    sleep(0.2)
    print("Cleanup complete")


def get_ip_address():
    """Get the Pi's IP address"""
    import subprocess
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        ip = result.stdout.strip().split()[0]
        return ip
    except:
        return "<pi-ip>"


def main():
    global connection_socket, px
    
    # Initialize PiCar first
    px = Picarx()
    px.set_cam_tilt_angle(0)
    px.set_cam_pan_angle(0)
    
    # Start camera with auto-enabled face + color detection
    print("Starting camera with detection...")
    initialize_camera()
    
    # Get IP address for display
    ip_addr = get_ip_address()
    
    # Create server socket
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_socket.bind(("", SERVER_PORT))
    server_socket.listen(1)
    
    print("=" * 50)
    print("PiCar-X Server Started")
    print(f"Control port: {SERVER_PORT}")
    print(f"Camera stream: http:0.0.0.0:9000/mjpg")
    print("=" * 50)
    
    try:
        while True:
            print("\nWaiting for client connection...")
            connection_socket, addr = server_socket.accept()
            print(f"Client connected: {addr[0]}:{addr[1]}")
            
            # Send welcome message
            welcome = f"Connected! http://{ip_addr}:9000/mjpg"
            send_response(welcome)
            
            try:
                while True:
                    data = connection_socket.recv(1024)
                    if not data:
                        print("Client disconnected")
                        break
                    
                    cmd = data.decode().lower()
                    
                    for c in cmd:  # Handle multiple chars if sent together
                        response, should_quit = handle_command(c)
                        send_response(response)
                        
                        if should_quit:
                            cleanup()
                            connection_socket.close()
                            server_socket.close()
                            print("Server shutdown complete")
                            sys.exit(0)
                    
                    # Brief stop after movement commands
                    if cmd in 'wasd':
                        sleep(0.3)
                        px.stop()
                        
            except Exception as e:
                print(f"Error handling client: {e}")
            finally:
                px.stop()
                connection_socket.close()
                
    except KeyboardInterrupt:
        print("\nServer interrupted")
    finally:
        cleanup()
        server_socket.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}")
        cleanup()
