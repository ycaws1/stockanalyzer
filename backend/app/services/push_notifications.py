"""
Web Push Notification Service for Stock Alerts
Sends notifications when stocks move beyond configurable thresholds.
"""
import os
from dotenv import load_dotenv
load_dotenv()  # Load .env before reading env vars

import json
from typing import Dict, Set
from pywebpush import webpush, WebPushException

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
    # In-memory store for subscriptions (for production, use database)
    _subscriptions: Set[str] = set()
    
    # Track notified stocks to avoid duplicate notifications
    _notified_stocks: Dict[str, float] = {}
    
    @classmethod
    def get_thresholds(cls) -> dict:
        """Return current threshold configuration."""
        return {
            "threshold_1h": THRESHOLD_1H,
            "threshold_1d": THRESHOLD_1D
        }
    
    @classmethod
    def add_subscription(cls, subscription: dict) -> bool:
        """Add a push subscription, replacing any existing subscription with the same endpoint."""
        endpoint = subscription.get("endpoint", "")
        
        # Remove any existing subscription with the same endpoint
        cls._remove_by_endpoint(endpoint)
        
        sub_str = json.dumps(subscription, sort_keys=True)
        cls._subscriptions.add(sub_str)
        print(f"[Push] Subscription added for endpoint: {endpoint[:50]}... Total: {len(cls._subscriptions)}")
        return True
    
    @classmethod
    def remove_subscription(cls, subscription: dict) -> bool:
        """Remove a push subscription by endpoint."""
        endpoint = subscription.get("endpoint", "")
        removed = cls._remove_by_endpoint(endpoint)
        if removed:
            print(f"[Push] Subscription removed. Total: {len(cls._subscriptions)}")
        return removed
    
    @classmethod
    def _remove_by_endpoint(cls, endpoint: str) -> bool:
        """Remove all subscriptions matching the given endpoint."""
        to_remove = []
        for sub_str in cls._subscriptions:
            try:
                sub = json.loads(sub_str)
                if sub.get("endpoint") == endpoint:
                    to_remove.append(sub_str)
            except:
                pass
        
        for sub_str in to_remove:
            cls._subscriptions.discard(sub_str)
        
        return len(to_remove) > 0
    
    @classmethod
    def get_subscription_count(cls) -> int:
        """Get the number of active subscriptions."""
        return len(cls._subscriptions)
    
    @classmethod
    def check_and_notify(cls, ticker: str, change_1h: float, change_1d: float) -> None:
        """
        Check if a stock's change exceeds thresholds and send notification if so.
        
        Args:
            ticker: Stock ticker symbol
            change_1h: 1-hour change percentage
            change_1d: 1-day change percentage
        """
        if not cls._subscriptions:
            return
        
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
            # Avoid duplicate notifications for the same event
            notif_key = notif["tag"]
            if notif_key in cls._notified_stocks:
                continue
            
            cls._notified_stocks[notif_key] = change_1h if "1h" in notif_key else change_1d
            cls._send_to_all(notif)
    
    @classmethod
    def _send_to_all(cls, notification_data: dict) -> None:
        """Send a notification to all subscribers."""
        failed_subs = []
        
        for sub_str in cls._subscriptions:
            try:
                subscription = json.loads(sub_str)
                webpush(
                    subscription_info=subscription,
                    data=json.dumps(notification_data),
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims=VAPID_CLAIMS
                )
                print(f"[Push] Sent: {notification_data['title']}")
            except WebPushException as e:
                print(f"[Push] Failed to send: {e}")
                # If subscription is invalid (410 Gone), mark for removal
                if e.response and e.response.status_code == 410:
                    failed_subs.append(sub_str)
            except Exception as e:
                print(f"[Push] Error: {e}")
        
        # Clean up invalid subscriptions
        for sub in failed_subs:
            cls._subscriptions.discard(sub)
    
    @classmethod
    def clear_notification_cache(cls) -> None:
        """Clear the notified stocks cache (call periodically)."""
        cls._notified_stocks.clear()
    
    @classmethod
    def get_vapid_public_key(cls) -> str:
        """Get the VAPID public key for frontend subscription."""
        return VAPID_PUBLIC_KEY
