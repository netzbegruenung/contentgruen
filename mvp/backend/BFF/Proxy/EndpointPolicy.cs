namespace BFF.Proxy;

/// <summary>
/// Eine Quelle fuer die Frage, wie das BFF einen Pfad behandelt.
///
/// Vorher lagen dieselben Listen in vier Dateien mit drei Bedeutungen und
/// unterschiedlichen Eintraegen: IdentityHeaderTransform (setzt X-User: anonymous),
/// Program.cs (der eigentliche Auth-Gate), mvp/shared/PublicEndpoints.cs (toter Code,
/// in keiner .csproj) und public-endpoints.ts (Frontend, unterdrueckt nur den Redirect
/// auf /login). Die Divergenzen fielen nicht auf, weil keine Liste die andere prueft.
///
/// Hier stehen jetzt die beiden Mengen, die serverseitig etwas entscheiden. Das
/// Frontend behaelt seine eigene Liste -- sie beantwortet eine andere Frage
/// (Redirect ja/nein) und enthaelt deshalb bewusst auch Pfade, die nicht oeffentlich
/// sind; siehe den Kommentar dort.
/// </summary>
public static class EndpointPolicy
{
    /// <summary>
    /// Endpunkte, die ohne Anmeldung erreichbar sind und einen anonymen Nutzer bekommen.
    /// Speist sowohl den Auth-Gate in Program.cs als auch die Anonymous-Zuweisung im
    /// IdentityHeaderTransform -- beide sahen das vorher unterschiedlich.
    /// </summary>
    public static readonly string[] AllowAnonymous =
    {
        "/api/v1/search/",
        "/api/v1/content/recent",        // anonymer Zugriff auf neue Inhalte
        "/api/v1/usage/content/",        // anonyme Nutzungserfassung
        "/api/v1/usage/trending",        // anonymer Zugriff auf Trending
        "/api/v1/moderation/report",     // anonyme Meldung mit Session-ID
        // Nur dieser eine Metrics-Endpunkt, nicht das ganze Praefix: /getMetrics
        // liefert Bestandszaehler fuer die Startseite, die uebrigen sechs sind
        // Betriebskennzahlen und im Backend admin-only. Der frueher hier stehende
        // Eintrag "/api/v1/metrics/" haette alle sieben durchgelassen.
        "/api/v1/metrics/getMetrics"
    };
    // Nicht uebernommen: "/api/metrics" stand in allen vier Listen, existiert aber
    // nicht -- der Pfad antwortet 404. Ebenso "/api/user-info" und
    // "/api/check-session": das sind Minimal-APIs, die vor dem Proxy gemappt werden
    // und diesen Gate nie durchlaufen.

    /// <summary>
    /// Endpunkte, die am Rand gar nicht erreichbar sind -- unabhaengig von Anmeldung
    /// und Rechten.
    ///
    /// /api/v1/seeding kann Inhalte neu einspielen, den Seeding-Zustand zuruecksetzen
    /// und laufende Laeufe stoppen, und zwar ohne jede Auth-Dependency. Geloescht wird
    /// der Router trotzdem nicht: mvp/scripts/dev/run-local.sh braucht ihn zum
    /// Aufsetzen von Seed-Content und spricht ihn ueber $SEMANTIC_URL direkt auf Port
    /// 8000 an, also am BFF vorbei. Dev funktioniert damit unveraendert, waehrend der
    /// Weg von aussen zu ist.
    ///
    /// /api/v1/test steht hier als Riegel fuer den Fall, dass der Debug-Router
    /// zurueckkehrt; entfernt ist er bereits.
    /// </summary>
    public static readonly string[] Blocked =
    {
        "/api/v1/seeding",
        "/api/v1/test"
    };

    /// <summary>
    /// Prueft einen Pfad gegen eine der Mengen.
    ///
    /// Zwei Eigenschaften, die beide vorher fehlten:
    ///
    /// 1. Praefix statt Contains. Mit Contains matcht "/api/v1/search/" auch mitten im
    ///    Pfad, etwa in "/api/v1/moderation/reports/api/v1/search/". Der Pfad kommt
    ///    ohne Query-String herein (HttpRequest.Path liefert genau das), sonst wuerde
    ///    "?next=/api/v1/search/" den Gate oeffnen.
    ///
    /// 2. Das Praefix muss an einer Segmentgrenze enden. Sonst deckt der oeffentliche
    ///    Eintrag "/api/v1/moderation/report" auch "/api/v1/moderation/reports" ab --
    ///    die Admin-Liste der Meldungen. Mit dem alten Contains war das ebenso der
    ///    Fall; aufgefallen ist es erst, als ein Test es geprueft hat.
    /// </summary>
    public static bool Matches(string[] endpoints, string? path)
    {
        if (string.IsNullOrEmpty(path))
        {
            return false;
        }

        // Case-insensitiv vergleichen, statt den Pfad vorab kleinzuschreiben: sonst
        // muessten alle Eintraege oben lowercase sein, und ein Eintrag mit Grossbuchstabe
        // (etwa "/api/v1/metrics/getMetrics") wuerde still nie matchen.
        return endpoints.Any(endpoint => IsPrefixAtSegmentBoundary(path, endpoint));
    }

    private static bool IsPrefixAtSegmentBoundary(string path, string endpoint)
    {
        if (!path.StartsWith(endpoint, StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        // Eintraege, die selbst auf "/" enden, sind bereits an einer Segmentgrenze.
        if (endpoint.EndsWith('/') || path.Length == endpoint.Length)
        {
            return true;
        }

        return path[endpoint.Length] == '/';
    }

    public static bool IsAnonymousAllowed(string? path) => Matches(AllowAnonymous, path);

    public static bool IsBlocked(string? path) => Matches(Blocked, path);
}
