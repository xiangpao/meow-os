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

# --- 2. CSS 拿铁风深度定制 (视觉回归) ---
st.markdown("""
<style>
    /* 全局背景：热牛奶白 -> 浅拿铁渐变 */
    .stApp {
        background: linear-gradient(180deg, #FFFDF7 0%, #F5E6D3 100%);
        color: #4E342E;
    }
    
    /* 标题样式：圆润、深咖啡色 */
    h1 { 
        color: #5D4037 !important; 
        font-family: 'Comic Sans MS', 'ZKKuaiLe', '幼圆', sans-serif !important;
        font-weight: 800;
        text-shadow: 2px 2px 0px #FFF;
    }
    
    /* 图片容器居中 */
    .header-img {
        display: flex;
        justify_content: center;
        align-items: center;
        margin-bottom: 10px;
    }
    
    /* 卡片/折叠面板/上传框：像一块白色的方糖 */
    .stExpander, .css-1r6slb0, [data-testid="stFileUploadDropzone"], .stSelectbox > div > div {
        background-color: #FFFFFF !important;
        border-radius: 20px !important;
        border: 2px solid #EFEBE9 !important;
        box-shadow: 0 4px 12px rgba(93, 64, 55, 0.1) !important;
    }
    
    /* 按钮：焦糖色果冻质感 */
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
    
    /* Tab 标签页：未选中是浅咖，选中是深咖 */
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
    
    /* 字体颜色优化 */
    p, label, .stMarkdown, li, .stCaption {
        color: #4E342E !important;
        font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
    }
    
    /* 隐藏上传组件自带的丑边框 */
    [data-testid="stFileUploadDropzone"] {
        border: 2px dashed #D7CCC8 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 顶部看板 (修复：使用本地 logo.gif) ---
def render_local_gif(filename, width=180):
    """读取本地 GIF 并以 Base64 显示，确保动图不黑屏"""
    try:
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                data = f.read()
            b64 = base64.b64encode(data).decode()
            return f'<div class="header-img"><img src="data:image/gif;base64,{b64}" width="{width}" style="border-radius:15px"></div>'
        else:
            # 备用：如果本地没文件，显示一个网络兜底图
            return f'<div class="header-img"><img src="https://media.giphy.com/media/GeimqsH0TLDt4tScGw/giphy.gif" width="{width}"></div>'
    except:
        return ""

# 显示顶部 Logo
st.markdown(render_local_gif("logo.gif", width=200), unsafe_allow_html=True)

st.title("🐱 喵星电波台")
st.markdown("<p style='text-align: center; margin-top: -15px; color: #8D6E63;'><i>—— 接收来自 50Hz 频段的加密心声 ——</i></p>", unsafe_allow_html=True)

# --- 4. 科学原理 (找回功能) ---
with st.expander("🔬 喵星发声学原理 (Science)", expanded=False):
    st.markdown("""
    **本台解码算法基于瑞典隆德大学 Susanne Schötz 教授的猫语旋律学研究：**
    * **🎵 升调 (Rising Pitch ↗)**: 类似人类的疑问句，通常代表**请求 (Soliciting)** 或 **友好的确认**。
    * **🎵 降调 (Falling Pitch ↘)**: 类似人类的陈述句，通常代表**拒绝**、**压力**或**自信的陈述**。
    * **⏳ 时长 (Duration)**: 
        * 短促音 (<0.5s): 社交问候 / 确认存在。
        * 长音 (>1.0s): 强烈需求 (我要吃!) / 抱怨 (放我出去!)。
    """)

# --- 5. 核心控制台 (场景必选) ---
st.markdown("### 🎛️ 信号控制台")

# 场景选择：移出折叠区，强制选择
scenario_options = [
    "🚫 请选择发射源 (必选)", 
    "🍽️ 干饭时刻 (Food)", 
    "🚪 门窗/受阻 (Barrier)", 
    "🛋️ 贴贴/求摸 (Affection)", 
    "🏥 害怕/应激 (Stress)", 
    "🦋 猎杀时刻 (Hunting)", 
    "😡 别挨老子 (Warning)", 
    "🌙 深夜跑酷 (Night)"
]
context = st.selectbox("📍 1. 锁定信号发射源 (必选)", scenario_options, label_visibility="collapsed")

# 校准功能 (依然折叠，保持整洁)
with st.expander("⚙️ 高级设置：声纹校准", expanded=False):
    st.caption("上传一段“平时最放松的喵叫”作为基准，提高识别率。")
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
                    st.error("校准失败，请重试")
    
    # 状态显示
    col_s, col_c = st.columns([3,1])
    with col_s:
        if st.session_state['baseline_pitch']:
            st.success(f"当前基准: {st.session_state['baseline_pitch']}Hz")
        else:
            st.info("尚未录入基准")
    with col_c:
        if st.button("清除"):
            st.session_state['baseline_pitch'] = None
            st.rerun()

# --- 连接云端 ---
ai_ready = False
# 定义等待用的“打字猫”动画 (仅网络链接，用于 st.image)
LOADING_GIF_URL = "https://media.tenor.com/4JPf4v6sHjIAAAAj/bongo-cat-typing.gif"

try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        # 使用你验证过的稳健模型
        model = genai.GenerativeModel(
            model_name='gemini-flash-latest',
            system_instruction="你是一只猫。用第一人称（'本喵'、'我'）。禁止解释。语气生动傲娇。根据场景和声音特征翻译心声。"
        )
        ai_ready = True
    else:
        st.error("⚠️ 密钥缺失")
except Exception:
    st.error("⚠️ AI 初始化失败")

# --- 6. 业务功能区 ---
st.markdown("### 📡 信号接收区")
tab1, tab2 = st.tabs(["🎙️ 语音解码", "📹 视频解码"])

# === Tab 1: 语音 ===
with tab1:
    audio_file = st.file_uploader("上传音频", type=["wav", "mp3", "m4a", "aac"], key="audio_up", label_visibility="collapsed")
    
    with st.expander("📷 (可选) 增加照片辅助", expanded=False):
        img_cam = st.camera_input("拍照")
        img_up = st.file_uploader("或上传图片", type=["jpg", "png"], key="img_up")
    img_final = img_cam if img_cam else img_up

    if st.button("▶️ 开始解码", key="btn_audio"):
        # 强制检查场景
        if "🚫" in context:
            st.error("⚠️ 无法解码：请先在上方控制台选择【信号发射源】！")
        elif not audio_file:
            st.error("⚠️ 请先上传喵叫声！")
        else:
            # === 等待特效 (在下方显示，不替换 Header) ===
            loading = st.empty()
            
            # 阶段 1
            with loading.container():
                st.markdown(f'<div class="header-img"><img src="{LOADING_GIF_URL}" width="150"></div>', unsafe_allow_html=True)
                st.info("📡 正在连接喵星基站 (50Hz)...")
                st.progress(20)
            
            data = analyze_audio_advanced(audio_file, st.session_state['baseline_pitch'])
            
            # 阶段 2
            with loading.container():
                st.markdown(f'<div class="header-img"><img src="{LOADING_GIF_URL}" width="150"></div>', unsafe_allow_html=True)
                st.info("🐈 正在破译加密电波...")
                st.progress(60)

            if data['status'] == 'error':
                loading.empty()
                st.error(f"❌ 失败: {data['msg']}")
            else:
                ai_result = ""
                if ai_ready:
                    try:
                        prompt = f"场景：{context}。声学特征：{data}。翻译我的心声。"
                        inputs = [prompt]
                        if img_final: inputs.append(Image.open(img_final))
                        ai_result = model.generate_content(inputs).text
                    except: 
                        st.warning("云端连接不稳定，转为离线模式。")

                loading.empty() # 清除等待动画

                # 结果展示
                st.success("✅ 解码成功")
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

    if st.button("▶️ 分析视频", key="btn_video"):
        if "🚫" in context:
            st.error("⚠️ 无法解码：请先在上方控制台选择【信号发射源】！")
        elif not video_file:
            st.error("⚠️ 请先上传视频！")
        else:
            loading = st.empty()
            with loading.container():
                st.markdown(f'<div class="header-img"><img src="{LOADING_GIF_URL}" width="150"></div>', unsafe_allow_html=True)
                st.info("🎞️ 正在分离音轨 & 逐帧解析...")
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
                data = analyze_audio_advanced(audio_path, st.session_state['baseline_pitch'])
                ai_msg = ""
                if ai_ready:
                    with loading.container():
                        st.markdown(f'<div class="header-img"><img src="{LOADING_GIF_URL}" width="150"></div>', unsafe_allow_html=True)
                        st.info("🧠 AI 大脑疯狂运转中...")
                        st.progress(80)
                    try:
                        video_blob = genai.upload_file(video_path)
                        while video_blob.state.name == "PROCESSING":
                            time.sleep(1)
                            video_blob = genai.get_file(video_blob.name)
                        
                        prompt = f"场景：{context}。声音：{data}。翻译心声。"
                        response = model.generate_content([prompt, video_blob])
                        ai_msg = response.text
                    except: pass
                
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
