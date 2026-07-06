namespace ContentGruen.Shared
{
    public static class PublicEndpoints
    {
        /// <summary>
        /// List of API endpoints that are accessible without authentication
        /// </summary>
        public static readonly string[] Endpoints = new[]
        {
            "/api/v1/search/",
            "/api/v1/metrics/",
            "/api/metrics",
            "/api/user-info",      // Auth check endpoint - returns 401 for anonymous but shouldn't redirect
            "/api/check-session"   // Session check endpoint - returns 401 for anonymous but shouldn't redirect
        };

        /// <summary>
        /// Checks if a given path is a public endpoint
        /// </summary>
        public static bool IsPublicEndpoint(string path)
        {
            if (string.IsNullOrEmpty(path))
                return false;

            var lowerPath = path.ToLower();
            return Endpoints.Any(endpoint => lowerPath.Contains(endpoint));
        }
    }
}
