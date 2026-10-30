
// ==================================================
// MULTIMODAL ATTENDANCE & ENGAGEMENT AGENT
// Frontend JavaScript
// ==================================================

document.addEventListener("DOMContentLoaded", () => {

    // ----------------------------------------------
    // DOM ELEMENTS
    // ----------------------------------------------

    const uploadForm = document.getElementById("uploadForm");
    const sessionName = document.getElementById("sessionName");
    const videoFile = document.getElementById("videoFile");
    const submitBtn = document.getElementById("submitBtn");
    const loader = document.getElementById("loader");

    const engScore = document.getElementById("engScore");
    const attStatus = document.getElementById("attStatus");
    const durPresent = document.getElementById("durPresent");
    const scoreMeter = document.getElementById("scoreMeter");

    const instSuggestions = document.getElementById("instSuggestions");
    const stuConsistency = document.getElementById("stuConsistency");
    const stuSummary = document.getElementById("stuSummary");

    const csvBtn = document.getElementById("csvBtn");
    const jsonBtn = document.getElementById("jsonBtn");

    const webcam = document.getElementById("webcam");
    const cameraOverlay = document.getElementById("cameraOverlay");
    const cameraPlaceholder = document.getElementById("cameraPlaceholder");

    const enableCameraBtn = document.getElementById("enableCameraBtn");
    const startLiveBtn = document.getElementById("startLiveBtn");
    const stopLiveBtn = document.getElementById("stopLiveBtn");

    const liveFaceCount = document.getElementById("liveFaceCount");
    const liveParticipants = document.getElementById("liveParticipants");
    const cameraStatus = document.getElementById("cameraStatus");
    const cameraMessage = document.getElementById("cameraMessage");

    // Live report elements
    const liveReport = document.getElementById("liveReport");

    let latestResults = null;
    let timelineChart = null;

    let cameraStream = null;
    let liveSessionId = null;
    let trackingTimer = null;
    let trackingBusy = false;

    let knownParticipants = new Set();

    // ----------------------------------------------
    // GENERAL HELPERS
    // ----------------------------------------------

    function setText(element, value) {
        if (element) {
            element.textContent = value;
        }
    }

    function showMessage(message) {
        setText(cameraMessage, message);
    }

    function setCameraStatus(message) {
        setText(cameraStatus, message);
    }

    async function readResponse(response) {
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(
                data.error || `Server error: ${response.status}`
            );
        }

        return data;
    }

    // ----------------------------------------------
    // RECORDED VIDEO UPLOAD
    // ----------------------------------------------

    if (uploadForm) {

        uploadForm.addEventListener("submit", async (event) => {

            event.preventDefault();

            if (!videoFile || !videoFile.files.length) {
                alert("Please select a classroom video.");
                return;
            }

            const formData = new FormData();

            formData.append(
                "video",
                videoFile.files[0]
            );

            formData.append(
                "session_name",
                sessionName ? sessionName.value : "Classroom Session"
            );

            if (submitBtn) submitBtn.disabled = true;
            if (loader) loader.style.display = "block";

            try {

                const response = await fetch("/upload", {
                    method: "POST",
                    body: formData
                });

                const data = await readResponse(response);

                latestResults = data;

                displayRecordedResults(data);

            } catch (error) {

                console.error("Upload error:", error);

                alert(error.message);

            } finally {

                if (submitBtn) submitBtn.disabled = false;
                if (loader) loader.style.display = "none";

            }

        });
    }

    // ----------------------------------------------
    // DISPLAY RECORDED VIDEO RESULTS
    // ----------------------------------------------

    function displayRecordedResults(data) {

        const score = Number(
            data.engagement_score ?? data.average_engagement ?? 0
        );

        setText(
            engScore,
            `${score.toFixed(1)}%`
        );

        if (scoreMeter) {
            scoreMeter.style.width =
                `${Math.max(0, Math.min(100, score))}%`;
        }

        setText(
            attStatus,
            data.attendance_status ?? data.status ?? "Analyzed"
        );

        setText(
            durPresent,
            data.duration_present ?? data.presence_time ?? "--"
        );

        // Instructor suggestions
        if (instSuggestions) {

            instSuggestions.replaceChildren();

            const suggestions =
                data.instructor_suggestions || [];

            if (suggestions.length === 0) {

                instSuggestions.textContent =
                    "No suggestions available.";

            } else {

                suggestions.forEach((suggestion) => {

                    const item = document.createElement("li");

                    item.textContent =
                        typeof suggestion === "string"
                            ? suggestion
                            : suggestion.message || JSON.stringify(suggestion);

                    instSuggestions.appendChild(item);

                });
            }
        }

        // Student analytics
        if (stuConsistency) {

            stuConsistency.textContent =
                data.focus_consistency ?? "--";
        }

        if (stuSummary) {

            stuSummary.textContent =
                data.summary || "Analysis completed.";
        }

        drawRecordedTimeline(data.timeline || []);

    }

    // ----------------------------------------------
    // RECORDED VIDEO TIMELINE CHART
    // ----------------------------------------------

    function drawRecordedTimeline(timeline) {

        const canvas = document.getElementById("timelineChart");

        if (!canvas || typeof Chart === "undefined") {
            return;
        }

        const labels = timeline.map((item) => {
            return item.time_sec ?? item.elapsed_seconds ?? 0;
        });

        const engagement = timeline.map((item) => {
            return item.engagement_score ?? 0;
        });

        const movement = timeline.map((item) => {
            return item.movement ?? 0;
        });

        const noise = timeline.map((item) => {
            return item.noise_db ?? 0;
        });

        if (timelineChart) {
            timelineChart.destroy();
        }

        timelineChart = new Chart(canvas, {

            type: "line",

            data: {

                labels: labels,

                datasets: [

                    {
                        label: "Engagement",
                        data: engagement,
                        borderWidth: 2,
                        tension: 0.3
                    },

                    {
                        label: "Movement",
                        data: movement,
                        borderWidth: 2,
                        tension: 0.3
                    },

                    {
                        label: "Noise",
                        data: noise,
                        borderWidth: 2,
                        tension: 0.3
                    }

                ]

            },

            options: {

                responsive: true,

                maintainAspectRatio: false,

                interaction: {
                    intersect: false,
                    mode: "index"
                },

                scales: {

                    y: {
                        beginAtZero: true
                    }

                }

            }

        });

    }

    // ----------------------------------------------
    // CSV AND JSON EXPORT FOR RECORDED ANALYSIS
    // ----------------------------------------------

    if (csvBtn) {

        csvBtn.addEventListener("click", () => {

            if (!latestResults) {
                alert("Analyze a video first.");
                return;
            }

            const timeline = latestResults.timeline || [];

            const rows = [
                ["Time", "Movement", "Noise", "Engagement"]
            ];

            timeline.forEach((item) => {

                rows.push([
                    item.time_sec ?? item.elapsed_seconds ?? 0,
                    item.movement ?? 0,
                    item.noise_db ?? 0,
                    item.engagement_score ?? 0
                ]);

            });

            downloadFile(
                "classroom_analysis.csv",
                rows.map((row) => row.join(",")).join("\n"),
                "text/csv"
            );

        });

    }

    if (jsonBtn) {

        jsonBtn.addEventListener("click", () => {

            if (!latestResults) {
                alert("Analyze a video first.");
                return;
            }

            downloadFile(
                "classroom_analysis.json",
                JSON.stringify(latestResults, null, 2),
                "application/json"
            );

        });

    }

    function downloadFile(filename, content, type) {

        const blob = new Blob(
            [content],
            { type }
        );

        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");

        link.href = url;
        link.download = filename;

        document.body.appendChild(link);

        link.click();

        link.remove();

        URL.revokeObjectURL(url);

    }

    // ==================================================
    // LIVE CAMERA SYSTEM
    // ==================================================

    // ----------------------------------------------
    // ENABLE CAMERA
    // ----------------------------------------------

    if (enableCameraBtn) {

        enableCameraBtn.addEventListener(
            "click",
            enableCamera
        );

    }

    async function enableCamera() {

        try {

            if (!navigator.mediaDevices ||
                !navigator.mediaDevices.getUserMedia) {

                throw new Error(
                    "Camera access is unavailable. Use localhost or HTTPS."
                );
            }

            cameraStream = await navigator.mediaDevices.getUserMedia({

                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: "user"
                },

                audio: false

            });

            webcam.srcObject = cameraStream;

            await webcam.play();

            if (cameraPlaceholder) {
                cameraPlaceholder.style.display = "none";
            }

            if (cameraOverlay) {
                cameraOverlay.width = webcam.videoWidth;
                cameraOverlay.height = webcam.videoHeight;
            }

            setCameraStatus("Camera connected");

            showMessage(
                "Camera ready. You can now start live tracking."
            );

            enableCameraBtn.disabled = true;

            if (startLiveBtn) {
                startLiveBtn.disabled = false;
            }

        } catch (error) {

            console.error("Camera error:", error);

            showMessage(
                "Camera error: " + error.message
            );

            setCameraStatus("Camera unavailable");

        }

    }

    // ----------------------------------------------
    // START LIVE TRACKING
    // ----------------------------------------------

    if (startLiveBtn) {

        startLiveBtn.addEventListener(
            "click",
            startLiveTracking
        );

    }

    async function startLiveTracking() {

        if (!cameraStream) {

            showMessage(
                "Enable the camera before starting tracking."
            );

            return;
        }

        try {

            startLiveBtn.disabled = true;

            showMessage("Creating live session...");

            const response = await fetch(
                "/api/sessions",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        name: sessionName
                            ? sessionName.value || "Live Classroom"
                            : "Live Classroom"
                    })
                }
            );

            const data = await readResponse(response);

            liveSessionId = data.session_id;

            if (!liveSessionId) {
                throw new Error("Server did not return a session ID.");
            }

            knownParticipants.clear();

            setText(liveFaceCount, "0");
            setText(liveParticipants, "0");

            setCameraStatus("Live tracking active");

            showMessage(
                "Tracking faces. Temporary IDs will appear as faces are detected."
            );

            if (stopLiveBtn) {
                stopLiveBtn.disabled = false;
            }

            trackingTimer = setInterval(
                processCameraFrame,
                500
            );

        } catch (error) {

            console.error("Start tracking error:", error);

            showMessage(
                "Could not start live tracking: " + error.message
            );

            startLiveBtn.disabled = false;

        }

    }

    // ----------------------------------------------
    // SEND CAMERA FRAME TO FLASK
    // ----------------------------------------------

    async function processCameraFrame() {

        if (
            !liveSessionId ||
            !cameraStream ||
            trackingBusy
        ) {
            return;
        }

        if (!webcam.videoWidth || !webcam.videoHeight) {
            return;
        }

        trackingBusy = true;

        try {

            const canvas = document.createElement("canvas");

            canvas.width = webcam.videoWidth;
            canvas.height = webcam.videoHeight;

            const context = canvas.getContext("2d");

            context.drawImage(
                webcam,
                0,
                0,
                canvas.width,
                canvas.height
            );

            const blob = await new Promise((resolve) => {

                canvas.toBlob(
                    resolve,
                    "image/jpeg",
                    0.75
                );

            });

            if (!blob) {
                throw new Error("Could not capture camera frame.");
            }

            const formData = new FormData();

            formData.append(
                "frame",
                blob,
                "frame.jpg"
            );

            const response = await fetch(
                `/api/sessions/${encodeURIComponent(liveSessionId)}/frame`,
                {
                    method: "POST",
                    body: formData
                }
            );

            const data = await readResponse(response);

            setText(
                liveFaceCount,
                data.count ?? 0
            );

            const faces = data.faces || [];

            faces.forEach((face) => {

                if (face.participant_id) {
                    knownParticipants.add(face.participant_id);
                }

            });

            setText(
                liveParticipants,
                knownParticipants.size
            );

            drawFaceBoxes(
                faces,
                data.frame_width,
                data.frame_height
            );

        } catch (error) {

            console.error("Frame processing error:", error);

            showMessage(
                "Tracking error: " + error.message
            );

            // Stop repeated requests if the server reports
            // that the session no longer exists.
            if (error.message.includes("not found")) {
                clearInterval(trackingTimer);
                trackingTimer = null;
                liveSessionId = null;

                if (startLiveBtn) {
                    startLiveBtn.disabled = false;
                }

                if (stopLiveBtn) {
                    stopLiveBtn.disabled = true;
                }
            }

        } finally {

            trackingBusy = false;

        }

    }

    // ----------------------------------------------
    // DRAW FACE BOXES
    // ----------------------------------------------

    function drawFaceBoxes(
        faces,
        frameWidth,
        frameHeight
    ) {

        if (!cameraOverlay || !webcam) {
            return;
        }

        const context = cameraOverlay.getContext("2d");

        const width = webcam.videoWidth;
        const height = webcam.videoHeight;

        if (!width || !height) {
            return;
        }

        cameraOverlay.width = width;
        cameraOverlay.height = height;

        context.clearRect(
            0,
            0,
            width,
            height
        );

        const scaleX = frameWidth
            ? width / frameWidth
            : 1;

        const scaleY = frameHeight
            ? height / frameHeight
            : 1;

        faces.forEach((face) => {

            const box = face.box;

            if (!box || box.length !== 4) {
                return;
            }

            const x = box[0] * scaleX;
            const y = box[1] * scaleY;
            const w = box[2] * scaleX;
            const h = box[3] * scaleY;

            context.strokeStyle = "#20e3b2";
            context.lineWidth = 3;

            context.strokeRect(
                x,
                y,
                w,
                h
            );

            context.fillStyle = "#20e3b2";

            context.font = "bold 15px Arial";

            context.fillText(
                face.participant_id,
                x,
                Math.max(16, y - 7)
            );

        });

    }

    // ----------------------------------------------
    // STOP LIVE TRACKING AND GENERATE REPORT
    // ----------------------------------------------

    if (stopLiveBtn) {

        stopLiveBtn.addEventListener(
            "click",
            stopLiveTracking
        );

        stopLiveBtn.disabled = true;

    }

    async function stopLiveTracking() {

        if (!liveSessionId) {
            showMessage("No active live session.");
            return;
        }

        const sessionToEnd = liveSessionId;

        if (trackingTimer) {
            clearInterval(trackingTimer);
            trackingTimer = null;
        }

        if (startLiveBtn) {
            startLiveBtn.disabled = true;
        }

        if (stopLiveBtn) {
            stopLiveBtn.disabled = true;
        }

        setCameraStatus("Generating report...");

        showMessage(
            "Finishing session and preparing your report..."
        );

        try {

            // Wait for an already-running frame request to finish.
            while (trackingBusy) {
                await new Promise((resolve) => {
                    setTimeout(resolve, 100);
                });
            }

            const response = await fetch(
                `/api/sessions/${encodeURIComponent(sessionToEnd)}/end`,
                {
                    method: "POST"
                }
            );

            const report = await readResponse(response);

            liveSessionId = null;

            showLiveReport(report);

            setCameraStatus("Session completed");

            showMessage(
                "Your live session report is ready."
            );

        } catch (error) {

            console.error("Stop tracking error:", error);

            showMessage(
                "Could not generate report: " + error.message
            );

            liveSessionId = null;

            setCameraStatus("Session ended with an error");

        } finally {

            if (startLiveBtn) {
                startLiveBtn.disabled = !cameraStream;
            }

            if (stopLiveBtn) {
                stopLiveBtn.disabled = true;
            }

            clearFaceBoxes();

        }

    }

    // ----------------------------------------------
    // LIVE REPORT DISPLAY
    // ----------------------------------------------

    function showLiveReport(report) {

        if (!liveReport) {
            alert(
                "Report generated, but the liveReport section " +
                "is missing from index.html."
            );
            return;
        }

        liveReport.hidden = false;

        setText(
            document.getElementById("reportSessionName"),
            report.session_name
        );

        const minutes = Math.floor(
            report.duration_seconds / 60
        );

        const seconds = Math.round(
            report.duration_seconds % 60
        );

        setText(
            document.getElementById("reportDuration"),
            `${minutes}m ${seconds}s`
        );

        setText(
            document.getElementById("reportPeak"),
            report.peak_faces
        );

        setText(
            document.getElementById("reportParticipants"),
            report.unique_temporary_ids
        );

        // Participant list
        const participantList = document.getElementById(
            "reportParticipantList"
        );

        if (participantList) {

            participantList.replaceChildren();

            if (!report.participants.length) {

                participantList.textContent =
                    "No faces were detected during this session.";

            } else {

                report.participants.forEach((participant) => {

                    const row = document.createElement("p");

                    row.textContent =
                        `${participant.participant_id} — ` +
                        `${participant.detected_seconds.toFixed(1)} ` +
                        `seconds detected — ` +
                        `${participant.detections} frame detections`;

                    participantList.appendChild(row);

                });

            }

        }

        // Detection timeline
        const timeline = document.getElementById(
            "reportTimeline"
        );

        if (timeline) {

            timeline.replaceChildren();

            report.timeline.forEach((entry) => {

                const row = document.createElement("p");

                row.textContent =
                    `${entry.elapsed_seconds}s — ` +
                    `${entry.face_count} faces detected`;

                timeline.appendChild(row);

            });

            if (!report.timeline.length) {
                timeline.textContent =
                    "No timeline samples were recorded.";
            }

        }

        setText(
            document.getElementById("reportNote"),
            report.note
        );

        const downloadButton = document.getElementById(
            "downloadLiveReport"
        );

        if (downloadButton) {

            downloadButton.onclick = () => {

                window.location.href =
                    `/api/reports/${encodeURIComponent(report.report_id)}/csv`;

            };

        }

        liveReport.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }

    // ----------------------------------------------
    // CLEAR FACE BOXES
    // ----------------------------------------------

    function clearFaceBoxes() {

        if (!cameraOverlay) {
            return;
        }

        const context = cameraOverlay.getContext("2d");

        context.clearRect(
            0,
            0,
            cameraOverlay.width,
            cameraOverlay.height
        );

    }

    // ----------------------------------------------
    // CAMERA CLEANUP
    // ----------------------------------------------

    // Stop camera tracks when the page is closed.
    window.addEventListener("beforeunload", () => {

        if (trackingTimer) {
            clearInterval(trackingTimer);
        }

        if (cameraStream) {

            cameraStream.getTracks().forEach((track) => {
                track.stop();
            });

        }

    });

});
