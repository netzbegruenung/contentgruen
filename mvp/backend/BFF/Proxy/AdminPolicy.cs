using System.Security.Claims;

namespace BFF.Proxy;

/// <summary>
/// Eine Quelle fuer die Frage, ob ein angemeldeter Nutzer Adminrechte hat.
///
/// Dieselbe Dreier-Pruefung stand vorher zweimal woertlich im Quelltext: im
/// <see cref="IdentityHeaderTransform"/>, der daraus X-Is-Admin fuer das Python-Backend
/// setzt, und in der Minimal-API /api/user-info, aus der das Frontend seinen AdminGuard
/// speist. Zwei Kopien einer Entscheidung, die nichts miteinander verband -- dieselbe
/// Ausgangslage, aus der bei den Endpunktlisten die Divergenzen entstanden sind, die
/// <see cref="EndpointPolicy"/> zusammengezogen hat.
///
/// Zwei Wege fuehren zu Adminrechten, verknuepft mit ODER:
///
/// 1. Ein Claim am angemeldeten Nutzer. Bei Managed Auth setzt ihn der AuthController aus
///    dem isAdmin-Feld der managed-users.json; bei Keycloak muesste ihn ein Protocol-Mapper
///    ins Token legen, denn OnTokenValidated uebernimmt die Token-Claims unveraendert.
/// 2. Die Nutzerkennung steht in einer konfigurierten Allowlist (ADMIN_USER_IDS). Das ist
///    der Weg, der ohne Zugriff auf die Keycloak-Realm-Konfiguration auskommt.
///
/// Der Claim wird zuerst geprueft: ein Nutzer, der ihn traegt, bleibt Admin, auch wenn die
/// Allowlist leer ist oder ihn nicht enthaelt.
/// </summary>
public static class AdminPolicy
{
    /// <summary>
    /// Zerlegt den konfigurierten Wert in einzelne Nutzerkennungen.
    ///
    /// Getrennt wird an Kommas, Leerraum um die Eintraege faellt weg, leere Eintraege
    /// ebenso -- dieselben Split-Optionen wie bei CORS_ALLOWED_ORIGINS in Program.cs,
    /// damit im BFF nicht zwei Listenformate nebeneinander existieren.
    ///
    /// Anders als dort wird ordinal und gross-/kleinschreibungsempfindlich verglichen
    /// (siehe <see cref="IsAdmin"/>): Nutzerkennungen sind opake Zeichenketten -- eine
    /// Keycloak-UUID oder eine userId wie "user-001" -- und das Python-Backend vergleicht
    /// seine eigene Adminliste (SEMANTIC_SEARCH_ADMIN_USERS) exakt. Ein toleranterer
    /// Vergleich hier liesse beide Seiten fuer denselben Wert unterschiedlich entscheiden.
    /// </summary>
    public static string[] ParseAllowlist(string? configured) =>
        (configured ?? string.Empty)
            .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Distinct(StringComparer.Ordinal)
            .ToArray();

    /// <summary>
    /// Ob der Nutzer Adminrechte hat -- ueber einen Claim oder ueber die Allowlist.
    /// </summary>
    /// <param name="user">Der angemeldete Nutzer.</param>
    /// <param name="allowlist">
    /// Ergebnis von <see cref="ParseAllowlist"/>. Eine leere Liste ist der Normalfall und
    /// kein Fehler: dann entscheidet allein der Claim, also genau wie vor der Einfuehrung
    /// der Variablen.
    /// </param>
    public static bool IsAdmin(ClaimsPrincipal user, IReadOnlyCollection<string> allowlist)
    {
        if (user.HasClaim("isAdmin", "true") ||
            user.HasClaim("role", "admin") ||
            user.HasClaim(ClaimTypes.Role, "admin"))
        {
            return true;
        }

        if (allowlist.Count == 0)
        {
            return false;
        }

        // Verglichen wird gegen ClaimUtilities.GetUserId und nicht gegen den rohen
        // sub-Claim. Zwei Gruende: Es ist genau der Wert, den der BFF als X-User weiterreicht,
        // also derselbe, gegen den das Python-Backend SEMANTIC_SEARCH_ADMIN_USERS prueft --
        // ein Wert in beiden Variablen meint damit dieselbe Person. Und GetUserId faellt auf
        // ClaimTypes.NameIdentifier zurueck, also auf das, was das Inbound-Claim-Mapping von
        // .NET aus einem sub machen kann; beide Formen sind so abgedeckt.
        var userId = ClaimUtilities.GetUserId(user);

        return !string.IsNullOrEmpty(userId) && allowlist.Contains(userId, StringComparer.Ordinal);
    }
}
