import { BaseContentResult, BaseSearchResult, ContentReference } from '../services/dtos/commonDtos';
import { ContentResult } from '../services/dtos/contributionDtos';
import { Einwurf } from '../services/einwurf.service';
import { CONTENT_TYPE_REGISTRY, resolveContentType } from '../shared/content-type-registry';
import { plattformAusUrl, plattformName } from '../shared/plattform';
import { KETTEN_ICONS } from '../shared/fangkorb-texte';

/**
 * Was eine Beitragskarte anzeigt, unabhaengig davon, woher die Daten kommen.
 *
 * Drei Quellen liefern verschieden geformte Daten: die Suche (und /recent) ein
 * Paket mit genau einem `*_result`, "Meine Beitraege" einen flachen Eintrag, der
 * Fangkorb einen Einwurf mit Saetzen und Verknuepfungen. Die Adapter unten bringen
 * alle drei auf diese eine Form; die Karte kennt keine der Quellen.
 */
export type KartenVariante = 'voll' | 'kompakt' | 'einwurf' | 'kopf';

/**
 * Was eine Einwurf-Karte anbietet: der eine Primaerknopf im Fuss und die
 * Eintraege im ⋮-Menue. Wohin das fuehrt, entscheidet die Seite, nicht die Karte.
 */
export type EinwurfAktion =
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

/** Ein Satz zum Einwurf, mit der Zahl der Beitraege, mit denen er ausformuliert wurde. */
export interface EinwurfSatz {
  id: string;
  text: string;
  /** Die Zahl der Beitraege aus genau diesem Satz; 0, solange keiner mit ihm verknuepft ist. */
  beitraege: number;
}

/** Ein Beitrag aus dem Einwurf - was das Sheet braucht, um ihn nachzuladen. */
export interface EinwurfBeitrag {
  contentId: string;
  /** Registry-Schluessel; null bei Verknuepfungen aus der Zeit vor Fangkorb v2. */
  typ: string | null;
  /** Der ausformulierte Satz als Beschriftung; null, wenn er spaeter geleert wurde. */
  satz: string | null;
}

export interface EinwurfAngaben {
  einwurfId: string;
  stufe: EinwurfStufe;
  /** Marke links in der Link-Zeile: Plattformname, sonst die Domain. */
  herkunft: string | null;
  /** Ziel der Link-Zeile: der Link, sonst die Bildadresse. */
  link: string | null;
  /** Der Link, wie er dasteht: ohne Schema und www, Domain und Pfad. */
  linkText: string | null;
  /** Alle Saetze, aelteste Aenderung zuerst. */
  saetze: EinwurfSatz[];
  /** Die verknuepften Beitraege, aelteste zuerst. */
  beitraege: EinwurfBeitrag[];
  /** Nur im Kopf: der Satz, aus dem gerade ein Beitrag entsteht. */
  kopfSatz?: string;
  /** Offen oder destilliert (`istVerwerfbar`); wer verwerfen darf, entscheidet die Karte. */
  verwerfbar: boolean;
}

