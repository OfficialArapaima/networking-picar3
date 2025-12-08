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
is_moving_forward = False

# Obstacle Avoidance settings
power = 60
safe_distance = 8
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
recv_buffer = b""


def recv_line(sock):
    """Read a single newline-terminated line from the client.

    The function appends incoming data into a global buffer until a newline
    character is found, at which point it returns the decoded line without
    the trailing newline.

    Args:
        sock: The socket to read data from.

    Returns:
        The decoded line (without the trailing newline) as a string, or
        None if the connection is closed.
    """
    global recv_buffer

    while True:
        # If we already have a full line buffered, split and return it.
        if b"\n" in recv_buffer:
            line, recv_buffer = recv_buffer.split(b"\n", 1)
            return line.decode(errors="ignore").rstrip("\r")

        # Otherwise, read more data from the socket.
        chunk = sock.recv(1024)
        if not chunk:
            # Connection closed by the client.
            return None
        recv_buffer += chunk


def initialize_camera():
    """Start the camera with web streaming and enable all detection.

    Starts the Vilib camera, brings up the web stream, and automatically
    turns on face detection plus a background color-detection loop.

    Raises:
        CameraError: If the camera fails to initialize correctly.
    """
    global camera_started, detection_running
    if not camera_started:
        try:
            print("Initializing camera...")
            Vilib.camera_start(vflip=False, hflip=False)
            sleep(0.5)
            # web=True enables Flask web server, local=False for headless operation.
            Vilib.display(local=False, web=True)
            sleep(1)  # Give camera time to start.
            camera_started = True
            print("Camera started successfully!")
            print("  http:0.0.0.0:9000/mjpg")

            # Auto-start face detection.
            print("Enabling face detection...")
            Vilib.face_detect_switch(True)

            # Auto-start all-color detection loop in a background thread.
            print("Enabling color detection (all colors)...")
            if not detection_running:
                detection_running = True
                thread = threading.Thread(target=toggle_color_detect, daemon=True)
                thread.start()
        except Exception as CameraError:
            print(f"Camera error: {CameraError}")
            camera_started = False


def send_response(msg):
    """Send a text response to the client.

    Ensures that each response is newline-terminated before sending.

    Args:
        msg: The message to be returned to the client as a string.

    Raises:
        SendError: If an error occurs when sending data back to the client.
    """
    global connection_socket
    try:
        if connection_socket:
            # Ensure every response is newline-terminated.
            if not msg.endswith("\n"):
                msg = msg + "\n"
            connection_socket.sendall(msg.encode())
    except Exception as SendError:
        print(f"Error sending response: {SendError}")


def send_multiline(msg: str):
    """Send a potentially multi-line message to the client.

    Splits the message on newline characters, sends each line individually,
    and then sends a sentinel "<END>" line to mark completion.

    Args:
        msg: The message to be sent, possibly containing newlines.
    """
    for line in msg.split("\n"):
        # Use the existing single-line sender for each individual line.
        send_response(line)
    # Send an end marker so the client knows the message is complete.
    send_response("<END>")


def take_photo():
    """Take and save a photo locally on the Pi.

    Initializes the camera if necessary, then captures an image and saves it
    to the current user's Pictures directory using a timestamp-based filename.

    Returns:
        The full path of where the photo is saved if successful, or a string
        describing the error if it fails.

    Raises:
        PhotoError: If there is an issue taking or saving the photo.
    """
    # Try to initialize the camera if it isn't already.
    initialize_camera()

    try:
        # Create a timestamp to uniquely identify the photo.
        _time = strftime('%Y-%m-%d-%H-%M-%S', localtime(time()))

        # Name the photo based on the time and put it in the user's Pictures folder.
        name = f'PiCarPhoto_{_time}'
        username = os.getlogin()
        path = f"/home/{username}/Pictures/"

        # Create directory if needed.
        os.makedirs(path, exist_ok=True)

        # Actually take the photo using Vilib.
        Vilib.take_photo(name, path)
        full_path = f"{path}{name}.jpg"
        print(f"Photo saved: {full_path}")
        return full_path
    except Exception as PhotoError:
        return f"Photo path error occured. Error: {PhotoError}"


