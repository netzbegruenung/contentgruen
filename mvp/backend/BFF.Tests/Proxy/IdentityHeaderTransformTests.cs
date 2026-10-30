using Xunit;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using System.Net.Http;
using System.Security.Claims;
using System.Linq;
using BFF.Proxy;
using BFF.Logging;
using BFF.Tests.Logging;

namespace BFF.Tests.Proxy;

/// <summary>
/// YARP kopiert eingehende Header in den Proxy-Request. Die Tests bilden das nach, indem sie
/// den Wert eines Clients vorab auf den HttpRequestMessage setzen, und pruefen, dass danach
/// ausschliesslich der vom BFF ermittelte Wert beim Backend ankommt.
/// </summary>
public class IdentityHeaderTransformTests
{
    private const string ClientSuppliedUser = "fremde-kennung";
    private const string ProtectedPath = "/api/v1/statement/addStatement";
    private const string PublicPath = "/api/v1/search/searchByText";

    private static readonly ILogger Logger = NullLogger.Instance;

    /// <summary>
    /// Der Normalfall: ADMIN_USER_IDS ist nicht gesetzt, es entscheidet allein der Claim.
    /// Als benannte Konstante an jeder Aufrufstelle statt als Standardwert an Apply --
    /// so ist an jedem Test ablesbar, welche Allowlist gilt.
    /// </summary>
    private static readonly string[] NoAllowlist = Array.Empty<string>();

    private static ClaimsPrincipal AuthenticatedUser(string userId, bool isAdmin = false)
    {
        var claims = new List<Claim> { new Claim("sub", userId) };
        if (isAdmin)
        {
            claims.Add(new Claim("isAdmin", "true"));
        }

        return new ClaimsPrincipal(new ClaimsIdentity(claims, "TestAuth"));
    }

    private static ClaimsPrincipal AnonymousUser() => new ClaimsPrincipal(new ClaimsIdentity());

    private static HttpRequestMessage ProxyRequestCarrying(params (string Name, string Value)[] headers)
    {
        var request = new HttpRequestMessage();
        foreach (var (name, value) in headers)
        {
            request.Headers.Add(name, value);
        }

        return request;
    }

    private static string[] ValuesOf(HttpRequestMessage request, string name) =>
        request.Headers.TryGetValues(name, out var values) ? values.ToArray() : Array.Empty<string>();

    [Fact]
    public void Apply_AuthenticatedUser_DropsClientSuppliedUserHeader()
    {
        var proxyRequest = ProxyRequestCarrying((IdentityHeaderTransform.UserHeader, ClientSuppliedUser));

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AuthenticatedUser("echte-kennung"),
            ProtectedPath,
            NoAllowlist,
            Logger);

