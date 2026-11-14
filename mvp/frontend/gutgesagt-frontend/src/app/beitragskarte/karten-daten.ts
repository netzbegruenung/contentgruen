import { BaseContentResult, BaseSearchResult, ContentReference } from '../services/dtos/commonDtos';
import { ContentResult } from '../services/dtos/contributionDtos';
import { BeitragZustand, Einwurf, AusformuliertIn } from '../services/einwurf.service';
import { CONTENT_TYPE_REGISTRY, resolveContentType } from '../shared/content-type-registry';
import { plattformAusUrl, plattformName } from '../shared/plattform';
import { KETTEN_ICONS } from '../shared/fangkorb-texte';
import type { NutzungJeFassung } from '../shared/fassung';
import { STIL_LABEL, Stil } from '../shared/zweck-stil';
import type { BeitragAnsicht } from '../services/content.service';

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
  /** Die Notiz dieses Beitrags, ohne den Text der Herkunft als Ersatz; zum Aendern (#299). */
  notiz?: string;
}

export interface KartenStatement {
  text: string;
  /** Prozent, 0-100. */
  aehnlichkeit: number;
  /** Prozent, 0-100. */
  antwortqualitaet: number;
}

/** Was das Siegel einer Karte zeigt und erklaert (#427, GLOSSARY.md "Siegel", "Guete"). */
export interface KartenGuete {
  /** 1-10; null = "neu", ohne Daten. */
  wert: number | null;
  /** Die erfuellten Kriterien des Gegenlesens (Arten wie in gegenlesen.service.ts). */
  erfuellt: string[];
  /** Ob Stimmen anderer eingegangen sind (erst ab einer Mindestzahl). */
  stimmenZaehlen: boolean;
  /** Zaehler an den Stimm-Knoepfen; null = unter der Mindestzahl oder unbekannt, dann ohne Zahl. */
  hilfreich: number | null;
  nichtHilfreich: number | null;
}

/** Siegel und Zaehler aus einem Beitrag der Antwort; ohne Feld `guete` (alte Antwort) undefined. */
type GueteFelder = Pick<
  BaseContentResult,
  'guete' | 'guete_erfuellt' | 'guete_stimmen_zaehlen' | 'stimmen_hilfreich' | 'stimmen_nicht_hilfreich'
>;

export function gueteAus(inhalt: GueteFelder): KartenGuete | undefined {
  if (inhalt.guete === undefined) {
    return undefined;
  }
  return {
    wert: inhalt.guete ?? null,
    erfuellt: inhalt.guete_erfuellt ?? [],
    stimmenZaehlen: inhalt.guete_stimmen_zaehlen ?? false,
    hilfreich: inhalt.stimmen_hilfreich ?? null,
    nichtHilfreich: inhalt.stimmen_nicht_hilfreich ?? null,
  };
}

/** Felder, die nur ein Typ hat. */
export interface KartenExtra {
  kurz?: string;
  lang?: string;
  /** Am Kommentar (#357): der Stil, falls einer gewaehlt ist. */
  stil?: Stil;
  /** Am Kommentar (#357): geschrieben fuer die eigenen Leute; sonst Kommentarspalte. */
  fuerEigeneLeute?: boolean;
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
  /** Die verknuepften Beitraege, die sich ansehen lassen, aelteste zuerst. */
  beitraege: EinwurfBeitrag[];
  /** Gesetzt, wenn keiner der verknuepften Beitraege mehr sichtbar ist (#507). */
  beitragZustand: NichtSichtbar | null;
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
  /** Vom Server berechnet: der eigene Beitrag bzw. Einwurf. null/fehlend = nicht der eigene. */
  eigen?: boolean | null;
  /** Anzeigename ("Anna B."); null ohne Anmeldung oder ohne gespeicherten Namen. */
  autorName: string | null;
  /**
   * Meilenstein-Abzeichen am Anzeigenamen (#351): Zahl der erreichten Meilensteine,
   * nur wenn die Person der Sichtbarkeit zugestimmt hat; fehlt = kein Abzeichen.
   */
  autorAbzeichen?: number | null;
  /** Verwendungen; null = unbekannt, dann kein Badge. */
  nutzung: number | null;
  /** Wie viele Beitraege auf diesem beruhen ("N Varianten", #356); fehlt = keine. */
  varianten?: number;
  /** Davon in den letzten 7 Tagen; nur in Meine Beitraege gesetzt, sonst kein Zuwachs. */
  nutzungLetzte7Tage?: number;
  /** Am Kommentar in Meine Beitraege: Nutzung und Zuwachs je vorhandener Fassung (#355). */
  nutzungJeFassung?: NutzungJeFassung;
  quellen: KartenQuelle[];
  bildUrl?: string;
  statement?: KartenStatement;
  stimme?: 'like' | 'dislike';
  /** Siegel und Stimm-Zaehler (#427); fehlt = unbekannt, dann kein Siegel. */
  guete?: KartenGuete;
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
    autorAbzeichen: inhalt.autor_abzeichen ?? null,
    nutzung: inhalt.usage_count ?? 0,
    varianten: inhalt.varianten ?? 0,
    quellen: (inhalt.references ?? []).map(quelle),
    bildUrl: inhalt['image_url'] || undefined,
    statement: statement(paket),
    stimme: paket.user_vote === 'like' || paket.user_vote === 'dislike' ? paket.user_vote : undefined,
    guete: gueteAus(inhalt),
    extra: extra(typ, inhalt),
  };
}

