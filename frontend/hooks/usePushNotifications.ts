'use client';

import { useState, useEffect, useCallback } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface PushState {
    isSupported: boolean;
    isSubscribed: boolean;
    isLoading: boolean;
    error: string | null;
    thresholds: { threshold_1h: number; threshold_1d: number } | null;
}

export function usePushNotifications() {
    const [state, setState] = useState<PushState>({
        isSupported: false,
        isSubscribed: false,
        isLoading: true,
        error: null,
        thresholds: null
    });

    // Check if push notifications are supported and auto-request permission
    useEffect(() => {
        const checkAndRequestPermission = async () => {
            const supported = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;

            if (!supported) {
                setState(prev => ({ ...prev, isSupported: false, isLoading: false }));
                return;
            }

            try {
                // Register service worker
                const registration = await navigator.serviceWorker.register('/sw.js');
                console.log('[Push] Service Worker registered:', registration.scope);

                // Check existing subscription
                const existingSubscription = await registration.pushManager.getSubscription();

                // Fetch thresholds
                const threshRes = await fetch(`${API_URL}/push/thresholds`);
                const thresholds = threshRes.ok ? await threshRes.json() : null;

                // Check current permission status
                const permissionStatus = Notification.permission;

                if (permissionStatus === 'default') {
                    // Permission not yet asked - request it
                    console.log('[Push] Requesting notification permission...');
                    const permission = await Notification.requestPermission();

                    if (permission === 'granted' && !existingSubscription) {
                        // Auto-subscribe after permission granted
                        console.log('[Push] Permission granted, auto-subscribing...');
                        await autoSubscribe(registration, thresholds);
                        return;
                    }
                } else if (permissionStatus === 'granted' && !existingSubscription) {
                    // Permission already granted but not subscribed - auto-subscribe
                    console.log('[Push] Already have permission, auto-subscribing...');
                    await autoSubscribe(registration, thresholds);
                    return;
                }

                setState({
                    isSupported: true,
                    isSubscribed: !!existingSubscription,
                    isLoading: false,
                    error: null,
                    thresholds
                });
            } catch (err) {
                console.error('[Push] Setup error:', err);
                setState(prev => ({
                    ...prev,
                    isSupported: true,
                    isLoading: false,
                    error: 'Failed to initialize push notifications'
                }));
            }
        };

        // Helper function to auto-subscribe
        const autoSubscribe = async (registration: ServiceWorkerRegistration, thresholds: any) => {
            try {
                const keyRes = await fetch(`${API_URL}/push/vapid-public-key`);
                if (!keyRes.ok) {
                    throw new Error('VAPID key not configured');
                }
                const { publicKey } = await keyRes.json();

                const subscription = await registration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: urlBase64ToUint8Array(publicKey) as BufferSource
                });

                await fetch(`${API_URL}/push/subscribe`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(subscription.toJSON())
                });

                console.log('[Push] Auto-subscribed successfully');
                setState({
                    isSupported: true,
                    isSubscribed: true,
                    isLoading: false,
                    error: null,
                    thresholds
                });
            } catch (err) {
                console.error('[Push] Auto-subscribe failed:', err);
                setState({
                    isSupported: true,
                    isSubscribed: false,
                    isLoading: false,
                    error: null,
                    thresholds
                });
            }
        };

        checkAndRequestPermission();
    }, []);

    // Subscribe to push notifications
    const subscribe = useCallback(async () => {
        setState(prev => ({ ...prev, isLoading: true, error: null }));

        try {
            // Get VAPID public key from server
            const keyRes = await fetch(`${API_URL}/push/vapid-public-key`);
            if (!keyRes.ok) {
                throw new Error('VAPID key not configured on server');
            }
            const { publicKey } = await keyRes.json();

            // Request notification permission
            const permission = await Notification.requestPermission();
            if (permission !== 'granted') {
                throw new Error('Notification permission denied');
            }

            // Get service worker registration
            const registration = await navigator.serviceWorker.ready;

            // Subscribe to push
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(publicKey) as BufferSource
            });

            // Send subscription to server
            const subRes = await fetch(`${API_URL}/push/subscribe`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(subscription.toJSON())
            });

            if (!subRes.ok) {
                throw new Error('Failed to register subscription on server');
            }

            setState(prev => ({ ...prev, isSubscribed: true, isLoading: false }));
            return true;
        } catch (err: any) {
            console.error('[Push] Subscribe error:', err);
            setState(prev => ({
                ...prev,
                isLoading: false,
                error: err.message || 'Failed to subscribe'
            }));
            return false;
        }
    }, []);

    // Unsubscribe from push notifications
    const unsubscribe = useCallback(async () => {
        setState(prev => ({ ...prev, isLoading: true, error: null }));

        try {
            const registration = await navigator.serviceWorker.ready;
            const subscription = await registration.pushManager.getSubscription();

            if (subscription) {
                // Unsubscribe locally
                await subscription.unsubscribe();

                // Notify server
                await fetch(`${API_URL}/push/unsubscribe`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(subscription.toJSON())
                });
            }

            setState(prev => ({ ...prev, isSubscribed: false, isLoading: false }));
            return true;
        } catch (err: any) {
            console.error('[Push] Unsubscribe error:', err);
            setState(prev => ({
                ...prev,
                isLoading: false,
                error: err.message || 'Failed to unsubscribe'
            }));
            return false;
        }
    }, []);

    return {
        ...state,
        subscribe,
        unsubscribe
    };
}

// Helper to convert VAPID key
function urlBase64ToUint8Array(base64String: string): Uint8Array {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}
