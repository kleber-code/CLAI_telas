const CACHE_NAME = 'clai-app-cache-v2'; // Bump version
const OFFLINE_URL = '/offline';
const ASSETS_TO_CACHE = [
  '/',
  '/login',
  OFFLINE_URL,
  '/static/css/style.css',
  '/static/img/logo-clai.jpeg',
  '/static/img/favicon.ico',
  '/static/img/android-chrome-192x192.png',
  '/static/img/android-chrome-512x512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Opened cache and caching app shell');
        // Use individual requests to avoid failure if one asset is missing
        const promises = ASSETS_TO_CACHE.map(url => {
          return cache.add(url).catch(err => {
            console.warn(`Failed to cache ${url}:`, err);
          });
        });
        return Promise.all(promises);
      })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.filter(cacheName => cacheName !== CACHE_NAME)
          .map(cacheName => {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Handle navigation requests
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          // If the network request fails, try to serve from cache
          return caches.match(event.request)
            .then(cachedResponse => {
              // If in cache, return it. Otherwise, return the general offline page.
              return cachedResponse || caches.match(OFFLINE_URL);
            });
        })
    );
  } else {
    // For non-navigation requests (assets), use a stale-while-revalidate strategy
    event.respondWith(
      caches.open(CACHE_NAME).then(cache => {
        return cache.match(event.request).then(cachedResponse => {
          const fetchPromise = fetch(event.request).then(networkResponse => {
            // Check if the response is valid to be cached (ok or opaque)
            if (networkResponse && (networkResponse.ok || networkResponse.type === 'opaque')) {
              try {
                // Clone the response before putting it in cache, as response streams can only be read once.
                cache.put(event.request, networkResponse.clone());
              } catch (e) {
                console.warn(`Failed to cache ${event.request.url}:`, e);
              }
            }
            return networkResponse;
          }).catch(error => {
            console.error('Fetch failed for:', event.request.url, error);
            // Fallback to cache on network error
            return cachedResponse || new Response(null, { status: 503, statusText: 'Service Unavailable' });
          });
          // Return cached response immediately, and update cache in background
          return cachedResponse || fetchPromise;
        });
      })
    );
  }
});