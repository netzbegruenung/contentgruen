import { HttpInterceptorFn, HttpRequest, HttpResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { finalize, of, tap } from 'rxjs';

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
 * POST-Anfragen, die nur lesen (Suche, Bildvorschlag, Stimmen mehrerer Beitraege).
 * Sie lassen den Cache stehen. Fehlt hier eine, kostet das nur einen Cache-Leerlauf.
 */
const LESENDE_POSTS = [
  '/api/v1/search/searchByText',
  '/api/v1/statement/searchStatements',
  '/api/v1/reference/search',
  '/api/v1/image/suggestCaption',
  '/api/v1/voting/votes/batch',
];

/**
 * Der Fangkorb ist ein gemeinsamer Arbeitsstapel: Andere Mitwirkende aendern ihn
 * laufend, und was jemand als naechstes destilliert, haengt an der aktuellen Stufe.
 * Ein Stand von vor fuenf Minuten fuehrte zu doppelter Arbeit, daher kein Cache.
 */
const NIE_CACHEN = ['/api/v1/rawinput/'];

/**
 * Zaehlt Aenderungen. Eine GET-Antwort kommt nur in den Cache, wenn seit ihrer
 * Anfrage keine Aenderung losging oder fertig wurde - sonst koennte sie den Stand
 * von vor der Aenderung wieder hineinschreiben.
 */
let aenderungen = 0;

function pfad(url: string): string {
  return new URL(url, window.location.origin).pathname;
}

function istAenderung(req: HttpRequest<unknown>): boolean {
  if (req.method === 'POST') {
    const p = pfad(req.url);
    return !LESENDE_POSTS.some((lesend) => p.endsWith(lesend));
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

  const urlPfad = pfad(req.url);
  if (NIE_CACHEN.some((nie) => urlPfad.includes(nie))) {
    return next(req);
  }

  const cacheKey = `${req.method}-${req.urlWithParams}`;
  const cachedResponse = cacheService.get(cacheKey);

  if (cachedResponse) {
    // Return cached response
    return of(cachedResponse);
  }

  // Forward request and cache the response
  const stand = aenderungen;
  return next(req).pipe(
    tap(event => {
      if (event instanceof HttpResponse && stand === aenderungen) {
        cacheService.set(cacheKey, event);
      }
    })
  );
};

// Export cache service for manual cache management
export { cacheService };
