#!/bin/bash

# Stop script for SWE-AGI dual containers

echo "Stopping SWE-AGI dual containers..."
docker-compose down

if [ $? -eq 0 ]; then
    echo "✓ Containers stopped and removed"
else
    echo "❌ Failed to stop containers"
    exit 1
fi
