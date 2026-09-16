using Xunit;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.AspNetCore.WebUtilities;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.IdentityModel.Protocols;
using Microsoft.IdentityModel.Protocols.OpenIdConnect;
using Microsoft.IdentityModel.Tokens;
using Microsoft.Net.Http.Headers;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using BFF.Controllers;

namespace BFF.Tests.Controllers;

/// <summary>
/// Die Keycloak-Anmeldung, einmal ganz durch die echte Pipeline: Challenge ueber
/// /api/auth/login/keycloak, Rueckkehr auf /signin-oidc, Einloesen des Codes.
///
/// Keycloak selbst ist eine Attrappe: eine feste OIDC-Konfiguration und ein Token-Endpunkt
/// im Backchannel, der ein mit einem Testschluessel signiertes ID-Token ausgibt. Alles
/// andere -- Correlation- und Nonce-Cookie, Validierung, Ticket, Anmelde-Cookie -- ist der
/// Code, der auch auf Test laeuft.
///
/// Anlass: Das Anmelde-Cookie ging ohne Expires raus, weil das Ticket nicht persistent war.
/// Ein solches Sitzungs-Cookie verwirft Android mit dem PWA-Prozess, und die Nutzerin musste
/// sich nach jedem App-Wechsel neu anmelden. Die Tests lesen deshalb den Set-Cookie-Header
/// selbst, nicht das Ticket.
/// </summary>
public class KeycloakLoginCookieTests
{
    private const string Authority = "https://keycloak.invalid/realms/test";
    private const string ClientId = "test-client";
    private const string FrontendUrl = "http://localhost:4200";

    private sealed class FakeTokenEndpoint : HttpMessageHandler
    {
        public string? Nonce { get; set; }
        public required SigningCredentials Credentials { get; init; }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            const string accessToken = "test-access-token";
            var hash = SHA256.HashData(Encoding.ASCII.GetBytes(accessToken));
            var now = DateTime.UtcNow;

            var idToken = new JsonWebTokenHandler().CreateToken(new SecurityTokenDescriptor
            {
                Issuer = Authority,
                Audience = ClientId,
                IssuedAt = now,
                NotBefore = now,
                Expires = now.AddMinutes(5),
                SigningCredentials = Credentials,
                Claims = new Dictionary<string, object>
                {
                    ["sub"] = "keycloak-user-1",
                    ["nonce"] = Nonce!,
                    ["at_hash"] = Base64UrlEncoder.Encode(hash.AsSpan(0, hash.Length / 2).ToArray()),
                    ["name"] = "Test Nutzerin",
                    ["email"] = "nutzerin@example.org"
                }
            });

