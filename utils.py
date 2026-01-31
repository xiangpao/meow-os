import librosa
import numpy as np
import os
import tempfile
import shutil
from moviepy.editor import VideoFileClip

def extract_audio_from_video(video_path, output_audio_path="temp_audio.wav"):
    """
    从视频中提取音频轨道
    """
    try:
        video = VideoFileClip(video_path)
        if video.audio is None:
            return False 
        video.audio.write_audiofile(output_audio_path, logger=None)
        video.close()
        return True
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return False

def analyze_audio_advanced(audio_file, baseline_pitch=None):
    """
    V8.0 核心算法：使用临时文件中转，完美支持 m4a/aac 等所有格式
    """
    temp_path = None
    try:
        # 1. 将上传的内存文件写入硬盘临时文件
        # 获取文件后缀 (例如 .m4a)
        suffix = os.path.splitext(audio_file.name)[1] if hasattr(audio_file, 'name') else ".tmp"
        if not suffix: suffix = ".tmp"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_file.getvalue())
            temp_path = tmp.name

        # 2. 加载音频 (此时 librosa 读取的是真实路径，ffmpeg 就能正常工作了)
        try:
            y, sr = librosa.load(temp_path, sr=None)
        except Exception as load_err:
            return {"status": "error", "msg": f"格式解析失败: {str(load_err)}。"}

        # 3. 基础特征
        duration = librosa.get_duration(y=y, sr=sr)
        if duration < 0.1: 
            return {"status": "error", "msg": "声音太短，无法分析。"}

        rms = np.mean(librosa.feature.rms(y=y))
        
        # 4. F0 提取
        f0, voiced_flag, voiced_probs = librosa.pyin(y, fmin=150, fmax=2000, sr=sr)
        valid_f0 = f0[~np.isnan(f0)]
        
        if len(valid_f0) == 0:
            return {"status": "error", "msg": "未检测到清晰的猫叫声。"}

        mean_pitch = np.mean(valid_f0)
        
        # 5. 趋势分析
        x = np.arange(len(valid_f0))
        slope = 0
        if len(x) > 1: 
            slope = np.polyfit(x, valid_f0, 1)[0]
            
        if slope > 0.5: trend = "Rising ↗"
        elif slope < -0.5: trend = "Falling ↘"
        else: trend = "Flat →"

        # 6. 粗糙度
        flatness = np.mean(librosa.feature.spectral_flatness(y=y))
        is_rough = flatness > 0.15 
        
        # 7. 基准线对比
        pitch_delta = 0
        if baseline_pitch: 
            pitch_delta = mean_pitch - baseline_pitch

        result = {
            "status": "success",
            "duration": round(duration, 2),
            "mean_pitch": int(mean_pitch),
            "pitch_trend": trend,
            "is_rough": is_rough,
            "pitch_delta": int(pitch_delta),
            "raw_f0": valid_f0
        }
        
        return result
            
    except Exception as e:
        return {"status": "error", "msg": f"系统错误: {str(e)}"}
    finally:
        # 清理临时文件
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
