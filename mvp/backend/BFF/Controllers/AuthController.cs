using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using System.Security.Claims;
using BFF.Models;
using BFF.Services;

namespace BFF.Controllers;

[ApiController]
[Route("api/auth")]
public class AuthController : ControllerBase
{
    private readonly ManagedUserService _managedUserService;
    private readonly IConfiguration _configuration;
    private readonly ILogger<AuthController> _logger;

    public AuthController(
        ManagedUserService managedUserService,
        IConfiguration configuration,
        ILogger<AuthController> logger)
    {
        _managedUserService = managedUserService;
        _configuration = configuration;
        _logger = logger;
    }

    [HttpGet("modes")]
    public async Task<IActionResult> GetAuthModes()
    {
        var useKeycloak = _configuration.GetValue<bool>("USE_KEYCLOAK", true);

        // Der Endpunkt beantwortet "welches Formular kann das Frontend zeichnen", nicht
        // "steht der Schalter auf an". Deshalb zaehlt hier beides: ein Button, hinter
        // dem keine Nutzerdatei liegt, koennte nie zu einer Anmeldung fuehren. Welcher
        // der beiden Gruende vorliegt, steht im Log -- siehe HasConfiguredUsersAsync.
        var enableManagedAuth = _managedUserService.IsEnabled()
                                && await _managedUserService.HasConfiguredUsersAsync();

        return Ok(new AuthModesResponse
        {
            KeycloakEnabled = useKeycloak,
            ManagedAuthEnabled = enableManagedAuth
        });
    }

    [HttpPost("login/managed")]
    public async Task<IActionResult> LoginManaged([FromBody] LoginRequest request)
    {
        // ENABLE_MANAGED_AUTH wurde bisher nur in GetAuthModes() gelesen, also von einem
        // reinen Auskunfts-Endpunkt, an dem sich das Frontend orientiert, welche
        // Login-Formulare es zeichnet. Diese Action pruefte den Schalter nicht:
        // ValidateUserAsync liest managed-users.json unabhaengig davon. Mit
        // ENABLE_MANAGED_AUTH=false verschwand also nur der Button, waehrend ein
        // direkter POST auf diese Route weiterhin ein gueltiges Auth-Cookie bekam.
        //
        // Managed Auth bleibt bewusst aktiv -- es ist der Zugangsweg fuer Menschen ohne
        // Vereinsmitgliedschaft, die der Keycloak-Realm nicht abdeckt. Der Guard steht
        // hier, damit der Schalter tut, was sein Name sagt, wenn ihn jemand umlegt.
        //
        // Gefragt wird ausschliesslich nach dem Schalter. Eine fehlende oder leere
        // Nutzerdatei fuehrt weiter unten zu 401, nicht zu 404 -- sonst behauptet diese
        // Logzeile "abgeschaltet", waehrend in Wirklichkeit nur der Mount fehlt.
        if (!_managedUserService.IsEnabled())
        {
            _logger.LogWarning("Managed auth login attempted while managed auth is disabled");
            return NotFound();
        }

        if (request?.Email == null || request.Password == null)
        {
            return BadRequest(new { message = "Email and password are required" });
        }

        // Validate user credentials
        var user = await _managedUserService.ValidateUserAsync(request.Email, request.Password);

        if (user == null)
        {
            // Ohne E-Mail: ein Tippfehler im Formular wuerde sonst die Adresse einer
            // unbeteiligten Person ins Log schreiben. Dass ein Versuch fehlschlug,
            // ist die Information, die zaehlt.
            _logger.LogWarning("Failed login attempt via managed auth");
            return Unauthorized(new { message = "Invalid email or password" });
        }

        // Create claims
        var claims = new List<Claim>
        {
            new Claim(ClaimTypes.NameIdentifier, user.UserId),
            new Claim(ClaimTypes.Name, user.DisplayName),
            new Claim("name", user.DisplayName),
            new Claim(ClaimTypes.Email, user.Email),
            new Claim("sub", user.UserId), // Subject claim for compatibility
            new Claim("auth_method", "managed"),
            new Claim("user_id", user.UserId)
        };

        // Add admin role claim if user is admin
        if (user.IsAdmin)
        {
            claims.Add(new Claim(ClaimTypes.Role, "admin"));
            claims.Add(new Claim("isAdmin", "true"));
        }

        var claimsIdentity = new ClaimsIdentity(claims, CookieAuthenticationDefaults.AuthenticationScheme);
        var authProperties = new AuthenticationProperties
        {
            IsPersistent = true,
            ExpiresUtc = DateTimeOffset.UtcNow.AddHours(8),
            IssuedUtc = DateTimeOffset.UtcNow
        };

        await HttpContext.SignInAsync(
            CookieAuthenticationDefaults.AuthenticationScheme,
            new ClaimsPrincipal(claimsIdentity),
            authProperties);

        _logger.LogInformation("User {UserId} logged in successfully via managed auth", user.UserId);

        return Ok(new
        {
            success = true,
            userId = user.UserId,
            userName = user.DisplayName,
            email = user.Email,
            message = "Login successful"
        });
    }

    // GET as well as POST: the frontend starts this flow with a top-level navigation
    // (window.location.href), which is always a GET. Without the GET route the request falls
    // through to the YARP catch-all route and is rejected there with 401 instead of reaching
    // this action at all.
    [HttpGet("login/keycloak")]
    [HttpPost("login/keycloak")]
    public IActionResult LoginKeycloak([FromQuery] string? returnUrl = null)
    {
        var frontendUrl = _configuration.GetValue<string>("FRONTEND_URL", "http://localhost:4200");
        var redirectUrl = string.IsNullOrEmpty(returnUrl) ? frontendUrl : returnUrl;

        // Trigger Keycloak authentication. Returning the challenge as the action result keeps the
        // 302 the OIDC handler produces -- calling ChallengeAsync and then returning Ok() would
        // overwrite that status with 200 and leave a Location header no browser follows.
        return Challenge(
            new AuthenticationProperties { RedirectUri = redirectUrl },
            OpenIdConnectDefaults.AuthenticationScheme);
    }

    [HttpPost("logout")]
    public async Task<IActionResult> Logout()
    {
        var authMethod = HttpContext.User.FindFirst("auth_method")?.Value;
        var frontendUrl = _configuration.GetValue<string>("FRONTEND_URL", "http://localhost:4200");

        if (authMethod == "keycloak")
        {
            // Sign out from both cookies and OpenID Connect for Keycloak
            await HttpContext.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
            await HttpContext.SignOutAsync(OpenIdConnectDefaults.AuthenticationScheme, new AuthenticationProperties
            {
                RedirectUri = frontendUrl
            });
        }
        else
        {
            // For managed auth, just clear the cookie
            await HttpContext.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
        }

        return Ok(new { message = "Logged out successfully", redirectUrl = frontendUrl });
    }
}
