using System.Security.Claims;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.IdentityModel.Tokens;
using Yarp.ReverseProxy.Configuration;
using Yarp.ReverseProxy.Transforms;
using BFF.Services;
using BFF.Proxy;

var builder = WebApplication.CreateBuilder(args);

// Configure logging
builder.Logging.ClearProviders();
builder.Logging.AddConsole();
builder.Logging.AddDebug();

var useKeycloak = builder.Configuration.GetValue<bool>("USE_KEYCLOAK", defaultValue: true);

// Create a logger for startup
using var loggerFactory = LoggerFactory.Create(loggingBuilder => loggingBuilder.AddConsole());
var startupLogger = loggerFactory.CreateLogger("Startup");
startupLogger.LogInformation("USE_KEYCLOAK is set to: {UseKeycloak}", useKeycloak);

// FRONTEND_URL is the origin the browser loads the SPA from. It drives the OIDC redirect,
// the dummy-auth CORS header, and the CORS allowlist below. Required outside Development so a
// missing value fails at startup instead of silently redirecting users to localhost.
var frontendUrl = builder.Configuration.GetValue<string>("FRONTEND_URL");
if (string.IsNullOrWhiteSpace(frontendUrl))
{
    if (!builder.Environment.IsDevelopment())
    {
        throw new InvalidOperationException("FRONTEND_URL configuration is missing.");
    }
    frontendUrl = "http://localhost:4200";
}
frontendUrl = frontendUrl.TrimEnd('/');

if (useKeycloak)
{
    // Read Keycloak configuration from appsettings.json
    var keycloakSettings = builder.Configuration.GetSection("Keycloak");
    if (string.IsNullOrEmpty(keycloakSettings["Authority"]) ||
        string.IsNullOrEmpty(keycloakSettings["ClientId"]) ||
        string.IsNullOrEmpty(keycloakSettings["ClientSecret"]))
    {
        throw new InvalidOperationException("Keycloak configuration is missing required values.");
    }

    // Configure Keycloak OpenID Connect with Cookie Authentication
    builder.Services.AddAuthentication(options =>
    {
        options.DefaultScheme = CookieAuthenticationDefaults.AuthenticationScheme;
        options.DefaultChallengeScheme = OpenIdConnectDefaults.AuthenticationScheme;
    })
    .AddCookie(CookieAuthenticationDefaults.AuthenticationScheme, options =>
    {
        options.Cookie.Name = "ContentGruenAuthCookie";
        options.Cookie.SameSite = SameSiteMode.None;    // Allow cross-site cookies between bff and frontend
        options.Cookie.SecurePolicy = CookieSecurePolicy.Always; // Enforce HTTPS
        options.Cookie.HttpOnly = true; // Prevent client-side JavaScript from accessing the cookie
    }
    ) // Cookie for session handling
    .AddOpenIdConnect(OpenIdConnectDefaults.AuthenticationScheme, options =>
    {
        options.Authority = keycloakSettings["Authority"];
        options.ClientId = keycloakSettings["ClientId"];
        options.ClientSecret = keycloakSettings["ClientSecret"];
        options.ResponseType = "code";  // Authorization Code flow
        options.SaveTokens = true;
        options.Scope.Add("openid");
        options.Scope.Add("profile");
        options.Scope.Add("email");
        options.CallbackPath = "/signin-oidc";
        options.Events = new OpenIdConnectEvents
        {
            OnRedirectToIdentityProvider = context =>
            {
                // Force HTTPS as the scheme for the redirect URI
                var scheme = "https";
                var host = context.Request.Host;
                var path = context.Options.CallbackPath;
                context.ProtocolMessage.RedirectUri = $"{scheme}://{host}{path}";
                return Task.CompletedTask;
            },
            OnTokenValidated = async context =>
            {
                Console.WriteLine("Token validated");
                if (context.Principal != null)
                {
                    Console.WriteLine($"Claims: {string.Join(", ", context.Principal.Claims.Select(c => $"{c.Type}: {c.Value}"))}");

                    // Create a ClaimsPrincipal from the validated token
                    var claims = context.Principal.Claims;

                    // Ensure relevant claims (like sub, email, etc.) are included
                    var identity = new ClaimsIdentity(claims, CookieAuthenticationDefaults.AuthenticationScheme);
                    var principal = new ClaimsPrincipal(identity);

                    Console.WriteLine($"Claims Principal: {string.Join(", ", principal.Claims.Select(c => $"{c.Type}: {c.Value}"))}");

                    // Issue the authentication cookie
                    await context.HttpContext.SignInAsync(CookieAuthenticationDefaults.AuthenticationScheme, principal);

                    Console.WriteLine("Authentication cookie issued");
                }
                else
                {
                    Console.WriteLine("No claims found, context.Principal is null.");
                }

                // Set the redirection target after successful login
                if (context.Properties != null)
                {
                    Console.WriteLine($"RedirectURL before: {context.Properties.RedirectUri}");
                    context.Properties.RedirectUri = frontendUrl;
                    Console.WriteLine($"RedirectURL after: {context.Properties.RedirectUri}");
                }
            }
        };
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidIssuer = keycloakSettings["Authority"],
            ValidateAudience = true,
            ValidAudience = keycloakSettings["ClientId"],
            ValidateLifetime = true
        };
    });
}
else
{
    // ContentGrün Managed Authentication (replaces Dummy-Authentication)
    builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
                   .AddCookie(options =>
                   {
                       options.Cookie.Name = "ContentGruenAuthCookie";
                       options.Cookie.SameSite = SameSiteMode.Lax;    // Allow same-site cookies
                       options.Cookie.SecurePolicy = CookieSecurePolicy.SameAsRequest; // Allow HTTP in dev
                       options.Cookie.HttpOnly = true; // Prevent client-side JavaScript access
                   });

    // Authorization
    builder.Services.AddAuthorization();

    // Keep the dummy auth for backward compatibility if managed users are not configured
    builder.Services.AddSingleton<IStartupFilter>(new DummyAuthStartupFilter(frontendUrl));
}


