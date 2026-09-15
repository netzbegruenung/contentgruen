import { BaseContentResult, BaseSearchResult, ContentReference } from '../services/dtos/commonDtos';
import { ContentResult } from '../services/dtos/contributionDtos';
import { RawInput, RawInputDraft, RawInputLink } from '../services/raw-input.service';
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
export type KartenVariante = 'voll' | 'kompakt' | 'rohling';

/** offen und verworfen gelten fuer die Einwurf-Karte, die anderen fuer Satz-Karten. */
export type RohlingZustand = 'offen' | 'destilliert' | 'ausformuliert' | 'verworfen';

export type RohlingRolle = 'eingeworfen' | 'destilliert' | 'ausformuliert';

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

export interface RohlingDaten {
  /** Die Einwurf-Karte oben im Stapel oder eine Satz-Karte darunter. */
  art: 'einwurf' | 'satz';
  einwurfId: string;
  zustand: RohlingZustand;
  antippbar: boolean;
  /** Name der Plattform des Links, nur auf der Einwurf-Karte. */
  plattform: string | null;
  link: string | null;
  bildAdresse: string | null;
  /** Der Hinweis fuer andere, sofern er mehr ist als der Link selbst. */
  hinweis: string | null;
  beteiligte: { rolle: RohlingRolle; kennung: string | null }[];
  /** Womit "In der Suche anzeigen" sucht; nur bei einem Satz mit Beitrag. */
  suchSatz: string | null;
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

function extra(typ: string | null, inhalt: Record<string, any>): KartenExtra | undefined {
  if (typ === 'commentary') {
    return { kurz: inhalt['short_text'] || undefined, lang: inhalt['long_text'] || undefined };
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
    titel: eintrag.title || (eintrag.text ? null : domainAusBildadresse(eintrag.image_url)),
    text: eintrag.text ?? null,
    erstellt: eintrag.created,
    autor: eintrag.original_author ?? null,
    autorName: null,
    nutzung: eintrag.usage_count ?? 0,
    quellen: (eintrag.references ?? []).map(quelle),
    bildUrl: eintrag.image_url || undefined,
  };
}

function domainAusBildadresse(adresse: string | null | undefined): string | null {
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
 * Ein Einwurf als Stapel: zuerst die Einwurf-Karte, dann je Satz eine Karte.
 *
 * Der Zustand eines Satzes haengt nur an den Verknuepfungen: zeigt eine auf ihn
 * (draft_id), ist daraus ein Beitrag geworden, sonst ist er destilliert. Der
 * Status des Einwurfs spielt dafuer keine Rolle, er steuert nur den Filter.
 *
 * Verknuepfungen ohne passenden Satz werden uebersprungen: Eine Karte ohne Titel und
 * ohne Suche traegt nichts, und der Altbestand hat seit der Migration vom 13.09.2026
 * eine draft_id. Uebrig bleiben nur Faelle, in denen der Satz spaeter geleert wurde.
 */
export function ausEinwurf(einwurf: RawInput): KartenDaten[] {
  const verworfen = einwurf.status === 'discarded';
  const antippbar = !verworfen;
  const saetze = einwurf.drafts ?? [];
  const links = einwurf.links ?? [];

  const einwurfKarte: KartenDaten = {
    id: einwurf.id,
    typ: null,
    titel: null,
    text: null,
    erstellt: einwurf.created_at,
    autor: einwurf.submitted_by,
    autorName: null,
    nutzung: null,
    quellen: [],
    rohling: {
      art: 'einwurf',
      einwurfId: einwurf.id,
      zustand: verworfen ? 'verworfen' : 'offen',
      antippbar,
      plattform: plattformNameAusUrl(einwurf.url),
      link: einwurf.url,
      bildAdresse: einwurf.image_url,
      hinweis: hinweis(einwurf),
      beteiligte: [{ rolle: 'eingeworfen', kennung: einwurf.submitted_by }],
      suchSatz: null,
    },
  };

  const satzKarten = saetze.map((satz) =>
    satzKarte(einwurf, satz, links.find((link) => link.draft_id === satz.id) ?? null, antippbar),
  );

  return [einwurfKarte, ...satzKarten];
}

function satzKarte(
  einwurf: RawInput,
  satz: RawInputDraft,
  link: RawInputLink | null,
  antippbar: boolean,
): KartenDaten {
  const beteiligte: RohlingDaten['beteiligte'] = [{ rolle: 'destilliert', kennung: satz.user_id }];
  if (link) {
    beteiligte.push({ rolle: 'ausformuliert', kennung: link.processed_by });
  }
  return {
    id: satz.id,
    typ: link ? (resolveContentType(link.content_type) ?? null) : null,
    titel: satz.sentence,
    text: null,
    erstellt: satz.updated_at,
    autor: satz.user_id,
    autorName: null,
    nutzung: null,
    quellen: [],
    rohling: {
      art: 'satz',
      einwurfId: einwurf.id,
      zustand: link ? 'ausformuliert' : 'destilliert',
      antippbar,
      plattform: null,
      link: null,
      bildAdresse: null,
      hinweis: null,
      beteiligte,
      suchSatz: link ? satz.sentence : null,
    },
  };
}

function plattformNameAusUrl(url: string | null): string | null {
  const plattform = plattformAusUrl(url);
  return plattform ? plattformName(plattform) : null;
}

function hinweis(einwurf: RawInput): string | null {
  const inhalt = einwurf.content?.trim();
  return inhalt && inhalt !== einwurf.url ? inhalt : null;
}
