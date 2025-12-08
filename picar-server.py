#!/usr/bin/env python3

import random
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
detection_running = False
face_detection_on = True
avoidance_enabled = False

# Obstacle Avoidance settings 
power = 60
safe_distance = 20
warn_distance = 25
stop_distance = 15
turn_angle = 30
turn_time = 1.0

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

def recv_line(sock):
    """
    Read a single newline-terminated line from the client.
    Returns:
        The decoded line (without the trailing newline) or
        None if the connection is closed.
    """
    global recv_buffer

    while True:
        # Do we already have a full line in the buffer?
        if b"\n" in recv_buffer:
            line, recv_buffer = recv_buffer.split(b"\n", 1)
            return line.decode(errors="ignore").rstrip("\r")

        # Otherwise, read more data
        chunk = sock.recv(1024)
        if not chunk:
            # Connection closed
            return None
        recv_buffer += chunk

"""
Start the camera with web streaming.

Raises:
    CameraError: Raises an error that the camera didn't initialize correctly.
"""
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
                thread = threading.Thread(target=toggle_color_detect, daemon=True)
                thread.start()
        except Exception as CameraError:
            print(f"Camera error: {CameraError}")
            camera_started = False


"""
Sends a text response to the client.

Args:
    msg: The message to be returned to the client.

Raises:
    SendError: Exception raised when trying to send back to client.
"""
def send_response(msg):
    global connection_socket
    try:
        if connection_socket:
            # Ensure every response is newline-terminated
            if not msg.endswith("\n"):
                msg = msg + "\n"
            connection_socket.sendall(msg.encode())
    except Exception as SendError:
        print(f"Error sending response: {SendError}")

def send_multiline(msg: str):
    for line in msg.split("\n"):
        send_response(line)  # your existing one-line sender
    send_response("<END>")


"""
Takes and saves a photo locally on the Pi

Returns:
    The full path of where the photo gets saved to.

Raises:
    PhotoError: Raises an exception if there was an issue taking the photo.
"""
def take_photo():
    # Tries to initialize the camera if it isn't already
    initialize_camera()

    # Sets the specific time the photo was taken
    try:
        _time = strftime('%Y-%m-%d-%H-%M-%S', localtime(time()))

        # Names the photo based on the time and then puts it in the user's Pictures
        name = f'PiCarPhoto_{_time}'
        username = os.getlogin()
        path = f"/home/{username}/Pictures/"

        # Create directory if needed
        os.makedirs(path, exist_ok=True)

        # Actually takes the photo
        Vilib.take_photo(name, path)
        full_path = f"{path}{name}.jpg"
        print(f"Photo saved: {full_path}")
        return full_path
    except Exception as PhotoError:
        return f"Photo path error occured. Error: {PhotoError}"


"""
Toggles face detection on/off

Returns:
    The status of if face detection is on or off or the error that occured.

Raises:
    FaceToggleError: Raises and exception if there is an error with toggling the face detection.
"""

def toggle_face_detect():
    """Toggle face detection on/off"""
    global face_detection_on
    
    face_detection_on = not face_detection_on
    Vilib.face_detect_switch(face_detection_on)
    
    status = "ON" if face_detection_on else "OFF"
    msg = f"Face detection: {status}"
    print(msg)
    return msg
# def toggle_face_detect():
#     global face_detect_on, color_detect_on, qr_detect_on

#     # Tries to initialize the camera if it isn't already
#     initialize_camera()

#     try:
#         # Turn off other modes
#         if color_detect_on:
#             Vilib.color_detect('close')
#             color_detect_on = False
#         if qr_detect_on:
#             Vilib.qrcode_detect_switch(False)
#             qr_detect_on = False

#         face_detect_on = not face_detect_on
#         Vilib.face_detect_switch(face_detect_on)

#         status = "ON" if face_detect_on else "OFF"
#         msg = f"Face detection: {status}"
#         print(msg)
#         return msg
#     except Exception as FaceToggleError:
#         return f'Error with face detection. Error: {FaceToggleError}'

"""
Toggle color detection and cycle through available colors

Returns:
    The current color that it is looking for or the error that occured.

Raises:
    ToggleColorError: Raises an exception if there is an error with toggling the color detection.
"""

def toggle_color_detect():
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
# def toggle_color_detect():
#     global face_detect_on, color_detect_on, qr_detect_on, current_color_idx

#     # Tries to initialize the camera if it isn't already
#     initialize_camera()

#     try:
#         # Turn off other modes
#         if face_detect_on:
#             Vilib.face_detect_switch(False)
#             face_detect_on = False
#         if qr_detect_on:
#             Vilib.qrcode_detect_switch(False)
#             qr_detect_on = False

