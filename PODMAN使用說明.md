# Podman 容器化部署說明

本專案支援使用 Podman（或 Docker）進行容器化部署，方便在任何環境快速啟動服務。

## 📋 前置需求

### macOS 安裝 Podman

```bash
# 使用 Homebrew 安裝
brew install podman

# 初始化 podman machine（首次使用）
podman machine init
podman machine start

# 驗證安裝
podman --version
```

### Linux 安裝 Podman

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y podman

# Fedora/CentOS/RHEL
sudo dnf install -y podman

# Arch Linux
sudo pacman -S podman
```

## 🚀 快速啟動

### 方法 1：使用腳本（推薦）

```bash
# 建置並啟動容器
./run-podman.sh --build

# 或直接啟動（如果映像檔已存在）
./run-podman.sh
```

腳本會自動：
- ✅ 檢查 podman 是否安裝
- ✅ 建置 Docker 映像檔
- ✅ 停止並移除舊容器
- ✅ 啟動新容器
- ✅ 掛載本地目錄
- ✅ 顯示服務狀態和日誌

### 方法 2：使用 docker-compose / podman-compose

```bash
# 使用 podman-compose（需先安裝）
pip install podman-compose
podman-compose up -d

# 或使用 docker-compose
docker-compose up -d
```

### 方法 3：手動執行 podman 指令

```bash
# 1. 建置映像檔
podman build -t omrchecker:latest .

# 2. 啟動容器
podman run -d \
    --name omrchecker-app \
    -p 7860:7860 \
    -v "$(pwd)/inputs:/app/inputs:z" \
    -v "$(pwd)/outputs:/app/outputs:z" \
    -v "$(pwd)/fonts:/app/fonts:z" \
    omrchecker:latest
```

## 🌐 訪問服務

容器啟動後，開啟瀏覽器訪問：

**http://localhost:7860**

## 📂 目錄掛載說明

容器會掛載以下本地目錄：

| 本地目錄 | 容器目錄 | 用途 |
|---------|---------|------|
| `./inputs` | `/app/inputs` | 放置要處理的 OMR 圖檔 |
| `./outputs` | `/app/outputs` | 辨識結果輸出位置 |
| `./fonts` | `/app/fonts` | 中文字體檔案（需手動放置） |

**重要：** 請將中文字體檔案放置到 `fonts/` 目錄：
```bash
cp ~/Library/Fonts/edukai-4.0.ttf fonts/TW-Kai.ttf
```

## 🔧 常用指令

### 容器管理

```bash
# 查看運行中的容器
podman ps

# 查看所有容器（包含停止的）
podman ps -a

# 停止容器
podman stop omrchecker-app

# 啟動容器
podman start omrchecker-app

# 重啟容器
podman restart omrchecker-app

# 刪除容器
podman rm omrchecker-app

# 強制刪除運行中的容器
podman rm -f omrchecker-app
```

### 日誌和除錯

```bash
# 查看容器日誌
podman logs omrchecker-app

# 即時查看日誌（追蹤模式）
podman logs -f omrchecker-app

# 查看最後 100 行日誌
podman logs --tail 100 omrchecker-app

# 進入容器執行指令
podman exec -it omrchecker-app /bin/bash

# 在容器內執行 Python 指令
podman exec omrchecker-app python --version
```

### 映像檔管理

```bash
# 列出所有映像檔
podman images

# 刪除映像檔
podman rmi omrchecker:latest

# 清理未使用的映像檔
podman image prune

# 查看映像檔詳細資訊
podman inspect omrchecker:latest
```

### 系統清理

```bash
# 停止所有容器
podman stop $(podman ps -aq)

# 刪除所有容器
podman rm $(podman ps -aq)

# 刪除所有未使用的資源（映像檔、容器、網路、快取）
podman system prune -a

# 查看磁碟使用情況
podman system df
```

## 🔄 更新部署

當程式碼更新後，重新建置並部署：

```bash
# 方法 1：使用腳本
./run-podman.sh --build

# 方法 2：手動執行
podman stop omrchecker-app
podman rm omrchecker-app
podman build -t omrchecker:latest .
podman run -d \
    --name omrchecker-app \
    -p 7860:7860 \
    -v "$(pwd)/inputs:/app/inputs:z" \
    -v "$(pwd)/outputs:/app/outputs:z" \
    -v "$(pwd)/fonts:/app/fonts:z" \
    omrchecker:latest
