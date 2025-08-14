#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv
import aiohttp

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

async def clear_webhook():
    """Очищаем webhook и pending updates"""
    url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url) as response:
            result = await response.json()
            print(f"Webhook cleared: {result}")
            
    # Также очищаем все pending updates
    url2 = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset=-1"
    async with aiohttp.ClientSession() as session:
        async with session.post(url2) as response:
            result = await response.json()
            print(f"Updates cleared: {result}")

if __name__ == "__main__":
    asyncio.run(clear_webhook())