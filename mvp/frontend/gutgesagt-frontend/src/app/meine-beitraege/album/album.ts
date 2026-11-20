import { KartenDaten, ausBeitrag } from '../../beitragskarte/karten-daten';
import { ContentResult } from '../../services/dtos/contributionDtos';
import { Thema } from '../../services/dtos/themenDtos';
import { Meilenstein } from '../../services/usage-tracking.service';
import { STIL_LABEL, Stil } from '../../shared/zweck-stil';

/**
 * Das Album in „Meine Beiträge“ (Variante A „Album nach Thema“, Entscheidung 20.11.):
 * die eigenen Beiträge in Abschnitten je Thema der Aussage, auf die sie antworten,
 * meistgenutzte zuerst. Hier steht nur die Rechnung, ohne Angular; die Seite zeigt sie.
 *
 * Eine Aussage hat bis zu drei Themen. Ein Beitrag steht deshalb in jedem Abschnitt,
 * dessen Thema seine Aussage trägt: Wer „Wohnen“ aufklappt, erwartet dort alles zu
 * Wohnen, auch wenn dieselbe Aussage zugleich unter „Soziales“ steht. Eine erste oder
 * Hauptzuordnung gibt es nicht (die Themen einer Aussage sind gleichrangig, ihre
 * Reihenfolge ist die der Liste), jede Auswahl wäre also willkürlich. Gezählt wird
 * trotzdem jeder Beitrag einmal: der Deckel oben, die Trefferzahl und die Filter
 * zählen Beiträge, nicht Karten; nur die Zahlen im Abschnittskopf gelten dem Abschnitt.
 */

/** Der Abschnitt für Beiträge ohne Thema (oder ohne sichtbare Aussage); er steht zuletzt. */
export const OHNE_THEMA: Thema = { schluessel: 'ohne-thema', name: 'Ohne Thema', motiv: 'themen/ohne-thema.svg' };

/** Bis zu so vielen Beiträgen keine Suche und keine Filter (Entscheidung 20.11.). */
export const SUCHE_AB = 7;

/** Bis zu so vielen Beiträgen keine Abschnitte: Drei Karten in drei Abschnitten wären nur Gliederung. */
export const ABSCHNITTE_AB = 4;

/**
 * So viele Karten zeigt ein aufgeklappter Abschnitt, der Rest kommt mit „Alle N zeigen“.
 * Ein Abschnitt mit höchstens zwei mehr zeigt gleich alle, sonst stünde der Knopf für
 * eine einzelne Karte da.
 */
export const KARTEN_JE_ABSCHNITT = 6;

export interface AlbumEintrag {
  karte: KartenDaten;
  /** Die Themen der beantworteten Aussage; leer heißt „Ohne Thema“. */
  themen: Thema[];
  stil: Stil | null;
  /** Kleingeschrieben, ohne Akzente: alles, worin die Suche findet. */
  suchtext: string;
}

export interface AlbumFilter {
  suche: string;
  /** Schlüssel eines Themas oder OHNE_THEMA.schluessel; null = alle. */
  thema: string | null;
  stil: Stil | null;
  nurGenutzt: boolean;
}

export const KEIN_FILTER: AlbumFilter = { suche: '', thema: null, stil: null, nurGenutzt: false };

export interface AlbumAbschnitt {
  thema: Thema;
  eintraege: AlbumEintrag[];
  /** Wie viele Beiträge des Abschnitts mindestens einmal genutzt wurden. */
  genutzt: number;
}

export interface AlbumKennzahlen {
  beitraege: number;
  /** Summe der Nutzung aller Beiträge. */
  nutzung: number;
  /** Davon in den letzten 7 Tagen. */
  dieseWoche: number;
  /** Verschiedene Themen; „Ohne Thema“ zählt nicht. */
  themen: number;
}

export interface Auswahl<T> {
  wert: T;
  name: string;
  anzahl: number;
}

/** Für die Suche: klein, ohne Akzente und mit ss statt ß, damit „warme“ auch „wärme“ findet. */
export function suchform(text: string): string {
  return text
    .toLocaleLowerCase('de-DE')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/ß/g, 'ss');
}

/** Ein Beitrag aus der Antwort als Eintrag: Karte mit „Antwort auf“, Themen, Stil, Suchtext. */
export function albumEintrag(eintrag: ContentResult): AlbumEintrag {
  const karte = ausBeitrag(eintrag);
  const aussage = eintrag.aussage ?? null;
  if (aussage?.text) {
    // Nur der Text: die Werte der Suche gibt es hier nicht, die Karte zeigt sie im Album nicht.
    karte.statement = { text: aussage.text, aehnlichkeit: 0, antwortqualitaet: 0 };
  }
  const themen = aussage?.themen ?? [];
  const stil = karte.extra?.stil ?? null;
  const teile = [
    karte.titel,
    karte.text,
    karte.extra?.kurz,
    karte.extra?.lang,
    aussage?.text,
    stil ? STIL_LABEL[stil] : null,
    ...themen.map((t) => t.name),
  ];
  return { karte, themen, stil, suchtext: suchform(teile.filter((t) => !!t).join(' ')) };
}

export function filterAktiv(filter: AlbumFilter): boolean {
  return !!filter.suche.trim() || filter.thema !== null || filter.stil !== null || filter.nurGenutzt;
}

function genutzt(eintrag: AlbumEintrag): boolean {
  return (eintrag.karte.nutzung ?? 0) > 0;
}

function hatThema(eintrag: AlbumEintrag, schluessel: string): boolean {
  return schluessel === OHNE_THEMA.schluessel
    ? eintrag.themen.length === 0
    : eintrag.themen.some((t) => t.schluessel === schluessel);
}

