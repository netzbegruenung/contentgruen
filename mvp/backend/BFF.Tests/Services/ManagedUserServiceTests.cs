using Xunit;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Configuration;
using Moq;
using System.Collections.Generic;
using BFF.Services;
using BFF.Models;
using System.Threading.Tasks;
using System.Collections.Generic;
using System;

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
    public async Task IsEnabledAsync_ReturnsFalse_WhenDisabledInConfiguration()
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
        var result = await service.IsEnabledAsync();

        // Assert
        Assert.False(result);
    }

    [Fact]
    public async Task IsEnabledAsync_ReturnsFalse_WhenNoUsersConfigured()
    {
        // Arrange - service already configured with non-existent file

        // Act
        var result = await _service.IsEnabledAsync();

        // Assert
        Assert.False(result);
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
}
