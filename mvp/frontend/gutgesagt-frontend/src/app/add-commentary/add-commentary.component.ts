import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { TextFieldModule } from '@angular/cdk/text-field';
import { MatDialog } from '@angular/material/dialog';
import { filter } from 'rxjs/operators';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { CommentaryService } from '../services/commentary.service';
import { VotingService } from '../services/voting.service';
import { LoggingService } from '../services/logging.service';
import { AddCommentaryRequest, AddCommentaryResponse } from '../services/dtos/commentaryDtos';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenDaten, ausSuchergebnis } from '../beitragskarte/karten-daten';
import { ReferenceInputComponent } from '../reference-input/reference-input.component';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import type { Vorbefuellung } from '../destillieren/destillier-uebergabe.service';
import { CONSENT_HINWEIS } from '../shared/consent-hinweis';
import { typFarbe } from '../shared/content-type-registry';
import { einzeilig } from '../beitragsformular/einzeilig';
import { validierungsMeldung } from '../beitragsformular/speicherfehler';
import { istAussageId } from '../shared/formular-adresse';
import { AntwortAuf, AntwortAufComponent, OHNE_AUSSAGE, zuKurz } from '../beitragsformular/antwort-auf/antwort-auf.component';
import { FormularHilfeComponent } from '../beitragsformular/formular-hilfe/formular-hilfe.component';
import { FormularLeisteComponent } from '../beitragsformular/formular-leiste/formular-leiste.component';
import type { BeitragGespeichert } from '../beitragsformular/beitrag-gespeichert/gespeichert-adresse';
import { BeitragAnsehenService } from '../beitragsformular/beitrag-ansehen.service';
import {
  BestaetigungsDialogComponent,
  BestaetigungsDialogDaten,
} from '../shared/components/bestaetigungs-dialog/bestaetigungs-dialog.component';

export const TITEL_MAX = 120;
export const TEXT_MAX = 500;
/** Zeichengrenze von X und Bluesky; nur ein Hinweis, keine Pruefung. */
export const PLATTFORM_GRENZE = 280;

export const DUBLETTE_HINWEIS = 'Es gibt schon einen sehr ähnlichen Kommentar.';

/** Dublette von jemand anderem: die wird nicht mit der eigenen Aussage verknüpft. */
export const DUBLETTE_FREMD_HINWEIS = 'Es gibt schon einen sehr ähnlichen Kommentar von jemand anderem.';

/** Die Absicht geht nicht verloren - nur über einen anderen Weg. */
export const DUBLETTE_FREMD_ZUORDNEN = 'Du kannst ihn dieser Aussage später über die Karte zuordnen.';

/** Hinweis, wenn der genommene vorhandene Kommentar jetzt auch an der gewaehlten Aussage haengt. */
export function dubletteVerknuepftHinweis(aussage: string): string {
  return `Diesen Kommentar gibt es schon – er ist jetzt auch mit „${aussage}“ verknüpft.`;
}

/** Nach dem Zustimmen: Die Stimme ist gezaehlt, gespeichert wurde nichts. */
export const ZUGESTIMMT_HINWEIS = 'Du hast dem vorhandenen Kommentar zugestimmt.';

/** Der eigene vorhandene Kommentar ist gewaehlt: keine Stimme, gespeichert wurde nichts. */
export const GENOMMEN_HINWEIS = 'Du nimmst deinen vorhandenen Kommentar.';

export const ZUSTIMMEN_FEHLGESCHLAGEN = 'Zustimmen hat nicht geklappt. Versuch es gleich noch einmal.';

/** Verknuepfen gescheitert - voruebergehend oder weil es die Aussage nicht mehr gibt. */
export const NEHMEN_FEHLGESCHLAGEN =
  'Dein vorhandener Kommentar ließ sich nicht mit der Aussage verknüpfen. Versuch es noch einmal oder wähl eine andere Aussage.';

/** Der gewaehlte vorhandene ist inzwischen weg: Die Eingaben bleiben, Speichern legt neu an. */
export const VORHANDEN_WEG = 'Den vorhandenen Kommentar gibt es nicht mehr. Du kannst deinen jetzt speichern.';

export const SPEICHERN_FEHLGESCHLAGEN =
  'Speichern hat nicht geklappt. Deine Eingaben sind noch da – versuch es gleich noch einmal.';

