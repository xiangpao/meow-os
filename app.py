import streamlit as st
import google.generativeai as genai
import os
import time
from PIL import Image
from utils import analyze_audio_advanced

# --- 0. 系统配置 ---
st.set_page_config(page_title="MeowOS ☕ V4", page_icon="🐾", layout="wide")

# ⚠️ 代理设置 (根据你的 Clash 端口保持 7890)
# os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
# os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"

# 初始化 Session State (找回“记忆”功能)
if 'baseline_pitch' not in st.session_state:
    st.session_state['baseline_pitch'] = None

# --- 1. ☕ 拿铁风格 UI 注入 (CSS Injection) ---
st.markdown("""
<style>
    /* 全局背景：奶油白 */
    .stApp {
        background-color: #FFF8E7;
        color: #5D4037;
    }
    
    /* 侧边栏：浅拿铁色 */
    [data-testid="stSidebar"] {
        background-color: #F5E6D3;
    }
    
    /* 标题颜色：深咖啡 */
    h1, h2, h3 {
        color: #6F4E37 !important;
        font-family: 'Comic Sans MS', 'Chalkboard SE', sans-serif !important;
    }
    
    /* 按钮：焦糖色，圆角 */
    .stButton>button {
        background-color: #D2691E;
        color: white;
        border-radius: 20px;
        border: none;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #A0522D;
        transform: scale(1.05);
    }
    
    /* 数据卡片：白色圆角卡片 */
    [data-testid="metric-container"] {
        background-color: #FFFFFF;
        border: 2px solid #EFEBE9;
        border-radius: 15px;
        padding: 10px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
    }
    
    /* 文本框高亮 */
    [data-testid="stMarkdownContainer"] p {
        font-size: 1.1em;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 侧边栏控制台 ---
st.sidebar.image("https://placekitten.com/300/100", caption="MeowOS Online") # 占位萌图
st.sidebar.header("⚙️ 设定 (Settings)")

# A. 环境上下文
context = st.sidebar.selectbox(
    "📍 当前场景",
    ["🍽️ 饭点/厨房", "🚪 门窗/阻隔", "🛋️ 互动/撸猫", "🌙 深夜", "🏥 陌生/就医", "🦋 狩猎模式"]
)

# B. 找回功能：基准线校准
st.sidebar.markdown("---")
st.sidebar.subheader("⚖️ 声音校准")
if st.session_state['baseline_pitch']:
    st.sidebar.success(f"已校准基准: {st.session_state['baseline_pitch']} Hz")
    if st.sidebar.button("清除记忆"):
        st.session_state['baseline_pitch'] = None
        st.rerun()
else:
    st.sidebar.info("尚未校准。建议录入一声平时最放松的‘喵’作为基准。")

# --- 3. 核心功能区 ---
st.title("🐾 喵星语翻译官 (MeowOS Café)")

# 连接 AI 引擎
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    ai_ready = True
except:
    st.error("⚠️ AI 密钥未配置或连接失败，将仅使用本地逻辑模式。")
    ai_ready = False

col1, col2 = st.columns([1, 1.2])

with col1:
    st.markdown("### 1️⃣ 采集信号")
    st.info("💡 声音是必填项，照片可辅助 AI 判断。")
    audio_file = st.file_uploader("录制/上传声音 (WAV/MP3)", type=["wav", "mp3"])
    img_file = st.camera_input("拍摄猫咪表情 (可选)")
    if not img_file:
        img_file = st.file_uploader("或上传照片", type=["jpg", "png", "jpeg"])

with col2:
    st.markdown("### 2️⃣ 分析面板")
    
    if st.button("开始解码 (Translate) 🐾", use_container_width=True):
        if not audio_file:
            st.warning("请至少上传一段声音！")
        else:
            with st.spinner("正在通过声学算法 + AI 视觉进行多模态融合..."):
                # --- Step A: 本地声学分析 (快思考) ---
                # 传入基准线进行对比
                audio_data = analyze_audio_advanced(audio_file, st.session_state['baseline_pitch'])
                
                # --- Step B: 逻辑判决 (回归 V2 功能) ---
                # 找回之前被删掉的逻辑树，作为基础保底
                basic_msg = "无法解析"
                if "Rising" in audio_data['pitch_trend']:
                    basic_msg = "🤔 疑问 / 请求 / 撒娇"
                elif "Falling" in audio_data['pitch_trend']:
                    basic_msg = "😤 拒绝 / 压力 / 陈述"
                
                # 如果有基准线，进行对比
                if audio_data['pitch_delta'] > 50:
                    basic_msg += " (音调偏高，情绪激动)"
                
                # --- Step C: Gemini AI 深度分析 (慢思考) ---
                ai_result = ""
                if ai_ready and img_file:
                    try:
                        image = Image.open(img_file)
                        prompt = f"""
                        角色：你是一位资深的猫行为学家。
                        数据输入：
                        1. 声音分析数据：{audio_data}
                        2. 环境背景：{context}
                        3. 视觉图像：(见附图)
                        
                        任务：请结合声音数据、环境和照片，用**第一人称**（猫的口吻）翻译这句话。
                        风格：傲娇、可爱或急切（根据情绪判定）。
                        
                        输出格式：
                        【猫咪心声】：(你的翻译)
                        【人类建议】：(给主人的行动指南)
                        """
                        response = model.generate_content([prompt, image])
                        ai_result = response.text
                    except Exception as e:
                        ai_result = f"AI 连接受阻，仅显示本地分析结果。({e})"
                elif ai_ready:
                     # 只有声音没有图，也让 AI 润色文案
                    prompt = f"环境：{context}。声音特征：{audio_data}。请用猫的口吻翻译这句话，并给出建议。"
                    response = model.generate_content(prompt)
                    ai_result = response.text

                # --- 结果展示 UI ---
                st.markdown("#### 📊 声学指纹")
                m1, m2, m3 = st.columns(3)
                m1.metric("旋律趋势", audio_data['pitch_trend'])
                m2.metric("时长", f"{audio_data['duration']}s")
                m3.metric("嘶吼/哈气", "是" if audio_data['is_rough'] else "否")
                
                # 校准按钮
                if st.button("🎯 将此声音设为平时基准线"):
                    st.session_state['baseline_pitch'] = audio_data['mean_pitch']
                    st.toast("✅ 校准成功！")
                    time.sleep(1)
                    st.rerun()

                st.markdown("---")
                if ai_result:
                    st.success("✨ 解码成功！")
                    st.markdown(ai_result)
                else:
                    st.info(f"本地逻辑推断：{basic_msg}")
                    if audio_data['is_rough']:
                        st.error("🚨 警告：检测到粗糙音质（嘶吼），请注意安全！")