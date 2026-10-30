
import csv
import io
import time
import uuid
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    make_response
)
from werkzeug.utils import secure_filename

from core.fusion import process_session


# --------------------------------------------------
# APPLICATION SETUP
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent
UPLOADS = ROOT / "uploads"
UPLOADS.mkdir(exist_ok=True)

ALLOWED = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

# Temporary in-memory storage for live sessions and reports.
live_sessions = {}
completed_reports = {}


# --------------------------------------------------
# GENERAL ROUTES
# --------------------------------------------------

@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "Multimodal Attendance & Engagement Agent"
    })


# --------------------------------------------------
# RECORDED VIDEO ANALYSIS
# --------------------------------------------------

@app.post("/upload")
def upload_video():

    file = request.files.get("video")

    if not file or not file.filename:
        return jsonify({
            "error": "Choose a classroom video first."
        }), 400

    suffix = Path(
        secure_filename(file.filename)
    ).suffix.lower()

    if suffix not in ALLOWED:
        return jsonify({
            "error": "Use MP4, AVI, MOV, MKV or WebM."
        }), 400

    filepath = UPLOADS / f"{uuid.uuid4().hex}{suffix}"

    file.save(filepath)

    try:
        results = process_session(str(filepath))

        results["session_name"] = request.form.get(
            "session_name",
            "Classroom Session"
        )[:100]

        return jsonify(results)

    except Exception as exc:

        app.logger.exception("Video processing failed")

        return jsonify({
            "error": f"Could not process video: {exc}"
        }), 500

    finally:
        filepath.unlink(missing_ok=True)


# --------------------------------------------------
# FACE DETECTOR
# --------------------------------------------------

def create_face_detector():

    if not hasattr(cv2, "CascadeClassifier"):
        raise RuntimeError(
            "Invalid OpenCV installation. "
            "Please reinstall opencv-python."
        )

    cascade_path = (
        Path(cv2.data.haarcascades)
        / "haarcascade_frontalface_default.xml"
    )

    detector = cv2.CascadeClassifier(
        str(cascade_path)
    )

    if detector.empty():
        raise RuntimeError(
            "Could not load Haar Cascade face detector."
        )

    return detector


# --------------------------------------------------
# CREATE LIVE SESSION
# --------------------------------------------------

@app.post("/api/sessions")
def create_live_session():

    try:
        detector = create_face_detector()

    except Exception as exc:

        app.logger.exception("Face detector initialization failed")

        return jsonify({
            "error": str(exc)
        }), 500

    data = request.get_json(silent=True) or {}

    session_id = uuid.uuid4().hex

    started = time.time()

    live_sessions[session_id] = {

        "name": str(
            data.get("name", "Live Classroom")
        )[:100],

        "detector": detector,

        "tracks": {},

        "next_participant": 1,

        "started_at": started,

        "last_frame_at": None,

        "peak_count": 0,

        "timeline": [],

        "attendance": {},

        "last_timeline_at": 0
    }

    return jsonify({
        "session_id": session_id,
        "message": "Live session created"
    }), 201


# --------------------------------------------------
# PROCESS LIVE CAMERA FRAME
# --------------------------------------------------

@app.post("/api/sessions/<session_id>/frame")
def process_live_frame(session_id):

    session = live_sessions.get(session_id)

    if session is None:
        return jsonify({
            "error": "Session not found. Start a new session."
        }), 404

    uploaded_frame = request.files.get("frame")

    if uploaded_frame is None:
        return jsonify({
            "error": "No camera frame received."
        }), 400

    try:

        image_bytes = uploaded_frame.read()

        image_array = np.frombuffer(
            image_bytes,
            dtype=np.uint8
        )

        frame = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        if frame is None:
            return jsonify({
                "error": "Invalid camera frame."
            }), 400

        height, width = frame.shape[:2]

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        gray = cv2.equalizeHist(gray)

        detections = session["detector"].detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        now = time.time()

        old_tracks = session["tracks"]

        updated_tracks = {}

        used_ids = set()

        faces = []

        # ------------------------------------------
        # MATCH DETECTED FACES TO EXISTING TRACKS
        # ------------------------------------------

        for x, y, w, h in detections:

            center_x = x + w / 2
            center_y = y + h / 2

            best_id = None
            best_distance = float("inf")

            max_distance = max(
                70,
                min(width, height) * 0.15
            )

            for participant_id, track in old_tracks.items():

                if participant_id in used_ids:
                    continue

                if now - track["last_seen"] > 2.0:
                    continue

                old_x, old_y = track["center"]

                distance = (
                    (center_x - old_x) ** 2
                    + (center_y - old_y) ** 2
                ) ** 0.5

                if (
                    distance < max_distance
                    and distance < best_distance
                ):

                    best_distance = distance
                    best_id = participant_id

            # Create a new temporary ID if no match exists.
            if best_id is None:

                best_id = (
                    f"P{session['next_participant']:03d}"
                )

                session["next_participant"] += 1

            used_ids.add(best_id)

            box = [
                int(x),
                int(y),
                int(w),
                int(h)
            ]

            updated_tracks[best_id] = {
                "center": (center_x, center_y),
                "box": box,
                "last_seen": now
            }

            faces.append({
                "participant_id": best_id,
                "box": box
            })

        # Keep recently missing IDs briefly.
        for participant_id, track in old_tracks.items():

            if (
                participant_id not in updated_tracks
                and now - track["last_seen"] <= 2.0
            ):

                updated_tracks[participant_id] = track

        session["tracks"] = updated_tracks

        # ------------------------------------------
        # RECORD ATTENDANCE ESTIMATES
        # ------------------------------------------

        previous_frame = session["last_frame_at"]

        elapsed = 0.0

        if previous_frame is not None:

            # Limit elapsed time to prevent large gaps
            # from being counted as continuous presence.
            elapsed = min(
                max(now - previous_frame, 0),
                1.5
            )

        session["last_frame_at"] = now

        participant_ids = [
            face["participant_id"]
            for face in faces
        ]

        for participant_id in participant_ids:

            attendance = session["attendance"].setdefault(
                participant_id,
                {
                    "detected_seconds": 0.0,
                    "detections": 0
                }
            )

            attendance["detected_seconds"] += elapsed

            attendance["detections"] += 1

        # ------------------------------------------
        # RECORD SESSION TIMELINE
        # ------------------------------------------

        session["peak_count"] = max(
            session["peak_count"],
            len(faces)
        )

        elapsed_session = round(
            now - session["started_at"],
            1
        )

        # Save timeline samples at approximately 1-second intervals.
        if (
            now - session["last_timeline_at"] >= 1.0
        ):

            session["timeline"].append({

                "elapsed_seconds": elapsed_session,

                "timestamp": datetime.now().isoformat(
                    timespec="seconds"
                ),

                "face_count": len(faces),

                "participant_ids": participant_ids
            })

            session["last_timeline_at"] = now

        return jsonify({

            "count": len(faces),

            "faces": faces,

            "frame_width": width,

            "frame_height": height

        })

    except Exception as exc:

        app.logger.exception("Live frame processing failed")

        return jsonify({
            "error": str(exc)
        }), 500


