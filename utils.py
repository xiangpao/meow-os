import librosa
import numpy as np
import os
from moviepy.editor import VideoFileClip

def extract_audio_from_video(video_path, output_audio_path="temp_audio.wav"):
    """
    从视频中提取音频轨道
    """
    try:
        video = VideoFileClip(video_path)
        if video.audio is None:
            return False # 视频没有声音
        
        # 写入临时音频文件
        video.audio.write_audiofile(output_audio_path, logger=None)
        video.close()
        return True
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return False

def analyze_audio_advanced(audio_file, baseline_pitch=None):
    """
    核心声学算法 (增强版：支持 m4a, 增加鲁棒性)
    """
    try:
        # 1. 加载音频 (增加异常捕获，防止 m4a 崩溃)
        try:
            # sr=None 保持原始采样率
            y, sr = librosa.load(audio_file, sr=None)
        except Exception as load_err:
            return {"status": "error", "msg": f"格式解析失败: {str(load_err)}。请尝试标准 WAV/MP3。"}

        # 2. 基础特征
        duration = librosa.get_duration(y=y, sr=sr)
        if duration < 0.1: 
            return {"status": "error", "msg": "声音太短，无法分析。"}

        rms = np.mean(librosa.feature.rms(y=y))
        
        # 3. F0 提取 (使用 PyIN 算法)
        f0, voiced_flag, voiced_probs = librosa.pyin(y, fmin=150, fmax=2000, sr=sr)
        valid_f0 = f0[~np.isnan(f0)]
        
        if len(valid_f0) == 0:
            return {"status": "error", "msg": "未检测到清晰的猫叫声(可能是噪音或频率超出范围)。"}

        mean_pitch = np.mean(valid_f0)
        
        # 4. 趋势分析
        x = np.arange(len(valid_f0))
        slope = 0
        if len(x) > 1: 
            slope = np.polyfit(x, valid_f0, 1)[0]
            
        if slope > 0.5: trend = "Rising ↗ (请求/疑问)"
        elif slope < -0.5: trend = "Falling ↘ (拒绝/陈述)"
        else: trend = "Flat → (呼唤)"

        # 5. 粗糙度 (检测嘶吼)
        flatness = np.mean(librosa.feature.spectral_flatness(y=y))
        is_rough = flatness > 0.15 
        
        # 6. 基准线对比
        pitch_delta = 0
        if baseline_pitch: 
            pitch_delta = mean_pitch - baseline_pitch

        return {
            "status": "success",
            "duration": round(duration, 2),
            "mean_pitch": int(mean_pitch),
            "pitch_trend": trend,
            "is_rough": is_rough,
            "pitch_delta": int(pitch_delta),
            "raw_f0": valid_f0
        }
            
    except Exception as e:
        return {"status": "error", "msg": f"系统错误: {str(e)}"}
