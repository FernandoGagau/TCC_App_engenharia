#!/bin/bash
# Script para inicializar buckets no MinIO

echo "🚀 Iniciando MinIO..."
docker-compose up -d minio

echo "⏳ Aguardando MinIO inicializar..."
sleep 5

echo "📦 Criando buckets no MinIO..."

# Instala mc (MinIO Client) se não existir
if ! command -v mc &> /dev/null; then
    echo "Instalando MinIO Client..."
    docker exec construction_agent_minio mc alias set local http://localhost:9000 minioadmin minioadmin123
fi

# Cria buckets
docker exec construction_agent_minio mc mb local/construction-images --ignore-existing
docker exec construction_agent_minio mc mb local/construction-documents --ignore-existing

# Define política pública para leitura (opcional)
docker exec construction_agent_minio mc anonymous set download local/construction-images
docker exec construction_agent_minio mc anonymous set download local/construction-documents

echo "✅ MinIO inicializado com sucesso!"
echo "📊 Console: http://localhost:9001 (minioadmin / minioadmin123)"
echo "🔌 API: http://localhost:9000"
