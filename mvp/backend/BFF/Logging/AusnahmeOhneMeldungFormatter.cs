using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Logging.Console;

namespace BFF.Logging;

/// <summary>
/// Konsolenausgabe wie der Standardformatter "simple", aber Ausnahmen ohne ihre Meldung
/// (#422). Die Meldung traegt oft, was hereinkam: ein Formatfehler den Wert, eine
/// ungueltige Adresse die Adresse. Typ und Stack reichen, um den Fehler zu finden. Das
/// Gegenstueck im Semantic-Service ist ausnahme_ohne_meldung() in app/core/logging.py.
///
/// Zeitstempel und Scopes schreibt er nicht; die Optionen dafuer
/// (Logging:Console:FormatterOptions) bleiben ohne Wirkung, wie bisher beim
/// Standardformatter ohne sie.
/// </summary>
public sealed class AusnahmeOhneMeldungFormatter : ConsoleFormatter
{
    public const string Name = "ohne-ausnahmemeldung";

    private const string Einzug = "      ";

    public AusnahmeOhneMeldungFormatter()
        : base(Name)
    {
    }

    public override void Write<TState>(
        in LogEntry<TState> logEntry,
        IExternalScopeProvider? scopeProvider,
        TextWriter textWriter)
    {
        // Ohne Ausnahme formatiert: ein Formatter, der sie in den Text zieht, kaeme
        // sonst an der Regel vorbei.
        var text = logEntry.Formatter(logEntry.State, null);
        if (text is null && logEntry.Exception is null)
        {
            return;
        }

        textWriter.Write(Stufe(logEntry.LogLevel));
        textWriter.Write(": ");
        textWriter.Write(logEntry.Category);
        textWriter.Write('[');
        textWriter.Write(logEntry.EventId.Id);
        textWriter.WriteLine(']');
        if (!string.IsNullOrEmpty(text))
        {
            textWriter.Write(Einzug);
            textWriter.WriteLine(text.Replace(Environment.NewLine, Environment.NewLine + Einzug));
        }

        if (logEntry.Exception is not null)
        {
            textWriter.WriteLine(OhneMeldung(logEntry.Exception));
        }
    }

    /// <summary>Typ und Stack der Ausnahme und ihrer inneren Ausnahmen, ohne Meldungen.</summary>
    public static string OhneMeldung(Exception ausnahme)
    {
        var text = new StringBuilder();
        Anhaengen(text, ausnahme, 0);
        return text.ToString().TrimEnd();
    }

    private static void Anhaengen(StringBuilder text, Exception ausnahme, int tiefe)
    {
        if (tiefe > 0)
        {
            text.Append(" ---> ");
        }

        text.Append(ausnahme.GetType().FullName).AppendLine(" (Meldung nicht protokolliert)");

        // Wie Exception.ToString(): erst die inneren Ausnahmen samt Stack, dann die
        // Marke, dann der eigene Stack.
        IReadOnlyList<Exception> innere = ausnahme is AggregateException gesammelt
            ? gesammelt.InnerExceptions
            : ausnahme.InnerException is null ? [] : [ausnahme.InnerException];
        foreach (var innen in innere)
        {
            Anhaengen(text, innen, tiefe + 1);
            text.AppendLine("   --- End of inner exception stack trace ---");
        }

        if (ausnahme.StackTrace is not null)
        {
            text.AppendLine(ausnahme.StackTrace);
        }
    }

    private static string Stufe(LogLevel stufe) => stufe switch
    {
        LogLevel.Trace => "trce",
        LogLevel.Debug => "dbug",
        LogLevel.Information => "info",
        LogLevel.Warning => "warn",
        LogLevel.Error => "fail",
        LogLevel.Critical => "crit",
        _ => stufe.ToString(),
    };
}

public static class AusnahmeOhneMeldungLogging
{
    /// <summary>
    /// Konsole mit <see cref="AusnahmeOhneMeldungFormatter"/>. Gesetzt im Code nach der
    /// Konfiguration, sodass ein Logging__Console__FormatterName von aussen ihn nicht
    /// ersetzt.
    /// </summary>
    public static ILoggingBuilder AddKonsoleOhneAusnahmemeldung(this ILoggingBuilder builder)
    {
        builder.AddConsole(optionen => optionen.FormatterName = AusnahmeOhneMeldungFormatter.Name);
        builder.AddConsoleFormatter<AusnahmeOhneMeldungFormatter, ConsoleFormatterOptions>();
        return builder;
    }
}