export interface KartenDaten {
  /** Content-ID; bei der Einwurf-Karte die ID des Einwurfs bzw. des Satzes. */
  id: string;
  /** Registry-Schluessel ('generictext'), null ohne Beitrag oder bei unbekanntem Typ. */
  typ: string | null;
  /** Die Behauptung; null auf der Einwurf-Karte. */
  titel: string | null;
  text: string | null;
  erstellt: string;
  /**
   * Kennung des Autors bzw. Einwerfers. Am Beitrag aus Suche, Einzelabruf und
   * /recent nur fuer Admins gesetzt (#333), sonst null; dort sagt `eigen`, ob er
   * der eigene ist.
   */
  autor: string | null;
  /** Vom Server berechnet: der eigene Beitrag. null/fehlend = unbekannt, dann zaehlt `autor`. */
  eigen?: boolean | null;
  /** Anzeigename ("Anna B."); null ohne Anmeldung oder ohne gespeicherten Namen. */
  autorName: string | null;
  /** Verwendungen; null = unbekannt, dann kein Badge. */
  nutzung: number | null;
  quellen: KartenQuelle[];
  bildUrl?: string;
  statement?: KartenStatement;
  stimme?: 'like' | 'dislike';
  extra?: KartenExtra;
  einwurfAngaben?: EinwurfAngaben;
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
    autor: inhalt.original_author || null,
    eigen: inhalt.ist_eigener_beitrag ?? null,
    autorName: inhalt.autor_name ?? null,
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
      // 0 heisst "nicht erfasst" (das Post-Formular fragt nicht danach), nicht "keine".
      engagement: inhalt['engagement'] || undefined,
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
    autor: eintrag.original_author || null,
    eigen: eintrag.ist_eigener_beitrag ?? null,
    autorName: eintrag.autor_name ?? null,
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
 * Die Stufe eines Einwurfs, wie das Glossar sie nennt. Die Tabs des Fangkorbs
 * heissen dagegen nach der naechsten Arbeit (``FangkorbTab``); Verworfenes liegt
 * dort hinter einem Chip, Ausformuliertes in keinem.
 */
export type EinwurfStufe = 'offen' | 'destilliert' | 'ausformuliert' | 'verworfen';

/** Wie eine Stufe angezeigt wird: Icon und Name. */
export interface StufenAnzeige {
  emoji: string;
  name: string;
}

/**
 * Die Stufe, an der der Einwurf gerade steht - dasselbe Icon wie ueberall entlang
 * der Kette. Das Band zeigt damit die Stufe: Ein offener Einwurf traegt das
 * Einwurf-Icon, ein destillierter das der Destille. Der Primaerknopf zeigt
 * dagegen die naechste Stufe (siehe primaerAktion). Verworfenes behaelt das Icon
 * des Einwurfs.
 */
export const STUFEN: Record<EinwurfStufe, StufenAnzeige> = {
  offen: { emoji: KETTEN_ICONS.einwerfen, name: 'Offen' },
  destilliert: { emoji: KETTEN_ICONS.destillieren, name: 'Destilliert' },
  ausformuliert: { emoji: KETTEN_ICONS.verfassen, name: 'Ausformuliert' },
  verworfen: { emoji: KETTEN_ICONS.einwerfen, name: 'Verworfen' },
};

/**
 * Die Stufe eines Einwurfs bestimmen.
 *
 * Verworfen zuerst: Verworfenes bleibt verworfen, auch wenn andere trotzdem
 * weiterdestillieren (das Backend erlaubt das ausdruecklich). Ausformuliert haengt
 * an den Verknuepfungen, nicht an den Saetzen - ein Einwurf kann auch ohne
 * gespeicherten Satz verknuepft worden sein (processed aus open), und ein spaeter
 * geleerter Satz darf den Einwurf nicht zurueckfallen lassen.
 *
 * Der gespeicherte Status (open, in_progress, processed, discarded) traegt noch
 * die alten Namen; die Stufe leitet sich hier ab, damit dafuer keine
 * Datenmigration noetig ist.
 */
export function stufeVonEinwurf(einwurf: Einwurf): EinwurfStufe {
  return einwurf.status === 'discarded' ? 'verworfen' : stufeInDerKette(einwurf);
}

/**
 * Wie weit ein Einwurf in der Kette ist, gleich ob verworfen: Der Fangkorb legt
 * Verworfenes in den Tab der Arbeit, die an ihm noch offen waere.
 */
export function stufeInDerKette(einwurf: Einwurf): Exclude<EinwurfStufe, 'verworfen'> {
  if ((einwurf.links ?? []).length > 0) {
    return 'ausformuliert';
  }
  return (einwurf.drafts ?? []).length > 0 ? 'destilliert' : 'offen';
}

/** Die mit einem Einwurf verknuepften Beitraege, aelteste zuerst, samt ausformuliertem Satz. */
export function beitraegeVonEinwurf(einwurf: Einwurf): EinwurfBeitrag[] {
  const saetze = einwurf.drafts ?? [];
  return (einwurf.links ?? []).map((link) => ({
    contentId: link.content_id,
    typ: resolveContentType(link.content_type) ?? null,
    satz: saetze.find((satz) => satz.id === link.draft_id)?.sentence ?? null,
  }));
}

/**
 * Ein Einwurf als eine Karte: Herkunft im Kopf, der Inhalt als Titel, die Saetze
 * innen.
 *
 * Titel ist, was jemand mitgegeben hat - der Hinweis, sonst nichts: Ohne Hinweis ist
 * die Link-Zeile die Aufschrift der Karte. Die Adresse steht dort gekuerzt
 * (Domain und Pfad, ohne Schema und www), nicht als roher Link.
 *
 * ``beitraege`` je Satz zaehlt die Verknuepfungen auf genau diesen Satz - dieselbe
 * Person kann ihren Satz mit mehr als einem Beitrag ausformuliert haben. Verknuepfungen
 * ohne Satz (verknuepft ohne gespeicherten Satz, oder der Satz wurde spaeter
 * geleert) haengen an keiner Zeile, bleiben aber unter ``beitraege`` erreichbar -
 * sichtbar werden sie im Sheet.
 */
export function ausEinwurf(einwurf: Einwurf): KartenDaten {
  const links = einwurf.links ?? [];
  const adresse = einwurf.url ?? einwurf.image_url;
  const stufe = stufeVonEinwurf(einwurf);
  const saetze: EinwurfSatz[] = (einwurf.drafts ?? []).map((satz) => ({
    id: satz.id,
    text: satz.sentence,
    beitraege: links.filter((link) => link.draft_id === satz.id).length,
  }));

  return {
    id: einwurf.id,
    // Ausformuliertes traegt die Farbe des ersten verknuepften Beitrags: Die Typklasse
    // setzt --karten-farbe, und davon nimmt das Kopfband. Offene und destillierte Einwuerfe
    // haben keinen Typ - ihr Band bleibt Sand.
    // Die erste Verknuepfung *mit* Typ: Verknuepfungen aus der Zeit vor Fangkorb v2
    // tragen keinen, und stuende so eine vorn, blieben Band und Emoji farblos,
    // obwohl ein typisierter Beitrag daneben liegt.
    typ:
      stufe === 'ausformuliert'
        ? (links.map((link) => resolveContentType(link.content_type)).find(Boolean) ?? null)
        : null,
    titel: hinweis(einwurf),
    text: null,
    erstellt: einwurf.created_at,
    autor: einwurf.submitted_by,
    autorName: einwurf.submitted_by_name ?? null,
    nutzung: null,
    quellen: [],
    einwurfAngaben: {
      einwurfId: einwurf.id,
      stufe,
      herkunft: plattformNameAusUrl(einwurf.url) ?? domainAus(adresse),
      link: adresse,
      linkText: adresseKurz(adresse),
      saetze,
      beitraege: beitraegeVonEinwurf(einwurf),
      verwerfbar: istVerwerfbar(einwurf),
    },
  };
}

/**
 * Verwerfen geht nur, solange ein Einwurf offen oder destilliert ist. Fangkorb-Karte
 * und Destillier-Ansicht fragen beide hier, damit die Regel nicht auseinanderlaeuft.
 */
export function istVerwerfbar(einwurf: Einwurf): boolean {
  return einwurf.status === 'open' || einwurf.status === 'in_progress';
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

function hinweis(einwurf: Einwurf): string | null {
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
