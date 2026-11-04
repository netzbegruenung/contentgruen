import { Params } from '@angular/router';
import { Observable, Subscription, map } from 'rxjs';

import { CommentaryService } from '../services/commentary.service';
import { GenericTextService } from '../services/generic-text.service';
import { CommentaryResult, GenerictextResult } from '../services/dtos/searchDtos';
import { FORMULAR_PFAD } from '../shared/formular-adresse';
import type { Stil, Zweck } from '../shared/zweck-stil';

/**
 * "Als Vorlage nehmen" (#356, Glossar "Variante"): Das Formular des Typs oeffnet mit
 * dem Text des Originals; gespeichert wird ein neuer Beitrag mit eigenem Autor, der
 * auf dem Original beruht. Die Adresse traegt nur die ID, das Formular laedt den
 * Beitrag selbst.
 *
 * Nur Kommentar und Hintergrundinfo: Ein Post ist der Beitrag eines fremden Kontos,
 * ein Bild braucht eine eigene Datei - beides laesst sich nicht vorbelegen.
 */
export const VORLAGE_PARAM = 'vorlage';

export type VorlageTyp = 'commentary' | 'generictext';

export function kannVorlageSein(typ: string | null | undefined): typ is VorlageTyp {
  return typ === 'commentary' || typ === 'generictext';
}

/** Wohin "Als Vorlage nehmen" fuehrt: das Formular des Typs mit ?vorlage=<id>. */
export function vorlageAdresse(typ: VorlageTyp, id: string): { pfad: string; queryParams: Params } {
  return { pfad: FORMULAR_PFAD[typ], queryParams: { [VORLAGE_PARAM]: id } };
}

/** Was das Formular aus dem Original uebernimmt; alles bleibt aenderbar. */
export interface Vorlage {
  id: string;
  titel: string;
  text: string;
  /** Nur am Kommentar: die Fassungen Kurz und Lang, Zweck und Stil. */
  kurz?: string;
  lang?: string;
  zweck?: Zweck;
  stil?: Stil | null;
}

/** Hinweis im Formular, wenn ?vorlage= auf nichts (mehr) zeigt. */
export const VORLAGE_NICHT_VERFUEGBAR =
  'Die Vorlage ist nicht mehr verfügbar — du kannst trotzdem einen eigenen Beitrag schreiben.';

/** Hinweis im Formular ueber dem Titel, solange eine Vorlage gilt. */
export function vorlageHinweis(vorlage: Vorlage): string {
  return `Variante von „${vorlage.titel}“ – dein Beitrag erscheint unter deinem Namen, das Original bleibt, wie es ist.`;
}

export function vorlageAusKommentar(kommentar: CommentaryResult): Vorlage {
  return {
    id: kommentar.id,
    titel: kommentar.title ?? '',
    text: kommentar.text ?? '',
    kurz: kommentar.short_text || undefined,
    lang: kommentar.long_text || undefined,
    zweck: kommentar.zweck,
    stil: kommentar.style ?? null,
  };
}

export function vorlageAusHintergrundinfo(info: GenerictextResult): Vorlage {
  return { id: info.id, titel: info.title ?? '', text: info.text ?? '' };
}

export function kommentarVorlageLaden(service: CommentaryService, id: string): Observable<Vorlage> {
  return service.getCommentaryById(id).pipe(map(vorlageAusKommentar));
}

export function hintergrundinfoVorlageLaden(service: GenericTextService, id: string): Observable<Vorlage> {
  return service.getGenericTextById(id).pipe(map(vorlageAusHintergrundinfo));
}

/**
 * Die Vorlage aus ?vorlage= fuer einen Formular-Workflow. Aendert sich die Adresse,
 * zaehlt nur noch die neue: Ein laufendes Laden fuer die alte wird abgebrochen, damit
 * eine spaete Antwort weder das Formular ueberschreibt noch mit dem falschen
 * Original verknuepft.
 */
export class VorlageAusAdresse {
  vorlage: Vorlage | null = null;
  private id: string | null = null;
  private laden: Subscription | null = null;

  constructor(
    private ladenVon: (id: string) => Observable<Vorlage>,
    private nichtLadbar: (error: unknown) => void,
  ) {}

  uebernehmen(id: string | null): void {
    if (id === this.id) {
      return;
    }
    this.beenden();
    this.id = id;
    this.vorlage = null;
    if (id) {
      this.laden = this.ladenVon(id).subscribe({
        next: (vorlage) => (this.vorlage = vorlage),
        error: (error) => this.nichtLadbar(error),
      });
    }
  }

  beenden(): void {
    this.laden?.unsubscribe();
    this.laden = null;
  }
}
