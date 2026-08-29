using Xunit;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Moq;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using BFF.Controllers;
using BFF.Services;
using BFF.Models;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Authentication;
using System.Security.Claims;

namespace BFF.Tests.Controllers;

public class AuthControllerTests : IDisposable
{
    private const string KnownEmail = "test@example.com";
    private const string KnownPassword = "Test123!";
    private const string KnownUserId = "user-001";

    private readonly Mock<ILogger<ManagedUserService>> _mockUserServiceLogger;
    private readonly ManagedUserService _userService;
    private readonly IConfiguration _configuration;
    private readonly Mock<ILogger<AuthController>> _mockLogger;
    private AuthController _controller;
    private readonly DefaultHttpContext _httpContext;
    private readonly string _usersFilePath;

    public AuthControllerTests()
    {
        _mockUserServiceLogger = new Mock<ILogger<ManagedUserService>>();

        // Eine echte Nutzerdatei, damit die Login-Tests den Pfad hinter dem
        // ENABLE_MANAGED_AUTH-Guard erreichen. Ohne Datei meldet IsEnabledAsync()
        // "keine Nutzer konfiguriert" und LoginManaged antwortet 404, bevor
        // irgendeine Anmeldelogik laeuft -- die Tests haben dann nichts geprueft.
        _usersFilePath = WriteUsersFile(new
        {
            users = new[]
            {
                new
                {
                    email = KnownEmail,
                    passwordHash = BCrypt.Net.BCrypt.HashPassword(KnownPassword),
                    displayName = "Test User",
                    userId = KnownUserId,
                    isAdmin = false
                }
            }
        });

        _userService = BuildUserService(_usersFilePath, managedAuthEnabled: true);

        var configBuilder = new ConfigurationBuilder();
        configBuilder.AddInMemoryCollection(new Dictionary<string, string?>
        {
            { "USE_KEYCLOAK", "true" },
            { "FRONTEND_URL", "http://localhost:4200" }
        });
        _configuration = configBuilder.Build();
        _mockLogger = new Mock<ILogger<AuthController>>();

        _httpContext = new DefaultHttpContext();
        var authServiceMock = new Mock<IAuthenticationService>();
        var serviceProviderMock = new Mock<IServiceProvider>();
        serviceProviderMock
            .Setup(s => s.GetService(typeof(IAuthenticationService)))
            .Returns(authServiceMock.Object);
        _httpContext.RequestServices = serviceProviderMock.Object;

        _controller = BuildController(_userService, _configuration);
    }

    public void Dispose()
    {
        if (File.Exists(_usersFilePath))
        {
            File.Delete(_usersFilePath);
        }
    }

    private static string WriteUsersFile(object config)
    {
        var path = Path.Combine(Path.GetTempPath(), $"managed-users-{Guid.NewGuid():N}.json");
        File.WriteAllText(path, JsonSerializer.Serialize(config));
        return path;
    }

    private ManagedUserService BuildUserService(string usersPath, bool managedAuthEnabled)
    {
        var builder = new ConfigurationBuilder();
        builder.AddInMemoryCollection(new Dictionary<string, string?>
        {
            { "MANAGED_USERS_PATH", usersPath },
            { "ENABLE_MANAGED_AUTH", managedAuthEnabled ? "true" : "false" }
        });
        return new ManagedUserService(_mockUserServiceLogger.Object, builder.Build());
    }

    private AuthController BuildController(ManagedUserService userService, IConfiguration configuration) =>
        new AuthController(userService, configuration, _mockLogger.Object)
        {
            ControllerContext = new ControllerContext { HttpContext = _httpContext }
        };

    private static IConfiguration ControllerConfig(bool useKeycloak)
    {
        var builder = new ConfigurationBuilder();
        builder.AddInMemoryCollection(new Dictionary<string, string?>
        {
            { "USE_KEYCLOAK", useKeycloak ? "true" : "false" },
            { "FRONTEND_URL", "http://localhost:4200" }
        });
        return builder.Build();
    }

    [Fact]
    public async Task GetAuthModes_ReturnsCorrectModes_WhenBothEnabled()
    {
        _controller = BuildController(_userService, ControllerConfig(useKeycloak: true));

        var result = await _controller.GetAuthModes();

        var okResult = Assert.IsType<OkObjectResult>(result);
        var response = Assert.IsType<AuthModesResponse>(okResult.Value);
        Assert.True(response.KeycloakEnabled);
        Assert.True(response.ManagedAuthEnabled);
    }

