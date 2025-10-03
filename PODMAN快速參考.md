# Podman 快速參考卡

## 🚀 快速啟動

```bash
# 一鍵啟動（首次使用）
./run-podman.sh --build

# 後續啟動（映像檔已存在）
./run-podman.sh
```

**訪問服務：** http://localhost:7860

---

## 📝 常用指令速查表

### 容器操作

| 指令 | 說明 |
|------|------|
| `podman ps` | 查看運行中的容器 |
| `podman ps -a` | 查看所有容器 |
| `podman start omrchecker-app` | 啟動容器 |
| `podman stop omrchecker-app` | 停止容器 |
| `podman restart omrchecker-app` | 重啟容器 |
| `podman rm omrchecker-app` | 刪除容器 |
| `podman rm -f omrchecker-app` | 強制刪除 |

### 日誌查看

| 指令 | 說明 |
|------|------|
| `podman logs omrchecker-app` | 查看日誌 |
| `podman logs -f omrchecker-app` | 即時追蹤日誌 |
| `podman logs --tail 50 omrchecker-app` | 查看最後 50 行 |

### 映像檔管理

| 指令 | 說明 |
|------|------|
| `podman images` | 列出所有映像檔 |
| `podman rmi omrchecker:latest` | 刪除映像檔 |
| `podman build -t omrchecker:latest .` | 建置映像檔 |
| `podman image prune` | 清理未使用的映像檔 |

### 進入容器

| 指令 | 說明 |
|------|------|
| `podman exec -it omrchecker-app /bin/bash` | 進入容器 shell |
| `podman exec omrchecker-app ls /app` | 執行指令 |
| `podman exec omrchecker-app python --version` | 檢查 Python 版本 |

---

## 🔧 重新部署流程

```bash
# 1. 停止並刪除舊容器
podman stop omrchecker-app
podman rm omrchecker-app

# 2. 重新建置映像檔
podman build -t omrchecker:latest .

# 3. 啟動新容器
./run-podman.sh
```

**或一鍵完成：**
```bash
./run-podman.sh --build
```

---

## 📂 目錄結構

```
OMRChecker/
├── Dockerfile              # Docker 映像檔定義
├── .dockerignore          # 排除檔案清單
├── docker-compose.yml     # Compose 配置
├── run-podman.sh          # 啟動腳本
├── inputs/                # 輸入檔案目錄（掛載）
├── outputs/               # 輸出結果目錄（掛載）
└── fonts/                 # 字體檔案目錄（掛載）
    └── TW-Kai.ttf        # 中文字體（需手動放置）
```

---

## ⚠️ 常見問題

### Port 被占用

```bash
# 停止占用 7860 的程序
kill $(lsof -ti:7860)

# 或使用不同 port
podman run -d -p 8080:7860 ...
```

### 中文字體問題

```bash
# 複製字體到專案
cp ~/Library/Fonts/edukai-4.0.ttf fonts/TW-Kai.ttf

# 重啟容器
podman restart omrchecker-app
```

### 清理所有資源

```bash
# 停止所有容器
podman stop $(podman ps -aq)

# 刪除所有容器
podman rm $(podman ps -aq)

# 清理系統
podman system prune -a
```

---

## 💡 效能監控

```bash
# 查看容器資源使用
podman stats omrchecker-app

# 查看容器詳細資訊
podman inspect omrchecker-app

# 查看磁碟使用
podman system df
```

---

## 📚 更多資訊

- **完整文件**: 見 `PODMAN使用說明.md`
- **環境設定**: 見 `環境設定說明.md`
- **快速開始**: 見 `快速開始.md`
