using Xunit;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using BFF.Services;

namespace BFF.Tests.Services;

/// <summary>Die Liste geloeschter Konten; der Weg durch die Pipeline steht in SitzungNachKontoloeschungTests.</summary>
public class GeloeschteKontenServiceTests : IDisposable
{
    private readonly string _pfad = Path.Combine(Path.GetTempPath(), $"geloeschte-konten-{Guid.NewGuid():N}.txt");
    private readonly StellbareUhr _uhr = new();

    public void Dispose() => File.Delete(_pfad);

    private GeloeschteKontenService Service() => new(
        NullLogger<GeloeschteKontenService>.Instance,
        new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?> { ["GELOESCHTE_KONTEN_PATH"] = _pfad })
            .Build(),
        _uhr);

    [Fact]
    public async Task IstGeloeschtAsync_OhneDatei_KeinKontoGeloescht()
    {
        Assert.False(await Service().IstGeloeschtAsync("kennung-1"));
    }

    [Fact]
    public async Task IstGeloeschtAsync_IgnoriertKommentareLeerzeilenUndLeerraum()
    {
        File.WriteAllText(_pfad, "# kennung-2\n\n  kennung-1 \n");
        var service = Service();

        Assert.True(await service.IstGeloeschtAsync("kennung-1"));
        Assert.False(await service.IstGeloeschtAsync("kennung-2"));
        Assert.False(await service.IstGeloeschtAsync("# kennung-2"));
        Assert.False(await service.IstGeloeschtAsync(""));
        Assert.False(await service.IstGeloeschtAsync(null));
    }

    [Fact]
    public async Task IstGeloeschtAsync_VergleichtOrdinal()
    {
        File.WriteAllText(_pfad, "Kennung-1\n");

        Assert.False(await Service().IstGeloeschtAsync("kennung-1"));
    }

    [Fact]
    public async Task IstGeloeschtAsync_NeuerEintrag_GiltSpaetestensNachFuenfMinuten()
    {
        var service = Service();
        Assert.False(await service.IstGeloeschtAsync("kennung-1"));

        File.WriteAllText(_pfad, "kennung-1\n");
        _uhr.Vorstellen(TimeSpan.FromMinutes(4));
        Assert.False(await service.IstGeloeschtAsync("kennung-1"));

        _uhr.Vorstellen(TimeSpan.FromMinutes(1));
        Assert.True(await service.IstGeloeschtAsync("kennung-1"));
    }
}

/// <summary>Eine Uhr, die nur der Test weiterstellt.</summary>
internal sealed class StellbareUhr : TimeProvider
{
    private DateTimeOffset _jetzt = new(2026, 10, 27, 12, 0, 0, TimeSpan.Zero);

    public override DateTimeOffset GetUtcNow() => _jetzt;

    public void Vorstellen(TimeSpan dauer) => _jetzt += dauer;
}
