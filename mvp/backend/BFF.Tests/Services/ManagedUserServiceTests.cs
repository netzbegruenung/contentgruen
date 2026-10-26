using Xunit;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Configuration;
using Moq;
using System.Collections.Generic;
using BFF.Services;
using BFF.Models;
using BFF.Logging;
using BFF.Tests.Logging;
using System.Threading.Tasks;
using System.Collections.Generic;
using System;
using System.IO;
using System.Linq;

namespace BFF.Tests.Services;

public class ManagedUserServiceTests
{
    private readonly Mock<ILogger<ManagedUserService>> _mockLogger;
    private IConfiguration _configuration;
    private ManagedUserService _service;

    public ManagedUserServiceTests()
    {
        _mockLogger = new Mock<ILogger<ManagedUserService>>();
        // Default configuration with no users
        var configBuilder = new ConfigurationBuilder();
        configBuilder.AddInMemoryCollection(new Dictionary<string, string>
        {
            { "MANAGED_USERS_PATH", "non-existent.json" },
            { "ENABLE_MANAGED_AUTH", "true" }
        });
        _configuration = configBuilder.Build();
        _service = new ManagedUserService(_mockLogger.Object, _configuration);
    }

    [Fact]
    public async Task ValidateUserAsync_ReturnsNull_WhenEmailIsEmpty()
    {
        // Act
        var result = await _service.ValidateUserAsync("", "password");

        // Assert
        Assert.Null(result);
    }

    [Fact]
    public async Task ValidateUserAsync_ReturnsNull_WhenPasswordIsEmpty()
    {
        // Act
        var result = await _service.ValidateUserAsync("test@example.com", "");

        // Assert
        Assert.Null(result);
    }

    [Fact]
    public async Task ValidateUserAsync_ReturnsNull_WhenEmailIsNull()
    {
        // Act
        var result = await _service.ValidateUserAsync(null!, "password");

        // Assert
        Assert.Null(result);
    }

    [Fact]
    public async Task ValidateUserAsync_ReturnsNull_WhenPasswordIsNull()
    {
        // Act
        var result = await _service.ValidateUserAsync("test@example.com", null!);

        // Assert
        Assert.Null(result);
    }

    [Fact]
    public async Task GetUserByIdAsync_ReturnsNull_WhenUserIdIsEmpty()
    {
        // Act
        var result = await _service.GetUserByIdAsync("");

        // Assert
        Assert.Null(result);
    }

    [Fact]
    public async Task GetUserByIdAsync_ReturnsNull_WhenUserIdIsNull()
    {
        // Act
        var result = await _service.GetUserByIdAsync(null!);

        // Assert
        Assert.Null(result);
    }

    [Fact]
    public async Task GetUserByEmailAsync_ReturnsNull_WhenEmailIsEmpty()
    {
        // Act
        var result = await _service.GetUserByEmailAsync("");

        // Assert
        Assert.Null(result);
    }

    [Fact]
    public async Task GetUserByEmailAsync_ReturnsNull_WhenEmailIsNull()
    {
        // Act
        var result = await _service.GetUserByEmailAsync(null!);

        // Assert
        Assert.Null(result);
    }

    [Fact]
    public void IsEnabled_ReturnsFalse_WhenDisabledInConfiguration()
    {
        // Arrange
        var configBuilder = new ConfigurationBuilder();
        configBuilder.AddInMemoryCollection(new Dictionary<string, string>
        {
            { "ENABLE_MANAGED_AUTH", "false" },
            { "MANAGED_USERS_PATH", "non-existent.json" }
        });
        var service = new ManagedUserService(_mockLogger.Object, configBuilder.Build());

        // Act
        var result = service.IsEnabled();

        // Assert
        Assert.False(result);
    }

    [Fact]
    public void IsEnabled_ReturnsTrue_WhenSwitchIsOn_EvenWithoutConfiguredUsers()
    {
        // _service zeigt auf eine nicht existierende Datei. Frueher meldete der Guard
        // hier false und LoginManaged antwortete 404 -- ein fehlender ./config-Mount
        // sah damit aus wie ein umgelegter Schalter. Der Schalter steht auf an, also
        // sagt der Schalter-Guard an.
        Assert.True(_service.IsEnabled());
    }

    [Fact]
    public async Task HasConfiguredUsersAsync_ReturnsFalse_WhenConfigFileIsMissing()
    {
        // Arrange - service already configured with non-existent file

        // Act
        var result = await _service.HasConfiguredUsersAsync();

        // Assert
        Assert.False(result);
    }

    [Fact]
    public async Task HasConfiguredUsersAsync_LogsWarning_WhenEnabledButEmpty()
    {
        // Die Zeile, die auf prod den Unterschied macht: sie benennt die Datenlage,
        // nicht den Schalter.
        await _service.HasConfiguredUsersAsync();

        _mockLogger.Verify(
            x => x.Log(
                LogLevel.Warning,
                It.IsAny<EventId>(),
                It.Is<It.IsAnyType>((v, t) => v.ToString()!.Contains("no users are configured")),
                It.IsAny<Exception>(),
                It.IsAny<Func<It.IsAnyType, Exception?, string>>()),
            Times.AtLeastOnce);
    }

