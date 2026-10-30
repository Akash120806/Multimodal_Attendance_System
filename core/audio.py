import wave
import numpy as np
import os

def analyze_audio(filepath, duration_sec):
    # Epic 4: Audio Extraction & Segmenting. Epic 5: Energy, Amplitude, Speech Detection.
    try:
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(filepath)
        if clip.audio is None:
            raise ValueError("No audio track in video.")
            
        wav_path = filepath + "_temp.wav"
        # Extract audio waveform using moviepy wrapper
        clip.audio.write_audiofile(wav_path, fps=16000, nbytes=2, codec='pcm_s16le', verbose=False, logger=None)
        
        with wave.open(wav_path, 'rb') as wf:
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            audio_data = wf.readframes(nframes)
            
        os.remove(wav_path)
        clip.close()
        
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        chunk_size = framerate # 1-second fixed windows
        
        audio_series = []
        for i in range(int(duration_sec)):
            start = i * chunk_size
            end = start + chunk_size
            chunk = audio_np[start:end]
            
            if len(chunk) > 0:
                # Compute RMS Energy and Amplitude variations
                rms = np.sqrt(np.mean(chunk.astype(np.float64)**2))
                db = 20 * np.log10(rms + 1e-5)
                # Map to pseudo-decibel scale (30-90 dB for classroom ambiance)
                mapped_db = min(max((db - 40) * 1.5, 30), 90) 
                speech_active = 1 if mapped_db > 55 else 0
            else:
                mapped_db = 30
                speech_active = 0
                
            audio_series.append({
                "time_sec": i,
                "noise_db": round(mapped_db, 2),
                "speech_active": speech_active
            })
            
        return audio_series
        
    except Exception as e:
        print(f"Audio processing fallback: {e}")
        # Fallback if no audio track exists
        return [{"time_sec": i, "noise_db": 35.0, "speech_active": 0} for i in range(int(duration_sec))]
