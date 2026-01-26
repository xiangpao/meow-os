import os

# --- 这里粘贴你的密钥 ---
my_key = input("请粘贴你的 Gemini API Key 并回车: ").strip()

# 1. 创建 .streamlit 文件夹
folder_name = ".streamlit"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)
    print(f"✅ 文件夹 {folder_name} 创建成功")
else:
    print(f"ℹ️ 文件夹 {folder_name} 已存在")

# 2. 写入 secrets.toml
file_path = os.path.join(folder_name, "secrets.toml")
content = f'GOOGLE_API_KEY = "{my_key}"'

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✅ 密钥已写入 {file_path}")
print("🚀 配置完成！你可以运行主程序了。")
input("按回车键退出...")