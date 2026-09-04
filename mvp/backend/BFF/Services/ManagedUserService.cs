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
            _logger.LogWarning("Authentication rate limit exceeded");
            return null;
        }

        var config = await LoadUsersAsync();
        var user = config.Users.FirstOrDefault(u =>
            string.Equals(u.Email, email, StringComparison.OrdinalIgnoreCase));

        if (user == null)
        {
            RecordFailedAttempt(email);
            _logger.LogWarning("Authentication failed - user not found");
            return null;
        }

        try
        {
            // Verify password using BCrypt
            if (BCrypt.Net.BCrypt.Verify(password, user.PasswordHash))
            {
                ClearFailedAttempts(email);
                _logger.LogInformation("Authentication successful for user: {UserId}", user.UserId);
                return user;
            }
            else
            {
                RecordFailedAttempt(email);
                _logger.LogWarning("Authentication failed - invalid password for user: {UserId}", user.UserId);
                return null;
            }
        }
        catch (Exception ex)
        {
            RecordFailedAttempt(email);
            _logger.LogError(ex, "Authentication error during managed auth");
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

    /// <summary>
    /// Ob Managed Auth eingeschaltet ist -- allein der Schalter, nicht die Datenlage.
    ///
    /// Bis hierher hat diese Methode beides vermischt und auch dann false geliefert,
    /// wenn nur keine Nutzer konfiguriert waren. Damit zeigte die Diagnose in die
    /// falsche Richtung: ein fehlgeschlagener ./config-Mount auf prod meldete sich als
    /// "managed auth is disabled", obwohl niemand den Schalter angefasst hatte -- und
    /// ein frischer Checkout ohne managed-users.json ebenso.
    /// </summary>
    public bool IsEnabled()
    {
        return _configuration.GetValue<bool>("ENABLE_MANAGED_AUTH", true);
    }

    /// <summary>
    /// Ob ueberhaupt Nutzer konfiguriert sind, unabhaengig vom Schalter.
    ///
    /// Getrennt von <see cref="IsEnabled"/>, damit "abgeschaltet" und "Datei fehlt
    /// oder ist leer" zwei unterscheidbare Zustaende bleiben. LoadUsersAsync
    /// protokolliert bei fehlender Datei bereits alle probierten Pfade; die Warnung
    /// hier deckt zusaetzlich den Fall einer vorhandenen, aber leeren Datei ab.
    /// </summary>
    public async Task<bool> HasConfiguredUsersAsync()
    {
        var config = await LoadUsersAsync();

        if (config.Users.Count == 0 && IsEnabled())
        {
            _logger.LogWarning(
                "Managed auth is enabled but no users are configured. Check MANAGED_USERS_PATH and the config mount.");
        }

        return config.Users.Count > 0;
    }
}
