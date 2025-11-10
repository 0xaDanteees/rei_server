#!/bin/bash

# Script maestro de DevOps para desarrollo local

set -e

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

show_help() {
    echo -e "${CYAN}🚀 Waifu Solutions - DevOps Script${NC}"
    echo ""
    echo "Usage: ./dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start       - Inicia todos los microservicios"
    echo "  stop        - Detiene todos los microservicios"
    echo "  restart     - Reinicia todos los microservicios"
    echo "  status      - Muestra el estado de los servicios"
    echo "  health      - Verifica el health de todos los servicios"
    echo "  logs        - Muestra los logs de todos los servicios"
    echo "  clean       - Limpia logs y archivos temporales"
    echo "  migrate     - Corre las migraciones de base de datos"
    echo "  test        - Corre todos los tests"
    echo "  help        - Muestra esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  ./dev.sh start"
    echo "  ./dev.sh health"
    echo "  ./dev.sh logs"
    echo ""
}

check_env() {
    if [ ! -f ".env" ]; then
        echo -e "${RED}❌ Error: .env file not found${NC}"
        echo "Crea un archivo .env con POSTGRES_DSN configurado"
        exit 1
    fi
    
    if ! grep -q "POSTGRES_DSN" .env; then
        echo -e "${YELLOW}⚠️  Warning: POSTGRES_DSN not found in .env${NC}"
        echo "Asegúrate de tener POSTGRES_DSN configurado"
    fi
}

start_services() {
    echo -e "${GREEN}🚀 Starting all services...${NC}"
    ./start_all_services.sh
}

stop_services() {
    echo -e "${RED}🛑 Stopping all services...${NC}"
    ./stop_all_services.sh
}

restart_services() {
    echo -e "${YELLOW}🔄 Restarting all services...${NC}"
    stop_services
    sleep 2
    start_services
}

show_status() {
    echo -e "${BLUE}📊 Service Status:${NC}"
    echo ""
    
    ports=(8000 8200 8300 8400 8500)
    names=("API Gateway" "Auth" "Partners" "Inventory" "RAG")
    
    for i in "${!ports[@]}"; do
        port="${ports[$i]}"
        name="${names[$i]}"
        
        if lsof -ti:$port > /dev/null 2>&1; then
            pid=$(lsof -ti:$port)
            echo -e "  ${GREEN}✓${NC} $name (port $port, PID: $pid)"
        else
            echo -e "  ${RED}✗${NC} $name (port $port) - Not running"
        fi
    done
    echo ""
}

check_health() {
    echo -e "${BLUE}🏥 Checking health...${NC}"
    echo ""
    chmod +x verify_health.sh
    ./verify_health.sh
}

show_logs() {
    echo -e "${BLUE}📋 Service Logs:${NC}"
    echo ""
    
    if [ -f "/tmp/API_Gateway.log" ]; then
        echo -e "${CYAN}=== API Gateway ===${NC}"
        tail -n 20 /tmp/API_Gateway.log
        echo ""
    fi
    
    if [ -f "/tmp/Auth_Service.log" ]; then
        echo -e "${CYAN}=== Auth Service ===${NC}"
        tail -n 20 /tmp/Auth_Service.log
        echo ""
    fi
    
    if [ -f "/tmp/Partners_Service.log" ]; then
        echo -e "${CYAN}=== Partners Service ===${NC}"
        tail -n 20 /tmp/Partners_Service.log
        echo ""
    fi
    
    if [ -f "/tmp/Inventory_Service.log" ]; then
        echo -e "${CYAN}=== Inventory Service ===${NC}"
        tail -n 20 /tmp/Inventory_Service.log
        echo ""
    fi
    
    if [ -f "/tmp/RAG_Service.log" ]; then
        echo -e "${CYAN}=== RAG Service ===${NC}"
        tail -n 20 /tmp/RAG_Service.log
        echo ""
    fi
}

clean_temp() {
    echo -e "${YELLOW}🧹 Cleaning temporary files...${NC}"
    rm -f /tmp/API_Gateway.* /tmp/Auth_Service.* /tmp/Partners_Service.* /tmp/Inventory_Service.* /tmp/RAG_Service.*
    echo -e "${GREEN}✓ Cleaned${NC}"
}

run_migrations() {
    echo -e "${BLUE}🗄️  Running migrations...${NC}"
    echo ""
    
    echo "Auth Service..."
    make auth-up
    
    echo "Partners Service..."
    make partners-up
    
    echo "Inventory Service..."
    make inventory-up
    
    echo "RAG Service..."
    make rag-up
    
    echo ""
    echo -e "${GREEN}✓ Migrations completed${NC}"
}

run_tests() {
    echo -e "${BLUE}🧪 Running tests...${NC}"
    echo ""
    pytest -v
}

# Main
case "${1:-help}" in
    start)
        check_env
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        check_env
        restart_services
        ;;
    status)
        show_status
        ;;
    health)
        check_health
        ;;
    logs)
        show_logs
        ;;
    clean)
        clean_temp
        ;;
    migrate)
        check_env
        run_migrations
        ;;
    test)
        run_tests
        ;;
    help|*)
        show_help
        ;;
esac
