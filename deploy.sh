#!/bin/bash

# 顏色定義
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}🚀 開始部署 Brain 系統...${NC}"

# 1. 檢查 Docker 是否安裝
if ! command -v docker &> /dev/null; then
    echo "Docker 未安裝，正在安裝..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "Docker 安裝完成，請重新登入以套用群組變更"
    exit 1
fi

# 2. 檢查 Docker Compose
if ! docker compose version &> /dev/null; then
    echo "Docker Compose 未安裝或版本過舊"
    # 新版 Docker 已內建 compose，通常不需要額外安裝
fi

# 3. 設定 Swap (針對小記憶體 VM)
if [ ! -f /swapfile ]; then
    echo -e "${GREEN}📦 設定 2GB Swap 空間...${NC}"
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

# 4. 停止舊容器
echo -e "${GREEN}🛑 停止舊服務...${NC}"
docker compose down

# 5. 重新建置並啟動
echo -e "${GREEN}🏗️ 建置並啟動服務...${NC}"
docker compose up -d --build

echo -e "${GREEN}✅ 部署完成！${NC}"
echo -e "前端訪問: http://<YOUR_VM_IP>"
echo -e "後端 API: http://<YOUR_VM_IP>/api"
