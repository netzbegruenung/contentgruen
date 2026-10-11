using System.Globalization;
using System.Security.Claims;

namespace BFF.Proxy;

/// <summary>
/// Leitet den Anzeigenamen ab, den Karten beim Autor und beim Einwerfer zeigen:
/// Vorname und Initial des Nachnamens, "Anna B.".
///
/// Die Ableitung passiert genau hier und nur hier; das Backend speichert, was ankommt, und
/// rechnet nichts nach. Quellen in dieser Reihenfolge:
///   1. GivenName + Surname (Keycloak: given_name/family_name aus dem Scope profile).
///   2. Claim "name": erstes Wort + Initial des letzten. Das ist der Weg fuer Managed-Login,
///      dort steht der DisplayName aus managed-users.json im Claim "name". Nur ab zwei
///      Woertern; ein einzelnes Wort ergibt keinen Namen (Vor- oder Nachname? unklar).
///   3. GivenName allein ("Kim") - hier ist klar, dass es der Vorname ist.
/// Das Initial kommt in 1. und 2. aus dem letzten Wort des Nachnamens und ist immer ein
/// Grossbuchstabe: "von der Leyen" -> "L.", "Mueller-Luedenscheidt" ist ein Wort -> "M.".
///
/// Bewusst nie preferred_username, E-Mail oder ClaimTypes.Name: das sind Login-Kennungen,
/// keine Namen, und ein Anzeigename ist oeffentlicher als beide. Steht in einer Quelle ein
/// "@", gilt sie als Adresse und wird verworfen.
/// </summary>
public static class DisplayNamePolicy
{
    public const string NameClaim = "name";

    /// <returns>Der Anzeigename, oder null, wenn keine Quelle einen hergibt.</returns>
    public static string? From(ClaimsPrincipal user)
    {
        var vornamen = Woerter(Wert(user, ClaimTypes.GivenName));
        var nachnamen = Woerter(Wert(user, ClaimTypes.Surname));
        if (vornamen.Length > 0 && nachnamen.Length > 0)
        {
            return $"{vornamen[0]} {Initial(nachnamen[^1])}.";
        }

        // Ein einzelnes Wort im Claim "name" bleibt ungenutzt: ob es Vor- oder Nachname ist,
        // laesst sich nicht sagen, und ein Nachname allein waere identifizierender als
        // "Vorname N.".
        var name = Woerter(Wert(user, NameClaim));
        if (name.Length > 1)
        {
            return $"{name[0]} {Initial(name[^1])}.";
        }

        return vornamen.Length > 0 ? vornamen[0] : null;
    }

    private static string? Wert(ClaimsPrincipal user, string typ)
    {
        var wert = user.Claims.FirstOrDefault(c => c.Type == typ)?.Value;
        return wert is null || wert.Contains('@') ? null : wert;
    }

    private static string[] Woerter(string? wert) =>
        wert?.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
        ?? Array.Empty<string>();

    /// <summary>
    /// Das erste Textelement, nicht das erste char: sonst zerfiele ein Surrogatpaar. Immer gross,
    /// damit "von der Leyen" nicht als "l." endet.
    /// </summary>
    private static string Initial(string wort) =>
        StringInfo.GetNextTextElement(wort, 0).ToUpperInvariant();
}
