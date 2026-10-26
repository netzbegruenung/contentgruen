import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { appConfig } from './app/app.config';

bootstrapApplication(AppComponent, appConfig)
  .catch((err) => console.error(err));

/*
 * Service Worker registrieren -- die Voraussetzung dafuer, dass Android die App
 * installieren und damit ueberhaupt im Teilen-Menue anbieten kann. Der Worker
 * selbst cacht nichts (public/sw.js).
 *
 * Nach dem load-Event, damit die Registrierung nicht mit dem ersten Rendern um
 * Bandbreite konkurriert. Ein Fehlschlag wird geloggt und sonst ignoriert: ohne
 * Worker laeuft die App unveraendert weiter, sie ist dann nur nicht installierbar.
 * Ausserhalb eines secure context (http auf einem anderen Host als localhost)
 * fehlt navigator.serviceWorker ganz -- deshalb die Pruefung.
 */
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((err) => {
      console.error('Service Worker konnte nicht registriert werden', err);
    });
  });
}
