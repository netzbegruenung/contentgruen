import { ersteAdresse, trackingParameterEntfernen, urlsInTextBereinigen } from './url-bereinigen';

describe('trackingParameterEntfernen', () => {
  it('entfernt das stkn von Instagram und laesst das Fragezeichen nicht stehen', () => {
    // Genau die Adresse aus dem Geraete-Test.
    expect(
      trackingParameterEntfernen(
        'https://www.instagram.com/reel/DdGvZ__grj9/?stkn=MWxkZmRocDVzZXpubg==',
      ),
    ).toBe('https://www.instagram.com/reel/DdGvZ__grj9/');
  });

  it('entfernt igsh, igshid und fbclid', () => {
    expect(trackingParameterEntfernen('https://example.org/a?igsh=1')).toBe('https://example.org/a');
    expect(trackingParameterEntfernen('https://example.org/a?igshid=1')).toBe(
      'https://example.org/a',
    );
    expect(trackingParameterEntfernen('https://example.org/a?fbclid=1')).toBe(
      'https://example.org/a',
    );
  });

  it('entfernt jeden utm_-Parameter', () => {
    expect(
      trackingParameterEntfernen(
        'https://example.org/a?utm_source=x&utm_medium=y&utm_campaign=z',
      ),
    ).toBe('https://example.org/a');
  });

  it('behaelt inhaltliche Parameter und entfernt nur das Tracking daneben', () => {
    expect(trackingParameterEntfernen('https://example.org/suche?q=waermepumpe&utm_source=x')).toBe(
      'https://example.org/suche?q=waermepumpe',
    );
  });

  it('laesst eine Adresse ohne Tracking voellig unveraendert', () => {
    // Auch die Kodierung darf sich nicht aendern: kein Umweg ueber URLSearchParams,
    // wenn es nichts zu entfernen gibt.
    const unveraendert = 'https://example.org/a?b=1&c=%C3%A4%20%2B';
    expect(trackingParameterEntfernen(unveraendert)).toBe(unveraendert);
  });

  it('behaelt das Fragment', () => {
    expect(trackingParameterEntfernen('https://example.org/a?utm_source=x#abschnitt')).toBe(
      'https://example.org/a#abschnitt',
    );
  });

  it('gibt zurueck, was es nicht als Adresse versteht, statt zu werfen', () => {
    expect(trackingParameterEntfernen('kein Link')).toBe('kein Link');
    expect(trackingParameterEntfernen('')).toBe('');
  });

  it('vergleicht Parameternamen ohne Ruecksicht auf Gross- und Kleinschreibung', () => {
    expect(trackingParameterEntfernen('https://example.org/a?UTM_Source=x&FBCLID=y')).toBe(
      'https://example.org/a',
    );
  });

  describe('YouTube', () => {
    it('entfernt si und feature auf youtube.com und behaelt v und t', () => {
      expect(
        trackingParameterEntfernen('https://youtube.com/watch?v=abc123&si=XyZ&feature=shared&t=42'),
      ).toBe('https://youtube.com/watch?v=abc123&t=42');
    });

    it('entfernt pp und is auch auf Subdomains wie www. und m.', () => {
      expect(trackingParameterEntfernen('https://www.youtube.com/watch?v=abc123&pp=ygUE')).toBe(
        'https://www.youtube.com/watch?v=abc123',
      );
      expect(trackingParameterEntfernen('https://m.youtube.com/watch?v=abc123&is=1')).toBe(
        'https://m.youtube.com/watch?v=abc123',
      );
    });

    it('entfernt si auf youtu.be und laesst kein Fragezeichen stehen', () => {
      expect(trackingParameterEntfernen('https://youtu.be/abc123?si=XyZ')).toBe(
        'https://youtu.be/abc123',
      );
    });

    it('laesst si, is, feature und pp auf anderen Hosts stehen', () => {
      const fremd = 'https://example.org/a?si=1&is=2&feature=3&pp=4';
      expect(trackingParameterEntfernen(fremd)).toBe(fremd);
      const aehnlich = 'https://notyoutube.com/watch?v=abc123&si=XyZ';
      expect(trackingParameterEntfernen(aehnlich)).toBe(aehnlich);
    });
  });
});

describe('urlsInTextBereinigen', () => {
  it('bereinigt eine Adresse mitten im Text', () => {
    expect(
      urlsInTextBereinigen('Schau mal https://www.instagram.com/reel/ABC/?stkn=xy an'),
    ).toBe('Schau mal https://www.instagram.com/reel/ABC/ an');
  });

  it('bereinigt mehrere Adressen im selben Text', () => {
    expect(
      urlsInTextBereinigen('https://a.example/?utm_source=x und https://b.example/?fbclid=y'),
    ).toBe('https://a.example/ und https://b.example/');
  });

  it('laesst Text ohne Adresse unangetastet', () => {
    expect(urlsInTextBereinigen('nur ein Gedanke')).toBe('nur ein Gedanke');
    expect(urlsInTextBereinigen('')).toBe('');
  });
});

describe('ersteAdresse', () => {
  it('findet die erste Adresse mitten im Text', () => {
    expect(ersteAdresse('Schau mal https://example.org/a und https://example.org/b')).toBe(
      'https://example.org/a',
    );
  });

  it('liefert null ohne Adresse', () => {
    expect(ersteAdresse('nur ein Gedanke')).toBeNull();
    expect(ersteAdresse('')).toBeNull();
    expect(ersteAdresse(null)).toBeNull();
  });
});
