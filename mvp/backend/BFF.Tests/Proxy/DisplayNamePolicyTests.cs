using Xunit;
using System.Security.Claims;
using BFF.Proxy;

namespace BFF.Tests.Proxy;

public class DisplayNamePolicyTests
{
    private static ClaimsPrincipal Mit(params (string Typ, string Wert)[] claims) =>
        new ClaimsPrincipal(new ClaimsIdentity(
            claims.Select(c => new Claim(c.Typ, c.Wert)).Prepend(new Claim("sub", "kennung")),
            "TestAuth"));

    [Fact]
    public void From_GivenNameAndSurname_GivesFirstNameAndInitial()
    {
        var user = Mit((ClaimTypes.GivenName, "Anna"), (ClaimTypes.Surname, "Berger"));

        Assert.Equal("Anna B.", DisplayNamePolicy.From(user));
    }

    [Fact]
    public void From_GivenNameAndSurname_WinOverNameClaim()
    {
        var user = Mit(
            (ClaimTypes.GivenName, "Anna"),
            (ClaimTypes.Surname, "Berger"),
            ("name", "Anna Maria Berger-Lutz"));

        Assert.Equal("Anna B.", DisplayNamePolicy.From(user));
    }

    [Fact]
    public void From_Umlauts_StayIntact()
    {
        var user = Mit((ClaimTypes.GivenName, "Jürgen"), (ClaimTypes.Surname, "Östermann"));

        Assert.Equal("Jürgen Ö.", DisplayNamePolicy.From(user));
    }

    [Fact]
    public void From_OnlyNameClaim_TakesFirstWordAndInitialOfLast()
    {
        var user = Mit(("name", "Anna Maria  Berger"));

        Assert.Equal("Anna B.", DisplayNamePolicy.From(user));
    }

    [Fact]
    public void From_ManagedLogin_UsesDisplayNameFromNameClaim()
    {
        // Die Claims, die AuthController.Login fuer Managed-Login setzt.
        var user = Mit(
            (ClaimTypes.NameIdentifier, "user-001"),
            (ClaimTypes.Name, "Test User"),
            ("name", "Test User"),
            (ClaimTypes.Email, "test.user@example.com"),
            ("auth_method", "managed"));

        Assert.Equal("Test U.", DisplayNamePolicy.From(user));
    }

    [Fact]
    public void From_SingleWord_HasNoInitial()
    {
        Assert.Equal("Kim", DisplayNamePolicy.From(Mit(("name", "Kim"))));
    }

    [Fact]
    public void From_GivenNameWithoutSurname_FallsBackToNameClaim()
    {
        var user = Mit((ClaimTypes.GivenName, "Anna"), ("name", "Anna Berger"));

        Assert.Equal("Anna B.", DisplayNamePolicy.From(user));
    }

    [Fact]
    public void From_OnlyGivenName_GivesGivenName()
    {
        Assert.Equal("Anna", DisplayNamePolicy.From(Mit((ClaimTypes.GivenName, "Anna"))));
    }

    [Fact]
    public void From_OnlyLoginIdentifiers_GivesNothing()
    {
        // preferred_username, E-Mail und ClaimTypes.Name sind Kennungen, keine Namen.
        var user = Mit(
            ("preferred_username", "anna.berger"),
            ("email", "anna@example.org"),
            (ClaimTypes.Email, "anna@example.org"),
            (ClaimTypes.Name, "anna.berger"));

        Assert.Null(DisplayNamePolicy.From(user));
    }

    [Fact]
    public void From_NameClaimHoldingAnAddress_GivesNothing()
    {
        Assert.Null(DisplayNamePolicy.From(Mit(("name", "anna@example.org"))));
    }

    [Fact]
    public void From_BlankClaims_GiveNothing()
    {
        var user = Mit((ClaimTypes.GivenName, "  "), (ClaimTypes.Surname, ""), ("name", " "));

        Assert.Null(DisplayNamePolicy.From(user));
    }
}