/** Jedes Wort der Suche muss vorkommen, in beliebiger Reihenfolge. */
export function filtern(eintraege: AlbumEintrag[], filter: AlbumFilter): AlbumEintrag[] {
  const woerter = suchform(filter.suche).split(/\s+/).filter((w) => !!w);
  return eintraege.filter(
    (e) =>
      (filter.thema === null || hatThema(e, filter.thema)) &&
      (filter.stil === null || e.stil === filter.stil) &&
      (!filter.nurGenutzt || genutzt(e)) &&
      woerter.every((w) => e.suchtext.includes(w)),
  );
}

/** Meistgenutzte zuerst, bei gleicher Nutzung die neuesten. */
export function nachNutzung(eintraege: AlbumEintrag[]): AlbumEintrag[] {
  return [...eintraege].sort(
    (a, b) =>
      (b.karte.nutzung ?? 0) - (a.karte.nutzung ?? 0) || b.karte.erstellt.localeCompare(a.karte.erstellt),
  );
}

/**
 * Die Abschnitte: je Thema die Beiträge, deren Aussage es trägt, darin meistgenutzte
 * zuerst. Abschnitte mit mehr genutzten Beiträgen stehen weiter oben, bei Gleichstand
 * die größeren, dann in der Reihenfolge der Themenliste; „Ohne Thema“ immer zuletzt.
 */
export function abschnitte(eintraege: AlbumEintrag[]): AlbumAbschnitt[] {
  const jeThema = new Map<string, { thema: Thema; eintraege: AlbumEintrag[] }>();
  const ohne: AlbumEintrag[] = [];
  for (const eintrag of eintraege) {
    if (!eintrag.themen.length) {
      ohne.push(eintrag);
    }
    for (const thema of eintrag.themen) {
      const gruppe = jeThema.get(thema.schluessel) ?? { thema, eintraege: [] };
      gruppe.eintraege.push(eintrag);
      jeThema.set(thema.schluessel, gruppe);
    }
  }
  const abschnitt = (thema: Thema, liste: AlbumEintrag[]): AlbumAbschnitt => ({
    thema,
    eintraege: nachNutzung(liste),
    genutzt: liste.filter(genutzt).length,
  });
  const mitThema = [...jeThema.values()]
    .map((g) => abschnitt(g.thema, g.eintraege))
    .sort((a, b) => b.genutzt - a.genutzt || b.eintraege.length - a.eintraege.length);
  return ohne.length ? [...mitThema, abschnitt(OHNE_THEMA, ohne)] : mitThema;
}

export function kennzahlen(eintraege: AlbumEintrag[]): AlbumKennzahlen {
  const themen = new Set(eintraege.flatMap((e) => e.themen.map((t) => t.schluessel)));
  return {
    beitraege: eintraege.length,
    nutzung: eintraege.reduce((summe, e) => summe + (e.karte.nutzung ?? 0), 0),
    dieseWoche: eintraege.reduce((summe, e) => summe + (e.karte.nutzungLetzte7Tage ?? 0), 0),
    themen: themen.size,
  };
}

/** Die Themen zur Wahl im Filter, mit Zahl der Beiträge, wie die Abschnitte geordnet. */
export function themenAuswahl(eintraege: AlbumEintrag[]): Auswahl<string>[] {
  return abschnitte(eintraege).map((a) => ({ wert: a.thema.schluessel, name: a.thema.name, anzahl: a.eintraege.length }));
}

/** Die Stile zur Wahl, nur die vorkommenden, in der Reihenfolge des Formulars. */
export function stilAuswahl(eintraege: AlbumEintrag[]): Auswahl<Stil>[] {
  return (Object.keys(STIL_LABEL) as Stil[])
    .map((stil) => ({ wert: stil, name: STIL_LABEL[stil], anzahl: eintraege.filter((e) => e.stil === stil).length }))
    .filter((a) => a.anzahl > 0);
}

/** „5 von 25 genutzt“ für den Abschnittskopf; ohne Nutzung „noch keiner genutzt“. */
export function abschnittStand(abschnitt: AlbumAbschnitt): string {
  const anzahl = abschnitt.eintraege.length;
  const beitraege = anzahl === 1 ? '1 Beitrag' : `${anzahl} Beiträge`;
  return abschnitt.genutzt ? `${abschnitt.genutzt} von ${anzahl} genutzt` : `${beitraege} · noch keiner genutzt`;
}

/**
 * Der Meilenstein im Deckel: der offene, dem man am nächsten ist (Anteil von Stand an
 * Schwelle). Bei Gleichstand einer der Wirkung (Nutzung, Zustimmung), denn ohne Nutzung
 * ersetzt er „0× genutzt“; sonst die Reihenfolge der Liste. Nach Listenreihenfolge allein
 * stünde bei 244 Beiträgen oft „Erster Einwurf 0 von 1“ oben, was mit dem Album nichts zu tun hat.
 */
export function naechsterMeilenstein(meilensteine: Meilenstein[]): Meilenstein | null {
  const anteil = (m: Meilenstein) => (m.schwelle > 0 ? m.stand / m.schwelle : 0);
  const offen = meilensteine.filter((m) => !m.erreicht);
  return offen.reduce<Meilenstein | null>((bester, m) => {
    if (!bester) {
      return m;
    }
    const unterschied = anteil(m) - anteil(bester);
    if (unterschied > 0) {
      return m;
    }
    return unterschied === 0 && m.art === 'wirkung' && bester.art !== 'wirkung' ? m : bester;
  }, null);
}
