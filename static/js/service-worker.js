const CACHE_NAME = 'cpar-shell-v2';
const OFFLINE_URL = '/static/offline.html';
const SHELL_FILES = [
  OFFLINE_URL,
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/manifest.json',
  '/static/icons/icon-192.svg',
  '/static/icons/icon-512.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') {
    return;
  }

  const requestUrl = new URL(event.request.url);
  const isStatic = requestUrl.pathname.startsWith('/static/');
  const isDocument = event.request.mode === 'navigate';

  if (isStatic) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        return cached || fetch(event.request).then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        });
      })
    );
    return;
  }

  if (isDocument) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        })
        .catch(() =>
          caches.match(event.request, { ignoreSearch: true }).then((cached) => cached || caches.match(OFFLINE_URL))
        )
    );
  }
});
