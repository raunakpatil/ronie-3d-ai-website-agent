// Keeps Ronie's natural voice on the visitor's computer.
// The voice model is a 325 MB file. Browsers won't hold a file that big in their caches, so it was downloaded again on
// every visit. This worker stores the voice's files in IndexedDB the first time they're fetched, and from then on answers
// the voice library's requests for them from there. It touches nothing else: every other request goes straight to the
// network as usual. main.js can also ask it to fetch them ahead of time ('warm-voice'), on landing, without anything
// being loaded onto the graphics chip until Ronie's room is opened.
const VOICE = /^https:\/\/huggingface\.co\/onnx-community\/Kokoro-82M-v1\.0-ONNX\/resolve\/main\//;
const VOICE_FILES = ['config.json', 'tokenizer.json', 'tokenizer_config.json', 'onnx/model.onnx', 'voices/am_puck.bin']
  .map((f) => `https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/resolve/main/${f}`);
const DB = 'ronie-voice', STORE = 'files';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

let dbp = null;
function db() {
  dbp = dbp || new Promise((res, rej) => {
    const q = indexedDB.open(DB, 1);
    q.onupgradeneeded = () => q.result.createObjectStore(STORE);
    q.onsuccess = () => res(q.result);
    q.onerror = () => rej(q.error);
  });
  return dbp;
}
async function get(url) {
  const d = await db();
  return new Promise((res) => {
    const q = d.transaction(STORE).objectStore(STORE).get(url);
    q.onsuccess = () => res(q.result || null);
    q.onerror = () => res(null);
  });
}
async function put(url, rec) {
  const d = await db();
  return new Promise((res) => {
    const tx = d.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).put(rec, url);
    tx.oncomplete = () => res(true);
    tx.onerror = tx.onabort = () => res(false);
  });
}
// one download per file at a time, however many ask for it
const inflight = new Map();
function download(url) {
  if (!inflight.has(url)) {
    inflight.set(url, (async () => {
      const r = await fetch(url, { mode: 'cors', credentials: 'omit' });
      if (!r.ok) throw new Error(`${r.status} ${url}`);
      const blob = await r.blob();
      await put(url, { blob, type: r.headers.get('content-type') || 'application/octet-stream' });
      return { blob, type: blob.type };
    })().finally(() => inflight.delete(url)));
  }
  return inflight.get(url);
}
async function serve(url) {
  const hit = (await get(url)) || (await download(url));
  return new Response(hit.blob, { headers: { 'Content-Type': hit.type, 'Content-Length': String(hit.blob.size) } });
}

self.addEventListener('fetch', (e) => {
  const { request } = e;
  if (request.method !== 'GET' || !VOICE.test(request.url)) return;
  // (should anything here fail, the request simply goes to the network as it always did)
  e.respondWith(serve(request.url).catch(() => fetch(request)));
});

self.addEventListener('message', (e) => {
  if (e.data && e.data.type === 'warm-voice') {
    e.waitUntil(Promise.all(VOICE_FILES.map(async (u) => { if (!(await get(u))) await download(u); })).catch(() => {}));
  }
});
