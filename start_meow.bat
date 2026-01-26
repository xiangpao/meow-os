@echo off
:: 1. 强制屏蔽所有系统代理，解决 SSL 报错
set NO_PROXY=*

:: 2. 设置 Python 使用 Clash 代理连接谷歌 (仅限代码内部)
:: 如果你的 Clash 端口不是 7890，请修改下面两行
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890

:: 3. 启动程序
echo 正在启动喵星人解码器...
streamlit run app.py
pause