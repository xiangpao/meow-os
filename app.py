import streamlit as st
import google.generativeai as genai
import os
import time
import tempfile
import base64
from PIL import Image
from utils import analyze_audio_advanced, extract_audio_from_video

# --- 0. 系统配置 ---
st.set_page_config(
    page_title="🐱 喵星电波台", 
    page_icon="📡", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

if "HTTP_PROXY" in os.environ: del os.environ["HTTP_PROXY"]
if "HTTPS_PROXY" in os.environ: del os.environ["HTTPS_PROXY"]

# --- 1. 记忆初始化 ---
if 'baseline_pitch' not in st.session_state:
    st.session_state['baseline_pitch'] = None

if 'latest_analysis' not in st.session_state:
    st.session_state['latest_analysis'] = None

# --- 2. CSS 拿铁风深度定制 ---
st.markdown("""
<style>
    /* 全局背景 */
    .stApp {
        background: linear-gradient(180deg, #FFFDF7 0%, #F5E6D3 100%);
        color: #4E342E;
    }
    h1 { 
        color: #5D4037 !important; 
        font-family: 'Comic Sans MS', 'ZKKuaiLe', '幼圆', sans-serif !important;
        font-weight: 800;
        text-shadow: 2px 2px 0px #FFF;
    }
    /* 图片容器 */
    .header-img {
        display: flex;
        justify_content: center;
        align-items: center;
        margin-bottom: 10px;
    }
    /* 卡片样式 */
    .stExpander, .css-1r6slb0, [data-testid="stFileUploadDropzone"], .stSelectbox > div > div {
        background-color: #FFFFFF !important;
        border-radius: 20px !important;
        border: 2px solid #EFEBE9 !important;
        box-shadow: 0 4px 12px rgba(93, 64, 55, 0.1) !important;
    }
    /* 按钮样式 */
    .stButton>button {
        width: 100%;
        background: linear-gradient(45deg, #D2691E, #8B4513);
        color: white;
        border-radius: 25px;
        height: 55px;
        font-size: 18px;
        font-weight: bold;
        border: none;
        box-shadow: 0 4px 10px rgba(139, 69, 19, 0.3);
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 15px rgba(139, 69, 19, 0.5);
        background: linear-gradient(45deg, #E67E22, #A0522D);
    }
    /* Tab 样式 */
    .stTabs [data-baseweb="tab"] {
        background-color: #F5E6D3;
        border-radius: 15px 15px 0 0;
        color: #5D4037;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF;
        border-top: 3px solid #D2691E;
        color: #D2691E;
    }
    p, label, .stMarkdown, li, .stCaption {
        color: #4E342E !important;
        font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
    }
    [data-testid="stFileUploadDropzone"] {
        border: 2px dashed #D7CCC8 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 资源定义 ---
# (1) 顶部 Logo：读取本地 logo.gif
def render_local_logo(width=200):
    if os.path.exists("logo.gif"):
        with open("logo.gif", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<div class="header-img"><img src="data:image/gif;base64,{b64}" width="{width}" style="border-radius:15px"></div>'
    else:
        # 兜底网络图
        return f'<div class="header-img"><img src="https://media.giphy.com/media/GeimqsH0TLDt4tScGw/giphy.gif" width="{width}"></div>'

# (2) 等待动画：打字猫链接
LOADING_GIF = "https://media.giphy.com/media/JIX9t2j0ZTN9S/giphy.gif"

def render_loading_gif(width=150):
    return f'<div class="header-img"><img src="{LOADING_GIF}" width="{width}" style="border-radius:15px"></div>'

# --- 4. 界面渲染 ---
# 顶部看板 (常驻)
st.markdown(render_local_logo(), unsafe_allow_html=True)
st.title("🐱 喵星电波台")
st.markdown("<p style='text-align: center; margin-top: -15px; color: #8D6E63;'><i>—— 接收来自 50Hz 频段的加密喵声 ——</i></p>", unsafe_allow_html=True)

# 科学原理
with st.expander("🔬 喵星发声学原理 (Science)", expanded=False):
    st.markdown("""
    **本台解码算法基于瑞典隆德大学 Susanne Schötz 教授的猫语旋律学研究：**
    * **🎵 升调 (Rising Pitch ↗)**: 类似人类的疑问句，通常代表**请求 (Soliciting)** 或 **友好的确认**。
    * **🎵 降调 (Falling Pitch ↘)**: 类似人类的陈述句，通常代表**拒绝**、**压力**或**自信的陈述**。
    * **⏳ 时长 (Duration)**: 
        * 短促音 (<0.5s): 社交问候 / 确认存在。
        * 长音 (>1.0s): 强烈需求 (我要吃!) / 抱怨 (放我出去!)。
    * **🌊 粗糙度 (Roughness)**: 声音嘶哑或带杂音，通常对应**防御**、**痛苦**或**极度亢奋**。
    """)

# 信号控制台
st.markdown("### 🎛️ 信号控制台")
scenario_options = [
    "🚫 请选择发射源 (必选)", "🍽️ 干饭时刻 (Food)", "🚪 门窗/受阻 (Barrier)", 
    "🛋️ 贴贴/求摸 (Affection)", "🏥 害怕/应激 (Stress)", 
    "🦋 猎杀时刻 (Hunting)", "😡 别挨老子 (Warning)", "🌙 深夜跑酷 (Night)"
]
context = st.selectbox("📍 1. 锁定信号发射源 (必选)", scenario_options, label_visibility="collapsed")

# 校准设置
with st.expander("⚙️ 高级设置：声纹校准", expanded=False):
    calib_file = st.file_uploader("上传校准录音", type=["wav", "mp3", "m4a", "aac"], key="cal_up", label_visibility="collapsed")
    if calib_file:
        if st.button("⚡ 设为基准"):
            with st.spinner("校准中..."):
                cal_data = analyze_audio_advanced(calib_file, baseline_pitch=None)
                if cal_data['status'] != 'error':
                    st.session_state['baseline_pitch'] = cal_data['mean_pitch']
                    st.success(f"✅ 已校准: {cal_data['mean_pitch']}Hz")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("校准失败")
    col_s, col_c = st.columns([3,1])
    with col_s:
        if st.session_state['baseline_pitch']: st.success(f"当前基准: {st.session_state['baseline_pitch']}Hz")
        else: st.info("尚未录入基准")
    with col_c:
        if st.button("清除"):
            st.session_state['baseline_pitch'] = None
            st.rerun()

# --- 连接云端 ---
ai_ready = False
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name='gemini-flash-latest',
            system_instruction="你是一只猫。用第一人称（'本喵'、'我'）。禁止解释。语气生动傲娇。根据场景和声音特征翻译心声。"
        )
        ai_ready = True
    else:
        st.error("⚠️ 密钥缺失")
except Exception:
    st.error("⚠️ AI 初始化失败")

# --- 5. 业务功能区 ---
st.markdown("### 📡 信号接收区")
tab1, tab2 = st.tabs(["🎙️ 语音解码", "📹 视频解码"])

# === Tab 1: 语音 ===
with tab1:
    audio_file = st.file_uploader("上传音频", type=["wav", "mp3", "m4a", "aac"], key="audio_up", label_visibility="collapsed")
    
    with st.expander("📷 (可选) 增加照片辅助", expanded=False):
        img_cam = st.camera_input("拍照")
        img_up = st.file_uploader("或上传图片", type=["jpg", "png"], key="img_up")
    img_final = img_cam if img_cam else img_up

    if st.button("📡 接收喵星电波", key="btn_audio"):
        if "🚫" in context:
            st.error("⚠️ 无法解码：请先在上方控制台选择【信号发射源】！")
        elif not audio_file:
            st.error("⚠️ 请先上传喵叫声！")
        else:
            # === 剧情模式加载 ===
            loading = st.empty()
            
            # 0% 阶段
            with loading.container():
                st.markdown(render_loading_gif(width=150), unsafe_allow_html=True)
                st.info("📡 正在连接喵星基站...")
                st.progress(0)
            time.sleep(0.5) # 增加微小延迟让用户看清文案

            # 30% 阶段
            with loading.container():
                st.markdown(render_loading_gif(width=150), unsafe_allow_html=True)
                st.info("📶 发现加密频率，正在握手...")
                st.progress(30)
            
            # 执行本地分析
            data = analyze_audio_advanced(audio_file, st.session_state['baseline_pitch'])
            
            if data['status'] == 'error':
                loading.empty()
                st.error(f"❌ 失败: {data['msg']}")
            else:
                # 60% 阶段
                with loading.container():
                    st.markdown(render_loading_gif(width=150), unsafe_allow_html=True)
                    st.info("🧠 AI 大脑正在疯狂运转...")
                    st.progress(60)

                ai_result = ""
                if ai_ready:
                    try:
                        prompt = f"场景：{context}。声学特征：{data}。翻译我的心声。"
                        inputs = [prompt]
                        if img_final: inputs.append(Image.open(img_final))
                        ai_result = model.generate_content(inputs).text
                    except: 
                        st.warning("云端信号弱，转为离线分析。")

                # 90% 阶段
                with loading.container():
                    st.markdown(render_loading_gif(width=150), unsafe_allow_html=True)
                    st.info("📩 翻译完成，准备发送！")
                    st.progress(90)
                time.sleep(0.5) # 增加微小延迟营造“发送”感

                loading.empty() # 清除等待动画

                st.success("✅ 电波接收成功")
                c1, c2, c3 = st.columns(3)
                c1.metric("情绪", data['pitch_trend'].split()[0])
                c2.metric("时长", f"{data['duration']}s")
                c3.metric("音高", f"{data['mean_pitch']}Hz")

                st.markdown("### 🐱 主子说：")
                if ai_result:
                    st.info(f"“ {ai_result} ”")
                else:
                    st.info(f"🤖 本地推断：这似乎是【{data['pitch_trend']}】的意思。")

# === Tab 2: 视频 ===
with tab2:
    video_file = st.file_uploader("上传视频", type=["mp4", "mov", "avi", "m4v"], key="video_up", label_visibility="collapsed")

    if st.button("📡 接收视频信号", key="btn_video"):
        if "🚫" in context:
            st.error("⚠️ 无法解码：请先在上方控制台选择【信号发射源】！")
        elif not video_file:
            st.error("⚠️ 请先上传视频！")
        else:
            loading = st.empty()
            
            # 0% 阶段
            with loading.container():
                st.markdown(render_loading_gif(width=150), unsafe_allow_html=True)
                st.info("📡 正在连接喵星基站...")
                st.progress(0)
            time.sleep(0.5)

            # 30% 阶段
            with loading.container():
                st.markdown(render_loading_gif(width=150), unsafe_allow_html=True)
                st.info("📶 发现加密频率，正在握手...")
                st.progress(30)

            tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            tfile.write(video_file.read())
            video_path = tfile.name
            audio_path = video_path.replace(".mp4", ".wav")
            
            has_audio = extract_audio_from_video(video_path, audio_path)
            
            if not has_audio:
                loading.empty()
                st.error("❌ 视频无声音")
            else:
                # 60% 阶段
                with loading.container():
                    st.markdown(render_loading_gif(width=150), unsafe_allow_html=True)
                    st.info("🧠 AI 大脑正在疯狂运转...")
                    st.progress(60)

                data = analyze_audio_advanced(audio_path, st.session_state['baseline_pitch'])
                ai_msg = ""
                if ai_ready:
                    try:
                        video_blob = genai.upload_file(video_path)
                        while video_blob.state.name == "PROCESSING":
                            time.sleep(1)
                            video_blob = genai.get_file(video_blob.name)
                        
                        prompt = f"场景：{context}。声音：{data}。翻译心声。"
                        response = model.generate_content([prompt, video_blob])
                        ai_msg = response.text
                    except: pass
                
                # 90% 阶段
                with loading.container():
                    st.markdown(render_loading_gif(width=150), unsafe_allow_html=True)
                    st.info("📩 翻译完成，准备发送！")
                    st.progress(90)
                time.sleep(0.5)

                loading.empty()
                st.success("✅ 完成")
                st.video(video_file)
                st.markdown("### 🐱 主子说：")
                if ai_msg:
                    st.info(f"“ {ai_msg} ”")
                else:
                    st.info("AI 暂时离线。")
            
            try:
                os.remove(video_path)
                os.remove(audio_path)
            except: pass


