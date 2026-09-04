using Xunit;
using Microsoft.AspNetCore.Http;
using BFF.Proxy;

namespace BFF.Tests.Proxy;

/// <summary>
/// Die Pfadentscheidung hinter dem Auth-Gate, isoliert betrachtet.
///
/// Diese Datei hat frueher die Entscheidungslogik der Middleware aus Program.cs
/// nachgebaut und dann den Nachbau geprueft. Das war die Zusicherung, die gerade nicht
/// gebraucht wird: die Tests waeren gruen geblieben, wenn jemand den Gate aus
/// MapReverseProxy entfernt oder wieder hinter if (useKeycloak) gestellt haette.
/// Der Gate selbst wird jetzt in AuthGatePipelineTests durch die echte Pipeline
/// geschickt. Hier bleibt nur, was EndpointPolicy fuer sich genommen zusichert.
/// </summary>
public class AuthGateTests
{
    [Theory]
    [InlineData("/api/v1/search/searchByText")]
    [InlineData("/api/v1/content/recent")]
    [InlineData("/api/v1/usage/content/abc/usage")]
    [InlineData("/api/v1/usage/trending")]
    [InlineData("/api/v1/moderation/report")]
    [InlineData("/api/v1/metrics/getMetrics")]
    public void PublicPath_IsAnonymousAllowed(string path)
    {
        Assert.True(EndpointPolicy.IsAnonymousAllowed(path));
    }

    [Theory]
    [InlineData("/api/v1/statement/addStatement")]
    [InlineData("/api/v1/commentary/addCommentary")]
    [InlineData("/api/v1/generic_text/addGenericText")]
    [InlineData("/api/v1/contribution/getContributionsOfUser")]
    [InlineData("/api/v1/rawinput/addRawInput")]
    [InlineData("/api/v1/voting/like")]
    [InlineData("/api/v1/moderation/reports")]
    [InlineData("/api/v1/usage/cleanup/run")]
    [InlineData("/api/v1/metrics/mvp-dashboard")]
    [InlineData("/api/v1/metrics/helpful-rate")]
    public void ProtectedPath_IsNotAnonymousAllowed(string path)
    {
        Assert.False(EndpointPolicy.IsAnonymousAllowed(path));
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
