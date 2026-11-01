using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Collections.Generic;
using BFF.Models;
using BFF.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace BFF.Tests;

/// <summary>
/// Die Beta-Zugangsliste (managed-users.json) fuer Tests: Zugaenge anlegen, die Datei
/// schreiben und den ManagedUserService darauf bauen. Alle Zugaenge tragen dasselbe
/// Passwort; BCrypt mit niedrigem Work-Factor haelt die Tests schnell.
/// </summary>
internal static class BetaZugangsliste
{
    public const string Passwort = "Test123!";

    private static readonly Lazy<string> PasswortHash =
        new(() => BCrypt.Net.BCrypt.HashPassword(Passwort, 4));

    public static ManagedUser Zugang(
        string email, string userId, string displayName = "Test", bool isAdmin = false) =>
        new()
        {
            Email = email,
            PasswordHash = PasswortHash.Value,
            DisplayName = displayName,
            UserId = userId,
            IsAdmin = isAdmin
        };

    /// <summary>Schreibt die Liste in eine neue Datei im Temp-Verzeichnis und liefert ihren Pfad.</summary>
    public static string Schreiben(params ManagedUser[] zugaenge)
    {
        var pfad = Path.Combine(Path.GetTempPath(), $"managed-users-{Guid.NewGuid():N}.json");
        SchreibenNach(pfad, zugaenge);
        return pfad;
    }

    /// <summary>Kurzform: je Zugang nur Mail-Adresse und Kennung.</summary>
    public static string Schreiben(params (string Email, string UserId)[] zugaenge) =>
        Schreiben(zugaenge.Select(z => Zugang(z.Email, z.UserId)).ToArray());

    /// <summary>Schreibt die Liste an diesen Pfad; ohne Zugaenge eine leere Liste.</summary>
    public static void SchreibenNach(string pfad, params ManagedUser[] zugaenge) =>
        File.WriteAllText(
            pfad, JsonSerializer.Serialize(new ManagedUsersConfig { Users = zugaenge.ToList() }));

    /// <summary>Der ManagedUserService auf die Liste unter diesem Pfad.</summary>
    public static ManagedUserService Dienst(
        ILogger<ManagedUserService> logger,
        string pfad,
        bool managedAuthEnabled = true,
        TimeProvider? uhr = null)
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                { "MANAGED_USERS_PATH", pfad },
                { "ENABLE_MANAGED_AUTH", managedAuthEnabled ? "true" : "false" }
            })
            .Build();
        return new ManagedUserService(logger, configuration, uhr);
    }
}
