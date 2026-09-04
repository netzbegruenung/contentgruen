using Xunit;
using BFF.Proxy;

namespace BFF.Tests.Proxy;

/// <summary>
/// Die Mengen aus EndpointPolicy entscheiden, ob ein Pfad ohne Anmeldung erreichbar ist
/// (AllowAnonymous) und ob er am Rand ueberhaupt durchgelassen wird (Blocked).
///
/// Der wichtigste Test hier ist der auf den Query-String: alle vier fruheren Listen
/// haben mit Contains gearbeitet, womit ein angehaengtes "?next=/api/v1/search/" den
/// Auth-Gate geoeffnet haette.
/// </summary>
public class EndpointPolicyTests
{
    [Theory]
    [InlineData("/api/v1/search/searchbytext")]
    [InlineData("/api/v1/content/recent")]
    [InlineData("/api/v1/usage/content/abc/usage")]
    [InlineData("/api/v1/usage/trending")]
    [InlineData("/api/v1/moderation/report")]
    [InlineData("/api/v1/metrics/getmetrics")]   // Bestandszaehler der Startseite
    [InlineData("/api/v1/metrics/getMetrics")]   // Schreibweise darf keine Rolle spielen
    public void IsAnonymousAllowed_TrueForPublicPaths(string path)
    {
        Assert.True(EndpointPolicy.IsAnonymousAllowed(path));
    }

    [Theory]
    [InlineData("/api/v1/statement/addstatement")]
    [InlineData("/api/v1/contribution/getcontributionsofuser")]
    [InlineData("/api/v1/moderation/reports")]   // Plural: Admin-Liste, nicht /report
    [InlineData("/api/v1/usage/cleanup/run")]
    [InlineData("/api/v1/metrics/mvp-dashboard")]  // admin-only, anders als /getMetrics
    public void IsAnonymousAllowed_FalseForProtectedPaths(string path)
    {
        Assert.False(EndpointPolicy.IsAnonymousAllowed(path));
    }

    [Theory]
    [InlineData("/api/v1/seeding/start")]
    [InlineData("/api/v1/seeding/reset")]
    [InlineData("/api/v1/seeding/stop")]
    [InlineData("/api/v1/seeding/status")]
    [InlineData("/api/v1/test/headers")]
    public void IsBlocked_TrueForInternalEndpoints(string path)
    {
        Assert.True(EndpointPolicy.IsBlocked(path));
    }

    [Theory]
    [InlineData("/api/v1/search/searchbytext")]
    [InlineData("/api/v1/statement/addstatement")]
    [InlineData("/api/v1/health")]
    public void IsBlocked_FalseForRegularEndpoints(string path)
    {
        Assert.False(EndpointPolicy.IsBlocked(path));
    }

    [Fact]
    public void Matches_IsCaseInsensitive()
    {
        Assert.True(EndpointPolicy.IsAnonymousAllowed("/API/V1/Search/SearchByText"));
        Assert.True(EndpointPolicy.IsBlocked("/API/V1/Seeding/Start"));
    }

    [Theory]
    [InlineData("/api/v1/moderation/reports/api/v1/search/")]
    [InlineData("/api/v1/usage/cleanup/run/api/v1/search/")]
    public void Matches_DoesNotMatchInTheMiddleOfAPath(string path)
    {
        // Mit Contains waere das ein Auth-Bypass in einer Zeile gewesen.
        Assert.False(EndpointPolicy.IsAnonymousAllowed(path));
    }

    [Fact]
    public void Matches_QueryStringCannotOpenTheGate()
    {
        // HttpRequest.Path liefert den Pfad ohne Query. Faende jemand doch einen Weg,
        // den Query-String mit hereinzureichen, darf er den Gate nicht oeffnen.
        Assert.False(EndpointPolicy.IsAnonymousAllowed("/api/v1/statement/addstatement?next=/api/v1/search/"));
        Assert.False(EndpointPolicy.IsAnonymousAllowed("/api/v1/usage/cleanup/run?x=/api/v1/usage/trending"));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    public void Matches_HandlesEmptyPath(string? path)
    {
        Assert.False(EndpointPolicy.IsAnonymousAllowed(path));
        Assert.False(EndpointPolicy.IsBlocked(path));
    }
}
