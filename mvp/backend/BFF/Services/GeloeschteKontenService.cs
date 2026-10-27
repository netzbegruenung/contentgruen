namespace BFF.Services;

/// <summary>
/// Die Kennungen geloeschter Konten, deren Anmelde-Cookie das BFF nicht mehr annimmt (#278).
///
/// Gebraucht fuer den Netzbegruenung-Login: Das Cookie traegt nur die Keycloak-Claims, keine
/// Tokens (Program.cs, SaveTokens), und das BFF kann Keycloak nicht fragen, ob ein Konto noch
/// besteht. Wer ein Konto nach dem Loeschkonzept loescht, traegt dessen Kennung hier ein; die
/// naechste Anfrage mit dem alten Cookie wird abgewiesen. Ein Beta-Zugang braucht die Liste
/// nicht, dort genuegt es, ihn aus managed-users.json zu entfernen (KontoPruefung).
///
/// Format: eine Kennung je Zeile, Leerzeilen und Zeilen mit '#' am Anfang zaehlen nicht. Eine
/// fehlende Datei ist der Normalfall und heisst: kein Konto eingetragen. Ein Eintrag wird nach
/// 14 Tagen ueberfluessig, sobald auch das Keycloak-Konto geloescht ist -- laenger lebt kein
/// Cookie ohne Anfrage, und jede Anfrage danach wird abgewiesen --, und soll dann wieder
/// heraus (docs/LOESCHKONZEPT.md, "Vorab: Sitzung beenden").
/// </summary>
public class GeloeschteKontenService
{
    private const string DefaultPath = "/config/geloeschte-konten.txt";

    private readonly ILogger<GeloeschteKontenService> _logger;
    private readonly string _path;
    private readonly TimeProvider _time;
    // Wie managed-users.json: nach einer Aenderung spaetestens nach fuenf Minuten, nach einem
    // Neustart sofort.
    private readonly TimeSpan _cacheExpiry = TimeSpan.FromMinutes(5);
    private HashSet<string>? _kennungen;
    private DateTimeOffset _lastLoadTime = DateTimeOffset.MinValue;

    public GeloeschteKontenService(
        ILogger<GeloeschteKontenService> logger,
        IConfiguration configuration,
        TimeProvider? timeProvider = null)
    {
        _logger = logger;
        var path = configuration["GELOESCHTE_KONTEN_PATH"];
        _path = string.IsNullOrWhiteSpace(path) ? DefaultPath : path.Trim();
        _time = timeProvider ?? TimeProvider.System;
    }

    public async Task<bool> IstGeloeschtAsync(string? kennung)
    {
        if (string.IsNullOrEmpty(kennung))
        {
            return false;
        }

        var kennungen = await LoadAsync();
        return kennungen.Contains(kennung);
    }

    private async Task<HashSet<string>> LoadAsync()
    {
        var now = _time.GetUtcNow();
        if (_kennungen != null && now - _lastLoadTime < _cacheExpiry)
        {
            return _kennungen;
        }

        if (!File.Exists(_path))
        {
            _kennungen = new HashSet<string>(StringComparer.Ordinal);
            _lastLoadTime = now;
            return _kennungen;
        }

        try
        {
            var lines = await File.ReadAllLinesAsync(_path);
            _kennungen = lines
                .Select(l => l.Trim())
                .Where(l => l.Length > 0 && !l.StartsWith('#'))
                .ToHashSet(StringComparer.Ordinal);
            _lastLoadTime = now;

            // Nur die Anzahl: die Kennungen sind personenbezogen. Wer nach einer Loeschung
            // prueft, ob das BFF die Datei liest, sieht hier die Zahl steigen.
            _logger.LogInformation("Loaded {Count} deleted accounts from {Path}", _kennungen.Count, _path);
            return _kennungen;
        }
        catch (Exception ex)
        {
            // Eine eben gelesene Liste bleibt gueltig: eine halb geschriebene oder kurz
            // gesperrte Datei darf keine Eintraege verlieren. Neuer Versuch erst nach Ablauf
            // des Caches, sonst schriebe jede angemeldete Anfrage diesen Fehler ins Log.
            _logger.LogError(ex, "Failed to read deleted accounts from {Path}", _path);
            _kennungen ??= new HashSet<string>(StringComparer.Ordinal);
            _lastLoadTime = now;
            return _kennungen;
        }
    }
}
