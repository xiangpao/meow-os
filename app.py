import streamlit as st
import google.generativeai as genai
import os
import time
import tempfile
from PIL import Image
from utils import analyze_audio_advanced, extract_audio_from_video

# --- 0. 系统配置 ---
st.set_page_config(
    page_title="🐱 喵星电波台", 
    page_icon="📡", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# 清除可能导致报错的代理环境变量
if "HTTP_PROXY" in os.environ: del os.environ["HTTP_PROXY"]
if "HTTPS_PROXY" in os.environ: del os.environ["HTTPS_PROXY"]

# 初始化记忆
if 'baseline_pitch' not in st.session_state:
    st.session_state['baseline_pitch'] = None

# --- 1. CSS 深度汉化与美化 ---
st.markdown("""
<style>
    /* 全局背景：奶茶色渐变 */
    .stApp {
        background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
    }
    
    /* 标题样式 */
    h1 { 
        color: #FF8C00; 
        font-family: 'Comic Sans MS', '幼圆', sans-serif !important;
        text-shadow: 2px 2px 0px #FFF;
    }
    
    /* 隐藏 Streamlit 默认的英文提示，用 CSS 伪装成中文 (黑科技) */
    /* 注意：Browse files 这种按钮内部文字很难改，取决于用户浏览器语言 */
    /* 但我们可以把上面的 Label 做得非常醒目 */
    
    .stFileUploader label {
        font-size: 1.2rem !important;
        color: #FF6347 !important;
        font-weight: bold !important;
    }
    
    /* 按钮美化：果冻质感 */
    .stButton>button {
        background: linear-gradient(45deg, #FF7F50, #FF4500);
        color: white;
        border-radius: 25px;
        height: 55px;
        font-size: 18px;
        font-weight: bold;
        border: none;
        box-shadow: 0 4px 10px rgba(255, 69, 0, 0.3);
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 15px rgba(255, 69, 0, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 顶部看板 ---
# 换了一个更稳定的动图源
st.image("https://media.giphy.com/media/GeimqsH0TLDt4tScGw/giphy.gif", use_column_width=True)
st.title("🐱 喵星电波台")
st.caption("—— 接收主子来自 50Hz 频段的加密通话")

# 科学原理 (折叠)
with st.expander("📡 信号解码原理 (基于 Susanne Schötz 研究)", expanded=False):
    st.markdown("""
    * **F0 基频 (Pitch)**: 升调 (↗) 通常代表请求/疑问；降调 (↘) 代表拒绝/陈述。
    * **时长 (Duration)**: 短音通常是打招呼；长音 (>1s) 代表强烈需求或抱怨。
    * **多模态**: 结合动作 (如尾巴竖直 vs 炸毛) 可大幅提高准确率。
    """)

# 设置区
with st.expander("⚙️ 信号校准 (Settings)", expanded=True):
    # 基于科学研究扩展的场景列表
    context = st.selectbox(
        "📍 发射源位置 (当前场景)",
        [
            "🍽️ 干饭时刻 (Food Soliciting) - 最常见", 
            "🚪 门窗/受阻 (Barrier Frustration)", 
            "🛋️ 贴贴/求摸 (Affection/Brushing)", 
            "🏥 害怕/应激 (Isolation/Vet)", 
            "🦋 猎杀时刻 (Prey/Hunting)",
            "😡 别挨老子 (Agonistic/Warning)",
            "🌙 深夜跑酷 (Night Activity)"
        ]
    )
    
    c1, c2 = st.columns([2, 1])
    with c1:
        if st.session_state['baseline_pitch']: 
            st.success(f"✅ 已锁定基准频率: {st.session_state['baseline_pitch']}Hz")
        else: 
            st.info("💡 建议录入一声「平时最放松的叫声」作为基准。")
    with c2:
        if st.button("清除缓存"):
            st.session_state['baseline_pitch'] = None
            st.rerun()

# --- 3. 连接云端大脑 ---
ai_status_msg = ""
ai_ready = False

try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        ai_ready = True
    else:
        ai_status_msg = "密钥未配置 (Secrets Empty)"
except Exception as e:
    ai_status_msg = str(e)

if not ai_ready:
    st.warning(f"⚠️ 只有本地算法在工作 (AI 离线)")
    st.caption(f"原因: {ai_status_msg}。请去 Manage App -> Settings -> Secrets 填入 GOOGLE_API_KEY。")

# --- 4. 核心功能区 (Tab) ---
tab1, tab2 = st.tabs(["🎙️ 语音接收", "📹 视频同传"])

# === Tab 1: 语音 ===
with tab1:
    st.markdown("##### 1. 采集声波 (录音/上传)")
    # 这里的 label 会显示为中文，但下方按钮语言取决于浏览器
    audio_file = st.file_uploader("支持 wav/mp3/m4a/aac", type=["wav", "mp3", "m4a", "aac"], key="audio_up")
    
    st.markdown("##### 2. (可选) 拍张照/录像提高准确度")
    # Camera Input 只能拍照，文案修改以符合实际功能
    with st.expander("📸 开启相机抓拍", expanded=False):
        img_cam = st.camera_input("拍摄猫咪表情")
    img_up = st.file_uploader("或从相册上传图片", type=["jpg", "png"], key="img_up", label_visibility="collapsed")
    img_final = img_cam if img_cam else img_up

    if st.button("📡 开始解码信号", key="btn_audio"):
        if not audio_file:
            st.error("请先上传一段喵叫声！")
        else:
            with st.spinner("正在分析 50Hz 生物电波..."):
                data = analyze_audio_advanced(audio_file, st.session_state['baseline_pitch'])
                
                if data['status'] == 'error':
                    st.error(f"❌ 信号干扰: {data['msg']}")
                else:
                    # 本地逻辑
                    local_logic = []
                    if data['duration'] < 0.6: local_logic.append("短促音(打招呼)")
                    elif data['duration'] > 1.2: local_logic.append("长音(需求/抱怨)")
                    
                    if "Rising" in data['pitch_trend']: local_logic.append("升调(疑问/请求)")
                    elif "Falling" in data['pitch_trend']: local_logic.append("降调(拒绝/陈述)")
                    
                    logic_str = " + ".join(local_logic)

                    # AI 分析
                    ai_result = ""
                    if ai_ready:
                        try:
                            prompt = f"""
                            角色：你就是这只猫。
                            任务：用【第一人称】翻译你的心声。
                            数据：
                            - 场景：{context}
                            - 声音特征：{data['pitch_trend']}，时长{data['duration']}秒。
                            - 逻辑参考：{logic_str}
                            要求：
                            - 语气：傲娇、可爱或急切。
                            - 不要说“这只猫”，直接说“本喵”或“我”。
                            - 简短有力，像发微信一样。
                            """
                            inputs = [prompt]
                            if img_final: inputs.append(Image.open(img_final))
                            ai_result = model.generate_content(inputs).text
                        except Exception as e: st.error(f"云端连接中断: {e}")

                    st.success("✅ 解码成功")
                    
                    # 萌化数据卡片
                    c1, c2, c3 = st.columns(3)
                    c1.metric("情绪", data['pitch_trend'].split()[0])
                    c2.metric("时长", f"{data['duration']}s")
                    c3.metric("哈气值", "高!!" if data['is_rough'] else "低")

                    st.markdown("### 🐱 主子说：")
                    if ai_result:
                        st.info(f"“ {ai_result} ”")
                    else:
                        st.info(f"（AI 离线）本地推断：大概是【{logic_str}】的意思。")

                    if st.button("🎯 记住这个声音 (设为基准)"):
                        st.session_state['baseline_pitch'] = data['mean_pitch']
                        st.toast("已录入声纹库！")
                        time.sleep(1)

# === Tab 2: 视频 ===
with tab2:
    st.info("💡 提示：点击下方按钮 -> 选择 **“录像”** 或 **“从图库选择”**。")
    video_file = st.file_uploader("📹 上传视频文件", type=["mp4", "mov", "avi", "m4v"], key="video_up")

    if st.button("🎬 分析视频信号", key="btn_video"):
        if not video_file:
            st.warning("请先上传视频喵！")
        else:
            with st.spinner("正在分离音轨并分析肢体语言..."):
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
                        st.warning("⚠️ 未检测到猫叫声，将仅分析动作。")
                        data = {"pitch_trend": "未知", "duration": 0} # 兜底
                    
                    ai_msg = ""
                    if ai_ready:
                        try:
                            video_blob = genai.upload_file(video_path)
                            while video_blob.state.name == "PROCESSING":
                                time.sleep(1)
                                video_blob = genai.get_file(video_blob.name)

                            prompt = f"""
                            角色：你就是视频里的这只猫。
                            任务：结合你的动作（尾巴/耳朵）和声音（{data}），用【第一人称】吐槽或表达需求。
                            场景：{context}。
                            语气：生动、有趣、二次元。
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
