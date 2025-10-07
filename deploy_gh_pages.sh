#!/bin/bash

# 專案根目錄
PROJECT_ROOT=$(pwd)
# 來源目錄
SOURCE_DIR="serverless_web"
# 臨時部署目錄
DEPLOY_DIR="/tmp/gh-pages-deploy"

echo "正在準備部署 gh-pages..."

# 1. 清理舊的臨時部署目錄 (如果存在)
if [ -d "$DEPLOY_DIR" ]; then
  echo "正在清理舊的部署目錄: $DEPLOY_DIR"
  rm -rf "$DEPLOY_DIR"
fi

# 2. 創建新的臨時部署目錄
echo "正在創建新的部署目錄: $DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

# 3. 將 serverless_web 的內容複製到臨時目錄
echo "正在複製 $SOURCE_DIR 的內容到 $DEPLOY_DIR"
cp -r "$PROJECT_ROOT/$SOURCE_DIR/." "$DEPLOY_DIR"

# 4. 進入臨時目錄並執行 Git 操作
echo "正在進入部署目錄並執行 Git 操作..."
cd "$DEPLOY_DIR"

# 初始化 Git 倉庫 (如果尚未初始化)
git init

# 添加遠端倉庫 (如果尚未添加)
# 這裡假設遠端名稱為 origin，並且指向當前專案的倉庫
if ! git remote -v | grep -q "origin"; then
  echo "正在添加遠端倉庫 'origin'..."
  git remote add origin "$(git -C "$PROJECT_ROOT" config --get remote.origin.url)"
fi

# 添加所有文件
echo "正在添加所有文件到 Git 暫存區..."
git add .

# 提交更改
echo "正在提交更改..."
git commit -m "Deploy gh-pages from $SOURCE_DIR"

# 5. 強制推送到 gh-pages 分支
echo "正在強制推送到 gh-pages 分支..."
echo "警告: 這將覆寫 gh-pages 分支的歷史記錄！"
git push origin HEAD:gh-pages --force

# 6. 返回專案根目錄並清理臨時目錄
echo "部署完成。正在清理臨時目錄..."
cd "$PROJECT_ROOT"
rm -rf "$DEPLOY_DIR"

echo "gh-pages 部署成功！"