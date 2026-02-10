'use client';

import { useState, useEffect, useCallback } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const ALERTS_OPT_OUT_KEY = 'stockanalyzer_alerts_optout';

interface PushState {
    isSupported: boolean;
    isSubscribed: boolean;
    isLoading: boolean;
    error: string | null;
    thresholds: { threshold_1h: number; threshold_1d: number } | null;
    isPWA: boolean;
    needsPermissionPrompt: boolean;
    permissionStatus: 'default' | 'granted' | 'denied' | 'unknown';
}

export function usePushNotifications() {
    const [state, setState] = useState<PushState>({
        isSupported: false,
        isSubscribed: false,
        isLoading: true,
        error: null,
        thresholds: null,
        isPWA: false,
        needsPermissionPrompt: false,
        permissionStatus: 'unknown'
    });

    // Check if push notifications are supported and handle permission
    useEffect(() => {
        const checkAndRequestPermission = async () => {
            console.log('[usePushNotifications] Using API_URL:', API_URL);
            const supported = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;

            // Detect if running as PWA (standalone mode)
            const isPWA = window.matchMedia('(display-mode: standalone)').matches ||
                (window.navigator as any).standalone === true;

            if (!supported) {
                setState(prev => ({ ...prev, isSupported: false, isLoading: false, isPWA }));
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

                // Check if user explicitly opted out
                const userOptedOut = localStorage.getItem(ALERTS_OPT_OUT_KEY) === 'true';

                // Sync existing subscription with backend to ensure it's not lost on server restart
                if (existingSubscription && !userOptedOut) {
                    console.log('[Push] Syncing existing subscription with backend...');
                    await fetch(`${API_URL}/push/subscribe`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(existingSubscription.toJSON())
                    }).catch(err => console.error('[Push] Sync failed:', err));
                }

                // If permission not yet asked, show banner (for both browser and PWA)
                if (permissionStatus === 'default') {
                    console.log('[Push] Permission not granted, showing permission prompt banner');
                    setState({
                        isSupported: true,
                        isSubscribed: false,
                        isLoading: false,
                        error: null,
                        thresholds,
                        isPWA,
                        needsPermissionPrompt: !userOptedOut,
                        permissionStatus: 'default'
                    });
                    return;
                }

                // If permission already granted but not subscribed, auto-subscribe
                if (permissionStatus === 'granted' && !existingSubscription && !userOptedOut) {
                    console.log('[Push] Already have permission, auto-subscribing...');
                    await autoSubscribe(registration, thresholds, isPWA);
                    return;
                }

                setState({
                    isSupported: true,
                    isSubscribed: !!existingSubscription,
                    isLoading: false,
                    error: null,
                    thresholds,
                    isPWA,
                    needsPermissionPrompt: false,
                    permissionStatus: permissionStatus as 'default' | 'granted' | 'denied'
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
        const autoSubscribe = async (registration: ServiceWorkerRegistration, thresholds: any, isPWA: boolean) => {
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
                    thresholds,
                    isPWA,
                    needsPermissionPrompt: false,
                    permissionStatus: 'granted'
                });
            } catch (err) {
                console.error('[Push] Auto-subscribe failed:', err);
                setState({
                    isSupported: true,
                    isSubscribed: false,
                    isLoading: false,
                    error: null,
                    thresholds,
                    isPWA,
                    needsPermissionPrompt: false,
                    permissionStatus: 'granted'
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

            // Clear opt-out flag since user is subscribing
            localStorage.removeItem(ALERTS_OPT_OUT_KEY);

            setState(prev => ({ ...prev, isSubscribed: true, isLoading: false, needsPermissionPrompt: false, permissionStatus: 'granted' }));
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

            // Set opt-out flag to prevent auto-resubscribing
            localStorage.setItem(ALERTS_OPT_OUT_KEY, 'true');

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

    // Dismiss permission prompt
    const dismissPermissionPrompt = useCallback(() => {
        localStorage.setItem(ALERTS_OPT_OUT_KEY, 'true');
        setState(prev => ({ ...prev, needsPermissionPrompt: false }));
    }, []);

    return {
        ...state,
        subscribe,
        unsubscribe,
        dismissPermissionPrompt
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
