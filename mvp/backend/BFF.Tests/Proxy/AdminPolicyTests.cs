using Xunit;
using System.Security.Claims;
using BFF.Proxy;

namespace BFF.Tests.Proxy;

/// <summary>
/// Adminrechte entstehen aus zwei Quellen, verknuepft mit ODER: einem Claim am angemeldeten
/// Nutzer oder der konfigurierten Allowlist. Die Tests halten beide Richtungen fest -- dass
/// die Liste Rechte gibt, und dass sie dem Claim keine nimmt.
/// </summary>
public class AdminPolicyTests
{
    private static readonly string[] NoAllowlist = Array.Empty<string>();

    private static ClaimsPrincipal UserWith(string userId, params (string Type, string Value)[] extraClaims)
    {
        var claims = new List<Claim> { new Claim("sub", userId) };
        foreach (var (type, value) in extraClaims)
        {
            claims.Add(new Claim(type, value));
        }

        return new ClaimsPrincipal(new ClaimsIdentity(claims, "TestAuth"));
    }

    [Fact]
    public void IsAdmin_UserIdInAllowlist_IsAdminWithoutAnyClaim()
    {
        Assert.True(AdminPolicy.IsAdmin(UserWith("kennung-1"), new[] { "kennung-1" }));
    }

    [Fact]
    public void IsAdmin_UserIdNotInAllowlistAndNoClaim_IsNotAdmin()
    {
        Assert.False(AdminPolicy.IsAdmin(UserWith("kennung-1"), new[] { "kennung-2", "kennung-3" }));
    }

    [Theory]
    [InlineData("isAdmin", "true")]
    [InlineData("role", "admin")]
    [InlineData(ClaimTypes.Role, "admin")]
    public void IsAdmin_AdminClaimAndUserIdNotInAllowlist_StaysAdmin(string claimType, string claimValue)
    {
        // Alle drei Claim-Formen, die vor der Allowlist schon Adminrechte ergaben. Der
        // Managed-Auth-Pfad setzt zwei davon (AuthController), ein Keycloak-Mapper koennte
        // jede setzen; keine davon darf davon abhaengen, in der Liste zu stehen.
        var user = UserWith("kennung-1", (claimType, claimValue));

        Assert.True(AdminPolicy.IsAdmin(user, new[] { "voellig-andere-kennung" }));
    }

    [Theory]
    [InlineData("isAdmin", "true")]
    [InlineData("role", "admin")]
    [InlineData(ClaimTypes.Role, "admin")]
    public void IsAdmin_AdminClaimAndEmptyAllowlist_StaysAdmin(string claimType, string claimValue)
    {
        // Der Zustand unmittelbar nach dem Ausrollen, solange ADMIN_USER_IDS nirgends
        // gesetzt ist: das Verhalten muss unveraendert sein.
        var user = UserWith("kennung-1", (claimType, claimValue));

        Assert.True(AdminPolicy.IsAdmin(user, NoAllowlist));
    }

    [Fact]
    public void IsAdmin_NoClaimAndEmptyAllowlist_IsNotAdmin()
    {
        Assert.False(AdminPolicy.IsAdmin(UserWith("kennung-1"), NoAllowlist));
    }

    [Fact]
    public void IsAdmin_NonAdminClaimValues_AreNotEnough()
    {
        // isAdmin mit einem anderen Wert als "true" und eine andere Rolle als "admin"
        // duerfen nicht durchrutschen.
        var user = UserWith("kennung-1", ("isAdmin", "false"), ("role", "moderator"));

        Assert.False(AdminPolicy.IsAdmin(user, NoAllowlist));
    }

    [Fact]
    public void IsAdmin_UserWithoutIdentifier_IsNotAdmin()
    {
        // Ohne sub und ohne NameIdentifier gibt es keine Kennung, die in einer Liste stehen
        // koennte. Der leere Wert darf nicht auf einen leeren Listeneintrag passen.
        var anonymous = new ClaimsPrincipal(new ClaimsIdentity());

        Assert.False(AdminPolicy.IsAdmin(anonymous, new[] { "kennung-1" }));
    }

    [Fact]
    public void IsAdmin_NameIdentifierInsteadOfSub_IsMatchedToo()
    {
        // ClaimUtilities.GetUserId faellt auf NameIdentifier zurueck -- das ist die Form,
        // die das Inbound-Claim-Mapping von .NET aus einem sub machen kann. Sonst haette
        // dieselbe Person je nach Mapping mal Rechte und mal nicht.
        var user = new ClaimsPrincipal(new ClaimsIdentity(
            new[] { new Claim(ClaimTypes.NameIdentifier, "kennung-1") }, "TestAuth"));

        Assert.True(AdminPolicy.IsAdmin(user, new[] { "kennung-1" }));
    }

    [Fact]
    public void ParseAllowlist_SplitsOnCommaAndTrims()
    {
        Assert.Equal(
            new[] { "kennung-1", "kennung-2", "kennung-3" },
            AdminPolicy.ParseAllowlist("  kennung-1 , kennung-2 ,, kennung-3  "));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData(",")]
    public void ParseAllowlist_WithoutEntries_IsEmpty(string? configured)
    {
        // Ungesetzt, leer oder nur Trennzeichen: alles derselbe Normalfall, kein Fehler.
        Assert.Empty(AdminPolicy.ParseAllowlist(configured));
    }

    [Fact]
    public void ParseAllowlist_DropsDuplicates()
    {
        Assert.Equal(new[] { "kennung-1" }, AdminPolicy.ParseAllowlist("kennung-1,kennung-1"));
    }

    [Fact]
    public void IsAdmin_ComparisonIsCaseSensitive()
    {
        // Anders als bei CORS_ALLOWED_ORIGINS wird ordinal verglichen. Nutzerkennungen sind
        // opake Zeichenketten, und das Python-Backend prueft SEMANTIC_SEARCH_ADMIN_USERS
        // exakt (config.py). Ein toleranterer Vergleich hier liesse beide Seiten fuer
        // denselben Wert unterschiedlich entscheiden.
        Assert.False(AdminPolicy.IsAdmin(UserWith("kennung-1"), new[] { "KENNUNG-1" }));
        Assert.True(AdminPolicy.IsAdmin(UserWith("kennung-1"), new[] { "kennung-1" }));
    }
}
