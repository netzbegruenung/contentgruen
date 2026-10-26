using System;
using System.Collections.Generic;
using Microsoft.Extensions.Logging;

namespace BFF.Tests.Logging;

/// <summary>
/// Haelt jede Zeile so fest, wie sie im Log stuende, auf allen Stufen. Fuer Zusicherungen
/// der Form "diese Kennung steht in keiner Zeile" -- mit Moq.Verify waere das eine Negation
/// ueber alle Aufrufe, hier ist es ein Contains auf dem Text.
/// </summary>
public sealed class CapturingLogger<T> : ILogger<T>
{
    public List<string> Lines { get; } = new();

    public string Text => string.Join(Environment.NewLine, Lines);

    public IDisposable? BeginScope<TState>(TState state) where TState : notnull => null;

    public bool IsEnabled(LogLevel logLevel) => true;

    public void Log<TState>(
        LogLevel logLevel,
        EventId eventId,
        TState state,
        Exception? exception,
        Func<TState, Exception?, string> formatter)
    {
        Lines.Add($"{logLevel}: {formatter(state, exception)}");
    }
}