    [Fact]
    public async Task ValidateUserAsync_HandlesRateLimiting()
    {
        // Arrange
        var email = "test@example.com";
        var password = "password";

        // Act - Simulate multiple failed attempts
        for (int i = 0; i < 6; i++)
        {
            await _service.ValidateUserAsync(email, password);
        }

        // The 6th attempt should be rate-limited
        var result = await _service.ValidateUserAsync(email, password);

        // Assert
        Assert.Null(result);
        _mockLogger.Verify(
            x => x.Log(
                LogLevel.Warning,
                It.IsAny<EventId>(),
                It.Is<It.IsAnyType>((v, t) => v.ToString()!.Contains("rate limit")),
                It.IsAny<Exception>(),
                It.IsAny<Func<It.IsAnyType, Exception?, string>>()),
            Times.AtLeastOnce);
    }

    // Warum reserviert: siehe ManagedUserService.EhemaligePersonKennung.
    [Theory]
    [InlineData("ehemalige-person")]
    [InlineData("ehemalige-person-6f1c2d3e-0000-4000-8000-000000000000")]
    public async Task ValidateUserAsync_ReturnsNull_WhenUserIdIsReserved(string reservedId)
    {
        var path = WriteUsersFile(
            ("ok@example.com", "user-001"),
            ("reserved@example.com", reservedId));
        try
        {
            var service = ServiceFor(path);

            Assert.Null(await service.GetUserByIdAsync(reservedId));
            Assert.Null(await service.GetUserByEmailAsync("reserved@example.com"));
            Assert.Null(await service.ValidateUserAsync("reserved@example.com", KnownPassword));
            Assert.NotNull(await service.GetUserByIdAsync("user-001"));
            Assert.NotNull(await service.ValidateUserAsync("ok@example.com", KnownPassword));

            _mockLogger.Verify(
                x => x.Log(
                    LogLevel.Error,
                    It.IsAny<EventId>(),
                    It.Is<It.IsAnyType>((v, t) =>
                        v.ToString()!.Contains($"userId {LogPseudonym.Of(reservedId)} rejected")
                        && !v.ToString()!.Contains("@")),
                    It.IsAny<Exception>(),
                    It.IsAny<Func<It.IsAnyType, Exception?, string>>()),
                Times.AtLeastOnce);
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Theory]
    [InlineData("ehemalige-personal")]
    [InlineData("user-ehemalige-person")]
    [InlineData("Ehemalige-Person")]
    public async Task GetUserByIdAsync_ReturnsUser_WhenUserIdOnlyResemblesReservedId(string userId)
    {
        var path = WriteUsersFile(("someone@example.com", userId));
        try
        {
            Assert.NotNull(await ServiceFor(path).GetUserByIdAsync(userId));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void IsReservedUserId_MatchesPlaceholderAndPrefixOnly()
    {
        Assert.True(ManagedUserService.IsReservedUserId("ehemalige-person"));
        Assert.True(ManagedUserService.IsReservedUserId("ehemalige-person-abc"));
        Assert.False(ManagedUserService.IsReservedUserId("ehemalige-personal"));
        Assert.False(ManagedUserService.IsReservedUserId("Ehemalige-Person"));
        Assert.False(ManagedUserService.IsReservedUserId("user-001"));
        Assert.False(ManagedUserService.IsReservedUserId(""));
    }

    // Die Kennung steht ab Information nicht im Klartext im Log (#277), auch nicht beim
    // Fehlversuch. Pseudonymisiert wie im Suchdienst, damit Zeilen beider Dienste
    // zusammenpassen.
    [Fact]
    public async Task ValidateUserAsync_LogsOnlyThePseudonym_OnSuccessAndWrongPassword()
    {
        var path = WriteUsersFile(("ok@example.com", "user-001"));
        try
        {
            var logger = new CapturingLogger<ManagedUserService>();
            var configuration = new ConfigurationBuilder()
                .AddInMemoryCollection(new Dictionary<string, string?>
                {
                    { "MANAGED_USERS_PATH", path },
                    { "ENABLE_MANAGED_AUTH", "true" }
                })
                .Build();
            var service = new ManagedUserService(logger, configuration);

            Assert.NotNull(await service.ValidateUserAsync("ok@example.com", KnownPassword));
            Assert.Null(await service.ValidateUserAsync("ok@example.com", "falsch"));

            Assert.DoesNotContain("user-001", logger.Text);
            Assert.Equal(2, logger.Lines.FindAll(l => l.Contains(LogPseudonym.Of("user-001"))).Count);
        }
        finally
        {
            File.Delete(path);
        }
    }

    private const string KnownPassword = "Passwort1!";

    private ManagedUserService ServiceFor(string path)
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                { "MANAGED_USERS_PATH", path },
                { "ENABLE_MANAGED_AUTH", "true" }
            })
            .Build();
        return new ManagedUserService(_mockLogger.Object, configuration);
    }

    private static string WriteUsersFile(params (string Email, string UserId)[] users)
    {
        // Ein Hash fuer alle: BCrypt mit niedrigem Work-Factor haelt den Test schnell.
        var hash = BCrypt.Net.BCrypt.HashPassword(KnownPassword, 4);
        var config = new ManagedUsersConfig
        {
            Users = users.Select(u => new ManagedUser
            {
                Email = u.Email,
                PasswordHash = hash,
                DisplayName = "Test",
                UserId = u.UserId
            }).ToList()
        };
        var path = Path.Combine(Path.GetTempPath(), $"managed-users-{Guid.NewGuid():N}.json");
        File.WriteAllText(path, System.Text.Json.JsonSerializer.Serialize(config));
        return path;
    }
}
