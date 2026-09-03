using Xunit;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using System.Net.Http;
using System.Security.Claims;
using System.Linq;
using BFF.Proxy;

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
            new HeaderDictionary(),
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
            new HeaderDictionary(),
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
            new HeaderDictionary(),
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
            new HeaderDictionary(),
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
            new HeaderDictionary(),
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
            new HeaderDictionary(),
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
            new HeaderDictionary(),
            NoAllowlist,
            Logger);

        Assert.Empty(ValuesOf(proxyRequest, "X-User-Id"));
        Assert.Empty(ValuesOf(proxyRequest, "X-Roles"));
        Assert.Equal(new[] { "echte-kennung" }, ValuesOf(proxyRequest, IdentityHeaderTransform.UserHeader));
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
    public void ClientControlledIdentityHeaders_DoesNotContainSessionHeader()
    {
        // X-Session-Id ist bewusst clientseitig (anonyme Votes und Meldungen) und traegt
        // keine Rechte. Er darf nicht versehentlich mit gestrippt werden.
        Assert.DoesNotContain(IdentityHeaderTransform.SessionHeader, IdentityHeaderTransform.ClientControlledIdentityHeaders);
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
            new HeaderDictionary(),
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
            new HeaderDictionary(),
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
            new HeaderDictionary(),
            new[] { "voellig-andere-kennung" },
            Logger);

        Assert.Equal(new[] { "true" }, ValuesOf(proxyRequest, IdentityHeaderTransform.AdminHeader));
    }

    [Fact]
    public void Apply_AllowlistWithNonEmptyEntries_DoesNotHelpAnonymousCaller()
    {
        // Die Allowlist darf keinen Weg an der bedingungslosen Entfernung weiter oben
        // vorbei oeffnen: ohne angemeldeten Nutzer gibt es keine Kennung, die in einer
        // Liste stehen koennte -- auch dann nicht, wenn der Client eine behauptet.
        var proxyRequest = ProxyRequestCarrying(
            (IdentityHeaderTransform.UserHeader, "kennung-in-liste"),
            (IdentityHeaderTransform.AdminHeader, "true"));

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AnonymousUser(),
            ProtectedPath,
            new HeaderDictionary(),
            new[] { "kennung-in-liste" },
            Logger);

        Assert.Empty(ValuesOf(proxyRequest, IdentityHeaderTransform.UserHeader));
        Assert.Empty(ValuesOf(proxyRequest, IdentityHeaderTransform.AdminHeader));
    }

    [Fact]
    public void Apply_SessionIdHeader_IsReplacedNotAppended()
    {
        var proxyRequest = ProxyRequestCarrying((IdentityHeaderTransform.SessionHeader, "kopie-von-yarp"));
        var incoming = new HeaderDictionary
        {
            { IdentityHeaderTransform.SessionHeader, "session-abc" }
        };

        IdentityHeaderTransform.Apply(
            proxyRequest,
            AnonymousUser(),
            PublicPath,
            incoming,
            NoAllowlist,
            Logger);

        Assert.Equal(new[] { "session-abc" }, ValuesOf(proxyRequest, IdentityHeaderTransform.SessionHeader));
    }
}
