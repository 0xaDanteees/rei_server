#!/bin/bash

# Script para detener todos los servicios

echo "🛑 Stopping all microservices..."
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Función para detener un servicio
stop_service() {
    local name="$1"
    local pidfile="/tmp/${name}.pid"
    
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${RED}⏹️  Stopping $name (PID: $pid)${NC}"
            kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null
            rm "$pidfile"
        else
            echo -e "${GREEN}✓ $name not running${NC}"
            rm "$pidfile"
        fi
    else
        echo -e "${GREEN}✓ $name not running${NC}"
    fi
}

# Detener servicios
stop_service "API_Gateway"
stop_service "Auth_Service"
stop_service "Partners_Service"
stop_service "Inventory_Service"
stop_service "RAG_Service"

# Limpiar logs
rm -f /tmp/API_Gateway.log /tmp/Auth_Service.log /tmp/Partners_Service.log /tmp/Inventory_Service.log /tmp/RAG_Service.log

echo ""
echo "✅ All services stopped!"
echo ""
