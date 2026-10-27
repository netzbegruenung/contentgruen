using System.Text.Json;
using System.Collections.Concurrent;
using BFF.Logging;
using BFF.Models;
using BCrypt.Net;

namespace BFF.Services;

public class ManagedUserService
{
    private readonly ILogger<ManagedUserService> _logger;
    private readonly IConfiguration _configuration;
    private readonly TimeProvider _time;
    private ManagedUsersConfig? _usersConfig;
    private DateTimeOffset _lastLoadTime = DateTimeOffset.MinValue;
    private readonly TimeSpan _cacheExpiry = TimeSpan.FromMinutes(5);

    // Rate limiting for failed login attempts
    private readonly ConcurrentDictionary<string, List<DateTime>> _failedAttempts = new();
    private readonly TimeSpan _rateLimitWindow = TimeSpan.FromMinutes(15);
    private readonly int _maxFailedAttempts = 5;

    /// <summary>
    /// Kennung des Platzhalters "ehemalige Person" an den Beitraegen geloeschter Personen.
    /// Reserviert, ebenso wie alles mit dem Praefix "ehemalige-person-" (Saetze im
    /// Fangkorb); muss zu EHEMALIGE_PERSON_KENNUNG in
    /// semantic-search-service/app/services/anzeigename_service.py passen.
    /// </summary>
    public const string EhemaligePersonKennung = "ehemalige-person";

    public ManagedUserService(
        ILogger<ManagedUserService> logger,
        IConfiguration configuration,
        TimeProvider? timeProvider = null)
    {
        _logger = logger;
        _configuration = configuration;
        _time = timeProvider ?? TimeProvider.System;
    }

    private async Task<ManagedUsersConfig> LoadUsersAsync()
    {
        // Check cache
        if (_usersConfig != null && _time.GetUtcNow() - _lastLoadTime < _cacheExpiry)
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
            var config = JsonSerializer.Deserialize<ManagedUsersConfig>(json) ?? new ManagedUsersConfig();
            config.Users = WithoutReservedUserIds(config.Users);
            _usersConfig = config;
            _lastLoadTime = _time.GetUtcNow();

            _logger.LogInformation("Loaded {Count} managed users from config", _usersConfig.Users.Count);
            return _usersConfig;
        }
        catch (Exception ex)
        {
            // Die zuletzt gelesene Liste bleibt gueltig: KontoPruefung beendet die Sitzung jedes
            // Beta-Zugangs, der nicht in der Liste steht, und eine halb geschriebene Datei darf
            // nicht alle abmelden (#278).
            _logger.LogError(ex, "Failed to load managed users config from {Path}", validPath);
            return _usersConfig ?? new ManagedUsersConfig();
        }
    }

    /// <summary>
    /// Ob eine userId fuer den Platzhalter "ehemalige Person" reserviert ist. Verglichen
    /// wird ordinal wie im Backend, das die Kennung ebenso exakt prueft.
    /// </summary>
    public static bool IsReservedUserId(string? userId)
    {
        return userId != null
            && (userId == EhemaligePersonKennung
                || userId.StartsWith(EhemaligePersonKennung + "-", StringComparison.Ordinal));
    }

    // Beta-Zugaenge mit reservierter Kennung fallen aus der Liste; die uebrigen bleiben
    // nutzbar. Geloggt wird nur das Pseudonym der Kennung, nicht die Mail-Adresse; wer den
    // Eintrag sucht, sucht in managed-users.json nach dem Platzhalter.
    private List<ManagedUser> WithoutReservedUserIds(List<ManagedUser> users)
    {
        var reserved = users.Where(u => IsReservedUserId(u.UserId)).ToList();
        foreach (var user in reserved)
        {
            _logger.LogError(
                "Beta-Zugang with userId {UserId} rejected: the id is reserved for the placeholder \"{Placeholder}\" of deleted persons. Choose a different userId in managed-users.json.",
                LogPseudonym.Of(user.UserId), EhemaligePersonKennung);
        }

        return reserved.Count == 0 ? users : users.Except(reserved).ToList();
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
                _logger.LogInformation("Authentication successful for user: {UserId}", LogPseudonym.Of(user.UserId));
                return user;
            }
            else
            {
                RecordFailedAttempt(email);
                _logger.LogWarning("Authentication failed - invalid password for user: {UserId}", LogPseudonym.Of(user.UserId));
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
