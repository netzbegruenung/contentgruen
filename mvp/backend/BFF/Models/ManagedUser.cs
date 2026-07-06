using System.Text.Json.Serialization;

namespace BFF.Models;

public class ManagedUser
{
    [JsonPropertyName("email")]
    public required string Email { get; set; }

    [JsonPropertyName("passwordHash")]
    public required string PasswordHash { get; set; }

    [JsonPropertyName("displayName")]
    public required string DisplayName { get; set; }

    [JsonPropertyName("userId")]
    public required string UserId { get; set; }

    [JsonPropertyName("createdAt")]
    public DateTime CreatedAt { get; set; }

    [JsonPropertyName("isAdmin")]
    public bool IsAdmin { get; set; } = false;
}

public class ManagedUsersConfig
{
    [JsonPropertyName("users")]
    public List<ManagedUser> Users { get; set; } = new();

    [JsonPropertyName("metadata")]
    public ConfigMetadata? Metadata { get; set; }
}

public class ConfigMetadata
{
    [JsonPropertyName("generated")]
    public string? Generated { get; set; }

    [JsonPropertyName("version")]
    public string? Version { get; set; }

    [JsonPropertyName("totalUsers")]
    public int TotalUsers { get; set; }
}

public class LoginRequest
{
    public string? Email { get; set; }
    public string? Password { get; set; }
}

public class AuthModesResponse
{
    [JsonPropertyName("keycloakEnabled")]
    public bool KeycloakEnabled { get; set; }

    [JsonPropertyName("managedAuthEnabled")]
    public bool ManagedAuthEnabled { get; set; }
}
