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
face_detect_on = False
color_detect_on = False
qr_detect_on = False
current_color_idx = 0
color_list = ['red', 'orange', 'yellow', 'green', 'blue', 'purple']

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
    """Start camera with web streaming"""
    global camera_started
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


def toggle_face_detect():
    """Toggle face detection on/off"""
    global face_detect_on, color_detect_on, qr_detect_on
    
    initialize_camera()
    
    # Turn off other modes
    if color_detect_on:
        Vilib.color_detect('close')
        color_detect_on = False
    if qr_detect_on:
        Vilib.qrcode_detect_switch(False)
        qr_detect_on = False
    
    face_detect_on = not face_detect_on
    Vilib.face_detect_switch(face_detect_on)
    
    status = "ON" if face_detect_on else "OFF"
    msg = f"Face detection: {status}"
    print(msg)
    return msg


def toggle_color_detect():
    """Toggle color detection and cycle through colors"""
    global face_detect_on, color_detect_on, qr_detect_on, current_color_idx
    
    initialize_camera()
    
    # Turn off other modes
    if face_detect_on:
        Vilib.face_detect_switch(False)
        face_detect_on = False
    if qr_detect_on:
        Vilib.qrcode_detect_switch(False)
        qr_detect_on = False
    
    if color_detect_on:
        # Cycle to next color
        current_color_idx = (current_color_idx + 1) % len(color_list)
        if current_color_idx == 0:
            # Cycled through all - turn off
            Vilib.color_detect('close')
            color_detect_on = False
            msg = "Color detection: OFF"
        else:
            color = color_list[current_color_idx]
            Vilib.color_detect(color)
            msg = f"Color detection: {color}"
    else:
        # Turn on with first color
        current_color_idx = 0
        color = color_list[current_color_idx]
        Vilib.color_detect(color)
        color_detect_on = True
        msg = f"Color detection: {color}"
    
    print(msg)
    return msg


def set_color_detect(color_num):
    """Set specific color detection (1-6)"""
    global face_detect_on, color_detect_on, qr_detect_on, current_color_idx
    
    initialize_camera()
    
    # Turn off other modes
    if face_detect_on:
        Vilib.face_detect_switch(False)
        face_detect_on = False
    if qr_detect_on:
        Vilib.qrcode_detect_switch(False)
        qr_detect_on = False
    
    if color_num == 0:
        Vilib.color_detect('close')
        color_detect_on = False
        msg = "Color detection: OFF"
    else:
        current_color_idx = color_num - 1
        color = color_list[current_color_idx]
        Vilib.color_detect(color)
        color_detect_on = True
        msg = f"Color detection: {color}"
    
    print(msg)
    return msg




def get_detection_info():
    """Get current detection information"""
    info_parts = []
    
    if face_detect_on:
        n = Vilib.detect_obj_parameter['human_n']
        if n > 0:
            x = Vilib.detect_obj_parameter['human_x']
            y = Vilib.detect_obj_parameter['human_y']
            info_parts.append(f"Faces: {n} at ({x},{y})")
        else:
            info_parts.append("Faces: none")
    
    if color_detect_on:
        n = Vilib.detect_obj_parameter['color_n']
        if n > 0:
            x = Vilib.detect_obj_parameter['color_x']
            y = Vilib.detect_obj_parameter['color_y']
            info_parts.append(f"Color: found at ({x},{y})")
        else:
            info_parts.append("Color: none")
    
    if qr_detect_on:
        qr_data = Vilib.detect_obj_parameter['qr_data']
        if qr_data and qr_data != "None":
            info_parts.append(f"QR: {qr_data}")
        else:
            info_parts.append("QR: none")
    
    if not info_parts:
        return "No detection mode active"
    
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
    
    # Detection modes
    elif cmd == 'f':
        response = toggle_face_detect()
        
    elif cmd == 'c':
        response = toggle_color_detect()
        
    elif cmd in '0123456':
        response = set_color_detect(int(cmd))       
    
    # Info/utility
    elif cmd == 'n':
        response = get_detection_info()
        
    elif cmd == 'p':
        path = take_photo()
        response = f"Photo saved: {path}"
    
    elif cmd == 'h':
        response = "Commands: wasd=move, x=stop, +-=speed, ijkl=cam, f=face, c=color, r=qr, p=photo, n=info, q=quit"
    
    elif cmd == 'q':
        response = "Shutting down..."
        return response, True  # Signal to quit
    
    else:
        response = f"Unknown command: {cmd}"
    
    print(f"[{cmd}] {response}")
    return response, False


def cleanup():
    """Clean up resources"""
    global px, camera_started
    
    print("\nCleaning up...")
    
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
    
    # Start camera immediately so user can view it
    print("Starting camera...")
    initialize_camera()

    toggle_face_detect()
    toggle_color_detect()
    
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
