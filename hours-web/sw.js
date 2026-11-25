// Tryb offline: aplikacja (kilka plików) jest w pamięci telefonu. Nowa wersja = nowa nazwa
// pamięci; stara jest usuwana po aktywacji. Dane użytkownika są w localStorage, nie tutaj.
const CACHE = 'godziny-pracy-1.7';
const FILES = ['./', 'index.html', 'app.css', 'app.js', 'core.js', 'manifest.webmanifest',
  'icons/icon.svg', 'icons/apple-touch-icon.png', 'icons/icon-192.png', 'icons/icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
// Najpierw sieć (świeża wersja po publikacji), a bez sieci — kopia z pamięci.
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET' || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(fetch(e.request)
    .then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; })
    .catch(() => caches.match(e.request, { ignoreSearch: true }).then(r => r || caches.match('index.html'))));
});