/**
 * Ein Beitrag unter seiner eigenen Adresse (/content/beitrag/{id}, #300): flach wie
 * getById seines Typs, der Typ in content_type, dazu die eigene Stimme (user_vote).
 * Dieselbe Karte wie in der Suche, nur ohne Aussage, ueber die er gefunden wurde.
 */
export function ausEinzelansicht(beitrag: BeitragAnsicht): KartenDaten {
  const typ = resolveContentType(beitrag.content_type);
  const feld = typ ? CONTENT_TYPE_REGISTRY[typ].resultField : undefined;
  return ausSuchergebnis({
    score: 1,
    statement_text: null,
    statement_similarity_score: null,
    reply_relevance: null,
    content_type: beitrag.content_type,
    user_vote: beitrag.user_vote ?? undefined,
    ...(feld ? { [feld]: beitrag } : {}),
  });
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
    ...(referenz.description ? { notiz: referenz.description } : {}),
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
    return {
      kurz: befuellt(inhalt['short_text']),
      lang: befuellt(inhalt['long_text']),
      ...zweckUndStil(inhalt),
    };
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

/** Nur Werte, die die Karte kennt: Ein Stil, den es nicht gibt, bekaeme kein Label. */
function zweckUndStil(inhalt: Record<string, any>): Pick<KartenExtra, 'stil' | 'fuerEigeneLeute'> {
  const stil = inhalt['style'];
  return {
    ...(typeof stil === 'string' && Object.hasOwn(STIL_LABEL, stil) ? { stil: stil as Stil } : {}),
    ...(inhalt['zweck'] === 'eigene_leute' ? { fuerEigeneLeute: true } : {}),
  };
}

// Meine Beitraege

/**
 * Ohne Text zeigt die Album-Karte den Titel; fehlt auch der, die Domain der
 * Bildadresse, damit ein Bild ohne Unterschrift nicht als leere Karte erscheint.
 * Der Text selbst bleibt leer, sonst stuende der Titel im Album doppelt da.
 */
export function ausBeitrag(eintrag: ContentResult): KartenDaten {
  const typ = resolveContentType(eintrag.content_type) ?? null;
  return {
    id: eintrag.id,
    typ,
    titel: eintrag.title || (eintrag.text ? null : domainAus(eintrag.image_url)),
    text: eintrag.text ?? null,
    erstellt: eintrag.created,
    autor: eintrag.original_author || null,
    eigen: eintrag.ist_eigener_beitrag ?? null,
    autorName: eintrag.autor_name ?? null,
    autorAbzeichen: eintrag.autor_abzeichen ?? null,
    nutzung: eintrag.usage_count ?? 0,
    nutzungLetzte7Tage: eintrag.nutzung_letzte_7_tage ?? 0,
    nutzungJeFassung: typ === 'commentary' ? (eintrag.nutzung_je_fassung ?? undefined) : undefined,
    quellen: (eintrag.references ?? []).map(quelle),
    bildUrl: eintrag.image_url || undefined,
    guete: gueteAus(eintrag),
    // Nur die Fassungen des Kommentars (#355); Post-Angaben zeigt Meine Beitraege nicht.
    extra: typ === 'commentary' ? extra(typ, eintrag as Record<string, any>) : undefined,
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

/** Was aus den Beitraegen eines Einwurfs wurde, wenn keiner mehr sichtbar ist. */
export type NichtSichtbar = Exclude<BeitragZustand, 'sichtbar'>;

/**
 * Die Beschriftung statt "Ausformuliert", wenn niemand die Beitraege mehr findet
 * (#507). Die Stufe bleibt ausformuliert - das ist der Einwurf ja -, aber
 * "Ausformuliert" und "Ansehen" versprechen einen Beitrag, den es nicht mehr gibt.
 */
export const NICHT_SICHTBAR: Record<NichtSichtbar, StufenAnzeige> = {
  gesperrt: { emoji: KETTEN_ICONS.verfassen, name: 'Beitrag gesperrt' },
  geloescht: { emoji: KETTEN_ICONS.verfassen, name: 'Beitrag gelöscht' },
};

/** Ob sich ein Beitrag, in dem der Einwurf ausformuliert ist, ansehen laesst; ohne Angabe vom Server: ja. */
export function istSichtbar(link: AusformuliertIn): boolean {
  return link.zustand !== 'gesperrt' && link.zustand !== 'geloescht';
}

/**
 * Gesperrt oder geloescht, wenn ein Einwurf ausformuliert ist, aber keiner der
 * Beitraege, in denen er ausformuliert ist, mehr sichtbar; sonst null. Solange einer sichtbar ist, bleibt alles
 * wie bisher. Sind die Beitraege teils gesperrt, teils geloescht, steht
 * "gesperrt": Eine Sperre laesst sich aufheben, ein Loeschen nicht.
 */
export function nichtSichtbar(einwurf: Einwurf): NichtSichtbar | null {
  const links = einwurf.links ?? [];
  if (!links.length || links.some(istSichtbar)) {
    return null;
  }
  return links.some((link) => link.zustand === 'gesperrt') ? 'gesperrt' : 'geloescht';
}

/**
 * Wie die Stufe eines Einwurfs angezeigt wird, etwa beim Einwerfen: die Stufe,
 * bei Ausformuliertem ohne sichtbaren Beitrag stattdessen dessen Zustand.
 */
export function stufenAnzeigeVonEinwurf(einwurf: Einwurf): StufenAnzeige {
  const stufe = stufeVonEinwurf(einwurf);
  const zustand = nichtSichtbar(einwurf);
  return stufe === 'ausformuliert' && zustand ? NICHT_SICHTBAR[zustand] : STUFEN[stufe];
}

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

/**
 * Die mit einem Einwurf verknuepften Beitraege, die sich ansehen lassen, aelteste
 * zuerst, samt ausformuliertem Satz. Gesperrte und geloeschte fehlen (#507): Das
 * Sheet koennte sie nicht laden.
 */
export function beitraegeVonEinwurf(einwurf: Einwurf): EinwurfBeitrag[] {
  const saetze = einwurf.drafts ?? [];
  return (einwurf.links ?? []).filter(istSichtbar).map((link) => ({
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
    // Nur sichtbare zaehlen, wie unter ``beitraege`` (#507): Sonst truege der Satz
    // einen Haken, waehrend der Kopf "Beitrag geloescht" sagt.
    beitraege: links.filter((link) => link.draft_id === satz.id && istSichtbar(link)).length,
  }));

  return {
    id: einwurf.id,
    // Ausformuliertes traegt die Farbe des ersten verknuepften Beitrags: Die Typklasse
    // setzt --karten-farbe, und davon nimmt das Kopfband. Offene und destillierte Einwuerfe
    // haben keinen Typ - ihr Band bleibt Sand.
    // Die erste Verknuepfung *mit* Typ: Verknuepfungen aus der Zeit vor Fangkorb v2
    // tragen keinen, und stuende so eine vorn, blieben Band und Emoji farblos,
    // obwohl ein typisierter Beitrag daneben liegt. Nur sichtbare Beitraege faerben:
    // Ist keiner mehr sichtbar, bleibt das Band Sand (#507).
    typ:
      stufe === 'ausformuliert'
        ? (links
            .filter(istSichtbar)
            .map((link) => resolveContentType(link.content_type))
            .find(Boolean) ?? null)
        : null,
    titel: hinweis(einwurf),
    text: null,
    erstellt: einwurf.created_at,
    autor: einwurf.submitted_by,
    eigen: einwurf.ist_eigener_einwurf ?? null,
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
      beitragZustand: nichtSichtbar(einwurf),
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

/**
 * Das Praefix, mit dem Einwerfen einen geteilten Seitentitel im Hinweis markiert
 * (SEITENTITEL_PRAEFIX in einwerfen.component.ts; hier eigens, damit die Karte nicht
 * vom Formular abhaengt, ein Test haelt beide gleich).
 */
export const SEITENTITEL_MARKE = 'Seitentitel: ';

/**
 * Der Hinweis als Kartentitel. Ein stehengelassenes „Seitentitel: “ aus dem Teilen
 * faellt weg: Der Seitentitel ist dann der Titel, nicht roh mit Marke davor
 * (Nutzerfuehrung 13.11.). Gespeichert bleibt der Hinweis, wie er ist.
 */
export function hinweisTitel(inhalt: string | null | undefined, url: string | null = null): string | null {
  let text = inhalt?.trim();
  const marke = SEITENTITEL_MARKE.trim();
  if (text?.startsWith(marke)) {
    // Seitentitel vorn, der Rest des geteilten Texts mit Strich dahinter: Die Karte
    // zeigt den Titel in einer Zeile, ein Zeilenumbruch fiele dort weg.
    const [titel, ...rest] = text.slice(marke.length).split('\n');
    text = [titel.trim(), rest.join(' ').trim()].filter(Boolean).join(' – ');
  }
  return text && text !== url ? text : null;
}

function hinweis(einwurf: Einwurf): string | null {
  return hinweisTitel(einwurf.content, einwurf.url);
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