#         if color_detect_on:
#             # Cycle to next color
#             current_color_idx = (current_color_idx + 1) % len(color_list)
#             if current_color_idx == 0:
#                 # Cycled through all - turn off
#                 Vilib.color_detect('close')
#                 color_detect_on = False
#                 msg = "Color detection: OFF"
#             else:
#                 color = color_list[current_color_idx]
#                 Vilib.color_detect(color)
#                 msg = f"Color detection: {color}"
#         else:
#             # Turn on with first color
#             current_color_idx = 0
#             color = color_list[current_color_idx]
#             Vilib.color_detect(color)
#             color_detect_on = True
#             msg = f"Color detection: {color}"

#         print(msg)
#         return msg
#     except Exception as ToggleColorError:
#         return f'Error with color detection. Error: {ToggleColorError}'


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


"""
Clamps the value between a min and a max number so that it doesn't exceed a max or fall below the min

Args:
    value: Value that is trying to be set
    min_val: The minimum value allowed
    max_val: The maximum value allowed

Returns:
    Either the value you are trying to set or the min/max if you go over either one
"""
def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))

def simple_avoidance():
    """
    Simple forward collision avoidance.

    This runs in the background while `running` is True.
    It does NOT try to drive the car on its own. Instead, it:
      - Continuously reads the ultrasonic sensor.
      - If an object is within `safe_distance` in front of the car,
        it sends a "brake" command by calling px.forward(0),
        which stops the motors regardless of current speed.

    This way, you can still drive normally with your existing controls,
    and this loop will only step in to stop you from hitting
    something head-on.
    """
    global px, running

    while running:
        # If the car isn't initialized yet, just wait
        if px is None:
            sleep(0.1)
            continue

        try:
            distance = px.ultrasonic.read()
        except Exception:
            # Sensor read failed; try again shortly
            sleep(0.1)
            continue

        # Make sure distance is a sane number
        if distance is not None:
            try:
                distance = float(distance)
            except (TypeError, ValueError):
                distance = None

        if distance is not None and distance > 0:
            # If we're too close to something in front, hit the brakes.
            # You can still choose to back up with your normal controls.
            if distance <= safe_distance:
                px.forward(0)

        # Don't hammer the CPU
        sleep(0.05)

"""
A background loop to smoothly move steering towards target_angle without slowing the response time.
"""
def steering_loop():
    global current_angle, target_angle, running, px
    while running:
        if current_angle < target_angle:
            current_angle += 0.5
        elif current_angle > target_angle:
            current_angle -= 0.5

        px.set_dir_servo_angle(current_angle)
        sleep(0.001)

"""
Loop that the car should use to handle the actual driving part. 
"""
def drive_loop(data):
    global target_angle, running, px, connection_socket
    match data:
        case 'start forward':
            px.forward(80)
        case 'start backward':
            px.backward(80)
        case 'start left':
            target_angle = -30
        case 'start right':
            target_angle = 30
        case 'stop forward':
            px.forward(0)
        case 'stop backward':
            px.forward(0)
        case 'stop left':
            target_angle = 0
        case 'stop right':
            target_angle = 0

"""
Process a command from the client: action=start/stop, command=name.
"""
def handle_command(action, command):
    global current_speed, pan_angle, tilt_angle, px, target_angle


    action = action.lower()
    command = command.lower()
    response = ""
    should_quit = False

    # ---------- Speed control ----------
    if command == "speed_increase":
        if action == "start":
            current_speed = clamp(current_speed + 10, 0, 100)
            response = f"Speed increased to {current_speed}"

    elif command == "speed_decrease":
        if action == "start":
            current_speed = clamp(current_speed - 10, 0, 100)
            response = f"Speed decreased to {current_speed}"

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

    elif command == "toggle_color":
        if action == "start":
            response = toggle_color_detect()

    elif command == "take_photo":
        if action == "start":
            path = take_photo()
            response = f"Photo saved: {path}"

    elif command == "show_detect":
        if action == "start":
            response = get_detection_info()

    elif command == "help":
        if action == "start":
            response = """
            MOVEMENT              CAMERA HEAD
            w : Forward           i : Tilt up
            s : Backward          k : Tilt down
            a : Turn left         j : Pan left
            d : Turn right        l : Pan right
            UTILITY
            p : Take photo        n : Show detection info
            q : Quit
            """


    # ---------- Optional quit ----------
    elif command in ("quit", "q"):
        if action == "start":
            response = "Shutting down..."
            should_quit = True
        else:
            response = "Quit ignored on stop"

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

    # Start simple obstacle avoidance thread
    avoid_thread = threading.Thread(target=simple_avoidance, daemon=True)
    avoid_thread.start()



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
                # Reset line buffer for this connection
                global recv_buffer
                recv_buffer = b""

                while True:
                    text = recv_line(connection_socket)
                    if text is None:
                        break

                    text = text.strip()
                    if not text:
                        continue

                    print(f"Received from client: {text}")

                    parts = text.split()
                    if len(parts) < 2:
                        response = f"Malformed command: '{text}'"
                        send_response(response)
                        continue

                    action = parts[0]
                    command = parts[1]

                    response, should_quit = handle_command(action, command)
                    drive_loop(text)
                    send_multiline(response)

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