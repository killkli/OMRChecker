# 使用 Python 3.12 官方映像檔作為基礎
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴（OpenCV 需要）
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 安裝 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 複製專案配置檔案（包含 README.md，pyproject.toml 需要）
COPY pyproject.toml .python-version README.md ./
COPY uv.lock ./

# 安裝 Python 依賴（使用 uv）
RUN uv sync --frozen --no-dev

# 複製整個專案
COPY . .

# 建立必要的目錄
RUN mkdir -p inputs outputs fonts

# 暴露 Gradio 預設 port
EXPOSE 7860

# 設定環境變數
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT="7860"

# 啟動 Gradio 界面
CMD ["uv", "run", "python", "frontend/app.py"]
