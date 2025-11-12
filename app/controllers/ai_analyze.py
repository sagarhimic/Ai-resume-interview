from fastapi import File, Form, UploadFile, Depends
import cv2
import numpy as np
import mediapipe as mp
from deepface import DeepFace
from typing import Optional
from sqlalchemy.orm import Session
from app.models.inactivity_log import InactivityLog
from app.config.database import get_db, SessionLocal
import time

# Initialize Mediapipe globally (⚡ much faster + avoids context leaks)
mp_face_mesh = mp.solutions.face_mesh
mp_face_detection = mp.solutions.face_detection

face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1)
face_detector = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)

# Global state
last_face_encoding: Optional[np.ndarray] = None
face_missing_counter = 0
no_lip_counter = 0
last_face_time = time.time()
last_lip_time = time.time()
IDLE_THRESHOLD = 25  # seconds
# Track last expression change
last_expression = "unknown"
last_expression_time = time.time()

# ────────────────────────────────────────────────
def log_event(db: Session, candidate_id: str, event_type: str, message: str, severity: str = "info"):
    """Save suspicious behavior to DB"""
    try:
        db = SessionLocal()
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
def extract_face_embedding(frame: np.ndarray) -> Optional[np.ndarray]:
    """Extract simple embedding from first 50 face landmarks"""
    results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    if not results.multi_face_landmarks:
        return None
    landmarks = results.multi_face_landmarks[0].landmark[:50]
    coords = np.array([[lm.x, lm.y, lm.z] for lm in landmarks]).flatten()
    return coords / np.linalg.norm(coords)

# ────────────────────────────────────────────────
def detect_expression(frame: np.ndarray) -> str:
    """Detect dominant facial emotion using DeepFace"""
    try:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        analysis = DeepFace.analyze(rgb, actions=["emotion"], enforce_detection=False)
        if isinstance(analysis, list):
            analysis = analysis[0]
        return analysis.get("dominant_emotion", "unknown")
    except Exception as e:
        print("⚠️ Emotion detection error:", e)
        return "unknown"

# ────────────────────────────────────────────────
def detect_lip_movement(frame: np.ndarray) -> bool:
    """Detect lip movement distance between upper/lower lip landmarks"""
    results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    if not results.multi_face_landmarks:
        return False
    upper = results.multi_face_landmarks[0].landmark[13]
    lower = results.multi_face_landmarks[0].landmark[14]
    return abs(upper.y - lower.y) > 0.02

# ────────────────────────────────────────────────
def get_face_boxes(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_detector.process(rgb)
    boxes = []
    if results.detections:
        h, w, _ = frame.shape
        for det in results.detections:
            bbox = det.location_data.relative_bounding_box
            x = int(bbox.xmin * w)
            y = int(bbox.ymin * h)
            width = int(bbox.width * w)
            height = int(bbox.height * h)

            # clamp
            x = max(0, min(x, w-1))
            y = max(0, min(y, h-1))
            width = max(0, min(width, w - x))
            height = max(0, min(height, h - y))

            score = float(det.score[0]) if det.score and len(det.score) > 0 else 0.0
            boxes.append({"x": x, "y": y, "w": width, "h": height, "score": score})
    return boxes
# ────────────────────────────────────────────────
def count_faces(frame: np.ndarray) -> int:
    """Detect number of faces using Mediapipe FaceDetection"""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_detector.process(rgb)
    if not results.detections:
        return 0
    return len(results.detections)

# ────────────────────────────────────────────────
async def analyze_frame(
    candidate_id: str = Form(...),
    frame: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    global last_face_encoding, face_missing_counter, no_lip_counter, last_face_time, last_lip_time, last_expression, last_expression_time

    try:
        content = await frame.read()
        npimg = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "Invalid image data"}

        now = time.time()
        idle_reason = None
        # 1️⃣ Detect number of faces first (⚡ avoids false idle)
        face_boxes = get_face_boxes(img)
        face_count = count_faces(img)

        if face_count > 1:
            log_event(db, candidate_id, "proxy_detected", f"Multiple ({face_count}) faces detected", "critical")
            return {
                "candidate_id": candidate_id,
                "status": "paused",
                "reason": "Multiple faces detected — possible proxy.",
                "alert": True,
                "face_boxes": face_boxes
            }

        # 2️⃣ Lip movement
        lip_sync = detect_lip_movement(img)

        # 3️⃣ Facial expression
        expression = detect_expression(img) or "unknown"

        # Detect if expression has changed recently
        if expression != last_expression:
            last_expression = expression
            last_expression_time = now

        # 4️⃣ Proxy detection via face encoding
        current_encoding = extract_face_embedding(img)

        if current_encoding is None:
            face_missing_counter += 1
            if face_missing_counter >= 3:
                log_event(db, candidate_id, "face_missing", "No face detected 3 consecutive frames", "warning")
                face_missing_counter = 0

            if now - last_face_time >= IDLE_THRESHOLD:
                idle_reason = "No face detected for 25 seconds"
                log_event(db, candidate_id, "idle_detected", idle_reason, "warning")
                last_face_time = now
                return {
                    "candidate_id": candidate_id,
                    "status": "idle",
                    "reason": idle_reason,
                    "expression": expression,
                    "alert": False,
                    "face_boxes": face_boxes
                }
        else:
            last_face_time = now

        # Compare with previous encoding for proxy detection
        is_proxy = False
        if last_face_encoding is not None:
            distance = np.linalg.norm(current_encoding - last_face_encoding)
            if distance > 0.15:
                is_proxy = True
                log_event(db, candidate_id, "proxy_detected",
                          f"Proxy face detected (distance={distance:.2f})", "critical")
        last_face_encoding = current_encoding

        # 🧠 Improved Idle Detection (combines lip + expression + stability)
        if not lip_sync:
            no_lip_counter += 1
            # Check inactivity across both lips and expressions
            inactive_time = min(now - last_lip_time, now - last_expression_time)

            if inactive_time >= IDLE_THRESHOLD:
                idle_reason = f"No visible speech or facial change for {IDLE_THRESHOLD} seconds"
                log_event(db, candidate_id, "idle_detected", idle_reason, "warning")
                last_lip_time = now
                last_expression_time = now
                return {
                    "candidate_id": candidate_id,
                    "status": "idle_for_submission",
                    "reason": idle_reason,
                    "expression": expression,
                    "alert": False,
                    "face_boxes": face_boxes
                }
        else:
            no_lip_counter = 0
            last_lip_time = now
            last_expression_time = now  # reset both if user moves/talks


        # ✅ Return active response
        return {
            "candidate_id": candidate_id,
            "lip_sync": bool(lip_sync),
            "expression": expression,
            "alert": is_proxy,
            "status": "active",
            "message": "Proxy detected" if is_proxy else "OK",
            "face_boxes": face_boxes
        }

    except Exception as e:
        print("❌ Error analyzing frame:", e)
        return {"error": str(e)}
