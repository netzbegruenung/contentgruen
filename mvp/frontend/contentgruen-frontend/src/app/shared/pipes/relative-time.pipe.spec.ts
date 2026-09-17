import { RelativeTimePipe } from './relative-time.pipe';

/**
 * Das Backend liefert Zeitstempel mit Offset (UTC). Ein naiver Altwert und ein neuer
 * Wert kommen dort als dieselbe Zeichenkette mit "Z" an - hier zaehlt, dass die
 * Anzeige dann stimmt, auch wenn der Browser nicht in UTC laeuft.
 */
describe('RelativeTimePipe', () => {
  const pipe = new RelativeTimePipe();

  function vor(minuten: number): Date {
    return new Date(Date.now() - minuten * 60_000);
  }

  it('zeigt einen eben gespeicherten Beitrag mit UTC-Offset als "vor wenigen Sekunden"', () => {
    const utc = new Date().toISOString(); // "...Z", wie das Backend jetzt ausliefert
    expect(pipe.transform(utc)).toBe('vor wenigen Sekunden');
  });

  it('zeigt "Z" und "+00:00" gleich an', () => {
    const zeit = vor(5).toISOString();
    const mitOffset = zeit.replace('Z', '+00:00');
    expect(pipe.transform(zeit)).toBe('vor 5 Minuten');
    expect(pipe.transform(mitOffset)).toBe(pipe.transform(zeit));
  });
});
