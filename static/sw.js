// StockPulse Service Worker
const CACHE_NAME = 'stockpulse-v4';
const STATIC_ASSETS = [
    '/',
    '/manifest.json',
    '/static/icon-192.png',
    '/static/icon-512.png',
    '/static/icon-180.png'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - cleanup old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name.startsWith('stockpulse-') && name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event - network first for live data and document navigations.
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Always fetch API requests from network (real-time data is critical)
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    return response;
                })
                .catch(() => {
                    // Never replay cached market data as if it were current.
                    return new Response(
                        JSON.stringify({
                            error: 'You are offline. Please check your connection.',
                            code: 'offline',
                            data_status: 'offline'
                        }),
                        {
                            status: 503,
                            headers: {
                                'Content-Type': 'application/json',
                                'Cache-Control': 'no-store'
                            }
                        }
                    );
                })
        );
        return;
    }

    // Always prefer the current HTML shell so a deployment cannot be hidden
    // behind a stale cached document. Fall back to the last known shell only
    // when the browser is offline.
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .then((networkResponse) => {
                    if (networkResponse && networkResponse.status === 200) {
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(event.request, networkResponse.clone());
                        });
                    }
                    return networkResponse;
                })
                .catch(() => caches.match(event.request).then((cachedResponse) => {
                    return cachedResponse || caches.match('/');
                }))
        );
        return;
    }

    // For static assets, use cache-first strategy
    event.respondWith(
        caches.match(event.request)
            .then((cachedResponse) => {
                if (cachedResponse) {
                    // Return cached response and update cache in background
                    fetch(event.request).then((networkResponse) => {
                        if (networkResponse && networkResponse.status === 200) {
                            caches.open(CACHE_NAME).then((cache) => {
                                cache.put(event.request, networkResponse.clone());
                            });
                        }
                    }).catch(() => {});
                    return cachedResponse;
                }

                // No cache, fetch from network
                return fetch(event.request).then((networkResponse) => {
                    if (networkResponse && networkResponse.status === 200) {
                        const responseClone = networkResponse.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(event.request, responseClone);
                        });
                    }
                    return networkResponse;
                });
            })
    );
});

// Handle push notifications (future feature)
self.addEventListener('push', (event) => {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body || 'New market update available',
            icon: '/static/icon-192.png',
            badge: '/static/icon-72.png',
            vibrate: [100, 50, 100],
            data: {
                url: data.url || '/'
            }
        };
        event.waitUntil(
            self.registration.showNotification(data.title || 'StockPulse', options)
        );
    }
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data.url || '/')
    );
});
