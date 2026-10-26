using System;
using System.Collections.Concurrent;
using System.Linq;
using Microsoft.Extensions.Logging;

namespace BFF.Tests.Logging;

/// <summary>
/// Sammelt die Zeilen aller Kategorien eines Testhosts, mit Kategorie und Stufe. Die
/// Filterregeln des Hosts gelten davor: was hier ankommt, stuende auch im Log.
/// </summary>
public sealed class CapturingLoggerProvider : ILoggerProvider
{
    public ConcurrentQueue<(string Category, LogLevel Level, string Message)> Entries { get; } = new();

    /// <summary>Alle Zeilen ab dieser Stufe, ueber alle Kategorien.</summary>
    public string TextAtOrAbove(LogLevel minimum) => string.Join(
        Environment.NewLine,
        Entries
            .Where(e => e.Level >= minimum)
            .Select(e => $"{e.Category} {e.Level}: {e.Message}"));

    public ILogger CreateLogger(string categoryName) => new Logger(this, categoryName);

    public void Dispose()
    {
    }

    private sealed class Logger(CapturingLoggerProvider provider, string category) : ILogger
    {
        public IDisposable? BeginScope<TState>(TState state) where TState : notnull => null;

        public bool IsEnabled(LogLevel logLevel) => true;

        public void Log<TState>(
            LogLevel logLevel,
            EventId eventId,
            TState state,
            Exception? exception,
            Func<TState, Exception?, string> formatter)
        {
            provider.Entries.Enqueue((category, logLevel, formatter(state, exception)));
        }
    }
}
