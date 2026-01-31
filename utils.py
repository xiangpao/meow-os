import librosa
import librosa.display
import numpy as np
import os
import tempfile
import matplotlib.pyplot as plt
from moviepy.editor import VideoFileClip

# [新增] 设置 matplotlib 后端为非交互式，防止 Streamlit 报错
plt.switch_backend('Agg')

def extract_audio_from_video(video_path, output_audio_path="temp_audio.wav"):
    """
    从视频中提取音频轨道 (保留原功能)
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

def plot_waveform(audio_file):
    """
    [新增] 绘制声纹波形图，配合“拿铁风”配色
    """
    try:
        # 加载音频
        y, sr = librosa.load(audio_file, sr=None)
        
        # 创建画布 (尺寸适中)
        fig, ax = plt.subplots(figsize=(6, 2))
        
        # 设置背景色与 App 统一 (米色)
        fig.patch.set_facecolor('#FFFDF7') 
        ax.set_facecolor('#FFFDF7')
        
        # 绘制波形 (使用焦糖色 #D2691E)
        librosa.display.waveshow(y, sr=sr, ax=ax, color='#D2691E', alpha=0.8)
        
        # 去除坐标轴，只保留波形美感
        ax.axis('off')
        plt.tight_layout()
        
        return fig
    except Exception as e:
        print(f"Plot error: {e}")
        return None

def analyze_audio_advanced(audio_file, baseline_pitch=None):
    """
    V17.0 核心算法：保留了 m4a 兼容逻辑，增加了绘图输出
    """
    temp_path = None
    try:
        # --- 1. 临时文件处理 (保留原逻辑，确保 m4a 不报错) ---
        suffix = os.path.splitext(audio_file.name)[1] if hasattr(audio_file, 'name') else ".tmp"
        if not suffix: suffix = ".tmp"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_file.getvalue())
            temp_path = tmp.name

        # --- 2. 加载音频 ---
        try:
            y, sr = librosa.load(temp_path, sr=None)
        except Exception as load_err:
            return {"status": "error", "msg": f"格式解析失败: {str(load_err)}"}

        # --- 3. 基础特征 ---
        duration = librosa.get_duration(y=y, sr=sr)
        if duration < 0.1: 
            return {"status": "error", "msg": "声音太短，无法分析。"}

        # --- 4. F0 提取 ---
        f0, voiced_flag, voiced_probs = librosa.pyin(y, fmin=150, fmax=2000, sr=sr)
        valid_f0 = f0[~np.isnan(f0)]
        
        if len(valid_f0) == 0:
            return {"status": "error", "msg": "未检测到清晰的猫叫声。"}

        mean_pitch = np.mean(valid_f0)
        
        # --- 5. 趋势分析 ---
        x = np.arange(len(valid_f0))
        slope = 0
        if len(x) > 1: 
            slope = np.polyfit(x, valid_f0, 1)[0]
            
        if slope > 0.5: trend = "Rising ↗ (请求)"
        elif slope < -0.5: trend = "Falling ↘ (拒绝)"
        else: trend = "Flat → (陈述)"

        # --- 6. 粗糙度 ---
        flatness = np.mean(librosa.feature.spectral_flatness(y=y))
        is_rough = flatness > 0.15 
        
        # --- 7. 基准线对比 ---
        pitch_delta = 0
        if baseline_pitch: 
            pitch_delta = mean_pitch - baseline_pitch

        # --- [新增] 8. 生成波形图 ---
        # 传入临时文件路径进行绘图
        waveform_fig = plot_waveform(temp_path)

        result = {
            "status": "success",
            "duration": round(duration, 2),
            "mean_pitch": int(mean_pitch),
            "pitch_trend": trend,
            "is_rough": is_rough,
            "pitch_delta": int(pitch_delta),
            "raw_f0": valid_f0,
            "waveform_fig": waveform_fig  # 将图片对象打包返回
        }
        
        return result
            
    except Exception as e:
        return {"status": "error", "msg": f"系统错误: {str(e)}"}
    finally:
        # 清理临时文件 (保留原逻辑)
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