# --------------------------------------------------
# END SESSION AND GENERATE REPORT
# --------------------------------------------------

@app.post("/api/sessions/<session_id>/end")
def end_live_session(session_id):

    session = live_sessions.pop(
        session_id,
        None
    )

    if session is None:

        return jsonify({
            "error": "Live session not found."
        }), 404

    ended_at = time.time()

    duration = max(
        0,
        ended_at - session["started_at"]
    )

    participants = []

    for participant_id, stats in session["attendance"].items():

        participants.append({

            "participant_id": participant_id,

            "detected_seconds": round(
                stats["detected_seconds"],
                1
            ),

            "detections": stats["detections"]

        })

    participants.sort(
        key=lambda item: item["participant_id"]
    )

    report_id = uuid.uuid4().hex

    report = {

        "report_id": report_id,

        "session_name": session["name"],

        "started_at": datetime.fromtimestamp(
            session["started_at"]
        ).isoformat(timespec="seconds"),

        "ended_at": datetime.fromtimestamp(
            ended_at
        ).isoformat(timespec="seconds"),

        "duration_seconds": round(
            duration,
            1
        ),

        "peak_faces": session["peak_count"],

        "unique_temporary_ids": len(participants),

        "participants": participants,

        "timeline": session["timeline"],

        "note": (
            "Detection-based estimates only. "
            "Temporary IDs are not verified identities. "
            "Detected time is not proof of attendance."
        )
    }

    completed_reports[report_id] = report

    return jsonify(report)


# --------------------------------------------------
# DOWNLOAD LIVE SESSION CSV
# --------------------------------------------------

@app.get("/api/reports/<report_id>/csv")
def download_live_report(report_id):

    report = completed_reports.get(report_id)

    if report is None:

        return jsonify({
            "error": "Report not found."
        }), 404

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow(["LIVE SESSION REPORT"])

    writer.writerow([
        "Session",
        report["session_name"]
    ])

    writer.writerow([
        "Started",
        report["started_at"]
    ])

    writer.writerow([
        "Ended",
        report["ended_at"]
    ])

    writer.writerow([
        "Duration seconds",
        report["duration_seconds"]
    ])

    writer.writerow([
        "Peak faces detected",
        report["peak_faces"]
    ])

    writer.writerow([
        "Unique temporary IDs",
        report["unique_temporary_ids"]
    ])

    writer.writerow([])

    writer.writerow([
        "Participant ID",
        "Detected seconds",
        "Frame detections"
    ])

    for participant in report["participants"]:

        writer.writerow([
            participant["participant_id"],
            participant["detected_seconds"],
            participant["detections"]
        ])

    writer.writerow([])

    writer.writerow([
        "Elapsed seconds",
        "Timestamp",
        "Faces detected",
        "Temporary IDs"
    ])

    for entry in report["timeline"]:

        writer.writerow([
            entry["elapsed_seconds"],
            entry["timestamp"],
            entry["face_count"],
            ", ".join(entry["participant_ids"])
        ])

    writer.writerow([])

    writer.writerow([
        "Note",
        report["note"]
    ])

    response = make_response(
        "\ufeff" + output.getvalue()
    )

    response.headers["Content-Type"] = (
        "text/csv; charset=utf-8"
    )

    response.headers["Content-Disposition"] = (
        f'attachment; filename="live_report_{report_id[:8]}.csv"'
    )

    return response


# --------------------------------------------------
# EXISTING CSV ROUTE
# --------------------------------------------------

@app.get("/report.csv")
def report_csv():

    return jsonify({
        "error": "Export is available from the dashboard."
    }), 400


# --------------------------------------------------
# START SERVER
# --------------------------------------------------

if __name__ == "__main__":

    print("----------------------------------------")
    print("Multimodal Attendance & Engagement Agent")
    print("Open http://127.0.0.1:5000")
    print("----------------------------------------")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
