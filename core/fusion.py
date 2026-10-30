from core.vision import analyze_video
from core.audio import analyze_audio
from core.insights import generate_temporal_insights

def process_session(filepath):
    # Epic 6: Timestamp-based Data Fusion
    vision_data = analyze_video(filepath)
    duration_sec = vision_data['duration']
    vision_series = vision_data['vision_series']
    
    # Pass duration to synchronize audio segmentation perfectly
    audio_series = analyze_audio(filepath, duration_sec)
    
    fused_timeline = []
    total_presence_sec = 0
    
    # Epic 7: Temporal Engagement Scoring (Rule-based rules applied per second)
    for i in range(len(vision_series)):
        v = vision_series[i]
        a = audio_series[i] if i < len(audio_series) else {"noise_db": 30, "speech_active": 0}
        
        # Rules: visual presence is baseline. Speech/Movement add bonuses. High noise distracts.
        presence_score = v['presence_ratio'] * 60
        movement_bonus = v['movement_intensity'] * 15
        speech_bonus = a['speech_active'] * 25
        
        eng_score = presence_score + movement_bonus + speech_bonus
        if a['noise_db'] > 75: eng_score -= 10 # Penalty for excessive noise
        eng_score = min(max(eng_score, 0), 100)
        
        if v['presence_ratio'] > 0.3:
            total_presence_sec += 1
            
        fused_timeline.append({
            "time_sec": v['time_sec'],
            "presence_ratio": round(v['presence_ratio'], 2),
            "movement": round(v['movement_intensity'], 2),
            "noise_db": a['noise_db'],
            "speech_active": a['speech_active'],
            "engagement_score": round(eng_score, 1)
        })
        
    # Epic 3 completion: Sustained presence threshold
    is_present = total_presence_sec > (duration_sec * 0.2) # Minimum duration threshold
    avg_score = sum(t['engagement_score'] for t in fused_timeline) / len(fused_timeline) if fused_timeline else 0
    
    final_data = {
        "duration": duration_sec,
        "total_presence_sec": total_presence_sec,
        "is_present": is_present,
        "average_engagement": round(avg_score, 2),
        "timeline": fused_timeline
    }
    
    # Generate insights based on the temporal data
    insights = generate_temporal_insights(final_data)
    final_data["instructor_suggestions"] = insights["instructor"]
    final_data["student_analytics"] = insights["student"]
    
    return final_data
