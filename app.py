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

# --- 2. CSS 拿铁风定制 ---
st.markdown("""
<style>
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
    .header-img {
        display: flex;
        justify_content: center;
        margin-bottom: 10px;
    }
    .stExpander, .css-1r6slb0, [data-testid="stFileUploadDropzone"] {
        background-color: #FFFFFF !important;
        border-radius: 20px !important;
        border: 2px solid #EFEBE9 !important;
        box-shadow: 0 4px 12px rgba(93, 64, 55, 0.1) !important;
    }
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
    p, label, .stMarkdown, li {
        color: #4E342E !important;
        font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
    }
    [data-testid="stFileUploadDropzone"] {
        border: 2px dashed #D7CCC8 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 顶部看板 (Base64 内置动图 - 绝不黑屏) ---
# 这是一只正在打字的 Bongo Cat 的 Base64 编码，无需网络请求
BONGO_CAT_B64 = "R0lGODlhZABkAPQAAP///wAAAPj4+Dg4OISEhMwMDAQEBBwcHJycHIyMjFBQUCgoKKioqLi4uDQ0FAQEBHx8fLy8vPz8/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH/C05FVFNDQVBFMi4wAwEAAAAh/h1HaWZCdWlsZGVyIDAuMiBieSBYvesgUGlndXVjACH+QQECgAAACwAAAAAZABkAAAF/iAljmRpnmiqrmzrvnAsz3Rt33iu73zv/8CgcEgsGo/IpHLJbDqf0Kh0Sq1ar9isdsvter/gsHhMLpvP6LR6zW673/C4fE6v2+/4vH7P7/v/gIGCg4SFhoeIiYqLjI2Oj5CRkpOUlZaXmJmam5ydnp+goaKjpKWmp6ipqqusra6vsLGys7S1tre4ubq7vL2+v8DBwsPExcbHyMnKy8zNzs/Q0dLT1NXW19jZ2tvc3d7f4OHi4+Tl5ufo6err7O3u7/Dx8vP09fb3+Pn6+/z9/v8AAwocSLCgwYMIEypcyLChw4cQI0qcSLGixYsYM2rcyLGjx48gQ4ocSbKkyZMo/lOqXMmypcuXMGPKnEmzps2bOHPq3Mmzp8+fQIMKHUq0qNGjSJMqXcq0qdOnUKNKnUq1qtWrWLNq3cq1q9evYMOKHUu2rNmzaNOqXcu2rdu3cOPKnUu3rt27ePPq3cu3r9+/gAMLHky4sOHDiBMrXsy4sePHkCNLnky5suXLmDNr3sy5s+fPoEOLHk26tOnTqFOrXs26tevXsGPLnk27tu3buHPr3s27t+/fwIMLH068uPHjyJMrX868ufPn0KNLn069uvXr2LNr3869u/fv4MOLH0++vPnz6NOrX8++vfv38OPLn0+/vv37+PPr38+/v///AAYo4IAEFmjggQgmqOBCDDbo4IMQRijhhBRWaOGFGGao4YYcdujhhyCGKOKIJJZo4okopqjiiiy26OKLMMYo44w01mjjjTjmqOOOPPbo449ABinkkEQWaeSRSCap5JJMNunkk1BGKeWUVFZp5ZVYZqnlllx26eWXYIYp5phklmnmmWimqeaabLbp5ptwxinnnHTWaeedeOap55589unnn4AGKuighBZq6KGIJqrooow26uijkEYq6aSUVmrppZhmqummnHbq6aeghirqqKSWauqpqKaq6qqsturqq7DGKuustNZq66245qrrrrz26uuvwAYr7LDEFmvsscgmq+yyzDbr7LPQRivttNRWa+212Gar7bbcduvtt+CGK+645JZr7rnopqvuuuy26+678MYr77z01mvvvfjmq+++/Pbr778AByzwwAQXbPDBCCes8MIMN+zwwxBHLPHEFFds8cUYZ6zxxhx37PHHIIcs8sgkl2zyySinrPLKLLfs8sswxyzzzDTXbPPNOOes88489+zzz0AHLfTQRBdt9NFIJ6300kw37fTTUEct9dRU7wcBADs="

def render_b64_gif(b64_string, width=150):
    return f'<div class="header-img"><img src="data:image/gif;base64,{b64_string}" width="{width}"></div>'

st.markdown(render_b64_gif(BONGO_CAT_B64), unsafe_allow_html=True)
st.title("🐱 喵星电波台")
st.markdown("<p style='text-align: center; margin-top: -15px; color: #8D6E63;'><i>—— 接收来自 50Hz 频段的加密心声 ——</i></p>", unsafe_allow_html=True)

# --- 科学原理 ---
with st.expander("🔬 喵星发声学原理 (Science)", expanded=False):
    st.markdown("""
    **本台解码算法基于瑞典隆德大学 Susanne Schötz 教授的猫语旋律学研究：**
    * **🎵 升调 (Rising Pitch ↗)**: 类似疑问句，代表**请求**或**确认**。
    * **🎵 降调 (Falling Pitch ↘)**: 类似陈述句，代表**拒绝**或**自信**。
    * **⏳ 时长**: 短音(<0.5s)为问候；长音(>1s)为强烈需求。
    """)

# --- 设置与校准区 ---
with st.expander("⚙️ 调频与校准 (Settings)", expanded=False):
    context = st.selectbox(
        "📍 信号发射源 (当前场景)",
        ["🍽️ 干饭时刻 (Food)", "🚪 门窗/受阻 (Barrier)", "🛋️ 贴贴/求摸 (Affection)", "🏥 害怕/应激 (Stress)", "🦋 猎杀时刻 (Hunting)", "😡 别挨老子 (Warning)", "🌙 深夜跑酷 (Night)"]
    )
    
    st.markdown("---")
    st.markdown("**🎛️ 声纹校准控制台**")

    calib_file = st.file_uploader(
        "🎙️ 上传一段“平时最放松的喵叫” (仅校准)", 
        type=["wav", "mp3", "m4a", "aac"], 
        key="cal_up",
        label_visibility="visible"
    )
    
    if calib_file:
        if st.button("⚡ 立即分析并设为基准", key="btn_cal_direct"):
            with st.spinner("正在提取声纹特征..."):
                cal_data = analyze_audio_advanced(calib_file, baseline_pitch=None)
                if cal_data['status'] == 'error':
                    st.error(f"❌ 校准失败: {cal_data['msg']}")
                else:
                    new_pitch = cal_data['mean_pitch']
                    st.session_state['baseline_pitch'] = new_pitch
                    st.success(f"✅ 校准成功！已锁定基准频率: {new_pitch}Hz")
                    time.sleep(1)
                    st.rerun()

    st.markdown("---")
    col_status, col_clear = st.columns([2, 1])
    with col_status:
        if st.session_state['baseline_pitch']: 
            st.success(f"✅ 当前基准: {st.session_state['baseline_pitch']}Hz")
        else: 
            st.info("💡 尚未录入基准")
    with col_clear:
        if st.button("🗑️ 清除缓存"):
            st.session_state['baseline_pitch'] = None
            st.rerun()

# --- 连接云端 (模型突围战) ---
ai_ready = False
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        
        # [核心修改] 使用 Experimental 模型，通常有独立配额
        model_target = 'gemini-exp-1206' 
        
        system_instruction = """
        你是一只猫。你只能用猫的视角和口吻说话。
        禁止使用任何第三人称描述（如'这只猫'、'它'、'主子'）。
        禁止解释你的回答。
        直接输出你的心声。
        语气要生动、二次元，根据数据判断是傲娇、慵懒、还是急切。
        """
        
        model = genai.GenerativeModel(
            model_name=model_target,
            system_instruction=system_instruction
        )
        ai_ready = True
    else:
        st.caption("⚠️ 密钥缺失")
except Exception as e:
    st.caption(f"⚠️ 初始化异常: {e}")

# --- 核心功能 ---
tab1, tab2 = st.tabs(["🎙️ 语音接收", "📹 视频同传"])

# === Tab 1: 语音 ===
with tab1:
    st.markdown("##### 1. 采集声波 (录音/上传)")
    audio_file = st.file_uploader("支持 wav/mp3/m4a/aac", type=["wav", "mp3", "m4a", "aac"], key="audio_up", label_visibility="collapsed")
    
    st.markdown("##### 2. (可选) 增加照片")
    with st.expander("📷 开启相机抓拍", expanded=False):
        img_cam = st.camera_input("拍摄猫咪表情")
    img_up = st.file_uploader("或从相册上传图片", type=["jpg", "png"], key="img_up", label_visibility="collapsed")
    img_final = img_cam if img_cam else img_up

    if st.button("📡 开始解码信号", key="btn_audio"):
        if not audio_file:
            st.error("请先上传一段喵叫声！")
        else:
            # === 等待特效 ===
            loading_placeholder = st.empty() 
            
            with loading_placeholder.container():
                st.markdown(render_b64_gif(BONGO_CAT_B64, width=150), unsafe_allow_html=True)
                st.info("🎧 正在捕获声波特征...")
                st.progress(10)
            
            # 本地分析
            data = analyze_audio_advanced(audio_file, st.session_state['baseline_pitch'])
            
            with loading_placeholder.container():
                st.markdown(render_b64_gif(BONGO_CAT_B64, width=150), unsafe_allow_html=True)
                st.info("📡 正在连接喵星基站 (50Hz)...")
                st.progress(50)

            if data['status'] == 'error':
                loading_placeholder.empty()
                st.error(f"❌ 信号干扰: {data['msg']}")
            else:
                local_logic = []
                if data['duration'] < 0.6: local_logic.append("短促音(打招呼)")
                elif data['duration'] > 1.2: local_logic.append("长音(需求/抱怨)")
                if "Rising" in data['pitch_trend']: local_logic.append("升调(疑问/请求)")
                elif "Falling" in data['pitch_trend']: local_logic.append("降调(拒绝/陈述)")
                logic_str = " + ".join(local_logic)

                # AI 分析
                ai_result = ""
                if ai_ready:
                    with loading_placeholder.container():
                        st.markdown(render_b64_gif(BONGO_CAT_B64, width=150), unsafe_allow_html=True)
                        st.info("🐈 正在破译加密电波...")
                        st.progress(80)
                    
                    try:
                        prompt = f"""
                        当前环境：{context}
                        声音特征：{data['pitch_trend']}，时长{data['duration']}秒。
                        请翻译我（猫）这一刻在说什么。
                        """
                        inputs = [prompt]
                        if img_final: inputs.append(Image.open(img_final))
                        ai_result = model.generate_content(inputs).text
                    except Exception as e: 
                        st.error(f"云端错误: {e}")
                
                loading_placeholder.empty()

                st.session_state['latest_analysis'] = {
                    "data": data,
                    "ai_result": ai_result,
                    "logic_str": logic_str,
                    "type": "audio"
                }

    if st.session_state['latest_analysis'] and st.session_state['latest_analysis']['type'] == 'audio':
        res = st.session_state['latest_analysis']
        data = res['data']
        
        st.success("✅ 电波破译成功")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("情绪", data['pitch_trend'].split()[0])
        c2.metric("时长", f"{data['duration']}s")
        c3.metric("音高", f"{data['mean_pitch']}Hz")

        st.markdown("### 🐱 主子说：")
        if res['ai_result']:
            st.info(f"“ {res['ai_result']} ”")
        else:
            st.warning(f"（AI 离线 - 启动备用翻译协议）")
            st.info(f"🤖 系统推断：根据声学特征，这句喵大概是【{res['logic_str']}】的意思。")

# === Tab 2: 视频 ===
with tab2:
    st.info("💡 提示：点击下方按钮 -> 选择 **“录像”** 或 **“从图库选择”**。")
    video_file = st.file_uploader("📹 上传视频文件", type=["mp4", "mov", "avi", "m4v"], key="video_up", label_visibility="collapsed")

    if st.button("🎬 分析视频信号", key="btn_video"):
        if not video_file:
            st.warning("请先上传视频喵！")
        else:
            loading_placeholder = st.empty()
            
            with loading_placeholder.container():
                st.markdown(render_b64_gif(BONGO_CAT_B64, width=150), unsafe_allow_html=True)
                st.info("🎞️ 正在分离音轨 & 逐帧解析...")
                st.progress(30)

            tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            tfile.write(video_file.read())
            video_path = tfile.name
            audio_path = video_path.replace(".mp4", ".wav")
            
            has_audio = extract_audio_from_video(video_path, audio_path)
            
            if not has_audio:
                loading_placeholder.empty()
                st.error("❌ 视频里没有声音呀！")
            else:
                data = analyze_audio_advanced(audio_path, st.session_state['baseline_pitch'])
                
                if data['status'] == 'error':
                    st.warning("⚠️ 未检测到猫叫声，将仅分析动作。")
                    data = {"pitch_trend": "未知", "duration": 0, "mean_pitch": 0} 
                
                ai_msg = ""
                if ai_ready:
                    with loading_placeholder.container():
                        st.markdown(render_b64_gif(BONGO_CAT_B64, width=150), unsafe_allow_html=True)
                        st.info("🐈 AI 大脑正在疯狂运转...")
                        st.progress(70)

                    try:
                        video_blob = genai.upload_file(video_path)
                        while video_blob.state.name == "PROCESSING":
                            time.sleep(1)
                            video_blob = genai.get_file(video_blob.name)

                        prompt = f"""
                        环境：{context}。
                        声音数据：{data}。
                        告诉我（猫）现在在抱怨什么或要什么。
                        """
                        response = model.generate_content([prompt, video_blob])
                        ai_msg = response.text
                    except Exception as e: 
                        st.error(f"AI 罢工了: {e}")

                loading_placeholder.empty()

                st.session_state['latest_analysis'] = {
                    "data": data,
                    "ai_result": ai_msg,
                    "video_path": video_file,
                    "type": "video"
                }
            
            try:
                os.remove(video_path)
                os.remove(audio_path)
            except: pass

    if st.session_state['latest_analysis'] and st.session_state['latest_analysis']['type'] == 'video':
        res = st.session_state['latest_analysis']
        st.success("✅ 多模态分析结束")
        if video_file: 
            st.video(video_file)
        
        st.markdown("### 🐱 主子说：")
        if res['ai_result']:
            st.info(f"“ {res['ai_result']} ”")
        else:
            st.info("AI 暂时无法连接。")
