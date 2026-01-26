import librosa
import numpy as np

def analyze_audio_advanced(audio_file, baseline_pitch=None):
    """
    V2.0 核心算法：增加了噪声检测(嘶吼)和相对音高分析
    """
    try:
        y, sr = librosa.load(audio_file, sr=None)
        
        # 1. 基础特征
        duration = librosa.get_duration(y=y, sr=sr)
        rms = np.mean(librosa.feature.rms(y=y)) # 能量/音量
        
        # 2. 音高提取 (F0)
        f0, voiced_flag, voiced_probs = librosa.pyin(y, fmin=150, fmax=2000, sr=sr)
        valid_f0 = f0[~np.isnan(f0)]
        
        if len(valid_f0) == 0:
            return {"status": "error", "msg": "未检测到有效猫叫"}

        mean_pitch = np.mean(valid_f0)
        
        # 3. 趋势分析 (升降调)
        x = np.arange(len(valid_f0))
        if len(x) > 1:
            slope = np.polyfit(x, valid_f0, 1)[0]
        else:
            slope = 0
            
        if slope > 0.5: trend = "Rising ↗"
        elif slope < -0.5: trend = "Falling ↘"
        else: trend = "Flat →"

        # 4. 异常检测：频谱平坦度 (检测嘶吼/哈气/呼噜)
        # 纯净的喵声平坦度低，嘶吼/哈气(噪音)平坦度高
        flatness = np.mean(librosa.feature.spectral_flatness(y=y))
        is_rough = flatness > 0.15 # 阈值需实测微调
        
        # 5. 基准线对比 (Delta Analysis)
        pitch_delta = 0
        if baseline_pitch:
            pitch_delta = mean_pitch - baseline_pitch

        return {
            "status": "success",
            "duration": round(duration, 2),
            "mean_pitch": int(mean_pitch),
            "pitch_trend": trend,
            "energy": round(rms, 3),
            "is_rough": is_rough, # 是否嘶吼/哈气
            "pitch_delta": int(pitch_delta),
            "raw_f0": valid_f0
        }
            
    except Exception as e:
        return {"status": "error", "msg": str(e)}