const CACHE_NAME = 'cpar-shell-v3';
const OFFLINE_URL = '/static/offline.html';
const SHELL_FILES = [
  OFFLINE_URL,
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/manifest.json',
  '/static/icons/icon-192.svg',
  '/static/icons/icon-512.svg',
];

function getDocumentCacheKeys(url) {
  const pathname = url.pathname;
  const normalizedPath = pathname.endsWith('/') ? pathname : pathname + '/';

  return [
    url.href,
    pathname,
    normalizedPath
  ];
}

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

self.addEventListener('message', (event) => {
  const data = event.data || {};
  if (data.type !== 'WARM_CACHE_URLS' || !Array.isArray(data.urls)) {
    return;
  }

  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      Promise.all(
        data.urls
          .filter(Boolean)
          .map((url) =>
            fetch(url, { credentials: 'same-origin' })
              .then((response) => {
                if (response && response.ok) {
                  const keys = getDocumentCacheKeys(new URL(url, self.location.origin));
                  return Promise.all(keys.map((key) => cache.put(key, response.clone())));
                }
                return null;
              })
              .catch(() => null)
          )
      )
    )
  );
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
    const documentCacheKeys = getDocumentCacheKeys(requestUrl);
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) =>
            Promise.all(documentCacheKeys.map((key) => cache.put(key, copy.clone())))
          );
          return response;
        })
        .catch(() =>
          caches.open(CACHE_NAME).then((cache) =>
            Promise.all(documentCacheKeys.map((key) => cache.match(key, { ignoreSearch: true })))
              .then((matches) => matches.find(Boolean) || caches.match(OFFLINE_URL))
          )
        )
    );
  }
});
