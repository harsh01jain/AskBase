#!/bin/bash

echo "========================================="
echo "       QueryLocal - 1-Click Setup"
echo "========================================="
echo ""

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed or not running."
    echo "Please install Docker: https://www.docker.com/"
    exit 1
fi

# Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo "[ERROR] Ollama is not installed."
    echo "Please install Ollama: https://ollama.com/"
    exit 1
fi

echo "Which AI model would you like to run?"
echo "(Recommended: qwen2.5-coder:7b)"
read -p "Enter model name (or press Enter for default): " MODEL_NAME

if [ -z "$MODEL_NAME" ]; then
    MODEL_NAME="qwen2.5-coder:7b"
fi

echo ""
echo "Save choice to .env file..."
echo "OLLAMA_MODEL=$MODEL_NAME" > .env

echo ""
echo "Pulling $MODEL_NAME... (This may take a moment if not already downloaded)"
ollama pull "$MODEL_NAME"

echo ""
echo "Starting Docker containers..."
docker-compose up --build
