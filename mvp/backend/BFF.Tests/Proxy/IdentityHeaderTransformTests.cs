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
            Logger);

        Assert.Equal(
            new[] { IdentityHeaderTransform.AnonymousUser },
            ValuesOf(proxyRequest, IdentityHeaderTransform.UserHeader));
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
            Logger);

        Assert.Equal(new[] { "session-abc" }, ValuesOf(proxyRequest, IdentityHeaderTransform.SessionHeader));
    }
}
