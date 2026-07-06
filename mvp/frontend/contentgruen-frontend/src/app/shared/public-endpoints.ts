/**
 * Centralized configuration for public API endpoints
 * These endpoints are accessible without authentication
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
