import cv2
import numpy as np

class FaceTracker:
    def __init__(self):
        self.next_id = 1
        self.objects = {} # id: (cx, cy)
        
    def update(self, rects):
        current_centroids = [(x + w//2, y + h//2) for (x, y, w, h) in rects]
        
        if len(self.objects) == 0:
            for pt in current_centroids:
                self.objects[self.next_id] = pt
                self.next_id += 1
        else:
            new_objects = {}
            used_centroids = set()
            
            for obj_id, old_pt in self.objects.items():
                best_dist = 9999
                best_idx = -1
                for i, pt in enumerate(current_centroids):
                    if i in used_centroids: continue
                    d = ((old_pt[0]-pt[0])**2 + (old_pt[1]-pt[1])**2)**0.5
                    if d < best_dist and d < 75: # Tracking threshold
                        best_dist = d
                        best_idx = i
                if best_idx != -1:
                    new_objects[obj_id] = current_centroids[best_idx]
                    used_centroids.add(best_idx)
                    
            for i, pt in enumerate(current_centroids):
                if i not in used_centroids:
                    new_objects[self.next_id] = pt
                    self.next_id += 1
            self.objects = new_objects
        return self.objects

def analyze_video(filepath):
    # Epic 2: Face Detection, Tracking (Unique IDs) & Epic 3: Sustained Presence Logic
    cap = cv2.VideoCapture(filepath)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0 or np.isnan(fps): fps = 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps if fps > 0 else 0
    
    tracker = FaceTracker()
    time_series = []
    current_sec = 0
    frames_in_sec = 0
    
    sec_faces_detected = 0
    sec_movement = 0
    prev_centroids = {}
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        # Update Unique ID tracker
        tracked_objects = tracker.update(faces)
        if len(tracked_objects) > 0:
            sec_faces_detected += 1
            
        # Calculate movement based on ID shift
        for obj_id, pt in tracked_objects.items():
            if obj_id in prev_centroids:
                old_pt = prev_centroids[obj_id]
                dist = np.sqrt((pt[0]-old_pt[0])**2 + (pt[1]-old_pt[1])**2)
                if dist > 3: sec_movement += 1
        prev_centroids = tracked_objects.copy()
        
        frames_in_sec += 1
        if frames_in_sec >= int(fps):
            # Aggregate per second for timestamp fusion
            time_series.append({
                "time_sec": current_sec,
                "presence_ratio": min(sec_faces_detected / fps, 1.0),
                "movement_intensity": min(sec_movement / fps, 1.0)
            })
            current_sec += 1
            frames_in_sec = 0
            sec_faces_detected = 0
            sec_movement = 0
            
    cap.release()
    
    # Fill remaining seconds
    while len(time_series) < int(duration_sec):
        time_series.append({"time_sec": len(time_series), "presence_ratio": 0, "movement_intensity": 0})
        
    return {
        "duration": round(duration_sec, 2),
        "vision_series": time_series
    }
