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
using System.Text.Json;
using System.Threading.Tasks;
using BFF.Tests.Logging;
using Microsoft.Extensions.Logging;

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

    private static WebApplicationFactory<Program> CreateHost(
        bool useKeycloak, string? adminUserIds = null, ILoggerProvider? logs = null) =>
        new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            // Die Werte hier ueberschreiben BFF/appsettings.json, damit ein spaeter
            // geaenderter Konfigurationswert diese Tests nicht stillschweigend umdeutet.
            // Ganz hermetisch ist das nicht: die Datei liegt per ProjectReference im
            // Testverzeichnis (= Content-Root), ihre Log-Regeln gelten also mit.
            builder.UseContentRoot(AppContext.BaseDirectory);
            builder.UseEnvironment("Development");
            builder.UseSetting("USE_KEYCLOAK", useKeycloak ? "true" : "false");
            builder.UseSetting("FRONTEND_URL", "http://localhost:4200");

            // Kein erreichbares Backend: alles, was den Gate passiert, endet in 502.
            builder.UseSetting("BACKEND_URL", "http://127.0.0.1:1");

            // Nur setzen, wenn ein Test die Allowlist braucht: im Betrieb ist die ungesetzte
            // Variable der Normalfall, und genau den soll der Negativfall abbilden.
            if (adminUserIds is not null)
            {
                builder.UseSetting("ADMIN_USER_IDS", adminUserIds);
            }

            // Nur Attrappen. Die Authority muss https sein, sonst wirft der
            // OpenIdConnect-Handler beim ersten Request, bevor der Gate laeuft.
            // Metadaten holt er erst bei einem Challenge, also geht hier nichts ins Netz.
            builder.UseSetting("Keycloak:Authority", "https://keycloak.invalid/realms/test");
            builder.UseSetting("Keycloak:ClientId", "test-client");
            builder.UseSetting("Keycloak:ClientSecret", "test-secret");

            // Sonst legt der Testhost den DataProtection-Schluesselring unter /keys an.
            builder.UseSetting(
                "DATAPROTECTION_KEYS_PATH",
                Path.Combine(Path.GetTempPath(), "gutgesagt-bff-test-keys"));

            builder.ConfigureTestServices(services =>
            {
                services.AddSingleton<IStartupFilter, TestUserStartupFilter>();
                if (logs is not null)
                {
                    services.AddSingleton(logs);
                }
            });
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

    /// <summary>
    /// Liest isAdmin aus /api/user-info -- ueber denselben Host und denselben Testnutzer
    /// (sub=test-user) wie die Gate-Tests oben.
    ///
    /// Nicht geprueft wird die Entscheidung selbst; die liegt in AdminPolicy und ist dort
    /// am reinen Aufruf abgedeckt. Geprueft wird die Verdrahtung dazwischen: dass Program.cs
    /// die Konfiguration unter genau dem Namen ADMIN_USER_IDS liest und die zerlegte Liste
    /// in der Closure von /api/user-info ankommt. Ein Tippfehler im Schluessel liesse jeden
    /// anderen Test gruen -- die Liste waere still leer, und das Frontend zeichnete seinen
    /// AdminGuard fuer niemanden.
    ///
    /// USE_KEYCLOAK=true, obwohl die Betriebsart fuer /api/user-info nichts entscheidet:
    /// nur im else-Zweig registriert Program.cs den DummyAuthStartupFilter, der context.User
    /// bei jedem angemeldeten Request durch den Dummy-Nutzer (test-user-id-1) ersetzt. Der
    /// liefe zwar vor dem TestUserStartupFilter und saehe noch keinen angemeldeten Nutzer --
    /// aber an dieser Reihenfolge soll die Aussage des Tests nicht haengen.
    /// </summary>
    private static async Task<bool> UserInfoIsAdmin(string? adminUserIds)
    {
        using var factory = CreateHost(useKeycloak: true, adminUserIds);
        using var client = factory.CreateClient(
            new WebApplicationFactoryClientOptions { AllowAutoRedirect = false });

        using var request = new HttpRequestMessage(HttpMethod.Get, "/api/user-info");
        request.Headers.Add(TestUserHeader, "1");

        using var response = await client.SendAsync(request);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        using var payload = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        return payload.RootElement.GetProperty("isAdmin").GetBoolean();
    }

    [Fact]
    public async Task UserInfo_ReportsAdmin_WhenTheUserIdIsListedInAdminUserIds()
    {
        // test-user ist der sub-Claim des Testnutzers und damit genau der Wert, den
        // ClaimUtilities.GetUserId gegen die Allowlist haelt.
        Assert.True(await UserInfoIsAdmin("test-user"));
    }

    [Fact]
    public async Task UserInfo_ReportsNoAdmin_WhenAdminUserIdsIsUnset()
    {
        // Der Normalfall, und das unveraenderte Verhalten von vor der Variablen: ohne
        // Allowlist entscheidet allein der Claim, und der Testnutzer traegt keinen.
        Assert.False(await UserInfoIsAdmin(adminUserIds: null));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("Information")]
    public async Task ProxiedRequest_DoesNotPutTheTargetUrlIntoTheLog(string? levelFromOutside)
    {
        // YARP schreibt jede Weiterleitung samt Ziel-URL auf Information ("Proxying to ...").
        // Die Zeile soll auch dann nicht entstehen, wenn ein Pfad doch einmal die Kennung
        // traegt (bis #284 die Nutzungsstatistik unter "Meine Beitraege"). Dasselbe gilt fuer "Request starting ..." von ASP.NET Core. Program.cs hebt Yarp
        // und Microsoft.AspNetCore im Code auf Warning (#277), also auch dann, wenn die
        // Konfiguration (appsettings.json, Logging__LogLevel__...) diese Kategorien
        // herabsetzt. Geprueft an der echten Pipeline und ueber alle Kategorien.
        var logs = new CapturingLoggerProvider();
        using var host = CreateHost(useKeycloak: true, logs: logs);
        using var fromOutside = levelFromOutside is null
            ? null
            : host.WithWebHostBuilder(builder =>
            {
                builder.UseSetting("Logging:LogLevel:Yarp", levelFromOutside);
                builder.UseSetting("Logging:LogLevel:Microsoft.AspNetCore", levelFromOutside);
            });
        var factory = fromOutside ?? host;
        using var client = factory.CreateClient(
            new WebApplicationFactoryClientOptions { AllowAutoRedirect = false });

        using var request = new HttpRequestMessage(HttpMethod.Get, "/api/v1/usage/users/test-user/usage-stats");
        request.Headers.Add(TestUserHeader, "1");
        using var response = await client.SendAsync(request);

        // 502: YARP hat weitergeleitet (und kein Backend gefunden), die Zeile waere also entstanden.
        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.DoesNotContain("test-user", logs.TextAtOrAbove(LogLevel.Information));
    }
}