    [Fact]
    public async Task GetAuthModes_ReturnsOnlyManaged_WhenKeycloakDisabled()
    {
        _controller = BuildController(_userService, ControllerConfig(useKeycloak: false));

        var result = await _controller.GetAuthModes();

        var okResult = Assert.IsType<OkObjectResult>(result);
        var response = Assert.IsType<AuthModesResponse>(okResult.Value);
        Assert.False(response.KeycloakEnabled);
        Assert.True(response.ManagedAuthEnabled);
    }

    [Fact]
    public async Task GetAuthModes_ReportsManagedDisabled_WhenNoUsersConfigured()
    {
        var emptyService = BuildUserService("non-existent.json", managedAuthEnabled: true);
        _controller = BuildController(emptyService, ControllerConfig(useKeycloak: true));

        var result = await _controller.GetAuthModes();

        var okResult = Assert.IsType<OkObjectResult>(result);
        var response = Assert.IsType<AuthModesResponse>(okResult.Value);
        Assert.False(response.ManagedAuthEnabled);
    }

    [Fact]
    public async Task LoginManaged_ReturnsBadRequest_WhenCredentialsMissing()
    {
        var request = new LoginRequest { Email = null, Password = null };

        var result = await _controller.LoginManaged(request);

        var badRequestResult = Assert.IsType<BadRequestObjectResult>(result);
        Assert.NotNull(badRequestResult.Value);
    }

    [Fact]
    public async Task LoginManaged_ReturnsUnauthorized_WhenInvalidCredentials()
    {
        var request = new LoginRequest { Email = KnownEmail, Password = "wrongpassword" };

        var result = await _controller.LoginManaged(request);

        var unauthorizedResult = Assert.IsType<UnauthorizedObjectResult>(result);
        Assert.NotNull(unauthorizedResult.Value);
    }

    [Fact]
    public async Task LoginManaged_ReturnsUnauthorized_WhenUserUnknown()
    {
        var request = new LoginRequest { Email = "niemand@example.com", Password = KnownPassword };

        var result = await _controller.LoginManaged(request);

        Assert.IsType<UnauthorizedObjectResult>(result);
    }

    [Fact]
    public async Task LoginManaged_ReturnsOk_WhenValidCredentials()
    {
        var request = new LoginRequest { Email = KnownEmail, Password = KnownPassword };

        var result = await _controller.LoginManaged(request);

        var okResult = Assert.IsType<OkObjectResult>(result);
        Assert.NotNull(okResult.Value);
    }

    [Fact]
    public async Task LoginManaged_ReturnsNotFound_WhenManagedAuthDisabled()
    {
        // Der Kern der Aenderung: ENABLE_MANAGED_AUTH=false wurde bisher nur in
        // GetAuthModes() ausgewertet. Ein direkter POST auf diese Route lieferte
        // trotzdem ein gueltiges Auth-Cookie -- abgeschaltet war nur der Button.
        var disabledService = BuildUserService(_usersFilePath, managedAuthEnabled: false);
        _controller = BuildController(disabledService, ControllerConfig(useKeycloak: true));

        var request = new LoginRequest { Email = KnownEmail, Password = KnownPassword };

        var result = await _controller.LoginManaged(request);

        Assert.IsType<NotFoundResult>(result);
    }

    [Fact]
    public async Task GetAuthModes_ReportsManagedDisabled_WhenFlagIsFalse()
    {
        var disabledService = BuildUserService(_usersFilePath, managedAuthEnabled: false);
        _controller = BuildController(disabledService, ControllerConfig(useKeycloak: true));

        var result = await _controller.GetAuthModes();

        var okResult = Assert.IsType<OkObjectResult>(result);
        var response = Assert.IsType<AuthModesResponse>(okResult.Value);
        Assert.False(response.ManagedAuthEnabled);
    }

    [Fact]
    public async Task Logout_ReturnsOk_Always()
    {
        var claims = new[] { new Claim("auth_method", "managed") };
        _httpContext.User = new ClaimsPrincipal(new ClaimsIdentity(claims));

        var result = await _controller.Logout();

        var okResult = Assert.IsType<OkObjectResult>(result);
        Assert.NotNull(okResult.Value);
    }
}