// Read the backend URL from an environment variable (use localhost:8000 as default for local dev)
var backendUrlFromConfig = builder.Configuration.GetValue<string>("BACKEND_URL");
var backendUrlFromEnv = Environment.GetEnvironmentVariable("BACKEND_URL");

// Log backend URL sources
startupLogger.LogDebug("BACKEND_URL from Configuration: '{ConfigUrl}'", backendUrlFromConfig);
startupLogger.LogDebug("BACKEND_URL from Environment: '{EnvUrl}'", backendUrlFromEnv);

var backendUrl = backendUrlFromConfig ?? backendUrlFromEnv ?? "http://localhost:8000";

// Trim all whitespace from the URL
backendUrl = backendUrl?.Trim();

// Validate and sanitize the backend URL
if (string.IsNullOrWhiteSpace(backendUrl))
{
    backendUrl = "http://localhost:8000";
    startupLogger.LogWarning("BACKEND_URL was empty, using default: {DefaultUrl}", backendUrl);
}

// Ensure the URL is properly formatted
if (!backendUrl.StartsWith("http://") && !backendUrl.StartsWith("https://"))
{
    backendUrl = "http://" + backendUrl;
    startupLogger.LogWarning("BACKEND_URL did not have a scheme, added http:// prefix");
}

// Remove any trailing slashes
backendUrl = backendUrl.TrimEnd('/');

startupLogger.LogInformation("BACKEND_URL configured: '{BackendUrl}'", backendUrl);

// Add services to the container.
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
builder.Services.AddControllers();

// Register HttpClient for health checks and other API calls
builder.Services.AddHttpClient();

// Register ManagedUserService
builder.Services.AddSingleton<ManagedUserService>();

