using Microsoft.AspNetCore.Mvc;

namespace BFF.Controllers;

/// <summary>
/// Health check and statistics controller that proxies requests to the semantic search service.
/// </summary>
[ApiController]
[Route("api/v1")]
public class HealthController : ControllerBase
{
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly IConfiguration _configuration;
    private readonly ILogger<HealthController> _logger;

    public HealthController(
        IHttpClientFactory httpClientFactory,
        IConfiguration configuration,
        ILogger<HealthController> logger)
    {
        _httpClientFactory = httpClientFactory;
        _configuration = configuration;
        _logger = logger;
    }

    /// <summary>
    /// Comprehensive health check endpoint.
    /// Proxies to the semantic search service health endpoint.
    /// </summary>
    [HttpGet("health")]
    public async Task<IActionResult> GetHealth()
    {
        try
        {
            var backendUrl = GetBackendUrl();
            _logger.LogDebug("Proxying health check to: {BackendUrl}/api/v1/health", backendUrl);

            var client = _httpClientFactory.CreateClient();
            client.Timeout = TimeSpan.FromSeconds(10);
            var response = await client.GetAsync($"{backendUrl}/api/v1/health");

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogWarning("Health check returned status code: {StatusCode}", response.StatusCode);
                return StatusCode((int)response.StatusCode, new
                {
                    status = "unhealthy",
                    message = "Backend health check failed",
                    statusCode = (int)response.StatusCode
                });
            }

            var content = await response.Content.ReadAsStringAsync();
            return Content(content, "application/json");
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "Failed to connect to backend health endpoint");
            return StatusCode(503, new
            {
                status = "unhealthy",
                message = "Cannot connect to backend service",
                error = ex.Message
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unexpected error during health check");
            return StatusCode(500, new
            {
                status = "unhealthy",
                message = "Internal server error during health check",
                error = ex.Message
            });
        }
    }

    /// <summary>
    /// System statistics endpoint.
    /// Proxies to the semantic search service stats endpoint.
    /// </summary>
    [HttpGet("stats")]
    public async Task<IActionResult> GetStats()
    {
        try
        {
            var backendUrl = GetBackendUrl();
            _logger.LogDebug("Proxying stats request to: {BackendUrl}/api/v1/stats", backendUrl);

            var client = _httpClientFactory.CreateClient();
            client.Timeout = TimeSpan.FromSeconds(10);
            var response = await client.GetAsync($"{backendUrl}/api/v1/stats");

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogWarning("Stats request returned status code: {StatusCode}", response.StatusCode);
                return StatusCode((int)response.StatusCode, new
                {
                    message = "Failed to retrieve statistics",
                    statusCode = (int)response.StatusCode
                });
            }

            var content = await response.Content.ReadAsStringAsync();
            return Content(content, "application/json");
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "Failed to connect to backend stats endpoint");
            return StatusCode(503, new
            {
                message = "Cannot connect to backend service",
                error = ex.Message
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unexpected error retrieving statistics");
            return StatusCode(500, new
            {
                message = "Internal server error retrieving statistics",
                error = ex.Message
            });
        }
    }

    private string GetBackendUrl()
    {
        var backendUrl = _configuration.GetValue<string>("BACKEND_URL")
            ?? Environment.GetEnvironmentVariable("BACKEND_URL")
            ?? "http://localhost:8000";

        return backendUrl.TrimEnd('/');
    }
}
