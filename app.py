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
    
    /* 标题样式：圆润、深咖啡色 */
    h1 { 
        color: #5D4037 !important; 
        font-family: 'Comic Sans MS', 'ZKKuaiLe', '幼圆', sans-serif !important;
        font-weight: 800;
        text-shadow: 2px 2px 0px #FFF;
    }
    
    /* 顶部动图容器居中 */
    .stImage {
        text-align: center;
        margin-bottom: -20px;
    }
    
    /* 卡片/折叠面板：像一块白色的方糖，圆角 */
    .stExpander, .css-1r6slb0, [data-testid="stFileUploadDropzone"] {
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
    p, label, .stMarkdown {
        color: #4E342E !important;
        font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