// Validate backend URL can be parsed
try
{
    var uri = new Uri(backendUrl);
    // Backend URL validation successful
    startupLogger.LogDebug("Backend URL validation successful - {Scheme}://{Host}:{Port}", uri.Scheme, uri.Host, uri.Port);
}
catch (Exception ex)
{
    startupLogger.LogError(ex, "Invalid backend URL '{BackendUrl}'", backendUrl);
    throw new InvalidOperationException($"BACKEND_URL is not a valid URI: {backendUrl}", ex);
}

// Add YARP services
builder.Services.AddReverseProxy()
    .LoadFromMemory(
    [
        new RouteConfig()
        {
            RouteId = "all_routes",
            ClusterId = "backend_cluster",
            Match = new RouteMatch
            {
                Path = "{**catch-all}" // Forward all paths
            }
        }
    ],
    [
        new ClusterConfig()
        {
            ClusterId = "backend_cluster",
            Destinations = new Dictionary<string, DestinationConfig>(StringComparer.OrdinalIgnoreCase)
            {
                { "backend", new DestinationConfig() { Address = backendUrl } }
            }
        }
    ])
    .AddTransforms(builderContext =>
    {
        builderContext.AddRequestTransform(transformContext =>
            {
                try
                {
                    var httpContext = transformContext.HttpContext;
                    var logger = httpContext.RequestServices.GetRequiredService<ILogger<Program>>();

                    logger.LogTrace("Processing request transform for path: {Path}", httpContext.Request.Path.Value);

                    IdentityHeaderTransform.Apply(
                        transformContext.ProxyRequest,
                        httpContext.User,
                        httpContext.Request.Path.Value,
                        httpContext.Request.Headers,
                        logger);
                }
                catch (Exception ex)
                {
                    var logger = transformContext.HttpContext.RequestServices.GetRequiredService<ILogger<Program>>();
                    logger.LogError(ex, "Request transform error for path: {Path}", transformContext.HttpContext.Request.Path);
                    throw;
                }

                return ValueTask.CompletedTask;
            });
    });


// Add CORS policy.
// The browser sends the *frontend's* origin, so FRONTEND_URL is the source of truth and each
// environment trusts only its own frontend. CORS_ALLOWED_ORIGINS (comma-separated) adds extra
// origins without a rebuild -- e.g. a second domain during a migration.
var corsOrigins = new[] { frontendUrl }
    .Concat((builder.Configuration.GetValue<string>("CORS_ALLOWED_ORIGINS") ?? string.Empty)
        .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
    .Where(origin => !string.IsNullOrWhiteSpace(origin))
    .Select(origin => origin.TrimEnd('/')) // a trailing slash never matches an Origin header
    .Distinct(StringComparer.OrdinalIgnoreCase)
    .ToArray();

if (builder.Environment.IsDevelopment())
{
    corsOrigins = corsOrigins
        .Concat(["http://localhost:4200", "http://localhost"])
        .Distinct(StringComparer.OrdinalIgnoreCase)
        .ToArray();
}

startupLogger.LogInformation("CORS allowed origins: {Origins}", string.Join(", ", corsOrigins));

builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowSpecificOrigin",
        policy =>
        {
            policy.WithOrigins(corsOrigins)
                  .AllowAnyMethod()
                  .AllowAnyHeader()
                  .AllowCredentials();
        });
});

builder.Services.Configure<ForwardedHeadersOptions>(options =>
{
    options.ForwardedHeaders = Microsoft.AspNetCore.HttpOverrides.ForwardedHeaders.XForwardedProto
                             | Microsoft.AspNetCore.HttpOverrides.ForwardedHeaders.XForwardedHost;

    // The default known-proxy list covers loopback only, so the Docker bridge gateway counts as an
    // unknown proxy and X-Forwarded-Proto gets dropped -- the app then treats every request as
    // plain http. Clearing both lists switches the proxy check off instead of pinning a CIDR,
    // which would break as soon as Docker hands out a different bridge network.
    //
    // This is safe only as long as the container port stays bound to 127.0.0.1 and nginx remains
    // the sole route in, so no external client can set these headers itself. Revisit if the
    // published port or the reverse proxy in front of it ever changes.
    options.KnownNetworks.Clear();
    options.KnownProxies.Clear();
});

