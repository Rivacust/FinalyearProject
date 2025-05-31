
import cv2
import numpy as np
import face_recognition
import pickle
import threading
from datetime import datetime
import mediapipe as mp
from .mongo_connect import client
from time import time

# Globals
latest_frame = None
status_message = ""
message_shown_once = False
lock = threading.Lock()
last_message_time = 0
message_duration = 0
frame_skip = 5
processing_thread = None
stop_processing = False
current_username = None

def set_username(username):
    global current_username
    try:
        with lock:
            current_username = username
    except Exception as e:
        print(f"[ERROR] Failed to set username: {e}")

def load_encoding_data():
    global encodeListKnown, studentIds
    try:
        if not current_username:
            print("Username not provided.")
            return False

        db = client[current_username]
        collection = db["Image_info"]

        # Only fetch the pickle_data field (excluding _id for cleaner output)
        doc = collection.find_one({}, {"_id": 0, "pickle_data": 1})

        if not doc:
            print("No document found in Image_info.")
            return False

        pickle_data = doc.get("pickle_data")
        if not pickle_data:
            print("No encoding data found in the document.")
            return False

        encodeListKnown, studentIds = pickle.loads(pickle_data)
        print("Encode file loaded from database.")
        return True

    except Exception as e:
        print(f"Error loading encode file from database: {e}")
        return False

# Mediapipe Face Detection
mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.5)

def clear_status_message():
    global status_message, last_message_time, message_duration, message_shown_once
    try:
        if message_shown_once and (time() - last_message_time >= message_duration):
            with lock:
                status_message = ""
                message_shown_once = False
    except Exception as e:
        print(f"[ERROR] Failed to clear status message: {e}")

def check_and_reset_recognized_today():
    try:
        if current_username:
            db = client[current_username]
            datasheet = db["Datasheet"]
            if datasheet.count_documents({}) == 0:
                db["recognized_today"].delete_many({})
                print("[INFO] recognized_today cleared due to missing CSV")
            else:
                print("[INFO] recognized_today is active (CSV found)")
    except Exception as e:
        print(f"[ERROR] Checking Datasheet CSVs failed: {e}")

def process_frame():
    global latest_frame, status_message, last_message_time, message_duration, message_shown_once
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] Camera could not be opened.")
        return

    frame_count = 0
    try:
        while not stop_processing:
            try:
                success, frame = cap.read()
                if not success:
                    print("[WARNING] Couldn't read from webcam.")
                    continue
            except Exception as e:
                print(f"[ERROR] Reading from webcam failed: {e}")
                continue

            try:
                frame_count += 1
            except Exception as e:
                print(f"[ERROR] Frame count increment failed: {e}")
                continue

            try:
                with lock:
                    latest_frame = frame.copy()
            except Exception as e:
                print(f"[ERROR] Failed to copy frame: {e}")
                continue

            try:
                if frame_count % frame_skip != 0:
                    continue
            except Exception as e:
                print(f"[ERROR] Frame skipping logic failed: {e}")
                continue

            try:
                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_detection.process(img_rgb)
            except Exception as e:
                print(f"[ERROR] Converting frame or processing face detection failed: {e}")
                continue

            try:
                if results.detections:
                    for detection in results.detections:
                        try:
                            h, w, _ = frame.shape
                            bboxC = detection.location_data.relative_bounding_box
                            x_min = int(bboxC.xmin * w)
                            y_min = int(bboxC.ymin * h)
                            box_width = int(bboxC.width * w)
                            box_height = int(bboxC.height * h)

                            x1 = max(0, x_min)
                            y1 = max(0, y_min)
                            x2 = min(w, x_min + box_width)
                            y2 = min(h, y_min + box_height)

                        except Exception as e:
                            print(f"[ERROR] Bounding box calculation failed: {e}")
                            continue

                        try:
                            face_img = img_rgb[y1:y2, x1:x2]
                            if face_img.size == 0:
                                continue
                            face_img = cv2.resize(face_img, (0, 0), None, 0.25, 0.25)
                            encodeCurFrame = face_recognition.face_encodings(face_img)
                        except Exception as e:
                            print(f"[ERROR] Face encoding failed: {e}")
                            continue

                        if encodeCurFrame:
                            try:
                                encodeFace = encodeCurFrame[0]
                                matches = face_recognition.compare_faces(encodeListKnown, encodeFace, tolerance=0.5)
                                faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
                                matchIndex = np.argmin(faceDis)
                            except Exception as e:
                                print(f"[ERROR] Face comparison failed: {e}")
                                continue

                            if matches[matchIndex]:
                                try:
                                    student_id = studentIds[matchIndex]
                                    current_date = datetime.now().strftime("%Y-%m-%d")

                                    if current_username:
                                        db = client[current_username]
                                        datasheet = db["Datasheet"]
                                        recognized_col = db["recognized_today"]
                                    
                                        result = datasheet.find_one({"ID": int(student_id)}, {"_id": 0, "Name": 1})


                                        name = result["Name"]


                                        if datasheet.count_documents({}) > 0:
                                            existing = recognized_col.find_one({
                                                "student_id": student_id,
                                                "date": current_date
                                            })

                                            if not existing:
                                                recognized_col.update_one(
                                                    {"student_id": student_id},
                                                    {"$set": {"date": current_date}},
                                                    upsert=True
                                                )

                                                current_date = datetime.now().strftime("%Y-%m-%d")
                                                day_name = datetime.now().strftime("%A")

                                                count_today = recognized_col.count_documents({"date": current_date})
                                                summary_col = db["daily_attendance_summary"]

                                                summary_col.update_one(
                                                    {"date": current_date},
                                                    {"$set": {
                                                        "recognized_count": count_today,
                                                        "day": day_name
                                                    }},
                                                    upsert=True
                                                )


                                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                                try:
                                                    datasheet.update_one(
                                                        {"ID": int(student_id)},
                                                        {"$push": {"Attendance": timestamp}}
                                                    )
                                                except Exception as e:
                                                    print(f"[ERROR] Attendance DB update failed: {e}")

                                            with lock:
                                                status_message = f"{name}, you may go now"
                                                message_shown_once = True
                                                last_message_time = time()
                                                message_duration = 10

                                        else:
                                            check_and_reset_recognized_today()
                                    else:
                                        with lock:
                                            status_message = "Error: User session not set."
                                            print("[WARNING]", status_message)

                                except Exception as e:
                                    print(f"[ERROR] Attendance marking failed: {e}")
            except Exception as e:
                print(f"[ERROR] Frame processing block failed: {e}")

            try:
                clear_status_message()
            except Exception as e:
                print(f"[ERROR] Clearing status message failed: {e}")

    finally:
        cap.release()

def gen_frames():
    global latest_frame, processing_thread, stop_processing
    stop_processing = False

    # Call load_encoding_data here
    if not load_encoding_data():
        print("[ERROR] Encoding data could not be loaded. Stopping frame processing.")
        return  # Do not proceed without encoding data

    if processing_thread is None or not processing_thread.is_alive():
        processing_thread = threading.Thread(target=process_frame, daemon=True)
        processing_thread.start()

    while True:
        if stop_processing:
            break
        if latest_frame is not None:
            with lock:
                frame = latest_frame.copy()
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


def get_status_message():
    with lock:
        return status_message

def mark_message_as_shown():
    global message_shown_once
    with lock:
        message_shown_once = True

def stop_frame_processing():
    global stop_processing
    with lock:
        stop_processing = True
