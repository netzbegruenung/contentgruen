using Xunit;
using BFF.Logging;

namespace BFF.Tests.Logging;

/// <summary>
/// Das Gegenstueck zu log_pseudonym() im Suchdienst (app/core/logging.py). Die erwarteten
/// Werte stammen von dort; stimmen sie hier, laesst sich eine Kennung ueber BFF- und
/// Suchdienst-Log hinweg verfolgen, ohne dass sie in einem davon im Klartext steht.
/// </summary>
public class LogPseudonymTests
{
    [Theory]
    [InlineData("user-001", "85c5fb49")]
    [InlineData("Grüne-01", "ea6a3637")]
    public void Of_MatchesTheSearchServicePseudonym(string userId, string expected)
    {
        Assert.Equal(expected, LogPseudonym.Of(userId));
    }

    [Fact]
    public void Of_DoesNotContainTheIdentifier()
    {
        Assert.DoesNotContain("user-001", LogPseudonym.Of("user-001"));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("anonymous")]
    public void Of_KeepsAnonymousReadable(string? userId)
    {
        // "anonymous" ist keine Kennung, sondern deren Abwesenheit.
        Assert.Equal("anonymous", LogPseudonym.Of(userId));
    }
}
