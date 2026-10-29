/**
 * Eine der Laengen eines Kommentars (GLOSSARY.md): Mittel ist der Haupttext, Kurz
 * und Lang sind optional. Kopiert und gezaehlt wird je Fassung (#355); die Werte
 * sind dieselben wie im Backend (`Fassung` in domain/models/commentary.py).
 */
export type Fassung = 'kurz' | 'mittel' | 'lang';

/** In der Reihenfolge der Reiter auf der Karte. */
export const FASSUNGEN: readonly Fassung[] = ['kurz', 'mittel', 'lang'];

export const FASSUNG_LABEL: Record<Fassung, string> = { kurz: 'Kurz', mittel: 'Mittel', lang: 'Lang' };

/** Nutzung einer Fassung und ihr Zuwachs der letzten 7 Tage, aus "Meine Beitraege". */
export interface FassungsNutzung {
  nutzung: number;
  letzte_7_tage: number;
}

/** Nur die Fassungen, die der Kommentar hat. */
export type NutzungJeFassung = Partial<Record<Fassung, FassungsNutzung>>;
