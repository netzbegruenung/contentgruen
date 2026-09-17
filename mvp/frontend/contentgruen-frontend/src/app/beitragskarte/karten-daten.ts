import { BaseContentResult, BaseSearchResult, ContentReference } from '../services/dtos/commonDtos';
import { ContentResult } from '../services/dtos/contributionDtos';
import { RawInput } from '../services/raw-input.service';
import { CONTENT_TYPE_REGISTRY, resolveContentType } from '../shared/content-type-registry';
import { plattformAusUrl, plattformName } from '../shared/plattform';

/**
 * Was eine Beitragskarte anzeigt, unabhaengig davon, woher die Daten kommen.
 *
 * Drei Quellen liefern verschieden geformte Daten: die Suche (und /recent) ein
 * Paket mit genau einem `*_result`, "Meine Beitraege" einen flachen Eintrag, der
 * Fangkorb einen Einwurf mit Saetzen und Verknuepfungen. Die Adapter unten bringen
 * alle drei auf diese eine Form; die Karte kennt keine der Quellen.
 */
export type KartenVariante = 'voll' | 'kompakt' | 'rohling' | 'kopf';

/**
 * Was eine Rohling-Karte anbietet: der eine Primaerknopf im Fuss und die
 * Eintraege im ⋮-Menue. Wohin das fuehrt, entscheidet die Seite, nicht die Karte.
 */
export type RohlingAktion =
  | 'destillieren'
  | 'ausformulieren'
  | 'ansehen'
  | 'weiterDestillieren'
  | 'linkKopieren'
  | 'verwerfen';

export interface KartenQuelle {
  id: string;
  url?: string;
  beschreibung?: string;
}

export interface KartenStatement {
  text: string;
  /** Prozent, 0-100. */
  aehnlichkeit: number;
  /** Prozent, 0-100. */
  antwortqualitaet: number;
}

/** Felder, die nur ein Typ hat. */
export interface KartenExtra {
  kurz?: string;
  lang?: string;
  plattform?: string;
  postAutor?: string;
  postUrl?: string;
  engagement?: number;
}

/** Ein Satz zum Einwurf, mit der Zahl der daraus entstandenen Beitraege. */
export interface RohlingSatz {
  id: string;
  text: string;
  /** 0 heisst Entwurf; sonst die Zahl der Beitraege aus genau diesem Satz. */
  beitraege: number;
}

/** Ein Beitrag aus dem Einwurf - was das Sheet braucht, um ihn nachzuladen. */
export interface RohlingBeitrag {
  contentId: string;
  /** Registry-Schluessel; null bei Verknuepfungen aus der Zeit vor Fangkorb v2. */
  typ: string | null;
  /** Der ausformulierte Satz als Beschriftung; null, wenn er spaeter geleert wurde. */
  satz: string | null;
}

export interface RohlingDaten {
  einwurfId: string;
  zustand: FangkorbZustand;
  /** Marke links in der Link-Zeile: Plattformname, sonst die Domain. */
  herkunft: string | null;
  /** Ziel der Link-Zeile: der Link, sonst die Bildadresse. */
  link: string | null;
  /** Der Link, wie er dasteht: ohne Schema und www, Domain und Pfad. */
  linkText: string | null;
  /** Alle Saetze, aelteste Aenderung zuerst. */
  saetze: RohlingSatz[];
  /** Die entstandenen Beitraege, aelteste zuerst. */
  beitraege: RohlingBeitrag[];
  /** Nur im Kopf: der Satz, aus dem gerade ein Beitrag entsteht. */
  kopfSatz?: string;
  /** Verworfen werden darf nur, was offen oder destilliert ist - und nur vom Einwerfer. */
  verwerfbar: boolean;
}

export interface KartenDaten {
  /** Content-ID; beim Rohling die ID des Einwurfs bzw. des Satzes. */
  id: string;
  /** Registry-Schluessel ('generictext'), null ohne Beitrag oder bei unbekanntem Typ. */
  typ: string | null;
  /** Die Behauptung; null auf der Einwurf-Karte. */
  titel: string | null;
  text: string | null;
  erstellt: string;
  /** Keycloak-Kennung. */
  autor: string | null;
  /** Anzeigename; in diesem Paket immer null, ein spaeteres Paket fuellt ihn. */
  autorName: string | null;
  /** Verwendungen; null = unbekannt, dann kein Badge. */
  nutzung: number | null;
  quellen: KartenQuelle[];
  bildUrl?: string;
  statement?: KartenStatement;
  stimme?: 'like' | 'dislike';
  extra?: KartenExtra;
  rohling?: RohlingDaten;
}

// Suchergebnis und /recent

type Suchpaket = BaseSearchResult & { content_type?: string; result_type?: string } & Record<string, any>;

/**
 * Ein Paket aus Suche, /recent oder Formular-Vorschau. Der Typ kommt aus einem
 * expliziten content_type/result_type, sonst aus dem vorhandenen `*_result`-Feld.
 */