/**
 * Ein schon vorhandener, sehr aehnlicher Kommentar - der eigene waere seine Dublette.
 * Angelegt wurde nichts; die Person entscheidet.
 */
export interface Vorhanden {
  id: string;
  /** Titel, soweit das Backend ihn nennt. */
  titel: string | null;
  /** Von derselben Person: Zustimmen sagt dann nichts, nehmen schon. */
  eigen: boolean;
  /** Text der Aussage, mit der er nach dem Nehmen verknuepft ist; sonst null. */
  aussage: string | null;
  /** Die Anfrage, die ihn gefunden hat; Nehmen schickt sie mit vorhanden_nehmen noch einmal. */
  anfrage: AddCommentaryRequest;
  /** Wie die Person ihn gewaehlt hat; null, solange sie nicht entschieden hat. */
  gewaehlt: 'zugestimmt' | 'genommen' | null;
}

const ZURUECKSETZEN_FRAGE: BestaetigungsDialogDaten = {
  titel: 'Formular zurücksetzen?',
  text: 'Titel, Text, Aussage und Herkunft werden geleert.',
  ja: 'Zurücksetzen',
  nein: 'Abbrechen',
};

/**
 * Das Kommentarformular: Antwort auf, Titel, Kommentar, Herkunft, Leiste - und
 * daneben (am Handy darunter) die Vorschau.
 *
 * Gespeichert wird in einem Aufruf, samt Aussage: mit ID, wenn eine gewaehlt ist,
 * sonst mit ihrem Text. Danach meldet `success` ID, Aussage und ob verknuepft
 * wurde; wohin es weitergeht, entscheidet der Workflow.
 *
 * Ist der Kommentar eine Dublette, wird nichts gespeichert und nichts verknuepft: Das
 * Formular zeigt den vorhandenen, und die Person entscheidet. Zustimmen gibt einem
 * fremden eine Stimme. Den eigenen kann sie ohne Stimme nehmen - mit Aussage schickt
 * das dasselbe noch einmal mit `vorhanden_nehmen`, und erst dann haengt er an der
 * Aussage. Beides meldet ihn ueber `vorhandenGewaehlt`. Trotzdem speichern schickt
 * dasselbe mit `trotz_dublette_von` und endet wie jedes Speichern in `success`; an der
 * Aussage haengt dann nur der neue.
 */
@Component({
  standalone: true,
  selector: 'app-add-commentary',
  templateUrl: './add-commentary.component.html',
  styleUrls: ['./add-commentary.component.scss'],
  imports: [
    ...SHARED_IMPORTS,
    CommonModule,
    ReactiveFormsModule,
    TextFieldModule,
    RouterLink,
    BeitragskarteComponent,
    ReferenceInputComponent,
    AntwortAufComponent,
    FormularHilfeComponent,
    FormularLeisteComponent,
  ],
})
export class AddCommentaryComponent implements OnChanges {
  readonly consentHinweis = CONSENT_HINWEIS;
  /** Streifen ueber dem Formular in der Farbe des Kartenbands. */
  readonly typFarbe = typFarbe('commentary');
  readonly titelMax = TITEL_MAX;
  readonly textMax = TEXT_MAX;
  readonly plattformGrenze = PLATTFORM_GRENZE;

  @Input() statementText = '';
  @Input() statementId = '';
  /** Die Aussage aus der Adresse war nicht ladbar: Hinweis zeigen, Feld leer. */
  @Input() aussageHinweis: string | null = null;
  /** Aus dem Destillier-Ablauf: Satz als Titel, Link als Herkunft, der Einwurf als Kopf. */
  @Input() vorbefuellung: Vorbefuellung | null = null;
  @Output() success = new EventEmitter<BeitragGespeichert>();
  /** Den vorhandenen Kommentar gewaehlt (zugestimmt oder genommen) statt zu speichern: seine ID. */
  @Output() vorhandenGewaehlt = new EventEmitter<string>();

  @ViewChild(ReferenceInputComponent) referenceInput?: ReferenceInputComponent;
  @ViewChild(AntwortAufComponent) antwortAuf?: AntwortAufComponent;

  readonly commentaryForm: FormGroup;

