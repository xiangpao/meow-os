import streamlit as st
import google.generativeai as genai
import os
import time
import tempfile
from PIL import Image
from utils import analyze_audio_advanced, extract_audio_from_video

# --- 0. 系统配置 (萌化版) ---
st.set_page_config(
    page_title="喵语翻译官 🐾", 
    page_icon="🐱", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# 清除代理防止报错
if "HTTP_PROXY" in os.environ: del os.environ["HTTP_PROXY"]
if "HTTPS_PROXY" in os.environ: del os.environ["HTTPS_PROXY"]

# 初始化记忆
if 'baseline_pitch' not in st.session_state:
    st.session_state['baseline_pitch'] = None

# --- 1. CSS 深度美化 (二次元风格) ---
st.markdown("""
<style>
    /* 全局背景：暖暖的猫爪白 */
    .stApp {
        background-color: #FFF5EE; 
        background-image: linear-gradient(120deg, #fdfbfb 0%, #ebedee 100%);
    }
    
    /* 标题字体：可爱圆体 */
    h1 { 
        color: #FF7F50; 
        font-family: 'Comic Sans MS', '幼圆', sans-serif !important;
        text-shadow: 2px 2px 0px #FFF;
    }
    
    /* 卡片容器：圆角+阴影 */
    .css-1r6slb0, .stExpander {
        background-color: rgba(255, 255, 255, 0.8);
        border-radius: 20px;
        border: 2px solid #FFDAB9;
        box-shadow: 0 4px 15px rgba(255, 182, 193, 0.3);
    }
    
    /* 按钮：果冻质感 */
    .stButton>button {
        background: linear-gradient(45deg, #FF7F50, #FF6347);
        color: white;
        border-radius: 30px;
        height: 55px;
        font-size: 18px;
        font-weight: bold;
        border: none;
        box-shadow: 0 5px 15px rgba(255, 99, 71, 0.4);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 8px 20px rgba(255, 99, 71, 0.6);
    }

    /* 字体优化 */
    p, label {
        color: #5D4037;
        font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 顶部看板与设置 ---
st.image("https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExbDN6eHd4aHlodXZ4aHlodXZ4aHlodXZ4aHlodXZ4aHlodXZ4aHlodXZ4aSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/Lq0h93752f6J9tijvr/giphy.gif", width=100)
st.title("🐾 喵语翻译官")
st.caption("—— 听懂主子每一句“喵”背后的心机")

# 科学原理折叠区
with st.expander("🔬 这不是玩具！点击查看科学原理", expanded=False):
    st.markdown("""
    **本应用基于生物声学 (Bio-acoustics) 与 多模态 AI 构建：**
    1.  **F0 基频分析**：通过 `Librosa` 提取猫叫声的旋律（升调通常代表请求，降调代表抗拒）。
    2.  **时长维度**：短促音 (<0.5s) 多为社交确认，长音 (>1.5s) 多为强烈需求。
    3.  **多模态融合**：结合 `Gemini Vision` 识别耳/尾体态，修正翻译准确率。
    """)

# 设置区
with st.expander("⚙️ 场景校准 (必选)", expanded=True):
    context = st.selectbox(
        "📍 刚才发生在哪？",
        ["🍽️ 饭点/厨房 (最常见)", "🚪 被关门外/窗边", "🛋️ 撸猫/沙发上", "🌙 深夜跑酷", "🏥 宠物医院/外出", "🦋 窗外有猎物"]
    )
    
    c1, c2 = st.columns([2, 1])
    with c1:
        if st.session_state['baseline_pitch']: 
            st.success(f"✅ 已记录主子标准音高: {st.session_state['baseline_pitch']}Hz")
        else: 
            st.info("💡 尚未记录标准音。建议录入一声平时最放松的叫声作为基准。")
    with c2:
        if st.button("清除记忆"):
            st.session_state['baseline_pitch'] = None
            st.rerun()

# --- 3. 连接云端大脑 ---
ai_error_msg = ""
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    ai_ready = True
except Exception as e:
    ai_ready = False
    ai_error_msg = str(e)

if not ai_ready:
    st.error(f"⚠️ 云端大脑离线 (仅本地模式)")
    if "did not find a label" in str(ai_error_msg):
        st.caption("🔴 原因：未在 Streamlit 后台配置 API Key。请去 Manage App -> Settings -> Secrets 填入密钥。")
    else:
        st.caption(f"🔴 原因：{ai_error_msg}")

# --- 4. 核心功能 (Tab) ---
tab1, tab2 = st.tabs(["🎙️ 语音翻译", "📹 视频同传"])

# === Tab 1: 语音 ===
with tab1:
    st.markdown("##### 1. 录下主子的声音")
    audio_file = st.file_uploader("点击录音 (支持 m4a/mp3/wav)", type=["wav", "mp3", "m4a", "aac"], label_visibility="collapsed")
    
    st.markdown("##### 2. (可选) 拍张照提高准确度")
    with st.expander("📸 点击展开相机", expanded=False):
        img_cam = st.camera_input("拍摄猫咪表情")
    img_up = st.file_uploader("或从相册上传", type=["jpg", "png"], label_visibility="collapsed")
    img_final = img_cam if img_cam else img_up

    if st.button("✨ 开始翻译 ✨", key="btn_audio"):
        if not audio_file:
            st.warning("请先喂我一段录音喵！")
        else:
            with st.spinner("🐈 正在分析声波与微表情..."):
                data = analyze_audio_advanced(audio_file, st.session_state['baseline_pitch'])
                
                if data['status'] == 'error':
                    st.error(f"❌ 解析失败: {data['msg']}")
                else:
                    # 构建本地逻辑结论 (兜底)
                    local_logic = ""
                    if data['duration'] < 0.6: local_logic += " (短促音:打招呼/确认)"
                    elif data['duration'] > 1.2: local_logic += " (长音:需求/抱怨)"
                    
                    if "Rising" in data['pitch_trend']: local_logic += " + (升调:疑问/请求)"
                    elif "Falling" in data['pitch_trend']: local_logic += " + (降调:拒绝/陈述)"
                    
                    # AI 分析
                    ai_result = ""
                    if ai_ready:
                        try:
                            prompt = f"""
                            你现在就是这只猫。请根据以下数据，用**第一人称**翻译你的心声。
                            
                            【传感器数据】
                            1. 场景：{context}
                            2. 声音特征：{data['pitch_trend']}，时长{data['duration']}秒，粗糙度(嘶吼)={'是' if data['is_rough'] else '否'}。
                            3. 逻辑推断参考：{local_logic}
                            
                            【要求】
                            - 语气：傲娇、可爱或急切（根据数据判断）。
                            - 格式：直接说出你想说的话，不要带引号，不要说“这只猫”。
                            - 如果包含视觉图片，请结合图片中的耳朵/瞳孔/尾巴状态修正翻译。
                            """
                            inputs = [prompt]
                            if img_final: inputs.append(Image.open(img_final))
                            ai_result = model.generate_content(inputs).text
                        except Exception as e: st.error(f"AI 连接中断: {e}")

                    # 结果展示
                    st.success("✅ 翻译完成")
                    
                    # 萌化数据展示
                    c1, c2, c3 = st.columns(3)
                    c1.metric("情绪", data['pitch_trend'].split()[0])
                    c2.metric("音长", f"{data['duration']}s")
                    c3.metric("嘶吼指数", "高!!" if data['is_rough'] else "低")

                    st.markdown("### 🐱 主子说：")
                    if ai_result:
                        st.info(f"“ {ai_result} ”")
                    else:
                        # 本地兜底文案
                        fallback_msg = "快理理我！" if "Rising" in data['pitch_trend'] else "朕现在不想动。"
                        st.info(f"（AI 休息中）本地分析：{fallback_msg} \n\n *依据：{local_logic}*")

                    # 校准按钮
                    if st.button("🎯 这就是它平时的声音 (设为基准)"):
                        st.session_state['baseline_pitch'] = data['mean_pitch']
                        st.toast("记住了喵！下次以此为准。")
                        time.sleep(1)

# === Tab 2: 视频 ===
with tab2:
    st.info("💡 提示：点击下方选择 **“录像”** 或 **“从相册选择”**。")
    video_file = st.file_uploader("📹 上传视频", type=["mp4", "mov", "avi", "m4v"], label_visibility="collapsed")

    if st.button("🎬 视频同传 🎬", key="btn_video"):
        if not video_file:
            st.warning("没有视频怎么看喵？")
        else:
            with st.spinner("⏳ 正在分离音轨并进行多模态分析..."):
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                tfile.write(video_file.read())
                video_path = tfile.name
                audio_path = video_path.replace(".mp4", ".wav")
                
                has_audio = extract_audio_from_video(video_path, audio_path)
                
                if not has_audio:
                    st.error("❌ 视频里没有声音呀！")
                else:
                    data = analyze_audio_advanced(audio_path, st.session_state['baseline_pitch'])
                    
                    if data['status'] == 'error':
                        st.warning("⚠️ 视频里好像没有猫叫声？将仅分析动作。")
                        data = {"pitch_trend": "未知", "mean_pitch": 0, "is_rough": False, "duration": 0}
                    
                    ai_msg = ""
                    if ai_ready:
                        try:
                            video_blob = genai.upload_file(video_path)
                            while video_blob.state.name == "PROCESSING":
                                time.sleep(1)
                                video_blob = genai.get_file(video_blob.name)

                            prompt = f"""
                            你就是视频里的这只猫。
                            结合你的动作（尾巴/耳朵/姿态）和刚才的声音数据（{data}），
                            用**第一人称**告诉人类你在想什么。
                            场景：{context}。
                            语气要生动！
                            """
                            response = model.generate_content([prompt, video_blob])
                            ai_msg = response.text
                        except Exception as e: st.error(f"AI 罢工了: {e}")

                    st.success("✅ 分析结束")
                    st.video(video_file)
                    
                    st.markdown("### 🐱 主子说：")
                    if ai_msg:
                        st.info(f"“ {ai_msg} ”")
                    else:
                        st.info("AI 暂时无法连接，无法解读视频内容。")

                try:
                    os.remove(video_path)
                    os.remove(audio_path)
                except: pass