export function ausSuchergebnis(paket: Suchpaket): KartenDaten {
  const typ = typAusPaket(paket);
  const feld = typ ? CONTENT_TYPE_REGISTRY[typ].resultField : undefined;
  const inhalt: BaseContentResult & Record<string, any> = (feld && paket[feld]) || {};

  return {
    id: inhalt.id,
    typ,
    titel: inhalt.title ?? null,
    text: inhalt.text ?? null,
    erstellt: inhalt.created,
    autor: inhalt.original_author ?? null,
    autorName: null,
    nutzung: inhalt.usage_count ?? 0,
    quellen: (inhalt.references ?? []).map(quelle),
    bildUrl: inhalt['image_url'] || undefined,
    statement: statement(paket),
    stimme: paket.user_vote === 'like' || paket.user_vote === 'dislike' ? paket.user_vote : undefined,
    extra: extra(typ, inhalt),
  };
}

function typAusPaket(paket: Suchpaket): string | null {
  const explizit = resolveContentType(paket.content_type ?? paket.result_type);
  if (explizit && CONTENT_TYPE_REGISTRY[explizit].resultField) {
    return explizit;
  }
  const passend = Object.values(CONTENT_TYPE_REGISTRY).find(
    (config) => config.resultField && paket[config.resultField],
  );
  if (!passend) {
    console.warn('[karten-daten] ausSuchergebnis: kein bekanntes Ergebnisfeld', paket);
  }
  return passend?.key ?? null;
}

function quelle(referenz: ContentReference): KartenQuelle {
  return {
    id: referenz.reference_id,
    url: referenz.reference_text || undefined,
    beschreibung: referenz.reference_description || undefined,
  };
}

function statement(paket: Suchpaket): KartenStatement | undefined {
  const text = paket.statement_text?.trim();
  if (!text) {
    return undefined;
  }
  return {
    text,
    aehnlichkeit: Math.round((paket.statement_similarity_score ?? 0) * 100),
    antwortqualitaet: Math.round((paket.reply_relevance ?? 0) * 100),
  };
}

function befuellt(wert: unknown): string | undefined {
  return typeof wert === 'string' && wert.trim() ? wert : undefined;
}

function extra(typ: string | null, inhalt: Record<string, any>): KartenExtra | undefined {
  if (typ === 'commentary') {
    // Nur befuellte Fassungen: sonst zeigte die Karte einen Umschalter ohne Wirkung.
    return { kurz: befuellt(inhalt['short_text']), lang: befuellt(inhalt['long_text']) };
  }
  if (typ === 'post') {
    return {
      plattform: inhalt['platform'] || undefined,
      postAutor: inhalt['author'] || undefined,
      postUrl: inhalt['url'] || undefined,
      engagement: inhalt['engagement'] ?? undefined,
    };
  }
  return undefined;
}

// Meine Beitraege

/**
 * Ohne Text zeigt die Album-Karte den Titel; fehlt auch der, die Domain der
 * Bildadresse, damit ein Bild ohne Unterschrift nicht als leere Karte erscheint.
 * Der Text selbst bleibt leer, sonst stuende der Titel im Album doppelt da.
 */
export function ausBeitrag(eintrag: ContentResult): KartenDaten {
  return {
    id: eintrag.id,
    typ: resolveContentType(eintrag.content_type) ?? null,
    titel: eintrag.title || (eintrag.text ? null : domainAus(eintrag.image_url)),
    text: eintrag.text ?? null,
    erstellt: eintrag.created,
    autor: eintrag.original_author ?? null,
    autorName: null,
    nutzung: eintrag.usage_count ?? 0,
    quellen: (eintrag.references ?? []).map(quelle),
    bildUrl: eintrag.image_url || undefined,
  };
}

/**
 * Die Adresse, wie sie in der Link-Zeile steht: Domain und Pfad, ohne Schema und
 * ohne www. Abfrage und Fragment bleiben weg - sie kosten die halbe Zeile und
 * sagen selten etwas. Was sich nicht als Adresse lesen laesst, faellt weg.
 */
function adresseKurz(adresse: string | null | undefined): string | null {
  if (!adresse) {
    return null;
  }
  try {
    const url = new URL(adresse);
    const pfad = url.pathname === '/' ? '' : url.pathname.replace(/\/$/, '');
    return `${url.hostname.replace(/^www\./, '')}${pfad}` || null;
  } catch {
    return null;
  }
}

function domainAus(adresse: string | null | undefined): string | null {
  if (!adresse) {
    return null;
  }
  try {
    return new URL(adresse).hostname.replace(/^www\./, '') || null;
  } catch {
    return null;
  }
}

// Fangkorb

/**
 * Woran ein Einwurf gerade ist - zugleich die drei Tabs des Fangkorbs und der
 * vierte Zustand, der hinter einem Chip unter "Erledigt" liegt.
 */