```

## 🌍 環境變數

可以透過 `-e` 選項設定環境變數：

```bash
podman run -d \
    --name omrchecker-app \
    -p 7860:7860 \
    -e GRADIO_SERVER_NAME=0.0.0.0 \
    -e GRADIO_SERVER_PORT=7860 \
    -v "$(pwd)/inputs:/app/inputs:z" \
    -v "$(pwd)/outputs:/app/outputs:z" \
    -v "$(pwd)/fonts:/app/fonts:z" \
    omrchecker:latest
```

## 🔐 安全性考量

### SELinux 支援（Linux）

在啟用 SELinux 的系統上，掛載目錄時需要加上 `:z` 或 `:Z` 標籤：

- `:z`：共享標籤（多個容器可以讀寫）
- `:Z`：私有標籤（只有此容器可以讀寫）

```bash
-v "$(pwd)/inputs:/app/inputs:z"  # 共享
-v "$(pwd)/outputs:/app/outputs:Z"  # 私有
```

### 資料持久化

容器刪除後，掛載的本地目錄資料不會遺失，但容器內部的資料會消失。

重要資料請務必掛載到本地目錄！

## 🐛 疑難排解

### 問題 1：Port 已被占用

**錯誤訊息：**
```
Error: cannot listen on the TCP port: listen tcp4 :7860: bind: address already in use
```

**解決方法：**
```bash
# 查看占用 7860 port 的程序
lsof -ti:7860

# 停止該程序
kill $(lsof -ti:7860)

# 或使用不同 port
podman run -d -p 8080:7860 ...
```

### 問題 2：Podman machine 未啟動（macOS）

**錯誤訊息：**
```
Error: cannot connect to Podman
```

**解決方法：**
```bash
# 啟動 podman machine
podman machine start

# 查看 machine 狀態
podman machine list
```

### 問題 3：中文字體顯示問題

**解決方法：**
```bash
# 確認字體檔案存在
ls -lh fonts/TW-Kai.ttf

# 如果不存在，複製字體
cp ~/Library/Fonts/edukai-4.0.ttf fonts/TW-Kai.ttf

# 重啟容器
podman restart omrchecker-app
```

### 問題 4：容器無法啟動

**解決方法：**
```bash
# 查看詳細日誌
podman logs omrchecker-app

# 檢查映像檔是否正確建置
podman images | grep omrchecker

# 重新建置映像檔
podman build --no-cache -t omrchecker:latest .
```

## 📊 效能優化

### 減少映像檔大小

Dockerfile 已使用 `python:3.12-slim` 作為基礎映像，並清理 apt 快取。

映像檔大小約：**1.5GB**（包含所有依賴）

### 快速重建

使用 Docker 多階段建置快取：
```bash
# 只有 requirements 改變時才重新安裝依賴
podman build --layers -t omrchecker:latest .
```

## 🚀 生產環境部署

### 使用 systemd 管理容器（Linux）

建立 systemd service 檔案：

```bash
sudo nano /etc/systemd/system/omrchecker.service
```

內容：
```ini
[Unit]
Description=OMRChecker Podman Container
After=network.target

[Service]
Type=simple
Restart=always
ExecStart=/usr/bin/podman start -a omrchecker-app
ExecStop=/usr/bin/podman stop -t 10 omrchecker-app

[Install]
WantedBy=multi-user.target
```

啟用服務：
```bash
sudo systemctl daemon-reload
sudo systemctl enable omrchecker
sudo systemctl start omrchecker
```

## 📚 相關資源

- **Podman 官方文件**: https://docs.podman.io/
- **Podman vs Docker**: https://podman.io/
- **Dockerfile 最佳實踐**: https://docs.docker.com/develop/develop-images/dockerfile_best-practices/

## 💡 提示

1. **首次建置會比較慢**（需下載所有依賴），之後會使用快取
2. **定期更新映像檔**以獲取最新的安全性更新
3. **使用 volume 掛載**確保資料不會遺失
4. **監控容器資源使用**：`podman stats omrchecker-app`

---

## ✅ 檢查清單

部署完成後，確認以下項目：

- [ ] Podman 已安裝並正常運作
- [ ] 映像檔建置成功
- [ ] 容器正常啟動
- [ ] http://localhost:7860 可以訪問
- [ ] 中文字體正常顯示
- [ ] inputs/outputs 目錄掛載正確
- [ ] 可以上傳檔案並處理

全部打勾表示部署成功！🎉