def toggle_face_detect():
    """Toggle face detection on or off.

    Flips the global face_detection_on flag and updates Vilib's face detection
    state accordingly.

    Returns:
        A string describing whether face detection is now ON or OFF.

    Raises:
        FaceToggleError: If there is an error toggling face detection.
    """
    global face_detection_on

    face_detection_on = not face_detection_on
    Vilib.face_detect_switch(face_detection_on)

    status = "ON" if face_detection_on else "OFF"
    msg = f"Face detection: {status}"
    print(msg)
    return msg


def toggle_color_detect():
    """Background thread that cycles through all colors for detection.

    Continuously iterates through the list of colors, enabling each one in turn.
    If a color is detected, the function briefly lingers on that color before
    moving on, to make detection more stable.

    This function is designed to run in a daemon thread while `detection_running`
    remains True.

    Raises:
        ToggleColorError: If there is an error managing color detection.
    """
    global detection_running, current_color_idx

    while detection_running:
        for i, color in enumerate(color_list):
            if not detection_running:
                break

            # Update the currently active color index.
            current_color_idx = i
            Vilib.color_detect(color)

            # Small delay to allow detection data to update.
            sleep(0.08)
            n = Vilib.detect_obj_parameter.get('color_n', 0)
            if n > 0:
                # Color detected - stay on it a bit longer.
                sleep(0.15)
            else:
                # No detection, quickly move on to the next color.
                sleep(0.02)


def get_detection_info():
    """Get current detection information for face and color tracking.

    Builds a human-readable summary of the current detection status, including
    face count and bounding box, as well as active color detection information.

    Returns:
        A string summarizing the current detection state (faces and colors).
    """
    info_parts = []

    # Face detection info.
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

    # Color detection info.
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
    """Clamp a numeric value between a minimum and maximum.

    Args:
        value: The value that is trying to be set.
        min_val: The minimum value allowed.
        max_val: The maximum value allowed.

    Returns:
        The clamped value, which will be within [min_val, max_val].
    """
    return max(min_val, min(max_val, value))


def simple_avoidance():
    """Forward collision avoidance loop.

    This function runs in a background thread and only intervenes when the
    car is moving forward:

    - Reads the ultrasonic distance sensor.
    - If an object is within `safe_distance` and the car is moving forward,
      it stops the motors.
    - It does NOT interfere with backing up.

    Uses the global `is_moving_forward` flag to know when intervention is needed.
    """
    global px, running, is_moving_forward

    while running:
        if px is None:
            # No car instance yet; wait and check again.
            sleep(0.1)
            continue

        try:
            distance = px.ultrasonic.read()
        except Exception:
            # If the ultrasonic read fails, skip this cycle.
            sleep(0.1)
            continue

        # Convert to a usable float if possible.
        if distance is not None:
            try:
                distance = float(distance)
            except (TypeError, ValueError):
                distance = None

        if (
            distance is not None
            and distance > 0
            and distance <= safe_distance
            and is_moving_forward
        ):
            # Only stop if we were actually going forward.
            px.forward(0)
            is_moving_forward = False  # We've just stopped due to an obstacle.

        sleep(0.05)


def steering_loop():
    """Background loop to smoothly move steering towards target_angle.

    Gradually adjusts current_angle toward target_angle in small increments
    so that steering changes feel smooth and responsive instead of jerky.
    """
    global current_angle, target_angle, running, px
    while running:
        if current_angle < target_angle:
            current_angle += 0.5
        elif current_angle > target_angle:
            current_angle -= 0.5

        # Apply the updated steering angle to the servo.
        px.set_dir_servo_angle(current_angle)
        sleep(0.001)