export type FangkorbZustand = 'destillieren' | 'ausformulieren' | 'erledigt' | 'verworfen';

/**
 * Den Bearbeitungsstand eines Einwurfs bestimmen.
 *
 * Verworfen zuerst: Verworfenes bleibt verworfen, auch wenn andere trotzdem
 * weiterdestillieren (das Backend erlaubt das ausdruecklich). Erledigt haengt an
 * den Verknuepfungen, nicht an den Saetzen - ein Beitrag kann auch ohne
 * gespeicherten Satz entstanden sein (processed aus open), und ein spaeter
 * geleerter Satz darf den Einwurf nicht zurueckfallen lassen.
 */
export function zustandVonEinwurf(einwurf: RawInput): FangkorbZustand {
  if (einwurf.status === 'discarded') {
    return 'verworfen';
  }
  if ((einwurf.links ?? []).length > 0) {
    return 'erledigt';
  }
  return (einwurf.drafts ?? []).length > 0 ? 'ausformulieren' : 'destillieren';
}

/**
 * Ein Einwurf als eine Karte: Herkunft im Kopf, der Inhalt als Titel, die Saetze
 * innen.
 *
 * Titel ist, was jemand mitgegeben hat - die Notiz, sonst nichts: Ohne Notiz ist
 * die Link-Zeile die Aufschrift der Karte. Die Adresse steht dort gekuerzt
 * (Domain und Pfad, ohne Schema und www), nicht als roher Link.
 *
 * ``beitraege`` je Satz zaehlt die Verknuepfungen auf genau diesen Satz - dieselbe
 * Person kann aus ihrem Satz mehr als einen Beitrag gemacht haben. Verknuepfungen
 * ohne Satz (verarbeitet ohne gespeicherten Satz, oder der Satz wurde spaeter
 * geleert) haengen an keiner Zeile, bleiben aber unter ``beitraege`` erreichbar -
 * sichtbar werden sie im Sheet.
 */
export function ausEinwurf(einwurf: RawInput): KartenDaten {
  const links = einwurf.links ?? [];
  const adresse = einwurf.url ?? einwurf.image_url;
  const zustand = zustandVonEinwurf(einwurf);
  const saetze: RohlingSatz[] = (einwurf.drafts ?? []).map((satz) => ({
    id: satz.id,
    text: satz.sentence,
    beitraege: links.filter((link) => link.draft_id === satz.id).length,
  }));

  return {
    id: einwurf.id,
    // Erledigt traegt die Farbe des ersten entstandenen Beitrags: Die Typklasse
    // setzt --karten-farbe, und davon nimmt das Kopfband. Unfertige Rohlinge
    // haben keinen Typ - ihr Band bleibt Sand.
    // Die erste Verknuepfung *mit* Typ: Verknuepfungen aus der Zeit vor Fangkorb v2
    // tragen keinen, und stuende so eine vorn, blieben Band und Emoji farblos,
    // obwohl ein typisierter Beitrag daneben liegt.
    typ:
      zustand === 'erledigt'
        ? (links.map((link) => resolveContentType(link.content_type)).find(Boolean) ?? null)
        : null,
    titel: hinweis(einwurf),
    text: null,
    erstellt: einwurf.created_at,
    autor: einwurf.submitted_by,
    autorName: null,
    nutzung: null,
    quellen: [],
    rohling: {
      einwurfId: einwurf.id,
      zustand,
      herkunft: plattformNameAusUrl(einwurf.url) ?? domainAus(adresse),
      link: adresse,
      linkText: adresseKurz(adresse),
      saetze,
      beitraege: links.map((link) => ({
        contentId: link.content_id,
        typ: resolveContentType(link.content_type) ?? null,
        satz: saetze.find((satz) => satz.id === link.draft_id)?.text ?? null,
      })),
      verwerfbar: einwurf.status === 'open' || einwurf.status === 'in_progress',
    },
  };
}

/**
 * Der Plattformname, aber nur wenn er etwas sagt.
 *
 * Die Erkennung faellt fuer jede unbekannte Adresse auf "web" zurueck. "Web"
 * traegt weniger als die Domain, deshalb gilt es hier als keine Angabe - die
 * Karte zeigt dann die Domain.
 */
function plattformNameAusUrl(url: string | null): string | null {
  const plattform = plattformAusUrl(url);
  return plattform && plattform !== 'web' ? plattformName(plattform) : null;
}

function hinweis(einwurf: RawInput): string | null {
  const inhalt = einwurf.content?.trim();
  return inhalt && inhalt !== einwurf.url ? inhalt : null;
}

// Aussage im Beitragsformular

/** Die Aussage, auf die ein Beitrag antwortet, fuer die Kopf-Variante. */
export function ausAussage(id: string, text: string): KartenDaten {
  return {
    id,
    typ: 'statement',
    titel: text,
    text: null,
    erstellt: '',
    autor: null,
    autorName: null,
    nutzung: null,
    quellen: [],
  };
}