// Without an explicit key ring, DataProtection writes to ~/.aspnet/DataProtection-Keys inside the
// container layer, so every recreate mints new keys and invalidates every ContentGruenAuthCookie
// along with any in-flight OIDC correlation cookie. /keys is expected to be a mounted volume; if
// it is not, the directory is simply created in the container layer and behaviour matches today's.
builder.Services.AddDataProtection()
    .PersistKeysToFileSystem(new DirectoryInfo("/keys"))
    .SetApplicationName("contentgruen-bff");

var app = builder.Build();

// Configure the HTTP request pipeline.

// Must run before anything that reads the request scheme or issues cookies -- notably
// UseHttpsRedirection below and the OIDC handler, whose correlation and nonce cookies default to
// SameSite=None with SecurePolicy=SameAsRequest. Without the forwarded scheme those cookies go out
// without the Secure flag, browsers reject them, and the Keycloak callback fails correlation.
app.UseForwardedHeaders();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();

// Configure app to use port 5054 - Use HTTP and not HTTPS as the reverse proxy in front of our app will handle HTTPS
app.Urls.Add("http://*:5054");

// Use CORS policy
app.UseCors("AllowSpecificOrigin");

// Add error handling middleware to catch proxy errors
app.Use(async (context, next) =>
{
    try
    {
        await next();
    }
    catch (UriFormatException ex)
    {
        var logger = context.RequestServices.GetRequiredService<ILogger<Program>>();
        logger.LogError(ex, "UriFormatException caught for {Method} {Path}", context.Request.Method, context.Request.Path);

        context.Response.StatusCode = 502;
        await context.Response.WriteAsync($"Proxy configuration error: {ex.Message}");
    }
    catch (Exception ex)
    {
        var logger = context.RequestServices.GetRequiredService<ILogger<Program>>();
        logger.LogError(ex, "Unhandled exception in proxy middleware");
        throw;
    }
});

// Use routing first, then authentication and authorization middleware
app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();

// Map controllers for the new AuthController
app.MapControllers();

// Note: /login endpoint removed to allow Angular routing to handle login page
// Authentication is now handled through AuthController endpoints:
// - /api/auth/login/managed for ContentGrün managed auth
// - /api/auth/login/keycloak for Keycloak auth
// - /api/auth/logout for logout (handles both Keycloak and managed users)


// Endpoint for frontend to retrieve user info
app.MapGet("/api/user-info", (HttpContext context) =>
{
    Console.WriteLine("/api/user-info called");

    if (context.User.Identity?.IsAuthenticated == true)
    {
        var userId = ClaimUtilities.GetUserId(context.User);
        var userName = ClaimUtilities.GetUserName(context.User);
        var claims = context.User.Claims.ToDictionary(c => c.Type, c => c.Value);

        // Check if user is admin (from claims)
        var isAdmin = context.User.HasClaim("isAdmin", "true") ||
                     context.User.HasClaim("role", "admin") ||
                     context.User.HasClaim(ClaimTypes.Role, "admin");

        Console.WriteLine("/api/user-info   User is authenticated, return ok and user info");
        return Results.Ok(new
        {
            IsAuthenticated = true,
            UserId = userId,
            UserName = userName,
            IsAdmin = isAdmin,
            Claims = claims
        });
    }
    Console.WriteLine("/api/user-info   User is not authenticated, return unauthorized");
    return Results.Unauthorized();
});


