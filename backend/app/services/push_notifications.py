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
from ..models import PushSubscription, NotificationLog
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()  # Load .env before reading env vars

# ============================================
# CONFIGURABLE THRESHOLDS
# ============================================
# 1H Change Threshold (in percent) - triggers notification if |change| > this value
THRESHOLD_1H = float(os.getenv('ALERT_THRESHOLD_1H', '2.0'))

# 1D Change Threshold (in percent) - triggers notification if |change| > this value
THRESHOLD_1D = float(os.getenv('ALERT_THRESHOLD_1D', '3.5'))

# Renotify Threshold (in percent) - additional move required within same bucket to re-notify
RENOTIFY_THRESHOLD = float(os.getenv('ALERT_RENOTIFY_THRESHOLD', '1.0'))


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
            "threshold_1d": THRESHOLD_1D,
            "renotify_threshold": RENOTIFY_THRESHOLD
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
    async def initialize_cache(cls):
        """
        Initialize the in-memory cache from the database logs.
        This prevents duplicate notifications after a server restart.
        """
        async with AsyncSessionLocal() as db:
            # Get the latest notification for each ticker/tag combination
            # We use a subquery to get the latest ID for each tag
            from sqlalchemy import func
            
            subquery = select(
                NotificationLog.tag,
                func.max(NotificationLog.id).label("max_id")
            ).group_by(NotificationLog.tag).subquery()
            
            query = select(NotificationLog).join(
                subquery,
                NotificationLog.id == subquery.c.max_id
            )
            
            result = await db.execute(query)
            logs = result.scalars().all()
            
            for log in logs:
                cls._notified_stocks[log.tag] = {
                    "value": log.value,
                    "timestamp": log.timestamp,
                    "data_timestamp": None  # We don't store data_timestamp in DB yet
                }
            print(f"[Push] Initialized cache with {len(logs)} recent notifications from DB.")

    @classmethod
    async def check_and_notify(cls, ticker: str, change_1h: float, change_1d: float, data_timestamp: datetime = None) -> None:
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

        # Send notifications
        for notif in notifications:
            notif_key = notif["tag"]
            current_value = change_1h if "1h" in notif_key else change_1d
            normalized_data_ts = None
            if data_timestamp:
                if "1d" in notif_key:
                    # For 1D alerts, dedupe by date only
                    normalized_data_ts = data_timestamp.date()
                else:
                    # For 1H alerts, dedupe by hour
                    normalized_data_ts = data_timestamp.replace(minute=0, second=0, microsecond=0)
            
            # Smart deduplication:
            # 1. If never notified, notify.
            # 2. If it's the EXACT same data point (same time AND same value), NEVER notify.
            # 3. Within same bucket, only re-notify if move exceeds RENOTIFY_THRESHOLD.
            # 4. For a new bucket, notify.
            
            should_notify = False
            last_record = cls._notified_stocks.get(notif_key)
            
            if not last_record:
                should_notify = True
                print(f"[Push] First notification for {notif_key} (or cache empty)")
            else:
                last_value = last_record["value"]
                last_time = last_record["timestamp"]
                last_data_ts = last_record.get("data_timestamp")
                
                # Check for identical data
                is_identical_value = abs(current_value - last_value) < 0.001
                
                if last_data_ts and normalized_data_ts:
                     # Strict check: Same value AND same data source timestamp
                    is_identical_data = is_identical_value and (normalized_data_ts == last_data_ts)
                else:
                    # Fallback: If loaded from DB (no data_timestamp) or input has no timestamp,
                    # rely on strict value check. This prevents duplicates on server restart.
                    is_identical_data = is_identical_value
                
                if is_identical_data:
                    should_notify = False
                else:
                    is_same_bucket = (normalized_data_ts == last_data_ts) if (normalized_data_ts and last_data_ts) else False
                    if is_same_bucket:
                        should_notify = abs(current_value - last_value) >= RENOTIFY_THRESHOLD
                    else:
                        should_notify = True

            
            if should_notify:
                cls._notified_stocks[notif_key] = {
                    "value": current_value,
                    "timestamp": datetime.now(),
                    "data_timestamp": normalized_data_ts
                }
                # Log to DB
                await cls._log_notification(
                    ticker=ticker,
                    title=notif["title"],
                    body=notif["body"],
                    tag=notif["tag"],
                    value=current_value
                )
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
    async def _log_notification(cls, ticker: str, title: str, body: str, tag: str, value: float):
        """Log a notification to the database."""
        async with AsyncSessionLocal() as db:
            new_log = NotificationLog(
                ticker=ticker,
                title=title,
                body=body,
                tag=tag,
                value=value
            )
            db.add(new_log)
            try:
                await db.commit()
            except Exception as e:
                await db.rollback()
                print(f"[Push] Error logging notification: {e}")

    @classmethod
    async def get_history(cls, limit: int = 50, ticker: str = None) -> List[dict]:
        """Fetch the latest notification history, optionally filtered by ticker."""
        async with AsyncSessionLocal() as db:
            from sqlalchemy import desc
            
            query = select(NotificationLog).order_by(desc(NotificationLog.timestamp)).limit(limit)
            
            if ticker:
                query = query.where(NotificationLog.ticker == ticker.upper())
                
            result = await db.execute(query)
            logs = result.scalars().all()
            return [
                {
                    "id": log.id,
                    "ticker": log.ticker,
                    "title": log.title,
                    "body": log.body,
                    "tag": log.tag,
                    "value": log.value,
                    "timestamp": (log.timestamp.isoformat() + "Z") if log.timestamp else None
                }
                for log in logs
            ]
    
    @classmethod
    async def clear_all_subscriptions(cls) -> int:
        """Remove all subscriptions from the database."""
        async with AsyncSessionLocal() as db:
            from sqlalchemy import delete
            result = await db.execute(delete(PushSubscription))
            count = result.rowcount
            await db.commit()
            print(f"[Push] Cleared {count} subscriptions.")
            return count

    @classmethod
    async def delete_history(cls) -> int:
        """Delete all notification history logs."""
        async with AsyncSessionLocal() as db:
            from sqlalchemy import delete
            result = await db.execute(delete(NotificationLog))
            count = result.rowcount
            await db.commit()
            print(f"[Push] Deleted {count} history logs.")
            return count
    
    @classmethod
    def clear_notification_cache(cls) -> None:
        """Clear the notified stocks cache."""
        cls._notified_stocks.clear()
    
    @classmethod
    def get_vapid_public_key(cls) -> str:
        """Get the VAPID public key for frontend subscription."""
        return VAPID_PUBLIC_KEY
