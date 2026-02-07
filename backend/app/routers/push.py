"""
Push Notification Router - API endpoints for web push subscriptions
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..services.push_notifications import PushNotificationService

router = APIRouter(prefix="/push", tags=["Push Notifications"])


class PushSubscription(BaseModel):
    """Web push subscription object from browser."""
    endpoint: str
    keys: dict
    expirationTime: Optional[float] = None


class SubscriptionResponse(BaseModel):
    success: bool
    message: str


@router.get("/vapid-public-key")
async def get_vapid_key():
    """Get the VAPID public key for frontend subscription."""
    key = PushNotificationService.get_vapid_public_key()
    if not key:
        raise HTTPException(status_code=500, detail="VAPID key not configured")
    return {"publicKey": key}


@router.get("/thresholds")
async def get_thresholds():
    """Get current notification thresholds."""
    return PushNotificationService.get_thresholds()


@router.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe(subscription: PushSubscription):
    """Subscribe to push notifications."""
    sub_dict = {
        "endpoint": subscription.endpoint,
        "keys": subscription.keys
    }
    if subscription.expirationTime:
        sub_dict["expirationTime"] = subscription.expirationTime
    
    added = await PushNotificationService.add_subscription(sub_dict)
    return SubscriptionResponse(
        success=True,
        message="Subscribed successfully" if added else "Already subscribed"
    )


@router.post("/unsubscribe", response_model=SubscriptionResponse)
async def unsubscribe(subscription: PushSubscription):
    """Unsubscribe from push notifications."""
    sub_dict = {
        "endpoint": subscription.endpoint,
        "keys": subscription.keys
    }
    
    removed = await PushNotificationService.remove_subscription(sub_dict)
    return SubscriptionResponse(
        success=True,
        message="Unsubscribed successfully" if removed else "Subscription not found"
    )


@router.get("/status")
async def get_status():
    """Get push notification service status."""
    return {
        "active_subscriptions": await PushNotificationService.get_subscription_count(),
        "thresholds": PushNotificationService.get_thresholds(),
        "vapid_configured": bool(PushNotificationService.get_vapid_public_key())
    }


@router.post("/test")
async def test_notification(ticker: str = "TEST", alert_type: str = "1h"):
    """
    Send a test notification to all subscribers.
    """
    count = await PushNotificationService.get_subscription_count()
    if count == 0:
        raise HTTPException(status_code=400, detail="No active subscriptions. Please enable alerts first.")
    
    if not PushNotificationService.get_vapid_public_key():
        raise HTTPException(status_code=500, detail="VAPID keys not configured")
    
    # Clear specific ticker from cache to allow repeated testing
    if f"{ticker}-1h" in PushNotificationService._notified_stocks:
        del PushNotificationService._notified_stocks[f"{ticker}-1h"]
    if f"{ticker}-1d" in PushNotificationService._notified_stocks:
        del PushNotificationService._notified_stocks[f"{ticker}-1d"]
    
    # Simulate a big price move
    if alert_type == "1d":
        # Simulate 1D alert with 5% change
        await PushNotificationService.check_and_notify(
            ticker=ticker,
            change_1h=0.5,  # Small 1h change (won't trigger)
            change_1d=5.0   # Big 1d change (will trigger)
        )
        return {"success": True, "message": f"Test 1D notification sent for {ticker} (+5%)"}
    else:
        # Simulate 1H alert with 3% change
        await PushNotificationService.check_and_notify(
            ticker=ticker,
            change_1h=3.0,  # Big 1h change (will trigger)
            change_1d=1.0   # Small 1d change (won't trigger)
        )
        return {"success": True, "message": f"Test 1H notification sent for {ticker} (+3%)"}


@router.post("/test-both")
async def test_both_notifications(ticker: str = "TEST"):
    """
    Send both 1H and 1D test notifications.
    """
    count = await PushNotificationService.get_subscription_count()
    if count == 0:
        raise HTTPException(status_code=400, detail="No active subscriptions. Please enable alerts first.")
    
    # Clear notification cache to allow retesting
    PushNotificationService.clear_notification_cache()
    
    # Simulate both alerts
    await PushNotificationService.check_and_notify(
        ticker=ticker,
        change_1h=3.0,   # Will trigger 1H alert
        change_1d=5.0    # Will trigger 1D alert
    )
    
    return {"success": True, "message": f"Test notifications sent for {ticker} (1H: +3%, 1D: +5%)"}


@router.post("/test-direct")
async def test_direct_notification(title: str = "Test Alert", body: str = "This is a test notification"):
    """
    Send a notification directly to all subscribers, bypassing all caching.
    """
    count = await PushNotificationService.get_subscription_count()
    if count == 0:
        raise HTTPException(status_code=400, detail="No active subscriptions. Please enable alerts first.")
    
    if not PushNotificationService.get_vapid_public_key():
        raise HTTPException(status_code=500, detail="VAPID keys not configured")
    
    # Send directly without caching
    notification = {
        "title": title,
        "body": body,
        "tag": f"test-{int(__import__('time').time())}"  # Unique tag each time
    }
    
    await PushNotificationService._send_to_all(notification)
    
    return {
        "success": True, 
        "message": f"Direct notification sent to {count} subscriber(s)",
        "notification": notification
    }
@router.get("/history")
async def get_history(limit: int = 50, ticker: Optional[str] = None):
    """Get the latest notification history, optionally filtered by ticker."""
    return await PushNotificationService.get_history(limit=limit, ticker=ticker)


@router.post("/reset-all")
async def reset_all():
    """Clear all subscriptions and notification cache."""
    count = await PushNotificationService.clear_all_subscriptions()
    PushNotificationService.clear_notification_cache()
    return {"success": True, "message": f"Cleared {count} subscriptions and reset notification cache"}


@router.post("/clear-history")
async def clear_history():
    """Delete all notification logs."""
    count = await PushNotificationService.delete_history()
    return {"success": True, "message": f"Deleted {count} notification logs"}
