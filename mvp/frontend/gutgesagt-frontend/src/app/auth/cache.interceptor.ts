import { HttpContext, HttpContextToken, HttpInterceptorFn, HttpRequest, HttpResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { finalize, of, tap } from 'rxjs';
import { STILLE_ABFRAGE } from '../shared/selbst-nachladen';

interface CacheEntry {
  response: HttpResponse<unknown>;
  timestamp: number;
}

class CacheService {
  private cache = new Map<string, CacheEntry>();
  private readonly CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

  get(key: string): HttpResponse<unknown> | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    const isExpired = Date.now() - entry.timestamp > this.CACHE_DURATION;
    if (isExpired) {
      this.cache.delete(key);
      return null;
    }

    return entry.response;
  }

  set(key: string, response: HttpResponse<unknown>): void {
    this.cache.set(key, {
      response: response.clone(),
      timestamp: Date.now()
    });
  }

  clear(): void {
    this.cache.clear();
  }
}

// Single instance of cache service
const cacheService = new CacheService();

/**
 * Markiert eine POST-Anfrage, die nur liest (Aussagen- und Herkunftssuche, Stimmen
 * mehrerer Beitraege): Sie laesst den Cache stehen. Jede andere POST-Anfrage gilt als
 * Aenderung. Die Markierung setzt der Service an seiner Anfrage, statt dass hier eine
 * Liste seiner Pfade gepflegt wird. Fehlt sie, wird der Cache nur unnoetig geleert;
 * steht sie an einer Anfrage, die schreibt, bleibt ein veralteter Stand stehen.
 * Die Suche (searchByText) traegt sie nicht: Sie legt eine Aussage an und zaehlt
 * Suchereignisse und Suchen ohne Treffer, die in den Kennzahlen erscheinen.
 */
export const NUR_LESEND = new HttpContextToken<boolean>(() => false);

/** Die Optionen fuer eine nur lesende POST-Anfrage: ``http.post(url, body, nurLesend())``. */
export function nurLesend(): { context: HttpContext } {
  return { context: new HttpContext().set(NUR_LESEND, true) };
}

/**
 * Der Fangkorb ist der gemeinsame Vorrat aller Einwuerfe: Andere Mitwirkende aendern ihn
 * laufend, und was jemand als naechstes destilliert, haengt an der aktuellen Stufe.
 * Ein Stand von vor fuenf Minuten fuehrte zu doppelter Arbeit, daher kein Cache.
 *
 * Sitzung pruefen und Nutzerinfo fragen das BFF, ob das Anmelde-Cookie noch gilt. Aus dem
 * Cache beantwortet, liessen AuthGuard und Kopfzeile eine beendete Sitzung, etwa nach einer
 * Kontoloeschung (#278), noch fuenf Minuten als angemeldet gelten.
 *
 * "Hier fehlt eine Antwort" ist geteilte Arbeit wie der Fangkorb: Was eben jemand
 * beantwortet hat, soll dort nicht mehr stehen. Ebenso die Suchanfragen, die in der
 * Moderation auf Freigabe warten: Die Liste laedt alle 30 Sekunden nach.
 *
 * Der eigene Punktestand laedt in „Meine Beitraege“ jede Minute nach (#352); aus dem
 * Cache kaeme fuenf Minuten lang derselbe Stand.
 */
const NIE_CACHEN = [
  '/api/v1/rawinput/',
  '/api/check-session',
  '/api/user-info',
  '/api/v1/statement/unbeantwortet',
  '/api/v1/moderation/suchanfragen',
  '/api/v1/usage/users/me/punkte',
  // Moderation: Meldungen, Sperren und Loeschauftraege muessen frisch sein (Zahl am Admin-Link, „Zu tun“).
  '/api/v1/moderation/',
];

/**
 * Zaehlt Aenderungen. Eine GET-Antwort kommt nur in den Cache, wenn seit ihrer
 * Anfrage keine Aenderung losging oder fertig wurde - sonst koennte sie den Stand
 * von vor der Aenderung wieder hineinschreiben.
 */
let aenderungen = 0;

/**
 * Enthaelt der Pfad der Anfrage einen der Pfade? Bewusst kein Praefixvergleich:
 * environment.baseUrl kann dem Pfad ein Praefix voranstellen.
 */
function pfadEnthaelt(req: HttpRequest<unknown>, pfade: string[]): boolean {
  const pfad = new URL(req.url, window.location.origin).pathname;
  return pfade.some((p) => pfad.includes(p));
}

function istAenderung(req: HttpRequest<unknown>): boolean {
  if (req.method === 'POST') {
    return !req.context.get(NUR_LESEND);
  }
  return req.method === 'PUT' || req.method === 'PATCH' || req.method === 'DELETE';
}

function cacheVerwerfen(): void {
  aenderungen++;
  cacheService.clear();
}

export const cacheInterceptor: HttpInterceptorFn = (req, next) => {
  if (req.method !== 'GET') {
    if (!istAenderung(req)) {
      return next(req);
    }
    // Eine Aenderung kann jede Liste, Suche und Zaehlung betreffen, nicht nur ihren
    // eigenen Pfad. Vorher und nachher leeren: Was waehrenddessen geholt wurde, kann
    // schon wieder alt sein.
    cacheVerwerfen();
    return next(req).pipe(finalize(cacheVerwerfen));
  }

  // Skip caching for auth endpoints
  if (req.url.includes('/auth/') || req.url.includes('/login')) {
    return next(req);
  }

  if (pfadEnthaelt(req, NIE_CACHEN)) {
    return next(req);
  }

  const cacheKey = `${req.method}-${req.urlWithParams}`;
  // Ein Nachladen im Hintergrund (STILLE_ABFRAGE) will den frischen Stand, nicht den Cache;
  // seine Antwort ersetzt den Eintrag.
  const cachedResponse = req.context.get(STILLE_ABFRAGE) ? null : cacheService.get(cacheKey);

  if (cachedResponse) {
    // Return cached response
    return of(cachedResponse);
  }

  // Forward request and cache the response
  const aenderungenBeiAnfrage = aenderungen;
  return next(req).pipe(
    tap(event => {
      if (event instanceof HttpResponse && aenderungenBeiAnfrage === aenderungen) {
        cacheService.set(cacheKey, event);
      }
    })
  );
};

// Exportiert fuer die Tests, die jeden Fall mit leerem Cache beginnen
export { cacheService };
