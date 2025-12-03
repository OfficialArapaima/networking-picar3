# networking-picar3
Repository for our networking class PiCar assignment.

## Features
- Remote control of PiCar-X via socket connection
- Real-time face detection using OpenCV
- Automatic image capture when faces are detected
- Images saved with timestamps in `captured_faces/` directory

## Requirements
- Python 3.x
- OpenCV (cv2)
- readchar
- picarx library (for the PiCar-X hardware)

## Installation

### Server (Raspberry Pi on PiCar-X)
```bash
pip install opencv-python
```

### Client (Control computer)
```bash
pip install readchar
```

## Usage

### 1. Start the Server on PiCar-X
Run on the Raspberry Pi:
```bash
python picar-server.py
```
The server will start listening on port 12000.

### 2. Connect from Client
Run on your control computer:
```bash
python picar-client.py
```
Enter the PiCar's IP address when prompted.

## Controls
- **w**: Move forward
- **a**: Turn left
- **s**: Move backward
- **d**: Turn right
- **f**: Toggle face detection ON/OFF
- **Ctrl+C**: Quit

## Face Detection
When face detection is enabled (press 'f'):
- The camera continuously monitors for faces
- When a face is detected, an image is automatically captured
- **Images are sent to the client computer** and saved in the `received_faces/` directory
- Cooldown of 2 seconds between captures to avoid duplicates
- Bounding boxes are drawn around detected faces in saved images
- Real-time transfer over socket connection

## File Structure
- `picar-server.py`: Server running on PiCar-X (handles movement and face detection)
- `picar-client.py`: Client for remote control (runs on your computer)
- `received_faces/`: Directory where face detection images are saved on client (auto-created)
- `requirements.txt`: Python package dependencies

## Notes
- Face detection uses Haar Cascade classifier from OpenCV
- Camera initializes automatically when face detection is first enabled
- All captured images include timestamp in filename format: `face_YYYYMMDD_HHMMSS.jpg`
- Images are transferred in real-time from server to client over the socket connection
- The client runs a background thread to receive images without blocking controls
- JPEG compression is used to optimize transfer speed (quality: 85%)