def drive_loop(data):
    """Handle the low-level driving commands for the car.

    This function adjusts motor direction, speed, and steering target based
    on single-string commands like 'start forward' or 'stop left'.

    Args:
        data: A command string such as 'start forward', 'stop backward', etc.
    """
    global target_angle, running, px, connection_socket, is_moving_forward, current_speed
    match data:
        case 'start forward':
            px.forward(current_speed)
            is_moving_forward = True
        case 'start backward':
            px.backward(current_speed)
            is_moving_forward = False
        case 'start left':
            target_angle = -30
        case 'start right':
            target_angle = 30
        case 'stop forward':
            px.forward(0)
            is_moving_forward = False
        case 'stop backward':
            px.forward(0)
            is_moving_forward = False
        case 'stop left':
            target_angle = 0
        case 'stop right':
            target_angle = 0


def handle_command(action, command):
    """Process a high-level command from the client.

    Commands are split into an action (e.g., "start", "stop") and a command
    name (e.g., "cam_up", "speed_increase"). This function handles:
    - Speed control
    - Camera pan/tilt
    - Detection/camera features
    - Help text
    - Optional quit/shutdown

    Args:
        action: The action part of the command, usually "start" or "stop".
        command: The command name (e.g., "cam_up", "take_photo", "toggle_face").

    Returns:
        A tuple (response, should_quit) where:
            response: A string to be sent back to the client.
            should_quit: True if the server should shut down, False otherwise.
    """
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
            # Multi-line help text explaining key bindings and commands.
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
    """Clean up hardware and camera resources.

    Stops the steering loop, centers the camera and steering, stops the car,
    and closes the camera if it was started.
    """
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
    """Get the Pi's primary IP address.

    Uses the `hostname -I` command to read the list of IPs and returns the first.

    Returns:
        The primary IP address as a string, or "<pi-ip>" on failure.
    """
    import subprocess
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        ip = result.stdout.strip().split()[0]
        return ip
    except Exception:
        return "<pi-ip>"


def main():
    """Main entry point for the PiCar-X server.

    Initializes the PiCar hardware and camera, starts background threads for
    steering and simple obstacle avoidance, and then enters a loop accepting
    client connections and processing their commands.
    """
    global connection_socket, px, running

    # Initialize PiCar first.
    px = Picarx()
    px.set_cam_tilt_angle(0)
    px.set_cam_pan_angle(0)

    # Start camera immediately so user can view it.
    print("Starting camera...")
    initialize_camera()

    # Start steering thread.
    steer_thread = threading.Thread(target=steering_loop, daemon=True)
    steer_thread.start()

    # Start simple obstacle avoidance thread.
    avoid_thread = threading.Thread(target=simple_avoidance, daemon=True)
    avoid_thread.start()

    # Get IP address for display.
    ip_addr = get_ip_address()

    # Create server socket.
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

            # Send welcome message containing camera URL.
            welcome = f"Connected! http://{ip_addr}:9000/mjpg"
            send_response(welcome)

            try:
                # Reset line buffer for this connection.
                global recv_buffer
                recv_buffer = b""

                while True:
                    # Read a single line command from the client.
                    text = recv_line(connection_socket)
                    if text is None:
                        # Client disconnected.
                        break

                    text = text.strip()
                    if not text:
                        # Ignore empty lines.
                        continue

                    print(f"Received from client: {text}")

                    parts = text.split()
                    if len(parts) < 2:
                        response = f"Malformed command: '{text}'"
                        send_response(response)
                        continue

                    action = parts[0]
                    command = parts[1]

                    # Handle high-level command (speed/camera/etc.).
                    response, should_quit = handle_command(action, command)

                    # Handle low-level drive logic using the raw text.
                    drive_loop(text)

                    # Send full response (multiline-safe).
                    send_multiline(response)

                    if should_quit:
                        # Perform cleanup and exit if the client requested shutdown.
                        cleanup()
                        connection_socket.close()
                        server_socket.close()
                        print("Server shutdown complete")
                        sys.exit(0)

            except Exception as e:
                print(f"Error handling client: {e}")
            finally:
                # Always stop the car and close the client socket on disconnect.
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