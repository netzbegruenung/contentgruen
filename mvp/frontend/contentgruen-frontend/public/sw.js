/*
 * Minimaler Service Worker -- absichtlich ohne Caching.
 *
 * Er existiert aus genau einem Grund: Chrome verlangt fuer die Installierbarkeit
 * einen Service Worker mit fetch-Handler, und ohne Installation taucht die App
 * nicht im Android-Teilen-Menue auf. Die Uebergabe der geteilten Daten laeuft
 * NICHT ueber ihn, sondern ueber "method": "GET" im share_target des Manifests --
 * der Browser navigiert dann schlicht auf /teilen?title=...&text=...&url=...,
 * was der Angular-Router selbst verarbeitet.
 *
 * Warum nicht @angular/pwa: dessen ngsw.json enthaelt SHA1-Hashes aller Bundles,
 * die zur Buildzeit entstehen. replace-env.sh schreibt beim Containerstart per sed
 * in dieselben Bundles (API_BASE_URL & Co.) -- die Hashes passen danach nicht mehr
 * und der Angular-Service-Worker verweigert den Dienst. Solange kein Offline-
 * Betrieb gewuenscht ist, ist diese Datei die ganze Loesung.
 *
 * Der fetch-Handler ruft bewusst kein respondWith() auf: jede Anfrage geht
 * unveraendert ans Netz. Damit kann dieser Worker nichts veralten lassen -- weder
 * die App noch API-Antworten.
 */

self.addEventListener('install', () => {
  // Kein Wartezustand: ein neuer Worker soll den alten sofort ersetzen.
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', () => {
  // Absichtlich leer. Siehe oben.
});
