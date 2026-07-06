using System.Text.Json;
using System.Collections.Concurrent;
using BFF.Models;
using BCrypt.Net;

namespace BFF.Services;

public class ManagedUserService
{
    private readonly ILogger<ManagedUserService> _logger;
    private readonly IConfiguration _configuration;
    private ManagedUsersConfig? _usersConfig;
    private DateTime _lastLoadTime = DateTime.MinValue;
    private readonly TimeSpan _cacheExpiry = TimeSpan.FromMinutes(5);

    // Rate limiting for failed login attempts
    private readonly ConcurrentDictionary<string, List<DateTime>> _failedAttempts = new();
    private readonly TimeSpan _rateLimitWindow = TimeSpan.FromMinutes(15);
    private readonly int _maxFailedAttempts = 5;

    public ManagedUserService(ILogger<ManagedUserService> logger, IConfiguration configuration)
    {
        _logger = logger;
        _configuration = configuration;
    }

    private async Task<ManagedUsersConfig> LoadUsersAsync()
    {
        // Check cache
        if (_usersConfig != null && DateTime.UtcNow - _lastLoadTime < _cacheExpiry)
        {
            return _usersConfig;
        }

        var configPath = _configuration["MANAGED_USERS_PATH"] ?? "config/managed-users.json";

        // Try multiple paths
        var possiblePaths = new[]
        {
            configPath,
            Path.Combine(Directory.GetCurrentDirectory(), configPath),
            Path.Combine(Directory.GetCurrentDirectory(), "..", configPath),
            Path.Combine(Directory.GetCurrentDirectory(), "..", "..", configPath), // This should find mvp/config from mvp/backend/BFF
            Path.Combine(Directory.GetCurrentDirectory(), "mvp", configPath),
            Path.Combine("/app", configPath), // Docker path
            Path.Combine("/config", "managed-users.json") // Docker config mount
        };

        string? validPath = null;
        foreach (var path in possiblePaths)
        {
            if (File.Exists(path))
            {
                validPath = path;
                _logger.LogInformation("Found managed users config at: {Path}", path);
                break;
            }
        }

        if (validPath == null)
        {
            _logger.LogWarning("Managed users config not found. Tried paths: {Paths}", string.Join(", ", possiblePaths));
            return new ManagedUsersConfig();
        }

        try
        {
            var json = await File.ReadAllTextAsync(validPath);
            _usersConfig = JsonSerializer.Deserialize<ManagedUsersConfig>(json) ?? new ManagedUsersConfig();
            _lastLoadTime = DateTime.UtcNow;

            _logger.LogInformation("Loaded {Count} managed users from config", _usersConfig.Users.Count);
            return _usersConfig;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load managed users config from {Path}", validPath);
            return new ManagedUsersConfig();
        }
    }

    private bool IsRateLimited(string email)
    {
        if (!_failedAttempts.TryGetValue(email.ToLowerInvariant(), out var attempts))
        {
            return false;
        }

        // Clean up old attempts
        var cutoff = DateTime.UtcNow - _rateLimitWindow;
        attempts.RemoveAll(a => a < cutoff);

        return attempts.Count >= _maxFailedAttempts;
    }

    private void RecordFailedAttempt(string email)
    {
        var key = email.ToLowerInvariant();
        _failedAttempts.AddOrUpdate(key,
            new List<DateTime> { DateTime.UtcNow },
            (k, list) =>
            {
                list.Add(DateTime.UtcNow);
                // Clean up old attempts
                var cutoff = DateTime.UtcNow - _rateLimitWindow;
                list.RemoveAll(a => a < cutoff);
                return list;
            });
    }

    private void ClearFailedAttempts(string email)
    {
        _failedAttempts.TryRemove(email.ToLowerInvariant(), out _);
    }

    public async Task<ManagedUser?> ValidateUserAsync(string email, string password)
    {
        if (string.IsNullOrWhiteSpace(email) || string.IsNullOrWhiteSpace(password))
        {
            return null;
        }

        // Check rate limiting
        if (IsRateLimited(email))
        {
            _logger.LogWarning("Authentication rate limit exceeded for user: {Email}", email);
            return null;
        }

        var config = await LoadUsersAsync();
        var user = config.Users.FirstOrDefault(u =>
            string.Equals(u.Email, email, StringComparison.OrdinalIgnoreCase));

        if (user == null)
        {
            RecordFailedAttempt(email);
            _logger.LogWarning("Authentication failed - user not found: {Email}", email);
            return null;
        }

        try
        {
            // Verify password using BCrypt
            if (BCrypt.Net.BCrypt.Verify(password, user.PasswordHash))
            {
                ClearFailedAttempts(email);
                _logger.LogInformation("Authentication successful for user: {Email}, UserId: {UserId}", email, user.UserId);
                return user;
            }
            else
            {
                RecordFailedAttempt(email);
                _logger.LogWarning("Authentication failed - invalid password for user: {Email}", email);
                return null;
            }
        }
        catch (Exception ex)
        {
            RecordFailedAttempt(email);
            _logger.LogError(ex, "Authentication error for user: {Email}", email);
            return null;
        }
    }

    public async Task<ManagedUser?> GetUserByIdAsync(string userId)
    {
        if (string.IsNullOrWhiteSpace(userId))
        {
            return null;
        }

        var config = await LoadUsersAsync();
        return config.Users.FirstOrDefault(u => u.UserId == userId);
    }

    public async Task<ManagedUser?> GetUserByEmailAsync(string email)
    {
        if (string.IsNullOrWhiteSpace(email))
        {
            return null;
        }

        var config = await LoadUsersAsync();
        return config.Users.FirstOrDefault(u =>
            string.Equals(u.Email, email, StringComparison.OrdinalIgnoreCase));
    }

    public async Task<bool> IsEnabledAsync()
    {
        // Check if managed auth is enabled
        var enabled = _configuration.GetValue<bool>("ENABLE_MANAGED_AUTH", true);

        if (!enabled)
        {
            return false;
        }

        // Check if we have any users configured
        var config = await LoadUsersAsync();
        return config.Users.Count > 0;
    }
}
