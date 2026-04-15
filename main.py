from picamera2 import Picamera2
from ultralytics import YOLO
import cv2
import time

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

# --- Main loop ---
def run():
  cam = Picamera2()
  cam.start()
  model = YOLO("yolov8n.pt")

  state = SEARCHING
  while True:
    frame = cam.capture_array()
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    results = model(frame_bgr, verbose=False)
    # Placeholder: find elevator door in detections
    door_detected = False
    door_centered = False
    door_close    = False
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
      # Will use ultrasonic sensor here
      move_forward()
      time.sleep(1)
      stop()
      state = WAITING
    elif state == WAITING:
      stop()
      # Will detect floor change here
      state = EXITING
    elif state == EXITING:
      move_backward()
      time.sleep(1)
      stop()
      state = SEARCHING
    time.sleep(0.1)

if __name__ == "__main__":
  run()