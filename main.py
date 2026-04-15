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
    # Add info on the screen
    annotated = results[0].plot()
    cv2.putText(annotated, f"State: {state}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
# Detection logic
    door_detected = False
    door_centered = False
    door_close    = False
    
    frame_width = frame_bgr.shape[1]
    for box in results[0].boxes:
      cls = int(box.cls[0])
      conf = float(box.conf[0])
      if conf < 0.5:
        continue
      # Temporarily use class 0 (person) as stand-in for door
      if cls == 0:
        door_detected = True
        x_center = float(box.xywh[0][0])
        box_width = float(box.xywh[0][2])
        # Centered if within middle 30% of frame
        door_centered = abs(x_center - frame_width / 2) < frame_width * 0.15
        # Close if bounding box is wide enough
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
    # Add screen info
    cv2.imshow("Robot", annotated)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    
    time.sleep(0.1)
  
  cam.stop()
  cv2.destroyAllWindows()

if __name__ == "__main__":
  run()