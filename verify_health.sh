#!/bin/bash

# Script para verificar el health de todos los servicios

echo "🔍 Verificando health de todos los servicios..."
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Función para verificar un servicio
check_service() {
    local name="$1"
    local url="$2"
    
    echo -n "Checking $name... "
    
    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        # Verificar si tiene conexión a DB
        if echo "$body" | grep -q '"db":"up"'; then
            echo -e "${GREEN}✓ OK (DB Connected)${NC}"
            echo "  Response: $body"
        elif echo "$body" | grep -q '"status":"ok"'; then
            echo -e "${GREEN}✓ OK${NC}"
            echo "  Response: $body"
        else
            echo -e "${YELLOW}⚠ OK pero respuesta inesperada${NC}"
            echo "  Response: $body"
        fi
    elif [ "$http_code" = "000" ]; then
        echo -e "${RED}✗ FAILED (No responde)${NC}"
    else
        echo -e "${RED}✗ FAILED (HTTP $http_code)${NC}"
        echo "  Response: $body"
    fi
    echo ""
}

# Verificar servicios individuales
echo -e "${BLUE}=== Servicios Individuales ===${NC}"
echo ""
check_service "Auth Service      " "http://localhost:8200/auth/health"
check_service "Partners Service  " "http://localhost:8300/partners/health"
check_service "Inventory Service " "http://localhost:8400/inventory/health"
check_service "RAG Service       " "http://localhost:8500/rag/health"

# Verificar API Gateway
echo -e "${BLUE}=== API Gateway (Agregado) ===${NC}"
echo ""
check_service "API Gateway       " "http://localhost:8000/api/health"

# Resumen
echo ""
echo -e "${BLUE}=== Resumen ===${NC}"
echo ""
echo "Si todos los servicios muestran:"
echo "  ✓ OK (DB Connected) - Todo funciona correctamente con Supabase"
echo ""
echo "Si ves errores:"
echo "  1. Verifica que POSTGRES_DSN esté en .env"
echo "  2. Verifica que los servicios estén corriendo: lsof -i :8000,8200,8300,8400,8500"
echo "  3. Revisa los logs: tail -f /tmp/*.log"
echo ""
