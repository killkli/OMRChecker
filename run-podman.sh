#!/bin/bash

# OMRChecker Podman 啟動腳本
# 用於在 macOS 上使用 podman 運行 OMRChecker

set -e

IMAGE_NAME="omrchecker"
IMAGE_TAG="latest"
CONTAINER_NAME="omrchecker-app"
PORT="7860"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 OMRChecker Podman 啟動腳本${NC}"
echo ""

# 檢查 podman 是否安裝
if ! command -v podman &> /dev/null; then
    echo -e "${RED}❌ 錯誤：找不到 podman${NC}"
    echo "請先安裝 podman："
    echo "  brew install podman"
    exit 1
fi

echo -e "${GREEN}✅ 找到 podman$(podman --version)${NC}"

# 檢查是否需要重新建置映像檔
BUILD=false
if [[ "$1" == "--build" ]] || [[ "$1" == "-b" ]]; then
    BUILD=true
fi

# 檢查映像檔是否存在
if ! podman image exists ${IMAGE_NAME}:${IMAGE_TAG}; then
    echo -e "${YELLOW}⚠️  映像檔不存在，開始建置...${NC}"
    BUILD=true
fi

# 建置映像檔
if [ "$BUILD" = true ]; then
    echo -e "${GREEN}🔨 建置 Docker 映像檔...${NC}"
    podman build -t ${IMAGE_NAME}:${IMAGE_TAG} .

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 映像檔建置成功！${NC}"
    else
        echo -e "${RED}❌ 映像檔建置失敗${NC}"
        exit 1
    fi
fi

# 停止並移除舊容器（如果存在）
if podman ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}⚠️  移除舊容器...${NC}"
    podman stop ${CONTAINER_NAME} 2>/dev/null || true
    podman rm ${CONTAINER_NAME} 2>/dev/null || true
fi

# 啟動容器
echo -e "${GREEN}🚀 啟動容器...${NC}"

# 建立本地掛載目錄（如果不存在）
mkdir -p ./inputs ./outputs ./fonts

podman run -d \
    --name ${CONTAINER_NAME} \
    -p ${PORT}:7860 \
    -v "$(pwd)/inputs:/app/inputs:z" \
    -v "$(pwd)/outputs:/app/outputs:z" \
    -v "$(pwd)/fonts:/app/fonts:z" \
    ${IMAGE_NAME}:${IMAGE_TAG}

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ 容器啟動成功！${NC}"
    echo ""
    echo "📊 容器資訊："
    echo "  名稱: ${CONTAINER_NAME}"
    echo "  映像: ${IMAGE_NAME}:${IMAGE_TAG}"
    echo "  Port: ${PORT}"
    echo ""
    echo "🌐 Gradio 界面："
    echo -e "  ${GREEN}http://localhost:${PORT}${NC}"
    echo ""
    echo "📝 常用指令："
    echo "  查看日誌: podman logs -f ${CONTAINER_NAME}"
    echo "  停止容器: podman stop ${CONTAINER_NAME}"
    echo "  刪除容器: podman rm ${CONTAINER_NAME}"
    echo "  進入容器: podman exec -it ${CONTAINER_NAME} /bin/bash"
    echo ""

    # 等待服務啟動
    echo -e "${YELLOW}⏳ 等待服務啟動...${NC}"
    sleep 3

    # 顯示日誌
    echo ""
    echo "📋 容器日誌（前幾行）："
    echo "---"
    podman logs ${CONTAINER_NAME} 2>&1 | head -n 20
    echo "---"
    echo ""
    echo -e "${GREEN}🎉 服務已就緒！請開啟瀏覽器訪問 http://localhost:${PORT}${NC}"
else
    echo -e "${RED}❌ 容器啟動失敗${NC}"
    exit 1
fi