        Assert.Equal(new[] { "echte-kennung" }, ValuesOf(proxyRequest, IdentityHeaderTransform.UserHeader));
    }

    [Fact]
    public void Apply_NonAdminUser_DropsClientSuppliedAdminHeader()
    {
        var proxyRequest = ProxyRequestCarrying(
            (IdentityHeaderTransform.UserHeader, ClientSuppliedUser),
            (IdentityHeaderTransform.AdminHeader, "true"));

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AuthenticatedUser("echte-kennung"),
            ProtectedPath,
            NoAllowlist,
            Logger);

        Assert.Empty(ValuesOf(proxyRequest, IdentityHeaderTransform.AdminHeader));
        Assert.Equal(new[] { "echte-kennung" }, ValuesOf(proxyRequest, IdentityHeaderTransform.UserHeader));
    }

    [Fact]
    public void Apply_AdminUser_SetsAdminHeaderExactlyOnce()
    {
        var proxyRequest = ProxyRequestCarrying((IdentityHeaderTransform.AdminHeader, "true"));

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AuthenticatedUser("echte-kennung", isAdmin: true),
            ProtectedPath,
            NoAllowlist,
            Logger);

        Assert.Equal(new[] { "true" }, ValuesOf(proxyRequest, IdentityHeaderTransform.AdminHeader));
    }

    [Fact]
    public void Apply_NoUserOnProtectedEndpoint_ForwardsNoIdentityAtAll()
    {
        // Der Zweig, in dem der BFF selbst nichts setzt: hier darf erst recht nichts
        // vom Client stehen bleiben.
        var proxyRequest = ProxyRequestCarrying(
            (IdentityHeaderTransform.UserHeader, ClientSuppliedUser),
            (IdentityHeaderTransform.AdminHeader, "true"));

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AnonymousUser(),
            ProtectedPath,
            NoAllowlist,
            Logger);

        Assert.Empty(ValuesOf(proxyRequest, IdentityHeaderTransform.UserHeader));
        Assert.Empty(ValuesOf(proxyRequest, IdentityHeaderTransform.AdminHeader));
    }

    [Fact]
    public void Apply_NoUserOnPublicEndpoint_ForwardsOnlyAnonymous()
    {
        var proxyRequest = ProxyRequestCarrying(
            (IdentityHeaderTransform.UserHeader, ClientSuppliedUser),
            (IdentityHeaderTransform.AdminHeader, "true"));

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AnonymousUser(),
            PublicPath,
            NoAllowlist,
            Logger);

        Assert.Equal(
            new[] { IdentityHeaderTransform.AnonymousUser },
            ValuesOf(proxyRequest, IdentityHeaderTransform.UserHeader));
        Assert.Empty(ValuesOf(proxyRequest, IdentityHeaderTransform.AdminHeader));
    }

    [Theory]
    [InlineData("X-User-Id")]
    [InlineData("X-User-Name")]
    [InlineData(IdentityHeaderTransform.DisplayNameHeader)]
    [InlineData("X-Roles")]
    [InlineData("X-Is-Authenticated")]
    public void Apply_StripsEveryClientControlledIdentityHeader(string header)
    {
        // X-User-Id war der konkrete Fall: nicht entfernt, aber vom Semantic-Service
        // gelesen -- ein anonymer Aufrufer konnte sich damit eine fremde Identitaet geben.
        var proxyRequest = ProxyRequestCarrying((header, ClientSuppliedUser));

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AnonymousUser(),
            PublicPath,
            NoAllowlist,
            Logger);

        Assert.Empty(ValuesOf(proxyRequest, header));
    }

    [Fact]
    public void Apply_AuthenticatedUser_StripsClientControlledHeadersToo()
    {
        // Auch der Zweig mit angemeldetem Nutzer darf nichts vom Client stehen lassen.
        var proxyRequest = ProxyRequestCarrying(
            ("X-User-Id", ClientSuppliedUser),
            ("X-Roles", "admin"));

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AuthenticatedUser("echte-kennung"),
            ProtectedPath,
            NoAllowlist,
            Logger);

        Assert.Empty(ValuesOf(proxyRequest, "X-User-Id"));
        Assert.Empty(ValuesOf(proxyRequest, "X-Roles"));
        Assert.Equal(new[] { "echte-kennung" }, ValuesOf(proxyRequest, IdentityHeaderTransform.UserHeader));
    }

    [Fact]
    public void Apply_AuthenticatedUserWithName_SetsEncodedDisplayNameOnce()
    {
        var proxyRequest = ProxyRequestCarrying((IdentityHeaderTransform.DisplayNameHeader, "Gefaelscht X."));
        var user = new ClaimsPrincipal(new ClaimsIdentity(new[]
        {
            new Claim("sub", "echte-kennung"),
            new Claim(ClaimTypes.GivenName, "Jürgen"),
            new Claim(ClaimTypes.Surname, "Östermann")
        }, "TestAuth"));

        IdentityHeaderTransform.Apply(
            proxyRequest,
            user,
            ProtectedPath,
            NoAllowlist,
            Logger);

        var werte = ValuesOf(proxyRequest, IdentityHeaderTransform.DisplayNameHeader);
        Assert.Equal(new[] { "J%C3%BCrgen%20%C3%96." }, werte);
        Assert.Equal("Jürgen Ö.", Uri.UnescapeDataString(werte[0]));
    }

    [Fact]
    public void Apply_AuthenticatedUserWithoutName_SetsNoDisplayName()
    {
        // Ohne verwertbaren Namen kein Header -- auch nicht der, den der Client mitschickt.
        var proxyRequest = ProxyRequestCarrying((IdentityHeaderTransform.DisplayNameHeader, "Gefaelscht X."));

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AuthenticatedUser("echte-kennung"),
            ProtectedPath,
            NoAllowlist,
            Logger);

        Assert.Empty(ValuesOf(proxyRequest, IdentityHeaderTransform.DisplayNameHeader));
    }

    [Fact]
    public void Apply_AnonymousOnPublicEndpoint_SetsNoDisplayName()
    {
        var proxyRequest = ProxyRequestCarrying((IdentityHeaderTransform.DisplayNameHeader, "Gefaelscht X."));

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AnonymousUser(),
            PublicPath,
            NoAllowlist,
            Logger);

        Assert.Empty(ValuesOf(proxyRequest, IdentityHeaderTransform.DisplayNameHeader));
    }

    [Fact]
    public void ClientControlledIdentityHeaders_CoversUserAndAdminHeader()
    {
        // Die beiden urspruenglich einzeln entfernten Header muessen in der Liste bleiben,
        // sonst faellt die Absicherung beim Umbau still hinten runter.
        Assert.Contains(IdentityHeaderTransform.UserHeader, IdentityHeaderTransform.ClientControlledIdentityHeaders);
        Assert.Contains(IdentityHeaderTransform.AdminHeader, IdentityHeaderTransform.ClientControlledIdentityHeaders);
    }

    [Fact]
    public void ClientControlledIdentityHeaders_ContainsSessionHeader()
    {
        // Seit #446 gibt es keine Sitzungskennung im Browser mehr; Besucher erkennt der
        // Suchdienst an einem Tagespseudonym. Ein mitgeschickter X-Session-Id darf ihn
        // nicht erreichen.
        Assert.Contains(IdentityHeaderTransform.SessionHeader, IdentityHeaderTransform.ClientControlledIdentityHeaders);
    }

    [Fact]
    public void Apply_UserIdInAllowlist_SetsAdminHeaderWithoutAnyClaim()
    {
        // Der Zweck der Variablen: Adminrechte ohne einen Claim, den nur die
        // Realm-Konfiguration in Keycloak liefern koennte.
        var proxyRequest = ProxyRequestCarrying();

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AuthenticatedUser("kennung-in-liste"),
            ProtectedPath,
            new[] { "andere-kennung", "kennung-in-liste" },
            Logger);

        Assert.Equal(new[] { "true" }, ValuesOf(proxyRequest, IdentityHeaderTransform.AdminHeader));
    }

    [Fact]
    public void Apply_UserIdNotInAllowlistAndNoClaim_SetsNoAdminHeader()
    {
        var proxyRequest = ProxyRequestCarrying();

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AuthenticatedUser("kennung-ohne-rechte"),
            ProtectedPath,
            new[] { "andere-kennung" },
            Logger);

        Assert.Empty(ValuesOf(proxyRequest, IdentityHeaderTransform.AdminHeader));
        Assert.Equal(new[] { "kennung-ohne-rechte" }, ValuesOf(proxyRequest, IdentityHeaderTransform.UserHeader));
    }

    [Fact]
    public void Apply_AdminClaimAndUserIdNotInAllowlist_StaysAdmin()
    {
        // Die Allowlist kommt als ODER dazu; sie ersetzt die Claim-Pruefung nicht. Ohne
        // diesen Test wuerde ein Umbau, der beides vertauscht, allen Managed-Auth-Admins
        // still die Rechte nehmen.
        var proxyRequest = ProxyRequestCarrying();

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AuthenticatedUser("kennung-mit-claim", isAdmin: true),
            ProtectedPath,
            new[] { "voellig-andere-kennung" },
            Logger);

        Assert.Equal(new[] { "true" }, ValuesOf(proxyRequest, IdentityHeaderTransform.AdminHeader));
    }

    /// <param name="expectedUser">
    /// Was der BFF selbst setzt: auf dem geschuetzten Pfad nichts (null), auf dem
    /// oeffentlichen die Sentinel-Kennung "anonymous". In beiden Faellen darf vom Client
    /// nichts uebrig bleiben.
    /// </param>
    [Theory]
    [InlineData(ProtectedPath, null)]
    [InlineData(PublicPath, IdentityHeaderTransform.AnonymousUser)]
    public void Apply_AllowlistWithNonEmptyEntries_DoesNotHelpAnonymousCaller(string path, string? expectedUser)
    {
        // Die Allowlist darf keinen Weg an der bedingungslosen Entfernung weiter oben
        // vorbei oeffnen: ohne angemeldeten Nutzer gibt es keine Kennung, die in einer
        // Liste stehen koennte -- auch dann nicht, wenn der Client eine behauptet.
        //
        // Beide Pfade, weil nur der oeffentliche Zweig selbst ein X-User setzt und die
        // Allowlist dort gar nicht gefragt wird. Heute stimmt das; der Test haelt es fest
        // fuer den Umbau, der die Admin-Entscheidung ueber die Verzweigung zieht.
        //
        // "anonymous" steht bewusst mit in der Liste: die Sentinel-Kennung des
        // oeffentlichen Zweigs ist eine Zeichenkette wie jede andere, und ein Eintrag
        // dieses Namens -- versehentlich oder nicht -- darf nicht jeden anonymen Aufrufer
        // zum Admin machen.
        var proxyRequest = ProxyRequestCarrying(
            (IdentityHeaderTransform.UserHeader, "kennung-in-liste"),
            (IdentityHeaderTransform.AdminHeader, "true"));

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AnonymousUser(),
            path,
            new[] { "kennung-in-liste", IdentityHeaderTransform.AnonymousUser },
            Logger);

        Assert.Equal(
            expectedUser is null ? Array.Empty<string>() : new[] { expectedUser },
            ValuesOf(proxyRequest, IdentityHeaderTransform.UserHeader));
        Assert.Empty(ValuesOf(proxyRequest, IdentityHeaderTransform.AdminHeader));
    }

    [Fact]
    public void Apply_SessionIdHeader_IsNotForwarded()
    {
        // YARP hat den Header des Clients schon auf den Proxy-Request kopiert.
        var proxyRequest = ProxyRequestCarrying((IdentityHeaderTransform.SessionHeader, "session-abc"));

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AnonymousUser(),
            PublicPath,
            NoAllowlist,
            Logger);

        Assert.Empty(ValuesOf(proxyRequest, IdentityHeaderTransform.SessionHeader));
    }

    [Fact]
    public void Apply_RealIpAndUserAgent_AreForwardedUnchanged()
    {
        // Aus beiden bildet der Suchdienst das Tagespseudonym der Besucher (#446). Nimmt die
        // Transformation sie weg, zaehlen alle Besucher mit gleichem Browser als eine Person.
        var proxyRequest = ProxyRequestCarrying(
            ("X-Real-IP", "198.51.100.5"),
            ("User-Agent", "Firefox/131.0"),
            (IdentityHeaderTransform.SessionHeader, "session-abc"));

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AnonymousUser(),
            PublicPath,
            NoAllowlist,
            Logger);

        Assert.Equal(new[] { "198.51.100.5" }, ValuesOf(proxyRequest, "X-Real-IP"));
        Assert.Equal(new[] { "Firefox/131.0" }, ValuesOf(proxyRequest, "User-Agent"));
    }

    [Fact]
    public void Apply_AdminUser_LogsOnlyThePseudonym()
    {
        // Auch auf Debug: der Dev-Stack laeuft auf Debug, und die Zeile entsteht bei jeder
        // angemeldeten Anfrage (#277).
        var logger = new CapturingLogger<IdentityHeaderTransformTests>();

        IdentityHeaderTransform.Apply(
            new HttpRequestMessage(),
            AuthenticatedUser("echte-kennung", isAdmin: true),
            ProtectedPath,
            NoAllowlist,
            logger);

        Assert.DoesNotContain("echte-kennung", logger.Text);
        Assert.Contains(LogPseudonym.Of("echte-kennung"), logger.Text);
    }
}
