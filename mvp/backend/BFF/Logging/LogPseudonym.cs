using System;
using System.Security.Cryptography;
using System.Text;

namespace BFF.Logging;

/// <summary>
/// Kurzes Pseudonym fuer eine Kennung in Log-Zeilen; das Gegenstueck zu
/// log_pseudonym() im Suchdienst (app/core/logging.py) und mit demselben Ergebnis:
/// die ersten acht Hex-Zeichen von SHA-256 ueber die Kennung in UTF-8. So laesst sich
/// eine Anfrage vom BFF- ins Suchdienst-Log verfolgen, ohne dass die Kennung in einem
/// davon im Klartext steht.
///
/// Wie dort ein ungesalzener Hash: ueber Zeilen verkettbar und bei bekanntem
/// Kennungsraum zurueckrechenbar. Fuer eine fluechtige Logzeile der Kompromiss, fuer
/// gespeicherte Daten nicht (dort gilt das Tagespseudonym).
/// </summary>
public static class LogPseudonym
{
    public const string Anonymous = "anonymous";

    // Der einzige Pfad mit Kennung, den das Frontend aufruft (api/v1/usage.py, Nutzungsstatistik
    // unter "Meine Beitraege"). Kommt ein zweiter dazu, gehoert er hierher.
    private const string UsersPrefix = "/api/v1/usage/users/";

    public static string Of(string? userId)
    {
        if (string.IsNullOrEmpty(userId) || userId == Anonymous)
        {
            return Anonymous;
        }

        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(userId));
        return Convert.ToHexString(hash, 0, 4).ToLowerInvariant();
    }

    /// <summary>
    /// Der Pfad fuer eine Logzeile: das Kennungs-Segment durch sein Pseudonym ersetzt,
    /// alles andere unveraendert.
    /// </summary>
    public static string InPath(string? path)
    {
        // Das Routing von ASP.NET Core und YARP ignoriert Gross- und Kleinschreibung, also
        // auch dieser Vergleich; sonst stuende /API/v1/usage/users/{id} im Klartext im Log.
        if (string.IsNullOrEmpty(path) || !path.StartsWith(UsersPrefix, StringComparison.OrdinalIgnoreCase))
        {
            return path ?? "";
        }

        var prefix = path[..UsersPrefix.Length];
        var rest = path[UsersPrefix.Length..];
        var end = rest.IndexOf('/');
        var userId = end < 0 ? rest : rest[..end];
        var tail = end < 0 ? "" : rest[end..];
        return prefix + Of(userId) + tail;
    }
}
