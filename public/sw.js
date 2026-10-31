// Mudra service worker — makes the app open offline.
// __BUILD__ is replaced with the commit SHA by the deploy workflow, so every deploy gets a fresh cache.
const CACHE = 'mudra-__BUILD__';
const SDK = 'https://www.gstatic.com/firebasejs/10.14.1/';
const FILES = ['./', './index.html', './config.js', './manifest.json', './icon-192.png', './icon-512.png'];
const SDK_FILES = ['firebase-app.js', 'firebase-auth.js', 'firebase-firestore.js'].map(f => SDK + f);

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.all([
    c.addAll(FILES),
    ...SDK_FILES.map(u => c.add(u).catch(() => {}))
  ])));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  if (url.origin === location.origin) {
    if (url.pathname.startsWith('/__/')) return;           // Firebase Hosting reserved URLs (sign-in handler)
    // App files: network-first so updates arrive; cache fallback when offline.
    e.respondWith(
      fetch(req).then(res => {
        if (res.ok && !res.redirected && res.type === 'basic') {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy));
        }
        return res;
      }).catch(() => caches.match(req, { ignoreSearch: true })
        .then(r => r || (req.mode === 'navigate' ? caches.match('./index.html') : null))
        .then(r => r || Response.error()))
    );
    return;
  }

  if (url.href.startsWith(SDK)) {
    // Firebase SDK files are versioned and never change: cache-first.
    e.respondWith(caches.match(req).then(r => r || fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
      return res;
    })));
  }
  // Everything else (Firestore, Google sign-in APIs) goes straight to the network.
});
