#!/bin/bash

# HabitMax Mini App Setup Script

echo "🚀 Setting up HabitMax Mini App..."

# Backend setup
echo "📦 Setting up backend..."
cd api
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy aiosqlite pydantic-settings aiohttp httpx

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Please edit api/.env with your credentials"
fi

cd ..

# Frontend setup
echo "📦 Setting up frontend..."
cd webapp
npm install

# Create .env.local if not exists
if [ ! -f .env.local ]; then
    cp .env.example .env.local
    echo "⚠️  Please edit webapp/.env.local with your API URL"
fi

cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start development:"
echo "  1. Backend: cd api && source venv/bin/activate && uvicorn main:app --reload"
echo "  2. Frontend: cd webapp && npm run dev"
echo ""
echo "Don't forget to:"
echo "  - Edit api/.env with your BOT_TOKEN and OPENROUTER_API_KEY"
echo "  - Configure your bot with @BotFather"