// Endpoint for frontend to check user login status
app.MapGet("/api/check-session", (HttpContext context) =>
{
    Console.WriteLine($"/api/check-session called");

    if (context.User.Claims.Any())
    {
        Console.WriteLine("/api/check-session   Claims:");
        foreach (var claim in context.User.Claims)
        {
            Console.WriteLine($"/api/check-session   {claim.Type}: {claim.Value}");
        }
    }

    var cookies = context.Request.Headers["Cookie"];
    Console.WriteLine($"/api/check-session   Cookies: {cookies}");

    Console.WriteLine($"/api/check-session   Returning IsAuthenticated: {context.User.Identity?.IsAuthenticated}");

    return context.User.Identity?.IsAuthenticated == true
        ? Results.Ok()
        : Results.Unauthorized();
});

if (useKeycloak)
{
    // Map reverse proxy with conditional authorization
    app.MapReverseProxy(proxyPipeline =>
    {
        // Add authorization conditionally based on the path
        proxyPipeline.UseAuthorization();
        proxyPipeline.Use(async (context, next) =>
        {
            var path = context.Request.Path.Value?.ToLower() ?? "";

            // List of public endpoints that don't require authentication
            var publicEndpoints = new[]
            {
                "/api/v1/search/",
                "/api/v1/metrics/",
                "/api/metrics",
                "/api/v1/content/recent",
                "/api/v1/moderation/report"
            };

            // Check if this is a public endpoint
            var isPublicEndpoint = publicEndpoints.Any(endpoint => path.Contains(endpoint));

            if (!isPublicEndpoint && context.User.Identity?.IsAuthenticated != true)
            {
                // Require authentication for non-public endpoints
                context.Response.StatusCode = 401;
                await context.Response.WriteAsync("Authentication required");
                return;
            }

            await next();
        });
    });
}
else
{
    app.MapReverseProxy();
}


app.Run();


public class DummyAuthStartupFilter : IStartupFilter
{
    private readonly string _frontendUrl;
    private readonly string _dummyUsername;
    private readonly string _dummyPassword;


    public DummyAuthStartupFilter(string frontendUrl)
    {
        _frontendUrl = frontendUrl;
        // Get dummy credentials from environment variables for security
        _dummyUsername = Environment.GetEnvironmentVariable("DUMMY_AUTH_USERNAME") ?? "testuser";
        _dummyPassword = Environment.GetEnvironmentVariable("DUMMY_AUTH_PASSWORD") ?? "Liebe>Hass!";
    }

