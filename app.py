import streamlit as st
import google.generativeai as genai
import os
import time
import tempfile
from PIL import Image
from utils import analyze_audio_advanced, extract_audio_from_video

# --- 0. 系统配置 ---
st.set_page_config(page_title="MeowOS 📱", page_icon="🐾", layout="centered", initial_sidebar_state="collapsed")

# ⚠️ 云端部署：必须确保没有设置 Proxy，否则连不上 Google
if "HTTP_PROXY" in os.environ: del os.environ["HTTP_PROXY"]
if "HTTPS_PROXY" in os.environ: del os.environ["HTTPS_PROXY"]

if 'baseline_pitch' not in st.session_state:
    st.session_state['baseline_pitch'] = None

# --- 1. CSS 移动端深度适配 ---
st.markdown("""
<style>
    .stApp { background-color: #FFF8E7; color: #5D4037; }
    
    /* 标题与字体优化 */
    h1 { font-size: 1.8rem !important; text-align: center; color: #6F4E37; }
    p { font-size: 1.1rem; }
    
    /* 按钮样式：大圆角，适合手指点击 */
    .stButton>button {
        width: 100%;
        background-color: #D2691E;
        color: white;
        border-radius: 25px;
        height: 55px;
        font-size: 18px;
        font-weight: bold;
        border: none;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
        margin-top: 10px;
    }
    .stButton>button:active { transform: scale(0.98); background-color: #A0522D; }

    /* Tab 标签页样式 */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        flex: 1; /* 让Tab等宽 */
        background-color: #F5E6D3;
        border-radius: 12px;
        color: #5D4037;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF;
        border: 2px solid #D2691E;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 顶部设置折叠区 ---
with st.expander("⚙️ 环境设置与校准 (点此展开)", expanded=False):
    st.caption("选择当前场景有助于 AI 做出更精准的判断。")
    context = st.selectbox(
        "📍 当前场景",
        ["🍽️ 饭点/厨房", "🚪 门窗/阻隔", "🛋️ 互动/撸猫", "🌙 深夜", "🏥 陌生/就医", "🦋 狩猎模式"]
    )
    
    c1, c2 = st.columns(2)
    with c1:
        if st.session_state['baseline_pitch']: st.success(f"基准: {st.session_state['baseline_pitch']}Hz")
        else: st.info("未校准")
    with c2:
        if st.button("清除校准"):
            st.session_state['baseline_pitch'] = None
            st.rerun()

# --- 3. 核心功能区 ---
st.title("🐾 MeowOS 全能版")

# 连接 AI
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    ai_ready = True
except:
    st.warning("⚠️ AI 离线 (仅本地模式)")
    ai_ready = False

# 模式切换
tab1, tab2 = st.tabs(["🎙️ 录音模式", "📹 录像模式"])

# ================= Tab 1: 录音 (经典) =================
with tab1:
    st.markdown("### 1. 采集信号")
    # 支持 wav, mp3, m4a 等格式
    audio_file = st.file_uploader("点击录制或上传音频", type=["wav", "mp3", "m4a", "aac"], key="audio_up")
    
    st.markdown("### 2. 视觉辅助 (可选)")
    # 隐藏式摄像头，点击展开
    with st.expander("📷 开启摄像头拍照", expanded=False):
        img_cam = st.camera_input("拍摄猫咪")
    img_up = st.file_uploader("或上传照片", type=["jpg", "png"], label_visibility="collapsed")
    img_final = img_cam if img_cam else img_up

    if st.button("开始分析 (音频) 🐾", key="btn_audio"):
        if not audio_file:
            st.error("请先上传声音！")
        else:
            with st.spinner("正在解码声波..."):
                data = analyze_audio_advanced(audio_file, st.session_state['baseline_pitch'])
                
                if data['status'] == 'error':
                    st.error(f"❌ 分析失败: {data['msg']}")
                else:
                    # AI 分析
                    ai_msg = ""
                    if ai_ready:
                        try:
                            prompt = f"环境：{context}。声学数据：{data}。请以猫的第一人称傲娇地翻译心声。"
                            inputs = [prompt]
                            if img_final: inputs.append(Image.open(img_final))
                            ai_msg = model.generate_content(inputs).text
                        except Exception as e: st.error(f"AI Error: {e}")

                    # 结果展示
                    st.success("✅ 完成")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("情绪", data['pitch_trend'].split()[0])
                    c2.metric("时长", f"{data['duration']}s")
                    c3.metric("音高", f"{data['mean_pitch']}Hz")
                    
                    if ai_msg: st.info(ai_msg)
                    else: st.info(f"本地推断: {data['pitch_trend']}")
                    
                    if st.button("🎯 设为基准音高"):
                        st.session_state['baseline_pitch'] = data['mean_pitch']
                        st.toast("校准成功！")
                        time.sleep(1)

# ================= Tab 2: 录像模式 =================
with tab2:
    st.info("💡 提示：点击下方按钮后，手机通常会弹出 **“录制”** 或 **“从相册选择”** 两个选项。")
    
    # 优化文案，明确告知用户支持相册
    video_file = st.file_uploader(
        "📹 点击此处 -> 选择“录像”或“图库”", 
        type=["mp4", "mov", "avi", "m4v"], # 增加了 m4v 格式支持
        key="video_up"
    )

    if st.button("开始分析 (视频) 🎬", key="btn_video"):
        if not video_file:
            st.error("请先录制或上传视频！")
        else:
            with st.spinner("⏳ 正在分离音轨并进行多模态分析..."):
                # 创建临时文件处理视频
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                tfile.write(video_file.read())
                video_path = tfile.name
                audio_path = video_path.replace(".mp4", ".wav")
                
                # 提取音频
                has_audio = extract_audio_from_video(video_path, audio_path)
                
                if not has_audio:
                    st.error("❌ 无法从视频中提取声音！")
                else:
                    # 声学分析
                    data = analyze_audio_advanced(audio_path, st.session_state['baseline_pitch'])
                    
                    if data['status'] == 'error':
                        st.warning(f"⚠️ 视频中有声音，但没检测到猫叫: {data['msg']}")
                        st.caption("AI 将仅基于视觉进行分析...")
                        # 给一个兜底数据防止 AI 报错
                        data = {"pitch_trend": "未知", "mean_pitch": 0, "is_rough": False, "duration": 0}
                    
                    # Gemini 视频分析
                    ai_msg = ""
                    if ai_ready:
                        try:
                            # 上传视频到 Gemini 缓存
                            video_blob = genai.upload_file(video_path)
                            while video_blob.state.name == "PROCESSING":
                                time.sleep(1)
                                video_blob = genai.get_file(video_blob.name)

                            prompt = f"""
                            分析这个猫的视频。
                            声学辅助数据：{data} (若包含'error'则忽略声学)。
                            环境：{context}。
                            请结合猫的动作(尾巴/耳朵)和叫声(如果有)，用第一人称翻译。
                            """
                            response = model.generate_content([prompt, video_blob])
                            ai_msg = response.text
                        except Exception as e:
                            st.error(f"AI 分析超时: {e}")

                    st.success("✅ 多模态分析完成")
                    st.video(video_file) # 回显视频
                    
                    if ai_msg:
                        st.markdown("### 🐱 猫咪心声 (视频版)")
                        st.info(ai_msg)

                # 清理垃圾
                try:
                    os.remove(video_path)
                    os.remove(audio_path)
                except: pass

