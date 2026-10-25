import { HttpInterceptorFn, HttpRequest, HttpResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { of, tap } from 'rxjs';

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

  delete(pattern: string): void {
    const keysToDelete: string[] = [];
    this.cache.forEach((_, key) => {
      if (key.includes(pattern)) {
        keysToDelete.push(key);
      }
    });
    keysToDelete.forEach(key => this.cache.delete(key));
  }
}

// Single instance of cache service
const cacheService = new CacheService();

export const cacheInterceptor: HttpInterceptorFn = (req, next) => {
  // Only cache GET requests
  if (req.method !== 'GET') {
    // Clear related cache on mutations
    if (req.method === 'POST' || req.method === 'PUT' || req.method === 'DELETE') {
      const urlPath = new URL(req.url, window.location.origin).pathname;
      cacheService.delete(urlPath);
    }
    return next(req);
  }

  // Skip caching for auth endpoints
  if (req.url.includes('/auth/') || req.url.includes('/login')) {
    return next(req);
  }

  const cacheKey = `${req.method}-${req.urlWithParams}`;
  const cachedResponse = cacheService.get(cacheKey);

  if (cachedResponse) {
    // Return cached response
    return of(cachedResponse);
  }

  // Forward request and cache the response
  return next(req).pipe(
    tap(event => {
      if (event instanceof HttpResponse) {
        cacheService.set(cacheKey, event);
      }
    })
  );
};

// Export cache service for manual cache management
export { cacheService };
