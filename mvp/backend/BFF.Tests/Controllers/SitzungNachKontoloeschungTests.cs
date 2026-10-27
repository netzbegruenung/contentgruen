using Xunit;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Net.Http.Headers;
using System;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading.Tasks;

namespace BFF.Tests.Controllers;

/// <summary>
/// Nach dem Loeschen eines Kontos weist das BFF die naechste Anfrage mit dem alten
/// Anmelde-Cookie ab (#278). Vorher lief das Cookie gleitend 14 Tage weiter, und eine
/// geloeschte Person konnte weiter Daten anlegen.
///
/// Jeder Test meldet sich bei einem Host an, aendert die Kontodateien und schickt das Cookie
/// an einen zweiten Host mit demselben Schluesselring -- so wie das Loeschkonzept es vorsieht:
/// Datei aendern, BFF neu starten. Gelesen wird /api/check-session, das allein am Cookie
/// haengt (200 angemeldet, 401 nicht).
/// </summary>
public class SitzungNachKontoloeschungTests : IDisposable
{
    private const string Email = "beta@example.org";
    private const string Passwort = "Test123!";
    private const string BetaKennung = "beta-001";

    private readonly string _verzeichnis =
        Path.Combine(Path.GetTempPath(), $"gutgesagt-kontoloeschung-{Guid.NewGuid():N}");
    private string NutzerDatei => Path.Combine(_verzeichnis, "managed-users.json");
    private string GeloeschteKontenDatei => Path.Combine(_verzeichnis, "geloeschte-konten.txt");

    public SitzungNachKontoloeschungTests()
    {
        Directory.CreateDirectory(_verzeichnis);
        SchreibeNutzerDatei(mitBetaZugang: true);
    }

    public void Dispose() => Directory.Delete(_verzeichnis, recursive: true);

    private void SchreibeNutzerDatei(bool mitBetaZugang)
    {
        var users = mitBetaZugang
            ? new[]
            {
                new
                {
                    email = Email,
                    passwordHash = BCrypt.Net.BCrypt.HashPassword(Passwort),
                    displayName = "Beta Person",
                    userId = BetaKennung,
                    isAdmin = false
                }
            }
            : [];
        File.WriteAllText(NutzerDatei, JsonSerializer.Serialize(new { users }));
    }

    private WebApplicationFactory<Program> CreateHost(bool useKeycloak) =>
        new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.UseContentRoot(AppContext.BaseDirectory);
            builder.UseEnvironment("Development");
            builder.UseSetting("USE_KEYCLOAK", useKeycloak ? "true" : "false");
            builder.UseSetting("FRONTEND_URL", "http://localhost:4200");
            builder.UseSetting("BACKEND_URL", "http://127.0.0.1:1");
            builder.UseSetting("Keycloak:Authority", "https://keycloak.invalid/realms/test");
            builder.UseSetting("Keycloak:ClientId", "test-client");
            builder.UseSetting("Keycloak:ClientSecret", "test-secret");
            builder.UseSetting("MANAGED_USERS_PATH", NutzerDatei);
            builder.UseSetting("GELOESCHTE_KONTEN_PATH", GeloeschteKontenDatei);
            // Derselbe Schluesselring wie in KeycloakLoginCookieTests: das Cookie von dort
            // muss sich hier entschluesseln lassen.
            builder.UseSetting(
                "DATAPROTECTION_KEYS_PATH",
                Path.Combine(Path.GetTempPath(), "gutgesagt-bff-test-keys"));
        });

    private static HttpClient Client(WebApplicationFactory<Program> factory) =>
        factory.CreateClient(new WebApplicationFactoryClientOptions
        {
            AllowAutoRedirect = false,
            HandleCookies = false
        });

    private async Task<string> BetaCookieAsync(bool useKeycloak)
    {
        using var factory = CreateHost(useKeycloak);
        using var client = Client(factory);
        using var response = await client.PostAsJsonAsync(
            "/api/auth/login/managed", new { email = Email, password = Passwort });
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        return CookieHeader(KeycloakLoginCookieTests.AuthCookie(response));
    }

    private static async Task<string> KeycloakCookieAsync()
    {
        using var response = await KeycloakLoginCookieTests.LoginAsync(returnUrl: null);
        return CookieHeader(KeycloakLoginCookieTests.AuthCookie(response));
    }

    private static string CookieHeader(SetCookieHeaderValue cookie) => $"{cookie.Name}={cookie.Value}";

    /// <summary>Fragt mit dem Cookie bei einem neu gestarteten Host nach der Sitzung.</summary>
    private async Task<HttpResponseMessage> CheckSessionAsync(bool useKeycloak, string cookie)
    {
        using var factory = CreateHost(useKeycloak);
        using var client = Client(factory);
        using var request = new HttpRequestMessage(HttpMethod.Get, "/api/check-session");
        request.Headers.Add("Cookie", cookie);
        return await client.SendAsync(request);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task BetaZugang_KontoBesteht_CookieGiltWeiter(bool useKeycloak)
    {
        var cookie = await BetaCookieAsync(useKeycloak);

        using var response = await CheckSessionAsync(useKeycloak, cookie);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task BetaZugang_AusNutzerdateiEntfernt_AltesCookieAbgewiesen(bool useKeycloak)
    {
        var cookie = await BetaCookieAsync(useKeycloak);
        SchreibeNutzerDatei(mitBetaZugang: false);

        using var response = await CheckSessionAsync(useKeycloak, cookie);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task Abweisung_LoeschtDasCookieImBrowser()
    {
        var cookie = await BetaCookieAsync(useKeycloak: false);
        SchreibeNutzerDatei(mitBetaZugang: false);

        using var response = await CheckSessionAsync(useKeycloak: false, cookie);

        var geloescht = KeycloakLoginCookieTests.AuthCookie(response);
        Assert.True(geloescht.Expires < DateTimeOffset.UtcNow, "the auth cookie is not expired");
    }

    [Fact]
    public async Task NetzbegruenungLogin_NichtAlsGeloeschtEingetragen_CookieGiltWeiter()
    {
        var cookie = await KeycloakCookieAsync();
        File.WriteAllText(GeloeschteKontenDatei, "eine-andere-kennung\n");

        using var response = await CheckSessionAsync(useKeycloak: true, cookie);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task NetzbegruenungLogin_OhneDateiGeloeschterKonten_CookieGiltWeiter()
    {
        var cookie = await KeycloakCookieAsync();

        using var response = await CheckSessionAsync(useKeycloak: true, cookie);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task NetzbegruenungLogin_AlsGeloeschtEingetragen_AltesCookieAbgewiesen()
    {
        var cookie = await KeycloakCookieAsync();
        File.WriteAllText(
            GeloeschteKontenDatei,
            $"# geloescht am 27.10.2026\n\n  {KeycloakLoginCookieTests.Kennung}  \n");

        using var response = await CheckSessionAsync(useKeycloak: true, cookie);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }
}
