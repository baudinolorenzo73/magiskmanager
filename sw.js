/* Service worker — by Lollo ®2026
   1. tiene sul telefono i file dell'app: si apre anche senza rete;
   2. si accorge delle nuove versioni (cambia versione.js) e aspetta il pulsante «Aggiorna».
   L'elenco dei file qui sotto lo scrive crea_pwa_zip.py a ogni versione. */
importScripts('versione.js'); // definisce self.VERSIONE

const CACHE = 'magiskmanager-' + self.VERSIONE;
const FILE = [
  "./",
  ".github/workflows/apk.yml",
  "buildozer.spec",
  "icon.png",
  "icone/icona-192.png",
  "icone/icona-512.png",
  "icone/icona-maskable-512.png",
  "index.html",
  "main.py",
  "manifest.webmanifest",
  "motore.py",
  "pwa.js",
  "requirements.txt",
  "versione.js"
];

self.addEventListener('install', (e) => {
  // cache: 'reload' = scarica davvero i file nuovi, saltando la cache del browser
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILE.map((f) => new Request(f, { cache: 'reload' })))));
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    for (const nome of await caches.keys()) {
      if (nome.startsWith('magiskmanager-') && nome !== CACHE) await caches.delete(nome);
    }
    await self.clients.claim();
  })());
});

self.addEventListener('message', (e) => {
  const tipo = e.data && e.data.tipo;
  if (tipo === 'versione' && e.ports[0]) e.ports[0].postMessage(self.VERSIONE);
  if (tipo === 'attiva') self.skipWaiting();
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin) return; // altri siti: rete normale
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const inCache = await cache.match(req, { ignoreSearch: true })
      || (req.mode === 'navigate' ? await cache.match('index.html') : undefined);
    return inCache || fetch(req);
  })());
});
