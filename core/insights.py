def generate_temporal_insights(fused_data):
    # Epic 8: Context-aware Instructor Suggestions & Epic 9: Student Analytics
    timeline = fused_data['timeline']
    instructor_suggestions = []
    
    # Detect temporal patterns (attention drops, peak interactions, sustained noise)
    consecutive_low_focus = 0
    consecutive_noise = 0
    
    for t in timeline:
        if t['engagement_score'] < 40:
            consecutive_low_focus += 1
        else:
            consecutive_low_focus = 0
            
        if t['noise_db'] > 70:
            consecutive_noise += 1
        else:
            consecutive_noise = 0
            
        # Trigger rules based on temporal accumulation
        if consecutive_low_focus == 5:
            timestamp = f"{t['time_sec'] // 60:02d}:{t['time_sec'] % 60:02d}"
            instructor_suggestions.append(f"Attention drop detected at {timestamp}. Consider introducing a quick interactive poll.")
            
        if consecutive_noise == 4:
            timestamp = f"{t['time_sec'] // 60:02d}:{t['time_sec'] % 60:02d}"
            instructor_suggestions.append(f"Sustained high noise at {timestamp}. A classroom management cue may be needed.")
            
    if not instructor_suggestions:
        instructor_suggestions.append("Engagement pacing looks optimal. No major attention drops detected.")
        
    # Reflective Student Analytics (Privacy Preserving, No grading/ranking)
    status = "Present" if fused_data['is_present'] else "Absent (Did not meet minimum sustained duration)"
    avg = fused_data['average_engagement']
    consistency = "High" if avg > 75 else ("Moderate" if avg > 50 else "Variable")
    
    student_analytics = {
        "status": status,
        "presence_time": f"{fused_data['total_presence_sec']} seconds logged",
        "focus_consistency": consistency,
        "summary": "Learner exhibited periods of focus and interaction matching the session pacing."
    }
    
    return {
        "instructor": instructor_suggestions,
        "student": student_analytics
    }
