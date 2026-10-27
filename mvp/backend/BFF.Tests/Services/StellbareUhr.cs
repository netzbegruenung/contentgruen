using System;

namespace BFF.Tests.Services;

/// <summary>Eine Uhr, die nur der Test weiterstellt.</summary>
internal sealed class StellbareUhr : TimeProvider
{
    private DateTimeOffset _jetzt = new(2026, 10, 27, 12, 0, 0, TimeSpan.Zero);

    public override DateTimeOffset GetUtcNow() => _jetzt;

    public void Vorstellen(TimeSpan dauer) => _jetzt += dauer;
}
