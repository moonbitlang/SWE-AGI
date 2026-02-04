#!/bin/bash

# Docker run script for SWE-AGI dual containers (client-server)
# Mounts local moonbit-proj directory to container workspace
# Containers communicate via REST API over bridge network

IMAGE_NAME="swe-agi:latest"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Check if image exists
if ! docker images | grep -q "swe-agi"; then
    echo "Error: Image $IMAGE_NAME not found. Please build it first:"
    echo "  docker build -t $IMAGE_NAME ."
    exit 1
fi

echo "================================================"
echo "Starting SWE-AGI Dual Containers"
echo "================================================"
echo "Workspace: $(pwd)"
echo "Timestamp: $TIMESTAMP"
echo ""

# Export environment variables for docker-compose
export TIMESTAMP

# Start containers using docker-compose
echo "Starting containers with docker-compose..."
docker-compose up -d

if [ $? -eq 0 ]; then
    echo ""
    echo "================================================"
    echo "Containers started successfully!"
    echo "================================================"
    echo ""
    echo "Container names:"
    echo "  Server: swe-agi-server-${TIMESTAMP}"
    echo "  Client: swe-agi-client-${TIMESTAMP}"
    echo ""
    echo "View logs:"
    echo "  Server: docker logs -f swe-agi-server-${TIMESTAMP}"
    echo "  Client: docker logs -f swe-agi-client-${TIMESTAMP}"
    echo "  Both:   docker-compose logs -f"
    echo ""
    echo "Test API connection:"
    echo "  docker exec -it swe-agi-client-${TIMESTAMP} curl http://server:8080/health"
    echo ""
    echo "Enter client container:"
    echo "  docker exec -it swe-agi-client-${TIMESTAMP} bash"
    echo ""
    echo "Stop containers:"
    echo "  docker-compose down"
    echo ""
    echo "To save changes as image:"
    echo "  docker commit swe-agi-server-${TIMESTAMP} swe-agi:server-saved"
    echo "  docker commit swe-agi-client-${TIMESTAMP} swe-agi:client-saved"
    echo ""
else
    echo ""
    echo "❌ Failed to start containers"
    exit 1
fi