  /** Die Aussage aus der Adresse, fuer den Antwort-auf-Block. */
  aussageAusAdresse: AntwortAuf = OHNE_AUSSAGE;
  /** Was im Antwort-auf-Block gerade gilt. */
  aussage: AntwortAuf = OHNE_AUSSAGE;

  showReferences = false;
  speichert = false;
  fehler: string | null = null;
  /**
   * Eine Meldung, nach der Speichern nicht dasselbe noch einmal schickt (die knappe
   * Validierungsmeldung des Backends bei 422, VORHANDEN_WEG); sonst null.
   */
  validierung: string | null = null;
  /** Gesetzt, sobald der Kommentar gespeichert ist. */
  responseId = '';
  /** Der eigene Kommentar ist eine Dublette dieses vorhandenen; sonst null. */
  vorhanden: Vorhanden | null = null;
  stimmtZu = false;
  /** Nehmen verknuepft gerade den vorhandenen mit der Aussage. */
  nimmt = false;
  /** Fehler beim Zustimmen oder Nehmen; die Entscheidung bleibt offen. */
  entscheidungsFehler: string | null = null;

  /** Ein Aufruf laeuft: Speichern, Zustimmen oder Nehmen. */
  get beschaeftigt(): boolean {
    return this.speichert || this.stimmtZu || this.nimmt;
  }

  /** Zu entscheiden ist, solange es einen vorhandenen gibt und noch nichts gewaehlt ist. */
  get offeneEntscheidung(): boolean {
    return !!this.vorhanden && !this.vorhanden.gewaehlt;
  }

  /** Zustimmen nur einem fremden Kommentar: sich selbst zuzustimmen sagt nichts. */
  get kannZustimmen(): boolean {
    return this.offeneEntscheidung && !this.vorhanden!.eigen;
  }

  /**
   * Den eigenen nehmen, wenn es etwas zu verknuepfen gibt: die mitgeschickte Aussage
   * oder, aus dem Fangkorb, den Einwurf. Sonst ist der eigene ohnehin da, und es gibt
   * nichts zu waehlen.
   */
  get kannNehmen(): boolean {
    return this.offeneEntscheidung && this.vorhanden!.eigen && (this.mitAussage || !!this.vorbefuellung);
  }

  get dublettenHinweis(): string {
    const vorhanden = this.vorhanden;
    if (vorhanden?.gewaehlt === 'zugestimmt') {
      return ZUGESTIMMT_HINWEIS;
    }
    if (vorhanden?.gewaehlt === 'genommen') {
      return vorhanden.aussage ? dubletteVerknuepftHinweis(vorhanden.aussage) : GENOMMEN_HINWEIS;
    }
    return vorhanden && !vorhanden.eigen && this.mitAussage
      ? `${DUBLETTE_FREMD_HINWEIS} ${DUBLETTE_FREMD_ZUORDNEN}`
      : DUBLETTE_HINWEIS;
  }

  private vorschauCache?: { titel: string; text: string; quellen: unknown; aussage: string; karte: KartenDaten };

