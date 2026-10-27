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

    public static string Of(string? userId)
    {
        if (string.IsNullOrEmpty(userId) || userId == Anonymous)
        {
            return Anonymous;
        }

        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(userId));
        return Convert.ToHexString(hash, 0, 4).ToLowerInvariant();
    }
}
