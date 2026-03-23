#!/bin/bash

set -e

# ─── Colors ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()     { echo -e "${GREEN}[+] $1${NC}"; }
warn()    { echo -e "${YELLOW}[!] $1${NC}"; }
error()   { echo -e "${RED}[✗] $1${NC}"; exit 1; }

# ─── Config ───
PROJECT_DIR="/root/veg-BE/Veggafresh_backend"
BUILD_DIR="$PROJECT_DIR/svv_store"
BRANCH="${1:-main}"
CONTAINER_NAME="veggafresh"
IMAGE_NAME="veggafresh-backend"
PORT="8000"

echo ""
echo "========================================"
echo "   VeggaFresh Backend Deployment"
echo "   Branch: $BRANCH"
echo "========================================"
echo ""

# ─── Step 1: Pull latest code ───
log "Pulling latest code from branch: $BRANCH"
cd "$PROJECT_DIR"
git pull origin "$BRANCH" || error "Git pull failed"

# ─── Step 2: Stop & remove existing container ───
log "Stopping existing container..."
if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
    docker stop "$CONTAINER_NAME"
    log "Container stopped"
else
    warn "No running container found, skipping stop"
fi

log "Removing existing container..."
if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
    docker rm "$CONTAINER_NAME"
    log "Container removed"
else
    warn "No container to remove, skipping"
fi

# ─── Step 3: Build new image ───
log "Building Docker image..."
cd "$BUILD_DIR"
docker build -t "$IMAGE_NAME" . || error "Docker build failed"

# ─── Step 4: Run new container ───
log "Starting new container..."
docker run -d -p "$PORT:$PORT" --name "$CONTAINER_NAME" "$IMAGE_NAME" || error "Docker run failed"

# ─── Step 5: Restart nginx ───
log "Restarting nginx..."
sudo systemctl restart nginx || error "Nginx restart failed"

# ─── Done ───
echo ""
echo "========================================"
echo -e "   ${GREEN}Deployment complete!${NC}"
echo "   Container : $CONTAINER_NAME"
echo "   Port      : $PORT"
echo "   Branch    : $BRANCH"
echo "========================================"
echo ""
