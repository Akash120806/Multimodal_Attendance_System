# Multimodal Attendance & Engagement Agent

A local Python prototype for classroom video analysis. It detects and tracks faces in a recorded video, extracts audio where available, calculates timestamped activity features, combines them into a transparent rule-based engagement heuristic, and shows a dashboard with charts and suggestions.

## Run on Windows / VS Code

Use Python 3.11 (recommended). Extract the ZIP, open the extracted folder in VS Code, then run these commands in PowerShell from the folder containing `app.py`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. Open **http://127.0.0.1:5000**. To stop the server, press `Ctrl+C`.

If you already have a venv, activate it and run `python -m pip install -r requirements.txt` followed by `python app.py`.

## Use

1. Upload an MP4, AVI, MOV, MKV, or WebM classroom recording.
2. Click **Run Multimodal Pipeline** and wait for video frames and audio to be analyzed.
3. Review the session summary, engagement timeline, instructor suggestions, and reflective analytics.

The first install needs internet access for Python packages. The dashboard loads Chart.js from a CDN, so charts also need internet access unless you vendor Chart.js locally.

## What is implemented

- OpenCV Haar-cascade face detection and a simple centroid-based face tracker for recorded video.
- One-second visual activity aggregation.
- MoviePy audio extraction and RMS/amplitude-based activity proxy.
- Timestamp-aligned audio/video feature fusion.
- Explainable threshold-based engagement scoring and instructor suggestions.
- Reflective session summary and a Chart.js timeline dashboard.

## Important limitations

- This ZIP is a runnable **prototype**, not a production attendance system. The current pipeline analyzes uploaded recordings; it does **not** provide a complete live-webcam multimodal pipeline or live microphone analysis.
- Face tracking IDs are temporary labels, not face recognition or verified student identities. They may change when detections are missed.
- The audio activity value is a rough loudness proxy. It cannot reliably distinguish speech from all other sounds, and its displayed noise scale is not calibrated room-noise measurement.
- Engagement scores are illustrative heuristics, not validated measures of attention, emotion, learning, or teaching effectiveness. Do not use them for grades or consequential decisions.
- Analytics are session-level, not verified named-student records. Suggestions support instructor reflection and do not replace professional judgment.
- Uploaded video files are deleted after processing. No login/authentication is included; run only on a trusted local machine.

## Troubleshooting

- **Video cannot open:** try an H.264-encoded MP4.
- **Audio unavailable:** the recording may have no audio track or a codec may not be readable. The app falls back to quiet audio values.
- **Install error:** confirm Python 3.11 64-bit is selected and run `python -m pip install --upgrade pip` before installing requirements.
- **Port 5000 busy:** close the other app using port 5000 or change the port in `app.py`.
