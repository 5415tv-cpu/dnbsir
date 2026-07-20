const CACHE_NAME = 'dongne-biseo-v8';
const ASSETS = [
    '/static/manifest.json'
];

// 1. Install Event: Cache essential assets and skip waiting to activate immediately
self.addEventListener('install', (event) => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(ASSETS))
    );
});

// 2. Activate Event: Clean up old caches and claim control of all clients
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// 3. Fetch Event: Network-First strategy with Cache fallback
self.addEventListener('fetch', (event) => {
    // Skip non-GET requests and API/Webhook calls
    if (event.request.method !== 'GET' || 
        event.request.url.includes('/api/') || 
        event.request.url.includes('/webhook/')) {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then((response) => {
                // If network request is successful, update the cache and return
                if (response && response.status === 200) {
                    const responseToCache = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseToCache);
                    });
                }
                return response;
            })
            .catch(() => {
                // Fallback to cache if network fails (offline)
                return caches.match(event.request);
            })
    );
});
