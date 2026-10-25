/**
 * Pfade, bei denen der Auth-Interceptor einen 401 NICHT in einen Redirect auf /login
 * uebersetzt.
 *
 * Diese Liste beantwortet bewusst eine andere Frage als die serverseitige
 * EndpointPolicy (mvp/backend/BFF/Proxy/EndpointPolicy.cs) und ist deshalb nicht mit
 * ihr identisch -- sie ist keine Kopie, die auseinandergelaufen ist:
 *
 * - '/api/v1/voting/' steht hier, ist aber NICHT oeffentlich. Voting verlangt eine
 *   Anmeldung; die Komponenten behandeln den 401 selbst und zeigen einen Hinweis,
 *   statt die Seite zu verlassen.
 * - '/api/user-info' und '/api/check-session' sind Anmelde-Pruefungen. Sie antworten
 *   fuer Anonyme absichtlich mit 401; ein Redirect darauf waere eine Schleife.
 * - '/api/metrics' existiert serverseitig nicht mehr (der Pfad antwortet 404) und
 *   steht hier nur noch, weil auth.interceptor.spec.ts ihn als Beispiel-URL nutzt.
 *
 * Wer einen Endpunkt wirklich oeffentlich machen will, traegt ihn in EndpointPolicy
 * ein -- nur dort entscheidet sich, ob das BFF ihn ohne Anmeldung durchlaesst.
 */
export class PublicEndpoints {
  /**
   * List of API endpoints that are accessible without authentication
   * or should handle authentication errors without redirecting
   */
  public static readonly endpoints: string[] = [
    '/api/v1/search/',
    '/api/v1/metrics/',
    '/api/metrics',
    '/api/user-info',      // Auth check endpoint - returns 401 for anonymous but shouldn't redirect
    '/api/check-session',  // Session check endpoint - returns 401 for anonymous but shouldn't redirect
    '/api/v1/usage/content/',  // Allow anonymous usage tracking
    '/api/v1/usage/trending',   // Allow anonymous access to trending content
    '/api/v1/content/recent',   // oeffentlich am BFF; fehlte hier, ein anonymer
                                // Besucher wurde deshalb auf /login umgeleitet
    '/api/v1/voting/',      // Voting endpoints - handle auth errors in components, don't redirect
    '/api/v1/moderation/report'  // Allow anonymous content reporting with session ID
  ];

  /**
   * Checks if a given URL is a public endpoint
   */
  public static isPublicEndpoint(url: string): boolean {
    if (!url) {
      return false;
    }

    return this.endpoints.some(endpoint => url.includes(endpoint));
  }
}
