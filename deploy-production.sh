#!/bin/bash

# ==============================================================================
# Brain AI 系統 - 完整生產部署腳本
# ==============================================================================

set -e  # 遇到錯誤立即停止

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Brain AI 系統 - 生產環境部署${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# ==============================================================================
# 1. 檢查必要參數
# ==============================================================================
if [ -z "$1" ]; then
    echo -e "${RED}錯誤：請提供您的網域名稱${NC}"
    echo "用法: sudo ./deploy-production.sh yourdomain.com"
    exit 1
fi

DOMAIN=$1
EMAIL="admin@${DOMAIN}"

echo -e "${YELLOW}網域：${DOMAIN}${NC}"
echo -e "${YELLOW}Email：${EMAIL}${NC}"
echo ""

# ==============================================================================
# 2. 系統環境檢查
# ==============================================================================
echo -e "${GREEN}[1/7] 檢查系統環境...${NC}"

# 檢查是否為 root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}請使用 sudo 執行此腳本${NC}"
    exit 1
fi

# 更新系統
apt-get update -qq

# ==============================================================================
# 3. 安裝 Docker (如果未安裝)
# ==============================================================================
echo -e "${GREEN}[2/7] 檢查 Docker...${NC}"

if ! command -v docker &> /dev/null; then
    echo "Docker 未安裝，正在安裝..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $SUDO_USER
    echo "Docker 安裝完成"
else
    echo "Docker 已安裝"
fi

# ==============================================================================
# 4. 安裝 Nginx
# ==============================================================================
echo -e "${GREEN}[3/7] 安裝 Nginx...${NC}"

if ! command -v nginx &> /dev/null; then
    apt-get install -y nginx
    systemctl enable nginx
    echo "Nginx 安裝完成"
else
    echo "Nginx 已安裝"
fi

# ==============================================================================
# 5. 配置 Nginx
# ==============================================================================
echo -e "${GREEN}[4/7] 配置 Nginx...${NC}"

# 從模板生成配置
sed "s/DOMAIN_PLACEHOLDER/${DOMAIN}/g" nginx.conf.template > /etc/nginx/sites-available/brain

# 啟用站點
ln -sf /etc/nginx/sites-available/brain /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 測試配置
nginx -t

# 重啟 Nginx
systemctl restart nginx

echo "Nginx 配置完成"

# ==============================================================================
# 6. 安裝 SSL 證書 (Certbot)
# ==============================================================================
echo -e "${GREEN}[5/7] 安裝 SSL 證書...${NC}"

if ! command -v certbot &> /dev/null; then
    apt-get install -y certbot python3-certbot-nginx
fi

# 申請證書
certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos --email ${EMAIL} --redirect

echo "SSL 證書安裝完成"

# ==============================================================================
# 7. 設定 Swap (針對小記憶體 VM)
# ==============================================================================
echo -e "${GREEN}[6/7] 設定 Swap 空間...${NC}"

if [ ! -f /swapfile ]; then
    echo "建立 2GB Swap..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "Swap 設定完成"
else
    echo "Swap 已存在"
fi

# ==============================================================================
# 8. 部署 Docker 容器
# ==============================================================================
echo -e "${GREEN}[7/7] 部署 Brain 容器...${NC}"

# 停止舊容器
docker compose down 2>/dev/null || true

# 建置並啟動
docker compose up -d --build

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  🎉 部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "訪問您的網站: ${YELLOW}https://${DOMAIN}${NC}"
echo -e "API 文件: ${YELLOW}https://${DOMAIN}/api/docs${NC}"
echo -e "LINE Webhook URL: ${YELLOW}https://${DOMAIN}/webhook/line${NC}"
echo ""
echo -e "${YELLOW}下一步：${NC}"
echo "1. 訪問 https://${DOMAIN} 確認網站運作"
echo "2. 在設定頁面填入 API Keys (Claude, LINE)"
echo "3. 在 LINE Console 設定 Webhook URL"
echo ""
echo -e "${GREEN}部署日誌已記錄${NC}"
