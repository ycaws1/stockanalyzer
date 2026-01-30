// Service Worker for Stock Analyzer Push Notifications
self.addEventListener('install', (event) => {
    console.log('[SW] Service Worker Installing');
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('[SW] Service Worker Activated');
    event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
    console.log('[SW] Push Received');

    let data = {
        title: 'Stock Alert',
        body: 'A stock in your watchlist has moved significantly.',
        tag: 'stock-alert'
    };

    try {
        if (event.data) {
            data = event.data.json();
        }
    } catch (e) {
        console.error('[SW] Failed to parse push data:', e);
    }

    const options = {
        body: data.body,
        icon: '/android-chrome-192x192.png',
        badge: '/favicon-32x32.png',
        tag: data.tag || 'stock-alert',
        requireInteraction: true,
        vibrate: [100, 50, 100],
        data: {
            url: '/',
            ...data
        },
        actions: [
            { action: 'view', title: 'View Details' },
            { action: 'dismiss', title: 'Dismiss' }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked');
    event.notification.close();

    if (event.action === 'dismiss') {
        return;
    }

    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            // If app is already open, focus it
            for (const client of clientList) {
                if ('focus' in client) {
                    return client.focus();
                }
            }
            // Otherwise open new window
            if (self.clients.openWindow) {
                return self.clients.openWindow('/');
            }
        })
    );
});
