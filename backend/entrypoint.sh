#!/bin/sh
set -e

# Build frontend
cd /app/../frontend
npm install
npm run build

# Copy build to backend static
cp -R build/. /app/static/

# Start backend
cd /app
exec uvicorn main:app --host 0.0.0.0 --port 8000