    public Action<IApplicationBuilder> Configure(Action<IApplicationBuilder> next)
    {
        return builder =>
        {
            builder.Use(async (context, next) =>
            {
                if (context.Request.Path.StartsWithSegments("/login") && context.Request.Method == "POST")
                {
                    Console.WriteLine("DummyAuthStartupFilter: Login endpoint called");

                    context.Response.Headers.Append("Access-Control-Allow-Origin", _frontendUrl);
                    context.Response.Headers.Append("Access-Control-Allow-Credentials", "true");

                    // Ensure the Content-Type is application/json
                    if (!context.Request.ContentType?.Contains("application/json") ?? true)
                    {
                        context.Response.StatusCode = 400; // Bad Request
                        await context.Response.WriteAsync("Invalid Content-Type. Expected application/json.");
                        return;
                    }

                    try
                    {
                        // Deserialize the JSON body to extract username and password from the request body
                        using var reader = new StreamReader(context.Request.Body);
                        var body = await reader.ReadToEndAsync();
                        var loginRequest = System.Text.Json.JsonSerializer.Deserialize<LoginRequest>(body);


                        Console.WriteLine($"DummyAuthStartupFilter: Received login request");
                        Console.WriteLine($"DummyAuthStartupFilter: Username: {loginRequest?.Username}");

                        if (loginRequest?.Username == _dummyUsername && loginRequest?.Password == _dummyPassword)
                        {
                            // Generate an identity with claims replicating Keycloak behavior
                            var identity = new ClaimsIdentity(new[]
                            {
                                new Claim("name", _dummyUsername),
                                new Claim(ClaimTypes.GivenName, "Test"),
                                new Claim(ClaimTypes.Surname, "User"),
                                new Claim(ClaimTypes.NameIdentifier, "test-user-id-1")
                            }, CookieAuthenticationDefaults.AuthenticationScheme);


                            var principal = new ClaimsPrincipal(identity);

                            Console.WriteLine("Created new Principal with claims:");
                            foreach (var claim in principal.Claims)
                            {
                                Console.WriteLine($"  {claim.Type}: {claim.Value}");
                            }

                            // Configure cookie options for proper cross-domain functionality
                            var authProperties = new AuthenticationProperties
                            {
                                IsPersistent = true,
                                ExpiresUtc = DateTimeOffset.UtcNow.AddHours(1)
                            };

                            await context.SignInAsync(CookieAuthenticationDefaults.AuthenticationScheme, principal, authProperties);

                            Console.WriteLine("Signed in with the principal, cookie should be set");

                            // Ensure the cookie is properly set before responding
                            context.Response.StatusCode = 200; // OK
                            await context.Response.WriteAsJsonAsync(new {
                                message = "Login successful",
                                userId = "test-user-id-1",
                                userName = _dummyUsername
                            });
                            return;
                        }

                        // Invalid credentials
                        Console.WriteLine("Invalid credentials provided.");
                        context.Response.StatusCode = 401; // Unauthorized
                        await context.Response.WriteAsync("Invalid username or password");
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Error processing login: {ex.Message}");
                        context.Response.StatusCode = 500; // Internal Server Error
                        await context.Response.WriteAsync("An error occurred while processing the login.");
                    }

                    return;
                }

                if (context.Request.Path.StartsWithSegments("/logout"))
                {
                    Console.WriteLine("DummyAuthStartupFilter: Logout endpoint called");

                    await context.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);

                    Console.WriteLine($"Signed out of context, redirecting to: {_frontendUrl}");

                    // Ensure proper redirect without double-encoding
                    context.Response.Headers["Location"] = _frontendUrl;
                    context.Response.StatusCode = 302; // Found (redirect)
                    return;
                }

                // Maintain dummy user session if signed in
                if (context.User.Identity?.IsAuthenticated == true)
                {
                    Console.WriteLine("DummyAuthStartupFilter: User is authenticated");

                    // Generate an identity with claims replicating Keycloak behavior
                    var identity = new ClaimsIdentity(new[]
                    {
                        new Claim("name", _dummyUsername),
                        new Claim(ClaimTypes.GivenName, "Test"),
                        new Claim(ClaimTypes.Surname, "User"),
                        new Claim(ClaimTypes.NameIdentifier, "test-user-id-1")
                    }, CookieAuthenticationDefaults.AuthenticationScheme);

                    context.User = new ClaimsPrincipal(identity);
                }

                await next();
            });

            next(builder);
        };
    }

    private class LoginRequest
    {
        public string? Username { get; set; }
        public string? Password { get; set; }
    }
}


public class ClaimUtilities
{

    public static string GetUserId(ClaimsPrincipal principal)
    {
        return principal.Claims.FirstOrDefault(c => c.Type == "sub")?.Value
            ?? principal.Claims.FirstOrDefault(c => c.Type == ClaimTypes.NameIdentifier)?.Value;
    }

    public static string GetUserName(ClaimsPrincipal principal)
    {
        return principal.Claims.FirstOrDefault(c => c.Type == ClaimTypes.Name)?.Value
        ?? principal.Claims.FirstOrDefault(c => c.Type == "name")?.Value
        ?? principal.Claims.FirstOrDefault(c => c.Type == ClaimTypes.GivenName)?.Value;
    }

}
