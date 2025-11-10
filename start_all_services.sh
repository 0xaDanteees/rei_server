#!/bin/bash

# Script para levantar todos los servicios en desarrollo

echo "🚀 Starting all microservices..."
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Directorio base
BASE_DIR="/Users/dan/dev/waifu_solutions/reicam_server"

# Función para verificar si un puerto está en uso
check_port() {
    lsof -ti:$1 > /dev/null 2>&1
}

# Función para iniciar un servicio
start_service() {
    local name="$1"
    local port="$2"
    local path="$3"
    local cmd="$4"
    
    if check_port "$port"; then
        echo -e "${YELLOW}⚠️  $name already running on port $port${NC}"
    else
        echo -e "${GREEN}▶️  Starting $name on port $port...${NC}"
        cd "$path" || exit 1
        $cmd --host 0.0.0.0 --port "$port" --reload > "/tmp/${name// /_}.log" 2>&1 &
        echo $! > "/tmp/${name// /_}.pid"
        cd - > /dev/null || exit 1
    fi
}

# Iniciar servicios
start_service "API_Gateway" 8000 "$BASE_DIR/api" "uvicorn main:app"
sleep 1
start_service "Auth_Service" 8200 "$BASE_DIR/services/auth" "uvicorn app.main:app"
sleep 1
start_service "Partners_Service" 8300 "$BASE_DIR/services/partners" "uvicorn app.main:app"
sleep 1
start_service "Inventory_Service" 8400 "$BASE_DIR/services/inventory" "uvicorn app.main:app"
sleep 1
start_service "RAG_Service" 8500 "$BASE_DIR/services/rag" "uvicorn app.main:app"

echo ""
echo "✅ All services started!"
echo ""
echo "📍 Service URLs:"
echo "  - API Gateway:    http://localhost:8000"
echo "  - Auth:           http://localhost:8200/auth/docs"
echo "  - Partners:       http://localhost:8300/partners/docs"
echo "  - Inventory:      http://localhost:8400/inventory/docs"
echo "  - RAG:            http://localhost:8500/rag/docs"
echo ""
echo "📊 Health Check:"
echo "  curl http://localhost:8000/api/health"
echo ""
echo "🛑 To stop all services:"
echo "  ./stop_all_services.sh"
echo ""
