using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using BFF.Controllers;
using BFF.Logging;

namespace BFF.Services;

/// <summary>
/// Prueft bei jeder Anfrage mit Anmelde-Cookie, ob das Konto dahinter noch besteht, und
/// beendet sonst die Sitzung (#278). Ohne diese Pruefung lief das Cookie nach einer
/// Kontoloeschung gleitend weiter, und die geloeschte Person konnte weiter Daten anlegen.
///
/// Abgewiesen wird ein Cookie, wenn
///   - seine Kennung in der Liste geloeschter Konten steht (beide Kontoarten), oder
///   - es von einem Beta-Zugang stammt, der nicht mehr in managed-users.json steht.
/// Beides liest nur bereits geladene Dateien (Cache fuenf Minuten), die Pruefung kostet also
/// keinen Netzaufruf.
/// </summary>
public static class KontoPruefung
{
    public static async Task ValidatePrincipalAsync(CookieValidatePrincipalContext context)
    {
        var principal = context.Principal;
        if (principal?.Identity?.IsAuthenticated != true)
        {
            return;
        }

        var services = context.HttpContext.RequestServices;
        var kennung = ClaimUtilities.GetUserId(principal);

        string? grund = null;
        if (await services.GetRequiredService<GeloeschteKontenService>().IstGeloeschtAsync(kennung))
        {
            grund = "the account is listed as deleted";
        }
        else if (principal.FindFirst(AuthController.AuthMethodClaim)?.Value == AuthController.AuthMethodManaged
                 && await services.GetRequiredService<ManagedUserService>().GetUserByIdAsync(kennung) == null)
        {
            grund = "the Beta-Zugang is no longer in managed-users.json";
        }

        if (grund == null)
        {
            return;
        }

        var logger = services.GetRequiredService<ILoggerFactory>().CreateLogger(typeof(KontoPruefung));
        logger.LogInformation("Session of user {UserId} ended: {Reason}", LogPseudonym.Of(kennung), grund);

        // RejectPrincipal laesst die Anfrage unangemeldet weiterlaufen; SignOutAsync loescht
        // zusaetzlich das Cookie im Browser, damit nicht jede weitere Anfrage es erneut vorlegt.
        context.RejectPrincipal();
        await context.HttpContext.SignOutAsync(context.Scheme.Name);
    }
}
