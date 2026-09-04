using Xunit;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Security.Claims;
using System.Threading.Tasks;

namespace BFF.Tests.Proxy;

/// <summary>
/// Der Auth-Gate der Proxy-Pipeline, durch die echte Pipeline geschickt.
///
/// Er stand bis zu dieser Aenderung in einem <c>if (useKeycloak)</c>; der else-Zweig
/// mappte den Proxy ohne jede Pruefung. Ob ueberhaupt etwas eine Anmeldung verlangt,
/// hing damit an einer Betriebsart-Variablen statt an der Endpunkt-Definition.
///
/// Diese Tests starten den vollstaendigen Host und stellen echte Requests. Das ist der
/// Unterschied zu einem Test, der die Entscheidungslogik nachbaut: sie werden rot, wenn
/// jemand den Gate aus <c>MapReverseProxy</c> entfernt oder ihn wieder hinter
/// <c>if (useKeycloak)</c> stellt -- genau die Regression, gegen die der Gate gebaut ist.
/// Ein nachgebauter Gate bliebe in beiden Faellen gruen.
///
/// Gelesen werden drei Antworten:
///   401  der Gate hat blockiert.
///   502  der Gate hat durchgelassen, YARP wollte weiterleiten und fand kein Backend.
///        BACKEND_URL zeigt absichtlich auf 127.0.0.1:1 -- die Verbindung wird sofort
///        abgelehnt, es gibt also nichts zu warten und nichts zu mocken.
///   200  kaeme nur von einem echten Backend und darf hier nicht auftreten.
/// </summary>
public class AuthGatePipelineTests
{
    private const string TestUserHeader = "X-Test-Authenticated-User";

    /// <summary>
    /// Setzt einen angemeldeten Nutzer, wenn der Testheader gesetzt ist.
    ///
    /// Laeuft vor UseAuthentication; deren Middleware ueberschreibt context.User nur,
    /// wenn ein Handler tatsaechlich ein Principal liefert, der hier gesetzte bleibt
    /// also stehen. Damit braucht der Test weder ein gueltiges Cookie noch Keycloak.
    /// </summary>
    private sealed class TestUserStartupFilter : IStartupFilter
    {
        public Action<IApplicationBuilder> Configure(Action<IApplicationBuilder> next) => builder =>
        {
            builder.Use(async (context, nextMiddleware) =>
            {
                if (context.Request.Headers.ContainsKey(TestUserHeader))
                {
                    context.User = new ClaimsPrincipal(
                        new ClaimsIdentity(new[] { new Claim("sub", "test-user") }, "TestAuth"));
                }

                await nextMiddleware();
            });

            next(builder);
        };
    }

    private static WebApplicationFactory<Program> CreateHost(bool useKeycloak) =>
        new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            // Bewusst hermetisch: der Host laeuft nicht auf BFF/appsettings.json, sondern
            // ausschliesslich auf den Werten hier, damit ein spaeter geaenderter
            // Konfigurationswert diese Tests nicht stillschweigend umdeutet.
            builder.UseContentRoot(AppContext.BaseDirectory);
            builder.UseEnvironment("Development");
            builder.UseSetting("USE_KEYCLOAK", useKeycloak ? "true" : "false");
            builder.UseSetting("FRONTEND_URL", "http://localhost:4200");

            // Kein erreichbares Backend: alles, was den Gate passiert, endet in 502.
            builder.UseSetting("BACKEND_URL", "http://127.0.0.1:1");

            // Nur Attrappen. Die Authority muss https sein, sonst wirft der
            // OpenIdConnect-Handler beim ersten Request, bevor der Gate laeuft.
            // Metadaten holt er erst bei einem Challenge, also geht hier nichts ins Netz.
            builder.UseSetting("Keycloak:Authority", "https://keycloak.invalid/realms/test");
            builder.UseSetting("Keycloak:ClientId", "test-client");
            builder.UseSetting("Keycloak:ClientSecret", "test-secret");

            // Sonst legt der Testhost den DataProtection-Schluesselring unter /keys an.
            builder.UseSetting(
                "DATAPROTECTION_KEYS_PATH",
                Path.Combine(Path.GetTempPath(), "contentgruen-bff-test-keys"));

            builder.ConfigureTestServices(services =>
                services.AddSingleton<IStartupFilter, TestUserStartupFilter>());
        });

    private static async Task<HttpStatusCode> Request(bool useKeycloak, string path, bool authenticated)
    {
        using var factory = CreateHost(useKeycloak);
        using var client = factory.CreateClient(
            new WebApplicationFactoryClientOptions { AllowAutoRedirect = false });

        using var request = new HttpRequestMessage(HttpMethod.Get, path);
        if (authenticated)
        {
            request.Headers.Add(TestUserHeader, "1");
        }

        using var response = await client.SendAsync(request);
        return response.StatusCode;
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
    public async Task PublicEndpoint_PassesTheGateAnonymously_InBothAuthModes(string path, bool useKeycloak)
    {
        Assert.Equal(HttpStatusCode.BadGateway, await Request(useKeycloak, path, authenticated: false));
    }

    [Theory]
    [MemberData(nameof(ProtectedPathsBothModes))]
    public async Task ProtectedEndpoint_IsUnauthorizedAnonymously_InBothAuthModes(string path, bool useKeycloak)
    {
        Assert.Equal(HttpStatusCode.Unauthorized, await Request(useKeycloak, path, authenticated: false));
    }

    [Theory]
    [MemberData(nameof(ProtectedPathsBothModes))]
    public async Task ProtectedEndpoint_PassesTheGateWhenAuthenticated_InBothAuthModes(string path, bool useKeycloak)
    {
        Assert.Equal(HttpStatusCode.BadGateway, await Request(useKeycloak, path, authenticated: true));
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task QueryString_CannotOpenTheGate(bool useKeycloak)
    {
        // Mit dem frueheren Contains waere das ein Auth-Bypass in einer Zeile gewesen.
        // Hier geprueft am echten Request, nicht nur an EndpointPolicy.
        Assert.Equal(
            HttpStatusCode.Unauthorized,
            await Request(useKeycloak, "/api/v1/statement/addStatement?next=/api/v1/search/", authenticated: false));
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task ModerationReport_IsPublic_ButReportsListIsNot(bool useKeycloak)
    {
        // Die Segmentgrenze in EndpointPolicy.Matches, an der echten Pipeline nachgewiesen.
        Assert.Equal(
            HttpStatusCode.BadGateway,
            await Request(useKeycloak, "/api/v1/moderation/report", authenticated: false));
        Assert.Equal(
            HttpStatusCode.Unauthorized,
            await Request(useKeycloak, "/api/v1/moderation/reports", authenticated: false));
    }
}