            var body = JsonSerializer.Serialize(new
            {
                access_token = accessToken,
                token_type = "Bearer",
                expires_in = 300,
                id_token = idToken
            });

            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(body, Encoding.UTF8, "application/json")
            });
        }
    }

    private static (WebApplicationFactory<Program> Factory, FakeTokenEndpoint Endpoint) CreateHost()
    {
        var key = new RsaSecurityKey(RSA.Create(2048)) { KeyId = "test-key" };
        var endpoint = new FakeTokenEndpoint
        {
            Credentials = new SigningCredentials(key, SecurityAlgorithms.RsaSha256)
        };

        var configuration = new OpenIdConnectConfiguration
        {
            Issuer = Authority,
            AuthorizationEndpoint = Authority + "/protocol/openid-connect/auth",
            TokenEndpoint = Authority + "/protocol/openid-connect/token"
        };
        configuration.SigningKeys.Add(key);

        var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            // Hermetisch wie AuthGatePipelineTests: nur die Werte hier, keine appsettings.json.
            builder.UseContentRoot(AppContext.BaseDirectory);
            builder.UseEnvironment("Development");
            builder.UseSetting("USE_KEYCLOAK", "true");
            builder.UseSetting("FRONTEND_URL", FrontendUrl);
            builder.UseSetting("BACKEND_URL", "http://127.0.0.1:1");
            builder.UseSetting("Keycloak:Authority", Authority);
            builder.UseSetting("Keycloak:ClientId", ClientId);
            builder.UseSetting("Keycloak:ClientSecret", "test-secret");
            builder.UseSetting(
                "DATAPROTECTION_KEYS_PATH",
                Path.Combine(Path.GetTempPath(), "contentgruen-bff-test-keys"));

            // Registriert nach AddOpenIdConnect, laeuft also nach dessen PostConfigure und
            // ersetzt den ConfigurationManager, der sonst die Metadaten aus dem Netz holen wuerde.
            builder.ConfigureTestServices(services =>
                services.PostConfigure<OpenIdConnectOptions>(OpenIdConnectDefaults.AuthenticationScheme, options =>
                {
                    options.Configuration = configuration;
                    options.ConfigurationManager = new StaticConfigurationManager<OpenIdConnectConfiguration>(configuration);
                    options.Backchannel = new HttpClient(endpoint);
                }));
        });

        return (factory, endpoint);
    }

    /// <summary>Spielt die Anmeldung durch und gibt die Antwort von /signin-oidc zurueck.</summary>
    private static async Task<HttpResponseMessage> LoginAsync(string? returnUrl)
    {
        var (factory, endpoint) = CreateHost();
        using var client = factory.CreateClient(new WebApplicationFactoryClientOptions
        {
            AllowAutoRedirect = false,
            HandleCookies = false
        });

        var loginPath = "/api/auth/login/keycloak"
                        + (returnUrl is null ? "" : "?returnUrl=" + Uri.EscapeDataString(returnUrl));
        using var challenge = await client.GetAsync(loginPath);
        Assert.Equal(HttpStatusCode.Redirect, challenge.StatusCode);

        var authorize = QueryHelpers.ParseQuery(challenge.Headers.Location!.Query);
        endpoint.Nonce = authorize["nonce"];

        // Correlation- und Nonce-Cookie von Hand zurueckgeben, damit der Test nicht davon
        // abhaengt, ob der Cookie-Container ohne HTTPS mitspielt.
        var cookies = SetCookieHeaderValue.ParseList(challenge.Headers.GetValues("Set-Cookie").ToList())
            .Select(c => $"{c.Name}={c.Value}");

        using var callback = new HttpRequestMessage(HttpMethod.Post, "/signin-oidc")
        {
            Content = new FormUrlEncodedContent(new Dictionary<string, string>
            {
                ["code"] = "test-code",
                ["state"] = authorize["state"]!
            })
        };
        callback.Headers.Add("Cookie", string.Join("; ", cookies));

        return await client.SendAsync(callback);
    }

    private static SetCookieHeaderValue AuthCookie(HttpResponseMessage response)
    {
        Assert.True(response.Headers.TryGetValues("Set-Cookie", out var values), "no Set-Cookie on the callback");
        var authCookies = SetCookieHeaderValue.ParseList(values!.ToList())
            .Where(c => c.Name == "ContentGruenAuthCookie")
            .ToList();

        // Genau eines: frueher stellte OnTokenValidated ein zweites aus, das das des Handlers
        // ueberschrieb.
        return Assert.Single(authCookies);
    }

    [Fact]
    public async Task KeycloakLogin_IssuesPersistentCookie_ValidForFourteenDays()
    {
        using var response = await LoginAsync(returnUrl: null);

        var cookie = AuthCookie(response);
        Assert.NotNull(cookie.Expires);
        var remaining = cookie.Expires!.Value - DateTimeOffset.UtcNow;
        Assert.InRange(remaining, TimeSpan.FromDays(14) - TimeSpan.FromMinutes(5), TimeSpan.FromDays(14));
    }

    [Fact]
    public async Task KeycloakLogin_ReturnsToReturnUrl()
    {
        using var response = await LoginAsync(returnUrl: "/einwerfen?quelle=teilen");

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        Assert.Equal(FrontendUrl + "/einwerfen?quelle=teilen", response.Headers.Location!.OriginalString);
        AuthCookie(response);
    }

    [Fact]
    public async Task KeycloakLogin_WithoutReturnUrl_ReturnsToFrontend()
    {
        using var response = await LoginAsync(returnUrl: null);

        Assert.Equal(FrontendUrl, response.Headers.Location!.OriginalString);
    }

    [Theory]
    [InlineData(null, FrontendUrl)]
    [InlineData("", FrontendUrl)]
    [InlineData("/", FrontendUrl + "/")]
    [InlineData("/fangkorb", FrontendUrl + "/fangkorb")]
    [InlineData("https://evil.example/", FrontendUrl)]
    [InlineData("//evil.example/", FrontendUrl)]
    [InlineData("/\\evil.example/", FrontendUrl)]
    [InlineData("einwerfen", FrontendUrl)]
    [InlineData("/einwerfen\r\nSet-Cookie: x=y", FrontendUrl)]
    public void LoginRedirectTarget_OnlyAcceptsPathsInsideTheFrontend(string? returnUrl, string expected)
    {
        Assert.Equal(expected, AuthController.LoginRedirectTarget(FrontendUrl + "/", returnUrl));
    }
}
