using System.Security.Claims;

namespace BFF.Proxy;

/// <summary>
/// Setzt die Header, aus denen das Backend Nutzeridentitaet und Adminrechte ableitet.
///
/// YARP kopiert per Default saemtliche eingehenden Header in den Proxy-Request. Ein Client
/// kann Identitaets- und Rechte-Header also selbst mitschicken; sie stehen bereits auf dem
/// Proxy-Request, bevor dieser Code laeuft. Deshalb wird die Liste in
/// <see cref="ClientControlledIdentityHeaders"/> hier zuerst bedingungslos entfernt -- vor
/// jeder Verzweigung, damit auch die Pfade ohne angemeldeten Nutzer nichts vom Client
/// durchreichen -- und danach werden X-User und X-Is-Admin ausschliesslich aus den Claims
/// des BFF gesetzt. Gesetzt wird ersetzend, damit beim Backend garantiert genau ein Wert
/// ankommt.
/// </summary>
public static class IdentityHeaderTransform
{
    public const string UserHeader = "X-User";
    public const string AdminHeader = "X-Is-Admin";
    public const string SessionHeader = "X-Session-Id";

    public const string AnonymousUser = "anonymous";

    /// <summary>
    /// Header, ueber die der Client keine Aussage treffen darf. Sie werden bedingungslos
    /// entfernt, bevor irgendetwas gesetzt wird.
    ///
    /// Eine Aufzaehlung statt Einzelaufrufe, weil genau hier der Fehler entstanden ist:
    /// X-User und X-Is-Admin wurden entfernt, X-User-Id nicht -- und der Semantic-Service
    /// las X-User-Id (dependencies.get_current_user_optional). Ein anonymer Aufrufer
    /// konnte sich damit per Header eine fremde Identitaet geben. X-User-Id wird
    /// inzwischen nirgends mehr gelesen; er bleibt hier trotzdem stehen, damit ein
    /// Wiedereinfuehren des Headers nicht erneut zur Luecke wird.
    ///
    /// Wer einen neuen Identitaets- oder Rechte-Header einfuehrt, traegt ihn hier ein.
    /// Nicht enthalten ist X-Session-Id: das ist bewusst clientseitig (siehe unten).
    /// </summary>
    public static readonly string[] ClientControlledIdentityHeaders =
    {
        UserHeader,
        AdminHeader,
        "X-User-Id",
        "X-User-Name",
        "X-Roles",
        "X-Is-Authenticated"
    };

    /// <summary>
    /// Endpunkte, die ohne Anmeldung erreichbar sind und einen anonymen Nutzer bekommen.
    /// </summary>
    private static readonly string[] PublicEndpoints =
    {
        "/api/v1/search/",
        "/api/v1/metrics/",
        "/api/metrics",
        "/api/v1/usage/content/",   // Allow anonymous usage tracking
        "/api/v1/usage/trending",   // Allow anonymous access to trending content
        "/api/v1/content/recent",   // Allow anonymous access to recent content
        "/api/v1/moderation/report" // Allow anonymous content reporting with session ID
    };

    public static void Apply(
        HttpRequestMessage proxyRequest,
        ClaimsPrincipal user,
        string? path,
        IHeaderDictionary incomingHeaders,
        ILogger logger)
    {
        // Zuerst und ohne Bedingung: der Client darf ueber Identitaet und Rechte nichts aussagen.
        foreach (var header in ClientControlledIdentityHeaders)
        {
            proxyRequest.Headers.Remove(header);
        }

        var normalizedPath = path?.ToLower() ?? "";
        var userId = ClaimUtilities.GetUserId(user);

        if (!string.IsNullOrEmpty(userId))
        {
            SetSingleValue(proxyRequest, UserHeader, userId);
            logger.LogDebug("Set X-User header for authenticated user: {UserId}", userId);

            var isAdmin = user.HasClaim("isAdmin", "true") ||
                          user.HasClaim("role", "admin") ||
                          user.HasClaim(ClaimTypes.Role, "admin");
            if (isAdmin)
            {
                SetSingleValue(proxyRequest, AdminHeader, "true");
                logger.LogDebug("Set X-Is-Admin header for admin user: {UserId}", userId);
            }
        }
        else if (PublicEndpoints.Any(endpoint => normalizedPath.Contains(endpoint)))
        {
            SetSingleValue(proxyRequest, UserHeader, AnonymousUser);
            logger.LogDebug("Set anonymous X-User header for public endpoint: {Path}", normalizedPath);
        }
        else
        {
            logger.LogWarning("No user identifier found for protected endpoint: {Path}", normalizedPath);
        }

        // X-Session-Id ist bewusst clientseitig (anonyme Votes und Meldungen) und traegt keine
        // Rechte. Es wird trotzdem ersetzt statt angehaengt, damit nicht zwei Werte ankommen.
        var sessionId = incomingHeaders[SessionHeader].FirstOrDefault();
        if (!string.IsNullOrEmpty(sessionId))
        {
            SetSingleValue(proxyRequest, SessionHeader, sessionId);
            logger.LogDebug("Forwarded X-Session-Id header");
        }
    }

    /// <summary>
    /// HttpHeaders kennt kein Set(): erst entfernen, dann genau einen Wert anhaengen.
    /// Add() allein wuerde einen bereits vorhandenen Wert stehen lassen, und beim Backend
    /// gewinnt bei zwei gleichnamigen Headern der erste.
    /// </summary>
    private static void SetSingleValue(HttpRequestMessage request, string name, string value)
    {
        request.Headers.Remove(name);
        request.Headers.Add(name, value);
    }
}
