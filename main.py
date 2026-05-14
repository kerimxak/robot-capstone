from picamera2 import Picamera2
from ultralytics import YOLO
import cv2
import time
import RPi.GPIO as GPIO
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- Ultrasonic sensor setup ---
TRIG = 23
ECHO = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# --- State machine states ---
SEARCHING   = "SEARCHING"
APPROACHING = "APPROACHING"
ENTERING    = "ENTERING"
WAITING     = "WAITING"
EXITING     = "EXITING"

# --- Motor commands (placeholders until ESP32 is connected) ---
def move_forward():  print("[MOTOR] Forward")
def move_backward(): print("[MOTOR] Backward")
def turn_left():     print("[MOTOR] Turn left")
def turn_right():    print("[MOTOR] Turn right")
def stop():          print("[MOTOR] Stop")

# --- Distance sensor function ---
def get_distance():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    duration = pulse_end - pulse_start
    distance = round(duration * 17150, 2)
    return distance

# --- Web stream ---
latest_frame = None
frame_lock = threading.Lock()

class StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
        self.end_headers()
        while True:
            with frame_lock:
                if latest_frame is None:
                    continue
                _, jpeg = cv2.imencode('.jpg', latest_frame)
            self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n')
            self.wfile.write(jpeg.tobytes())
            self.wfile.write(b'\r\n')
            time.sleep(0.05)

def start_stream():
    HTTPServer(('0.0.0.0', 8080), StreamHandler).serve_forever()

# --- Main loop ---
def run():
  cam = Picamera2()
  cam.start()
  model = YOLO("yolov8n.pt")

  threading.Thread(target=start_stream, daemon=True).start()
  print("Stream at http://10.42.0.1:8080")

  state = SEARCHING
  while True:
    frame = cam.capture_array()
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    results = model(frame_bgr, verbose=False)

    annotated = results[0].plot()
    cv2.putText(annotated, f"State: {state}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Detection logic
    door_detected = False
    door_centered = False

    distance = get_distance()
    door_close = distance < 20

    frame_width = frame_bgr.shape[1]
    for box in results[0].boxes:
      cls = int(box.cls[0])
      conf = float(box.conf[0])
      if conf < 0.5:
        continue
      if cls == 0:
        door_detected = True
        x_center = float(box.xywh[0][0])
        box_width = float(box.xywh[0][2])
        door_centered = abs(x_center - frame_width / 2) < frame_width * 0.15
        door_close = box_width > frame_width * 0.4

    if state == SEARCHING:
      if door_detected:
        state = APPROACHING
      else:
        turn_right()
    elif state == APPROACHING:
      if door_close:
        stop()
        state = ENTERING
      elif not door_centered:
        turn_right() if door_detected else turn_left()
      else:
        move_forward()
    elif state == ENTERING:
      move_forward()
      time.sleep(1)
      stop()
      state = WAITING
    elif state == WAITING:
      stop()
      state = EXITING
    elif state == EXITING:
      move_backward()
      time.sleep(1)
      stop()
      state = SEARCHING

    cv2.putText(annotated, f"Distance: {distance}cm", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

    with frame_lock:
      latest_frame = cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR)

    time.sleep(0.1)

  cam.stop()
  GPIO.cleanup()

if __name__ == "__main__":
  run()