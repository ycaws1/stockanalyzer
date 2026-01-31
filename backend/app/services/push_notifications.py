"""
Web Push Notification Service for Stock Alerts
Sends notifications when stocks move beyond configurable thresholds.
"""
import os
import json
import asyncio
from typing import Dict, Set, List
from pywebpush import webpush, WebPushException
from sqlalchemy.future import select
from ..database import AsyncSessionLocal
from ..models import PushSubscription

from dotenv import load_dotenv
load_dotenv()  # Load .env before reading env vars

# ============================================
# CONFIGURABLE THRESHOLDS
# ============================================
# 1H Change Threshold (in percent) - triggers notification if |change| > this value
THRESHOLD_1H = float(os.getenv('ALERT_THRESHOLD_1H', '2.0'))

# 1D Change Threshold (in percent) - triggers notification if |change| > this value
THRESHOLD_1D = float(os.getenv('ALERT_THRESHOLD_1D', '3.5'))

# VAPID Keys - Generate your own at https://vapidkeys.com/
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', '')
VAPID_CLAIMS = {"sub": os.getenv('VAPID_SUBJECT', 'mailto:admin@stockanalyzer.local')}


class PushNotificationService:
    """
    Manages web push subscriptions and sends notifications for stock alerts.
    """
    # Track notified stocks to avoid duplicate notifications
    # Format: { "ticker-tag": {"value": 2.5, "timestamp": datetime} }
    _notified_stocks: Dict[str, dict] = {}
    
    @classmethod
    def get_thresholds(cls) -> dict:
        """Return current threshold configuration."""
        return {
            "threshold_1h": THRESHOLD_1H,
            "threshold_1d": THRESHOLD_1D
        }
    
    @classmethod
    async def add_subscription(cls, sub_data: dict) -> bool:
        """Add a push subscription, updating its keys if it already exists."""
        endpoint = sub_data.get("endpoint", "")
        keys = sub_data.get("keys", {})
        
        async with AsyncSessionLocal() as db:
            # Check if subscription already exists for this endpoint
            result = await db.execute(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
            existing_sub = result.scalars().first()
            
            if existing_sub:
                # Update existing record
                existing_sub.keys_auth = keys.get("auth")
                existing_sub.keys_p256dh = keys.get("p256dh")
                print(f"[Push] Updated existing subscription: {endpoint[:50]}...")
            else:
                # Create new record
                new_sub = PushSubscription(
                    endpoint=endpoint,
                    keys_auth=keys.get("auth"),
                    keys_p256dh=keys.get("p256dh")
                )
                db.add(new_sub)
                print(f"[Push] Added new subscription: {endpoint[:50]}...")
            
            try:
                await db.commit()
                return True
            except Exception as e:
                await db.rollback()
                print(f"[Push] Error saving subscription: {e}")
                return False
    
    @classmethod
    async def remove_subscription(cls, sub_data: dict) -> bool:
        """Remove a push subscription by endpoint."""
        endpoint = sub_data.get("endpoint", "")
        async with AsyncSessionLocal() as db:
            removed = await cls._remove_by_endpoint(endpoint, db)
            if removed:
                await db.commit()
                print(f"[Push] Subscription removed from DB.")
            return removed
    
    @classmethod
    async def _remove_by_endpoint(cls, endpoint: str, db) -> bool:
        """Remove all subscriptions matching the given endpoint."""
        result = await db.execute(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
        subs = result.scalars().all()
        
        if not subs:
            return False
            
        for sub in subs:
            await db.delete(sub)
        
        return True
    
    @classmethod
    async def get_subscription_count(cls) -> int:
        """Get the number of active subscriptions."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(PushSubscription))
            return len(result.scalars().all())
    
    @classmethod
    async def check_and_notify(cls, ticker: str, change_1h: float, change_1d: float) -> None:
        """
        Check if a stock's change exceeds thresholds and send notification if so.
        """
        if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
            print("[Push] VAPID keys not configured. Skipping notifications.")
            return
        
        notifications = []
        
        # Check 1H threshold
        if abs(change_1h) >= THRESHOLD_1H:
            direction = "📈 UP" if change_1h > 0 else "📉 DOWN"
            notifications.append({
                "title": f"{ticker} Alert (1H)",
                "body": f"{direction} {abs(change_1h):.2f}% in the last hour",
                "tag": f"{ticker}-1h"
            })
        
        # Check 1D threshold
        if abs(change_1d) >= THRESHOLD_1D:
            direction = "📈 UP" if change_1d > 0 else "📉 DOWN"
            notifications.append({
                "title": f"{ticker} Alert (1D)",
                "body": f"{direction} {abs(change_1d):.2f}% today",
                "tag": f"{ticker}-1d"
            })
        
        from datetime import datetime, timedelta

        # Send notifications
        for notif in notifications:
            notif_key = notif["tag"]
            current_value = change_1h if "1h" in notif_key else change_1d
            
            # Smart deduplication:
            # 1. If never notified, notify.
            # 2. If notified before, but value has shifted significantly (>0.5%), notify again.
            # 3. If notified before, but > 4 hours ago, notify again as a reminder.
            
            should_notify = False
            last_record = cls._notified_stocks.get(notif_key)
            
            if not last_record:
                should_notify = True
            else:
                last_value = last_record["value"]
                last_time = last_record["timestamp"]
                
                value_shifted = abs(current_value - last_value) >= 0.5
                time_passed = datetime.now() - last_time > timedelta(hours=4)
                
                if value_shifted or time_passed:
                    should_notify = True
            
            if should_notify:
                cls._notified_stocks[notif_key] = {
                    "value": current_value,
                    "timestamp": datetime.now()
                }
                await cls._send_to_all(notif)
    
    @classmethod
    async def _send_to_all(cls, notification_data: dict) -> None:
        """Send a notification to all subscribers."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(PushSubscription))
            subs = result.scalars().all()
            
            if not subs:
                return

            failed_subs = []
            
            # Send to each subscription
            for sub in subs:
                try:
                    # Reconstruct subscription info for pywebpush
                    subscription_info = {
                        "endpoint": sub.endpoint,
                        "keys": {
                            "auth": sub.keys_auth,
                            "p256dh": sub.keys_p256dh
                        }
                    }
                    
                    # Wrap in to_thread because webpush is a synchronous block
                    await asyncio.to_thread(
                        webpush,
                        subscription_info=subscription_info,
                        data=json.dumps(notification_data),
                        vapid_private_key=VAPID_PRIVATE_KEY,
                        vapid_claims=VAPID_CLAIMS
                    )
                    print(f"[Push] Sent: {notification_data['title']} to {sub.endpoint[:30]}...")
                except WebPushException as e:
                    print(f"[Push] Failed to send: {e}")
                    # If subscription is invalid (410 Gone), mark for removal
                    if e.response and e.response.status_code == 410:
                        failed_subs.append(sub)
                except Exception as e:
                    print(f"[Push] Error: {e}")
            
            # Clean up invalid subscriptions
            if failed_subs:
                for sub in failed_subs:
                    await db.delete(sub)
                await db.commit()
                print(f"[Push] Cleaned up {len(failed_subs)} failed subscriptions.")
    
    @classmethod
    def clear_notification_cache(cls) -> None:
        """Clear the notified stocks cache."""
        cls._notified_stocks.clear()
    
    @classmethod
    def get_vapid_public_key(cls) -> str:
        """Get the VAPID public key for frontend subscription."""
        return VAPID_PUBLIC_KEY
