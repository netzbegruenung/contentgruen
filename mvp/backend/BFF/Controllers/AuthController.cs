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
        var enableManagedAuth = await _managedUserService.IsEnabledAsync();

        return Ok(new AuthModesResponse
        {
            KeycloakEnabled = useKeycloak,
            ManagedAuthEnabled = enableManagedAuth
        });
    }

    [HttpPost("login/managed")]
    public async Task<IActionResult> LoginManaged([FromBody] LoginRequest request)
    {
        if (request?.Email == null || request.Password == null)
        {
            return BadRequest(new { message = "Email and password are required" });
        }

        // Validate user credentials
        var user = await _managedUserService.ValidateUserAsync(request.Email, request.Password);

        if (user == null)
        {
            _logger.LogWarning("Failed login attempt for: {Email}", request.Email);
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

        _logger.LogInformation("User {Email} logged in successfully via managed auth", user.Email);

        return Ok(new
        {
            success = true,
            userId = user.UserId,
            userName = user.DisplayName,
            email = user.Email,
            message = "Login successful"
        });
    }

    [HttpPost("login/keycloak")]
    public async Task<IActionResult> LoginKeycloak([FromQuery] string? returnUrl = null)
    {
        var frontendUrl = _configuration.GetValue<string>("FRONTEND_URL", "http://localhost:4200");
        var redirectUrl = string.IsNullOrEmpty(returnUrl) ? frontendUrl : returnUrl;

        // Trigger Keycloak authentication
        await HttpContext.ChallengeAsync(OpenIdConnectDefaults.AuthenticationScheme, new AuthenticationProperties
        {
            RedirectUri = redirectUrl
        });

        return Ok(new { message = "Redirecting to Keycloak..." });
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
