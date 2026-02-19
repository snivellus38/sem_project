#!/usr/bin/env bash
# build.sh — Build script for Render deployment
# Installs Python deps, builds React frontend, copies dist → static/

set -o errexit  # exit on error

echo "=== Installing Python dependencies ==="
pip install -r backend/requirements.txt

echo "=== Installing Node dependencies ==="
cd frontend
npm ci

echo "=== Building React frontend ==="
npm run build

echo "=== Copying build to static/ ==="
cd ..
rm -rf static
cp -r frontend/dist static

echo "=== Build complete ==="
