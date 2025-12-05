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

# Smooth steering state
current_angle = 0.0
target_angle = 0.0
running = True

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
            # print("  http:0.0.0.0:9000/mjpg")
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


def steering_loop():
    """Background loop to smoothly move steering towards target_angle."""
    global current_angle, target_angle, running, px
    while running:
        if current_angle < target_angle:
            current_angle += 0.5
        elif current_angle > target_angle:
            current_angle -= 0.5

        px.set_dir_servo_angle(current_angle)
        sleep(0.001)

def drive_loop():
    global target_angle, running, px, connection_socket
    while running:
        data = connection_socket.recv(1024).decode()
        match data:
            case 'start forward':
                px.forward(80)
            case 'start backward':
                px.backward(80)
            case 'start left':
                target_angle = -35
            case 'start right':
                target_angle = 35
            case 'stop forward':
                px.forward(0)
            case 'stop backward':
                px.forward(0)
            case 'stop left' | 'stop right':
                target_angle = 0

def handle_command(action, command):
    """Process a command from the client: action=start/stop, command=name."""
    global current_speed, pan_angle, tilt_angle, px, target_angle

    action = action.lower()
    command = command.lower()
    response = ""
    should_quit = False

    # ---------- Movement ----------
    
    
    
    
    # if command == "forward":
    #     if action == "start":
    #         px.forward(current_speed)
    #         response = f"Forward (speed: {current_speed})"
    #     elif action == "stop":
    #         px.stop()
    #         response = "Stopped (forward)"

    # elif command == "backward":
    #     if action == "start":
    #         px.backward(current_speed)
    #         response = f"Backward (speed: {current_speed})"
    #     elif action == "stop":
    #         px.stop()
    #         response = "Stopped (backward)"

    # elif command == "left":
    #     if action == "start":
    #         target_angle = -35
    #         px.forward(current_speed)
    #         response = f"Turning left (target_angle: {target_angle}, speed: {current_speed})"
    #     elif action == "stop":
    #         target_angle = 0
    #         px.stop()
    #         response = "Stopped (left), steering returning to center"

    # elif command == "right":
    #     if action == "start":
    #         target_angle = 35
    #         px.forward(current_speed)
    #         response = f"Turning right (target_angle: {target_angle}, speed: {current_speed})"
    #     elif action == "stop":
    #         target_angle = 0
    #         px.stop()
    #         response = "Stopped (right), steering returning to center"

    # ---------- Speed control ----------
    if command == "speed_increase":
        if action == "start":
            current_speed = clamp(current_speed + 10, 0, 100)
            response = f"Speed increased to {current_speed}"
        else:
            response = f"Speed unchanged ({current_speed})"

    elif command == "speed_decrease":
        if action == "start":
            current_speed = clamp(current_speed - 10, 0, 100)
            response = f"Speed decreased to {current_speed}"
        else:
            response = f"Speed unchanged ({current_speed})"

    # ---------- Camera pan/tilt ----------
    elif command == "cam_up":
        if action == "start":
            tilt_angle = clamp(tilt_angle + 5, -35, 35)
            px.set_cam_tilt_angle(tilt_angle)
            response = f"Tilt: {tilt_angle}"
        else:
            response = f"Tilt (no change): {tilt_angle}"

    elif command == "cam_down":
        if action == "start":
            tilt_angle = clamp(tilt_angle - 5, -35, 35)
            px.set_cam_tilt_angle(tilt_angle)
            response = f"Tilt: {tilt_angle}"
        else:
            response = f"Tilt (no change): {tilt_angle}"

    elif command == "cam_left":
        if action == "start":
            pan_angle = clamp(pan_angle - 5, -35, 35)
            px.set_cam_pan_angle(pan_angle)
            response = f"Pan: {pan_angle}"
        else:
            response = f"Pan (no change): {pan_angle}"

    elif command == "cam_right":
        if action == "start":
            pan_angle = clamp(pan_angle + 5, -35, 35)
            px.set_cam_pan_angle(pan_angle)
            response = f"Pan: {pan_angle}"
        else:
            response = f"Pan (no change): {pan_angle}"

    # ---------- Detection / camera features ----------
    elif command == "toggle_face":
        if action == "start":
            response = toggle_face_detect()
        else:
            response = "Face toggle ignored on stop"

    elif command == "toggle_color":
        if action == "start":
            response = toggle_color_detect()
        else:
            response = "Color toggle ignored on stop"

    elif command == "take_photo":
        if action == "start":
            path = take_photo()
            response = f"Photo saved: {path}"
        else:
            response = "Photo command ignored on stop"

    elif command == "show_detect":
        if action == "start":
            response = get_detection_info()
        else:
            response = "Detection info ignored on stop"

    elif command == "help":
        if action == "start":
            response = (
                "Commands: forward/backward/left/right, "
                "speed_increase/speed_decrease, "
                "cam_up/cam_down/cam_left/cam_right, "
                "toggle_face/toggle_color, take_photo, show_detect, help"
            )
        else:
            response = "Help ignored on stop"

    # ---------- Optional quit ----------
    elif command in ("quit", "q"):
        if action == "start":
            response = "Shutting down..."
            should_quit = True
        else:
            response = "Quit ignored on stop"

    else:
        response = f"Unknown command: action={action}, command={command}"

    print(f"[{action} {command}] {response}")
    return response, should_quit


def cleanup():
    """Clean up resources"""
    global px, camera_started, running

    print("\nCleaning up...")
    running = False

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
    except Exception:
        return "<pi-ip>"


def main():
    global connection_socket, px, running

    # Initialize PiCar first
    px = Picarx()
    px.set_cam_tilt_angle(0)
    px.set_cam_pan_angle(0)

    # Start camera immediately so user can view it
    print("Starting camera...")
    initialize_camera()

    # toggle_face_detect()
    # toggle_color_detect()

    # Start steering thread
    steer_thread = threading.Thread(target=steering_loop, daemon=True)
    steer_thread.start()
    drive_thread = threading.Thread(target=drive_loop())
    drive_thread.start()

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

                    text = data.decode().strip()
                    print(f"Received from client: {text}")

                    parts = text.split()
                    if len(parts) < 2:
                        response = f"Malformed command: '{text}'"
                        send_response(response)
                        continue

                    action = parts[0]
                    command = parts[1]

                    response, should_quit = handle_command(action, command)
                    send_response(response)

                    if should_quit:
                        cleanup()
                        connection_socket.close()
                        server_socket.close()
                        print("Server shutdown complete")
                        sys.exit(0)

            except Exception as e:
                print(f"Error handling client: {e}")
            finally:
                if px:
                    px.stop()
                if connection_socket:
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