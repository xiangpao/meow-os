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
    page_icon="☕", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# 清除代理
if "HTTP_PROXY" in os.environ: del os.environ["HTTP_PROXY"]
if "HTTPS_PROXY" in os.environ: del os.environ["HTTPS_PROXY"]

# 初始化记忆
if 'baseline_pitch' not in st.session_state:
    st.session_state['baseline_pitch'] = None

# --- 1. CSS 拿铁风深度定制 ---
st.markdown("""
<style>
    /* 全局背景：热牛奶白 -> 浅拿铁渐变 */
    .stApp {
        background: linear-gradient(180deg, #FFFDF7 0%, #F5E6D3 100%);
        color: #4E342E;
    }
    
    /* 标题样式 */
    h1 { 
        color: #5D4037 !important; 
        font-family: 'Comic Sans MS', 'ZKKuaiLe', '幼圆', sans-serif !important;
        font-weight: 800;
        text-shadow: 2px 2px 0px #FFF;
    }
    
    /* 顶部图片居中 */
    .stImage, .css-1v0mbdj {
        display: flex;
        justify_content: center;
        align-items: center;
        margin-bottom: -10px;
    }
    
    /* 卡片/折叠面板/上传框 */
    .stExpander, .css-1r6slb0, [data-testid="stFileUploadDropzone"] {
        background-color: #FFFFFF !important;
        border-radius: 20px !important;
        border: 2px solid #EFEBE9 !important;
        box-shadow: 0 4px 12px rgba(93, 64, 55, 0.1) !important;
    }
    
    /* 按钮：焦糖色 */
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
    
    /* 字体优化 */
    p, label, .stMarkdown, li {
        color: #4E342E !important;
        font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
    }
    
    /* 隐藏边框 */
    [data-testid="stFileUploadDropzone"] {
        border: 2px dashed #D7CCC8 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 顶部看板 (动图引擎) ---
def render_gif(gif_path, width=200):
    try:
        with open(gif_path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        st.markdown(
            f'<div style="text-align: center;"><img src="data:image/gif;base64,{b64}" width="{width}"></div>', 
            unsafe_allow_html=True
        )
    except:
        st.markdown(
            f'<div style="text-align: center;"><img src="https://media.tenor.com/4JPf4v6sHjIAAAAj/bongo-cat-typing.gif" width="{width}"></div>', 
            unsafe_allow_html=True
        )

# 显示 Logo
render_gif("logo.gif")

st.title("☕ 喵星电波台")
st.markdown("<p style='text-align: center; margin-top: -15px; color: #8D6E63;'><i>—— 接收来自 50Hz 频段的加密心声 ——</i></p>", unsafe_allow_html=True)

# --- [新增] 科学原理科普区 ---
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

# 设置区
with st.expander("⚙️ 调频与校准 (Settings)", expanded=False):
    context = st.selectbox(
        "📍 信号发射源 (当前场景)",
        [
            "🍽️ 干饭时刻 (Food)", 
            "🚪 门窗/受阻 (Barrier)", 
            "🛋️ 贴贴/求摸 (Affection)", 
            "🏥 害怕/应激 (Stress)", 
            "🦋 猎杀时刻 (Hunting)",
            "😡 别挨老子 (Warning)",
            "🌙 深夜跑酷 (Night)"
        ]
    )
    
    c1, c2 = st.columns([2, 1])
    with c1:
        if st.session_state['baseline_pitch']: 
            st.success(f"✅ 已锁定基准: {st.session_state['baseline_pitch']}Hz")
        else: 
            st.info("💡 建议录入一声「平时最放松的叫声」")
    with c2:
        if st.button("清除缓存"):
            st.session_state['baseline_pitch'] = None
            st.rerun()

# --- 3. 连接云端 ---
ai_status_msg = ""
ai_ready = False
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        ai_ready = True
    else:
        ai_status_msg = "密钥缺失"
except Exception as e:
    ai_status_msg = str(e)

if not ai_ready:
    st.warning(f"⚠️ 仅本地模式 (AI 离线)")
    st.caption(f"原因: {ai_status_msg}。请去 Secrets 填入 GOOGLE_API_KEY。")

# --- 4. 核心功能 (Tab) ---
tab1, tab2 = st.tabs(["🎙️ 语音接收", "📹 视频同传"])

# === Tab 1: 语音 ===
with tab1:
    st.markdown("##### 1. 采集声波 (录音/上传)")
    audio_file = st.file_uploader("支持 wav/mp3/m4a/aac", type=["wav", "mp3", "m4a", "aac"], key="audio_up", label_visibility="collapsed")
    
    # [修改点] 文案修改为“增加照片”
    st.markdown("##### 2. (可选) 增加照片")
    with st.expander("📷 开启相机抓拍", expanded=False):
        img_cam = st.camera_input("拍摄猫咪表情")
    img_up = st.file_uploader("或从相册上传图片", type=["jpg", "png"], key="img_up", label_visibility="collapsed")
    img_final = img_cam if img_cam else img_up

    if st.button("📡 开始解码信号", key="btn_audio"):
        if not audio_file:
            st.error("请先上传一段喵叫声！")
        else:
            with st.spinner("☕ 正在冲泡数据..."):
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
                            - 简短有力，像发朋友圈一样。
                            """
                            inputs = [prompt]
                            if img_final: inputs.append(Image.open(img_final))
                            ai_result = model.generate_content(inputs).text
                        except Exception as e: st.error(f"云端连接中断: {e}")

                    st.success("✅ 解码成功")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("情绪", data['pitch_trend'].split()[0])
                    c2.metric("时长", f"{data['duration']}s")
                    c3.metric("音高", f"{data['mean_pitch']}Hz")

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
    video_file = st.file_uploader("📹 上传视频文件", type=["mp4", "mov", "avi", "m4v"], key="video_up", label_visibility="collapsed")

    if st.button("🎬 分析视频信号", key="btn_video"):
        if not video_file:
            st.warning("请先上传视频喵！")
        else:
            with st.spinner("⏳ 正在分析肢体语言..."):
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
                        data = {"pitch_trend": "未知", "duration": 0} 
                    
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
