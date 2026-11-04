using System;
using System.IO;
using BFF.Logging;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Logging.Console;
using Microsoft.Extensions.Options;
using Xunit;

namespace BFF.Tests.Logging;

/// <summary>
/// Keine Eingabewerte in Fehlerzeilen (#422). Der Fehlertext einer Ausnahme traegt oft, was
/// hereinkam (ein Formatfehler den Wert, eine ungueltige Adresse die Adresse). Die
/// Konsolenausgabe nennt Typ und Stack der Ausnahme, nicht ihren Fehlertext.
/// </summary>
public class AusnahmeOhneFehlertextFormatterTests
{
    private const string Eingabe = "Waermepumpe-im-Altbau-422";

    private static Exception Ausgeloest(Func<Exception> erzeugen)
    {
        try
        {
            throw erzeugen();
        }
        catch (Exception gefangen)
        {
            return gefangen;
        }
    }

    private static string Zeile(Exception? ausnahme, string text = "Speichern fehlgeschlagen")
    {
        var formatter = new AusnahmeOhneFehlertextFormatter();
        using var schreiber = new StringWriter();
        var eintrag = new LogEntry<string>(
            LogLevel.Error, "BFF.Beispiel", new EventId(7), text, ausnahme, (s, _) => s);
        formatter.Write(in eintrag, null, schreiber);
        return schreiber.ToString();
    }

    [Fact]
    public void Nennt_Typ_und_Stelle_aber_nicht_den_Fehlertext()
    {
        var ausnahme = Ausgeloest(() => new FormatException($"ungueltiger Wert: {Eingabe}"));

        var zeile = Zeile(ausnahme);

        Assert.Contains("Speichern fehlgeschlagen", zeile);
        Assert.Contains("BFF.Beispiel", zeile);
        Assert.Contains("System.FormatException", zeile);
        Assert.Contains(nameof(Ausgeloest), zeile);
        Assert.DoesNotContain(Eingabe, zeile);
    }

    [Fact]
    public void Auch_nicht_den_Fehlertext_der_inneren_Ausnahme()
    {
        var innen = Ausgeloest(() => new UriFormatException(Eingabe));
        var ausnahme = Ausgeloest(() => new InvalidOperationException($"Folgefehler: {Eingabe}", innen));

        var zeile = Zeile(ausnahme);

        Assert.Contains("System.InvalidOperationException", zeile);
        Assert.Contains("System.UriFormatException", zeile);
        Assert.DoesNotContain(Eingabe, zeile);

        // Wie Exception.ToString(): innerer Stack vor der Marke, die Marke vor dem aeusseren.
        var marke = zeile.IndexOf("--- End of inner exception stack trace ---", StringComparison.Ordinal);
        Assert.True(zeile.IndexOf("System.UriFormatException", StringComparison.Ordinal) < marke);
        Assert.True(marke < zeile.LastIndexOf(nameof(Ausgeloest), StringComparison.Ordinal));
        Assert.True(zeile.IndexOf(nameof(Ausgeloest), StringComparison.Ordinal) < marke);
    }

    [Fact]
    public void Ohne_Ausnahme_bleibt_die_Zeile_wie_geschrieben()
    {
        var zeile = Zeile(null, "Loaded 3 deleted accounts");

        var zeilen = zeile.Split(Environment.NewLine);
        Assert.Equal("fail: BFF.Beispiel[7]", zeilen[0]);
        Assert.Equal("      Loaded 3 deleted accounts", zeilen[1]);
    }

    [Fact]
    public void Der_Host_schreibt_mit_diesem_Formatter_auch_wenn_die_Konfiguration_einen_anderen_nennt()
    {
        // Ein Logging__Console__FormatterName=json am Container brachte sonst die volle
        // Ausnahme samt Fehlertext zurueck.
        using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.UseContentRoot(AppContext.BaseDirectory);
            builder.UseEnvironment("Development");
            builder.UseSetting("USE_KEYCLOAK", "false");
            builder.UseSetting("FRONTEND_URL", "http://localhost:4200");
            builder.UseSetting("BACKEND_URL", "http://127.0.0.1:1");
            builder.UseSetting(
                "DATAPROTECTION_KEYS_PATH",
                Path.Combine(Path.GetTempPath(), "gutgesagt-bff-test-keys"));
            builder.UseSetting("Logging:Console:FormatterName", ConsoleFormatterNames.Json);
        });

        var optionen = factory.Services.GetRequiredService<IOptionsMonitor<ConsoleLoggerOptions>>();

        Assert.Equal(AusnahmeOhneFehlertextFormatter.Name, optionen.CurrentValue.FormatterName);
    }
}
