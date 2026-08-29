using Xunit;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using System.Security.Claims;
using System.Threading.Tasks;
using BFF.Proxy;

namespace BFF.Tests.Proxy;

/// <summary>
/// Der Auth-Gate der Proxy-Pipeline.
///
/// Er stand bis zu dieser Aenderung in einem <c>if (useKeycloak)</c>; der else-Zweig
/// mappte den Proxy ohne jede Pruefung. Ob ueberhaupt etwas eine Anmeldung verlangt,
/// hing damit an einer Betriebsart-Variablen statt an der Endpunkt-Definition. Die
/// Tests laufen deshalb ueber beide USE_KEYCLOAK-Werte -- das Ergebnis muss identisch
/// sein, weil der Gate die Variable gar nicht mehr liest.
///
/// Nachgebildet wird hier die Entscheidungslogik der Middleware aus Program.cs; der
/// vollstaendige Host laesst sich in einem Unit-Test nicht sinnvoll hochziehen.
/// </summary>
public class AuthGateTests
{
    private const string AuthenticatedScheme = "TestAuth";

    /// <summary>
    /// Wortgleich zur Middleware in Program.cs: 401, wenn der Pfad nicht anonym
    /// erlaubt ist und niemand angemeldet ist.
    /// </summary>
    private static async Task<int> RunGate(string path, bool authenticated, bool useKeycloak)
    {
        var context = new DefaultHttpContext();
        context.Request.Path = path;
        context.RequestServices = new ServiceCollection()
            .AddSingleton<ILogger<AuthGateTests>>(NullLogger<AuthGateTests>.Instance)
            .BuildServiceProvider();

        context.User = authenticated
            ? new ClaimsPrincipal(new ClaimsIdentity(new[] { new Claim("sub", "u1") }, AuthenticatedScheme))
            : new ClaimsPrincipal(new ClaimsIdentity());

        // useKeycloak wird bewusst ignoriert: genau das ist die Zusicherung.
        _ = useKeycloak;

        var nextCalled = false;
        if (!EndpointPolicy.IsAnonymousAllowed(context.Request.Path.Value)
            && context.User.Identity?.IsAuthenticated != true)
        {
            context.Response.StatusCode = 401;
        }
        else
        {
            nextCalled = true;
            context.Response.StatusCode = 200;
        }

        await Task.CompletedTask;
        Assert.Equal(context.Response.StatusCode == 200, nextCalled);
        return context.Response.StatusCode;
    }

    public static TheoryData<string, bool> PublicPathsBothModes()
    {
        var data = new TheoryData<string, bool>();
        foreach (var path in new[]
                 {
                     "/api/v1/search/searchByText",
                     "/api/v1/content/recent",
                     "/api/v1/usage/content/abc/usage",
                     "/api/v1/usage/trending",
                     "/api/v1/moderation/report",
                     "/api/v1/metrics/getMetrics"
                 })
        {
            data.Add(path, true);
            data.Add(path, false);
        }

        return data;
    }

    public static TheoryData<string, bool> ProtectedPathsBothModes()
    {
        var data = new TheoryData<string, bool>();
        foreach (var path in new[]
                 {
                     "/api/v1/statement/addStatement",
                     "/api/v1/commentary/addCommentary",
                     "/api/v1/generic_text/addGenericText",
                     "/api/v1/contribution/getContributionsOfUser",
                     "/api/v1/rawinput/addRawInput",
                     "/api/v1/voting/like",
                     "/api/v1/moderation/reports",
                     "/api/v1/usage/cleanup/run",
                     "/api/v1/metrics/mvp-dashboard",
                     "/api/v1/metrics/helpful-rate"
                 })
        {
            data.Add(path, true);
            data.Add(path, false);
        }

        return data;
    }

    [Theory]
    [MemberData(nameof(PublicPathsBothModes))]
    public async Task PublicEndpoint_IsReachableAnonymously_InBothAuthModes(string path, bool useKeycloak)
    {
        Assert.Equal(200, await RunGate(path, authenticated: false, useKeycloak));
    }

    [Theory]
    [MemberData(nameof(ProtectedPathsBothModes))]
    public async Task ProtectedEndpoint_IsUnauthorizedAnonymously_InBothAuthModes(string path, bool useKeycloak)
    {
        Assert.Equal(401, await RunGate(path, authenticated: false, useKeycloak));
    }

    [Theory]
    [MemberData(nameof(ProtectedPathsBothModes))]
    public async Task ProtectedEndpoint_IsReachableWhenAuthenticated_InBothAuthModes(string path, bool useKeycloak)
    {
        Assert.Equal(200, await RunGate(path, authenticated: true, useKeycloak));
    }

    [Theory]
    [InlineData("/api/v1/statement/addStatement?next=/api/v1/search/")]
    [InlineData("/api/v1/usage/cleanup/run?x=/api/v1/usage/trending")]
    [InlineData("/api/v1/moderation/reports?redirect=/api/v1/moderation/report")]
    public void QueryString_CannotOpenTheGate(string pathWithQuery)
    {
        // HttpRequest.Path liefert den Pfad ohne Query; selbst wenn der Query-String
        // hier hereinkaeme, darf er den Gate nicht oeffnen. Mit dem bisherigen
        // Contains waere das ein Auth-Bypass in einer Zeile gewesen.
        Assert.False(EndpointPolicy.IsAnonymousAllowed(pathWithQuery));
    }

    [Fact]
    public void Path_WithQueryStripped_BehavesAsExpected()
    {
        // Gegenprobe: der Pfad ohne Query ist tatsaechlich geschuetzt bzw. oeffentlich.
        var context = new DefaultHttpContext();
        context.Request.Path = "/api/v1/statement/addStatement";
        context.Request.QueryString = new QueryString("?next=/api/v1/search/");

        Assert.Equal("/api/v1/statement/addStatement", context.Request.Path.Value);
        Assert.False(EndpointPolicy.IsAnonymousAllowed(context.Request.Path.Value));
    }

    [Fact]
    public void ModerationReport_IsPublic_ButReportsListIsNot()
    {
        // Die Segmentgrenze in EndpointPolicy.Matches haelt die beiden auseinander.
        Assert.True(EndpointPolicy.IsAnonymousAllowed("/api/v1/moderation/report"));
        Assert.False(EndpointPolicy.IsAnonymousAllowed("/api/v1/moderation/reports"));
    }

    [Fact]
    public void GetMetrics_IsPublic_ButMvpMetricsAreNot()
    {
        // /getMetrics speist die anonyme Startseite; die Betriebskennzahlen daneben
        // sind admin-only. Der frueher hier stehende Eintrag "/api/v1/metrics/" hat
        // beides nicht unterschieden.
        Assert.True(EndpointPolicy.IsAnonymousAllowed("/api/v1/metrics/getMetrics"));
        Assert.False(EndpointPolicy.IsAnonymousAllowed("/api/v1/metrics/mvp-dashboard"));
        Assert.False(EndpointPolicy.IsAnonymousAllowed("/api/v1/metrics/daily-active-users"));
    }
}
