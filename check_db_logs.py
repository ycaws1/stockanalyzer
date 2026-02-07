
import asyncio
import os
import sys
from sqlalchemy.future import select
from sqlalchemy import desc

# Add the parent directory to sys.path to import app
sys.path.append(os.getcwd())

from backend.app.database import AsyncSessionLocal
from backend.app.models import NotificationLog

async def check_logs():
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(NotificationLog).order_by(NotificationLog.timestamp.desc()).limit(20)
            )
            logs = result.scalars().all()
            if not logs:
                print("No logs found.")
                return
            for log in logs:
                print(f"ID: {log.id}, Ticker: {log.ticker}, Tag: {log.tag}, Value: {log.value:.4f}, Time: {log.timestamp}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_logs())
