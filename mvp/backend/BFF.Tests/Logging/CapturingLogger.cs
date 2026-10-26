using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Extensions.Logging;

namespace BFF.Tests.Logging;

/// <summary>
/// Haelt jede Zeile so fest, wie sie im Log stuende, auf allen Stufen. Fuer Zusicherungen
/// der Form "diese Kennung steht in keiner Zeile" -- mit Moq.Verify waere das eine Negation
/// ueber alle Aufrufe, hier ist es ein Contains auf dem Text.
/// </summary>
public sealed class CapturingLogger<T> : ILogger<T>
{
    private readonly CapturingLoggerProvider _provider = new();
    private readonly ILogger _inner;

    public CapturingLogger()
    {
        _inner = _provider.CreateLogger(typeof(T).FullName!);
    }

    public List<string> Lines => _provider.Entries.Select(e => $"{e.Level}: {e.Message}").ToList();

    public string Text => string.Join(Environment.NewLine, Lines);

    public IDisposable? BeginScope<TState>(TState state) where TState : notnull => _inner.BeginScope(state);

    public bool IsEnabled(LogLevel logLevel) => _inner.IsEnabled(logLevel);

    public void Log<TState>(
        LogLevel logLevel,
        EventId eventId,
        TState state,
        Exception? exception,
        Func<TState, Exception?, string> formatter) =>
        _inner.Log(logLevel, eventId, state, exception, formatter);
}