  constructor(
    fb: FormBuilder,
    private commentaryService: CommentaryService,
    private logger: LoggingService,
    private dialog: MatDialog,
    private beitragAnsehen: BeitragAnsehenService,
    private votingService: VotingService,
  ) {
    this.commentaryForm = fb.group({
      title: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(TITEL_MAX)]],
      text: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(TEXT_MAX)]],
      references: [[]],
    });
    // Der Hinweis gilt nur fuer den Text, der geprueft wurde: Wer ihn aendert,
    // entscheidet nicht mehr ueber diesen vorhandenen, sondern speichert neu. Titel
    // und Herkunft raeumen ihn nicht weg - die Dublettenpruefung vergleicht nur den Text.
    this.commentaryForm
      .get('text')!
      .valueChanges.pipe(takeUntilDestroyed())
      .subscribe(() => {
        if (this.vorhanden && !this.speichert && !this.nimmt) {
          this.vorhandenVergessen();
        }
      });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['statementText'] || changes['statementId']) {
      const text = this.statementText?.trim() ?? '';
      const id = text && istAussageId(this.statementId) ? this.statementId : '';
      this.aussageAusAdresse = { id, text };
      this.aussage = this.aussageAusAdresse;
    }
    if (changes['vorbefuellung'] && this.vorbefuellung) {
      this.vorbefuellungAnwenden(this.vorbefuellung);
    }
  }

  // Titel = Satz aus dem Destillier-Ablauf, Herkunft = Link des Einwurfs. Beides
  // bleibt aenderbar; die Herkunft wird aufgeklappt, damit sie sichtbar ist.
  vorbefuellungAnwenden(vorbefuellung: Vorbefuellung): void {
    this.commentaryForm.patchValue({
      title: vorbefuellung.titel,
      references: vorbefuellung.url ? [{ reference_string: vorbefuellung.url }] : [],
    });
    if (vorbefuellung.url) {
      this.showReferences = true;
    }
  }

  get titelLaenge(): number {
    return this.commentaryForm.get('title')?.value?.length ?? 0;
  }

  get textLaenge(): number {
    return this.commentaryForm.get('text')?.value?.length ?? 0;
  }

  get plattformHinweis(): string {
    return this.textLaenge > PLATTFORM_GRENZE ? 'zu lang für X/Bluesky' : 'passt auf X/Bluesky';
  }

  /** Irgendetwas eingetragen oder vorbelegt - dann fragt Zuruecksetzen nach. */
  get hatEingaben(): boolean {
    const { title, text, references } = this.commentaryForm.value;
    return !!(title?.trim() || text?.trim() || references?.length || this.aussage.id || this.aussage.text);
  }

  /**
   * Die Vorschau als KartenDaten, zwischengespeichert, solange sich nichts
   * aendert - sonst setzte jede Change Detection die Karte zurueck.
   *
   * Ohne Nutzung und ohne Datum: "0×" und das Neu-Zeichen sagen ueber einen
   * Entwurf nichts.
   */
  get vorschauKarte(): KartenDaten {
    const { title, text, references } = this.commentaryForm.value;
    const cache = this.vorschauCache;
    if (
      cache &&
      cache.titel === title &&
      cache.text === text &&
      cache.quellen === references &&
      cache.aussage === this.aussage.text
    ) {
      return cache.karte;
    }
    const karte = ausSuchergebnis({
      commentary_result: {
        id: 'vorschau',
        content_type: 'commentary',
        title: title || 'Titel',
        text: text || 'Dein Kommentar',
        references: (references ?? [])
          .filter((ref: any) => ref?.reference_string?.trim())
          .map((ref: any, index: number) => ({
            reference_id: `vorschau-${index}`,
            reference_text: ref.reference_string,
            reference_description: ref.description || undefined,
          })),
        original_author: 'Du',
      },
      score: 1,
      statement_text: this.aussage.text,
      statement_similarity_score: 0,
      reply_relevance: 0,
    } as any);
    this.vorschauCache = {
      titel: title,
      text,
      quellen: references,
      aussage: this.aussage.text,
      karte: { ...karte, nutzung: null, erstellt: '', autorName: 'Du' },
    };
    return this.vorschauCache.karte;
  }

  revealReferences(): void {
    this.showReferences = true;
  }

  speichern(): void {
    this.absenden(null);
  }

  /** Die Person hat den vorhandenen gesehen und will ihren Kommentar trotzdem. */
  trotzdemSpeichern(): void {
    if (this.offeneEntscheidung) {
      this.absenden(this.vorhanden!.id);
    }
  }

  /** ``trotzDubletteVon``: der gezeigte vorhandene Kommentar, den die Person uebergeht. */
  private absenden(trotzDubletteVon: string | null): void {
    // Noch nicht bestaetigte Herkunft uebernehmen, bevor der Formularwert gelesen
    // wird - sonst geht sie beim Speichern stumm verloren.
    this.referenceInput?.flushPendingInput();

    if (this.commentaryForm.invalid || this.aussageZuKurz) {
      this.commentaryForm.markAllAsTouched();
      return;
    }
    if (this.beschaeftigt) {
      return;
    }

    this.speichert = true;
    this.fehler = null;
    this.validierung = null;
    this.vorhandenVergessen();

    const { text, references } = this.commentaryForm.value;
    // Ein Satz: eingefuegte Umbrueche werden zu Leerzeichen (Enter selbst bricht nicht um).
    const title = einzeilig(this.commentaryForm.value.title);
    const request: AddCommentaryRequest = {
      commentary: { title, text, references: [] },
      // Die Herkunft als Text; das Backend legt sie an oder findet sie wieder.
      references: references || [],
      ...this.aussageFuerAnfrage(),
      ...(trotzDubletteVon ? { trotz_dublette_von: trotzDubletteVon } : {}),
    };

    this.commentaryService.addCommentary(request).subscribe({
      next: (antwort) => {
        this.speichert = false;
        if (antwort.dublette) {
          // Nichts angelegt und nichts verknuepft: Das Formular bleibt, der Hinweis
          // zeigt den vorhandenen. Kein Erfolg - ein Einwurf aus dem Fangkorb bleibt,
          // wie er war.
          this.vorhandenZeigen(request, antwort);
          return;
        }
        this.responseId = antwort.id;
        this.success.emit(this.ergebnisAus(request, antwort));
      },
      error: (error: Error) => {
        // Die Eingaben bleiben stehen; "Erneut versuchen" speichert dasselbe noch einmal.
        this.logger.error('Error saving commentary', error);
        this.speichert = false;
        // Bei 422 sagt das Backend, was nicht passt - das ist hilfreicher als "nicht geklappt".
        const meldung = validierungsMeldung(error);
        if (meldung) {
          this.meldungZeigen(meldung);
        } else {
          this.fehler = SPEICHERN_FEHLGESCHLAGEN;
        }
      },
    });
  }

  /**
   * Das Ergebnis fuer die Ergebnisseite. Wurde eine Aussage mitgeschickt, gilt sie nur
   * als verknuepft, wenn die Antwort das ausdruecklich sagt - fehlt das Feld (etwa
   * ein aelteres Backend), steht der Hinweis da. Gezeigt wird die tatsaechlich
   * verknuepfte Aussage; bei Text kann das eine schon vorhandene, aehnliche sein.
   */
  private ergebnisAus(
    anfrage: { statement_id?: string; statement_text?: string },
    antwort: { id: string; statement_id?: string | null; statement_text?: string | null; verknuepft?: boolean },
  ): BeitragGespeichert {
    const aussageGeschickt = !!(anfrage.statement_id || anfrage.statement_text);
    const verknuepft = !aussageGeschickt || antwort.verknuepft === true;
    const aussage =
      aussageGeschickt && verknuepft && antwort.statement_id
        ? { id: antwort.statement_id, text: antwort.statement_text ?? this.aussage.text }
        : this.aussage;
    return { id: antwort.id, aussage, verknuepft };
  }

  /** Im Antwort-auf-Block steht eine Aussage (per ID oder als Text). */
  get mitAussage(): boolean {
    return !!(this.aussage.id || this.aussage.text);
  }

  /** Aussage ohne Auswahl mit 1-9 Zeichen: Speichern bleibt gesperrt, leer ist erlaubt. */
  get aussageZuKurz(): boolean {
    return !this.aussage.id && zuKurz(this.aussage.text);
  }

  /** Die gewaehlte Aussage per ID, sonst ihr Text, sonst nichts. */
  aussageFuerAnfrage(): Pick<AddCommentaryRequest, 'statement_id' | 'statement_text'> {
    if (this.aussage.id) {
      return { statement_id: this.aussage.id };
    }
    return this.aussage.text ? { statement_text: this.aussage.text } : {};
  }

  /** Dem vorhandenen, fremden Kommentar eine Stimme geben statt den eigenen zu speichern. */
  zustimmen(): void {
    const vorhanden = this.vorhanden;
    if (!vorhanden || !this.kannZustimmen || this.beschaeftigt) {
      return;
    }
    this.stimmtZu = true;
    this.entscheidungsFehler = null;
    this.votingService.setLike(vorhanden.id).subscribe({
      next: () => {
        this.stimmtZu = false;
        vorhanden.gewaehlt = 'zugestimmt';
        this.vorhandenGewaehlt.emit(vorhanden.id);
      },
      error: (error: Error) => {
        this.logger.error('Error voting for the existing commentary', error);
        this.stimmtZu = false;
        this.entscheidungsFehler = ZUSTIMMEN_FEHLGESCHLAGEN;
      },
    });
  }

  private vorhandenZeigen(anfrage: AddCommentaryRequest, antwort: AddCommentaryResponse): void {
    // Ueber diesen vorhandenen hat die Person noch nicht entschieden: Gemerkt wird die
    // Anfrage ohne die Entscheidung, die sie hierher gebracht hat.
    const { trotz_dublette_von, vorhanden_nehmen, ...ohneEntscheidung } = anfrage;
    this.vorhanden = {
      id: antwort.id,
      titel: antwort.vorhanden_titel ?? null,
      eigen: antwort.vorhanden_eigen === true,
      aussage: null,
      anfrage: ohneEntscheidung,
      gewaehlt: null,
    };
  }

  /**
   * Den eigenen vorhandenen Kommentar nehmen, ohne Stimme und ohne zweite Kopie. Mit
   * Aussage haengt ihn erst diese Wahl an sie: dieselbe Anfrage noch einmal, mit
   * `vorhanden_nehmen`. Scheitert das Verknuepfen, bleibt die Entscheidung offen.
   */
  nehmen(): void {
    const vorhanden = this.vorhanden;
    if (!vorhanden || !this.kannNehmen || this.beschaeftigt) {
      return;
    }
    if (!this.mitAussage) {
      vorhanden.gewaehlt = 'genommen';
      this.vorhandenGewaehlt.emit(vorhanden.id);
      return;
    }
    if (this.aussageZuKurz) {
      return;
    }
    this.nimmt = true;
    this.entscheidungsFehler = null;
    // Die Aussage, die jetzt im Antwort-auf-Block steht - die Person kann sie seit dem
    // ersten Versuch geaendert haben. Der Text kann es nicht: Dann waere der Hinweis weg.
    const { statement_id, statement_text, ...anfrage } = vorhanden.anfrage;
    const nehmen: AddCommentaryRequest = { ...anfrage, ...this.aussageFuerAnfrage(), vorhanden_nehmen: vorhanden.id };
    this.commentaryService.addCommentary(nehmen).subscribe({
      next: (antwort) => {
        this.nimmt = false;
        if (antwort.dublette && antwort.id !== vorhanden.id) {
          // Inzwischen ist ein anderer vorhanden: Die Person sieht erst ihn.
          this.vorhandenZeigen(nehmen, antwort);
          return;
        }
        if (antwort.verknuepft !== true || !antwort.statement_text) {
          this.entscheidungsFehler = NEHMEN_FEHLGESCHLAGEN;
          return;
        }
        vorhanden.aussage = antwort.statement_text;
        vorhanden.gewaehlt = 'genommen';
        this.vorhandenGewaehlt.emit(vorhanden.id);
      },
      error: (error: Error) => {
        this.logger.error('Error taking the existing commentary', error);
        this.nimmt = false;
        if (error instanceof HttpErrorResponse && error.status === 409) {
          // Der vorhandene ist weg; die Eingaben bleiben, Speichern legt neu an.
          this.vorhandenVergessen();
          this.meldungZeigen(VORHANDEN_WEG);
          return;
        }
        // Bei 422 sagt das Backend, was nicht passt (etwa eine zu kurze Aussage).
        this.entscheidungsFehler = validierungsMeldung(error) ?? NEHMEN_FEHLGESCHLAGEN;
      },
    });
  }

  vorhandenAnsehen(): void {
    if (this.vorhanden) {
      this.beitragAnsehen.oeffnen(this.vorhanden.id, 'commentary');
    }
  }

  zuruecksetzen(): void {
    if (!this.hatEingaben) {
      this.leeren();
      return;
    }
    this.dialog
      .open(BestaetigungsDialogComponent, { data: ZURUECKSETZEN_FRAGE, autoFocus: 'dialog' })
      .afterClosed()
      .pipe(filter((ja) => ja === true))
      .subscribe(() => this.leeren());
  }

  leeren(): void {
    this.commentaryForm.reset({ title: '', text: '', references: [] });
    this.antwortAuf?.leeren();
    this.aussage = OHNE_AUSSAGE;
    this.showReferences = false;
    this.fehler = null;
    this.vorhandenVergessen();
  }

  /**
   * Eine Meldung, nach der Speichern nicht dasselbe noch einmal schickt: Die Leiste
   * zeigt sie, und der Knopf heisst "Kommentar speichern" statt "Erneut versuchen".
   */
  private meldungZeigen(meldung: string): void {
    this.validierung = meldung;
    this.fehler = meldung;
  }

  private vorhandenVergessen(): void {
    this.vorhanden = null;
    this.entscheidungsFehler = null;
  }
}
