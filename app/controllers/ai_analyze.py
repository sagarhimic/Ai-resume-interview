from fastapi import File, Form, UploadFile, Depends
import cv2
import numpy as np
import mediapipe as mp
from deepface import DeepFace
from typing import Optional
from sqlalchemy.orm import Session
from app.models.inactivity_log import InactivityLog
from app.config.database import get_db
import time


# Initialize Mediapipe models
mp_face_mesh = mp.solutions.face_mesh

# Global state for proxy/inactivity detection
last_face_encoding: Optional[np.ndarray] = None
face_missing_counter = 0
no_lip_counter = 0

# Add time trackers
last_face_time = time.time()
last_lip_time = time.time()

IDLE_THRESHOLD = 20  # 20 seconds

# ────────────────────────────────────────────────
# Helper: log_event → Save suspicious behavior to DB
# ────────────────────────────────────────────────
def log_event(db: Session, candidate_id: str, event_type: str, message: str, severity: str = "info"):
    """Store inactivity or cheating events in DB"""
    try:
        log = InactivityLog(
            candidate_id=candidate_id,
            event_type=event_type,
            event_message=message,
            severity=severity
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"⚠️ Logging error: {e}")


# ────────────────────────────────────────────────
# Helper: extract_face_embedding
# ────────────────────────────────────────────────
def extract_face_embedding(frame: np.ndarray) -> Optional[np.ndarray]:
    """Extract simple embedding from face landmarks"""
    with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1) as mesh:
        results = mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if not results.multi_face_landmarks:
            return None
        landmarks = results.multi_face_landmarks[0].landmark[:50]
        coords = np.array([[lm.x, lm.y, lm.z] for lm in landmarks]).flatten()
        return coords / np.linalg.norm(coords)


# ────────────────────────────────────────────────
# Helper: detect_expression
# ────────────────────────────────────────────────
def detect_expression(frame: np.ndarray) -> str:
    """Detect dominant facial emotion using DeepFace"""
    try:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        analysis = DeepFace.analyze(rgb_frame, actions=['emotion'], enforce_detection=False)
        if isinstance(analysis, list):
            analysis = analysis[0]
        expr = analysis.get("dominant_emotion", "unknown")
        return expr or "unknown"
    except Exception as e:
        print("⚠️ Emotion detection error:", e)
        return "unknown"


# ────────────────────────────────────────────────
# Helper: detect_lip_movement
# ────────────────────────────────────────────────
def detect_lip_movement(frame: np.ndarray) -> bool:
    """Detect lip movement by measuring distance between upper/lower lip landmarks"""
    with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1) as mesh:
        results = mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if not results.multi_face_landmarks:
            return False
        upper_lip = results.multi_face_landmarks[0].landmark[13]
        lower_lip = results.multi_face_landmarks[0].landmark[14]
        lip_distance = abs(upper_lip.y - lower_lip.y)
        return lip_distance > 0.02

# ────────────────────────────────────────────────
# Helper: detect_multiple_faces
# ────────────────────────────────────────────────
def count_faces(frame: np.ndarray) -> int:
    """Return number of faces detected in the frame using Mediapipe."""
    with mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as detector:
        results = detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if not results.detections:
            return 0
        return len(results.detections)


# ────────────────────────────────────────────────
# Endpoint: analyze_frame
# ────────────────────────────────────────────────
async def analyze_frame(
    candidate_id: str = Form(...),
    frame: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    global last_face_encoding, face_missing_counter, no_lip_counter, last_face_time, last_lip_time

    try:
        # Read frame
        content = await frame.read()
        npimg = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "Invalid image data"}

        # 1️⃣ Detect lip movement
        lip_sync = detect_lip_movement(img)

        # 2️⃣ Detect expression (always return a valid string)
        expression = detect_expression(img) or "unknown"

        # 3️⃣ Extract face encoding for proxy detection
        current_encoding = extract_face_embedding(img)

        now = time.time()
        idle_reason = None

        # ── Face not found (handle and log)
        if current_encoding is None:
            face_missing_counter += 1
            if face_missing_counter >= 3:
                log_event(db, candidate_id, "face_missing", "No face detected 3 consecutive frames", "warning")
                face_missing_counter = 0  # reset after logging

        # Check idle threshold for no face
            if now - last_face_time >= IDLE_THRESHOLD:
                idle_reason = "No face detected for 20 seconds"
                log_event(db, candidate_id, "idle_detected", idle_reason, "warning")
                last_face_time = now  # reset timer after logging
                return {
                        "candidate_id": candidate_id,
                        "status": "idle",
                        "reason": idle_reason,
                        "expression": expression,
                        "alert": False
                    }
            else:
                last_face_time = now  # reset idle timer when face found


        # ── PROXY DETECTION ───────────────────────
        is_proxy = False
        if last_face_encoding is not None:
            distance = np.linalg.norm(current_encoding - last_face_encoding)
            if distance > 0.15:
                is_proxy = True
                log_event(db, candidate_id, "proxy_detected",
                          f"Proxy face detected (distance={distance:.2f})", "critical")

        last_face_encoding = current_encoding

        # ── NO LIP MOVEMENT ───────────────────────
        if not lip_sync:
            no_lip_counter += 1
            if no_lip_counter >= 5:
                log_event(db, candidate_id, "no_lip_movement", "No lip movement for 5 frames", "info")

            # Check idle threshold for no lip
            if now - last_lip_time >= IDLE_THRESHOLD:
                idle_reason = "No lip movement for 20 seconds"
                log_event(db, candidate_id, "idle_detected", idle_reason, "warning")
                last_lip_time = now  # reset timer
                return {
                    "candidate_id": candidate_id,
                    "status": "idle",
                    "reason": idle_reason,
                    "expression": expression,
                    "alert": False
                }
        else:
            no_lip_counter = 0
            last_lip_time = now

        # ── Multi-face detection ───────────────────────
        face_count = count_faces(img)

        if face_count > 1:
            log_event(db, candidate_id, "proxy_detected", f"Multiple ({face_count}) faces detected", "critical")
            return {
                "candidate_id": candidate_id,
                "status": "paused",
                "reason": "Multiple faces detected — possible proxy.",
                "alert": True
            }

        # ✅ Return normal active response
        return {
            "candidate_id": candidate_id,
            "lip_sync": bool(lip_sync),
            "expression": expression,
            "alert": is_proxy,
            "status": "active",
            "message": "Proxy detected" if is_proxy else "OK",
        }

    except Exception as e:
        print("❌ Error analyzing frame:", e)
        return {"error": str(e)}
