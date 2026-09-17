import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { TextFieldModule } from '@angular/cdk/text-field';
import { MatDialog } from '@angular/material/dialog';
import { filter } from 'rxjs/operators';

import { CommentaryService } from '../services/commentary.service';
import { LoggingService } from '../services/logging.service';
import { AddCommentaryRequest } from '../services/dtos/commentaryDtos';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenDaten, ausSuchergebnis } from '../beitragskarte/karten-daten';
import { ReferenceInputComponent } from '../reference-input/reference-input.component';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import type { Vorbefuellung } from '../destillieren/destillier-uebergabe.service';
import { CONSENT_HINWEIS } from '../shared/consent-hinweis';
import { typFarbe } from '../shared/content-type-registry';
import { einzeilig } from '../beitragsformular/einzeilig';
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

export const SPEICHERN_FEHLGESCHLAGEN =
  'Speichern hat nicht geklappt. Deine Eingaben sind noch da – versuch es gleich noch einmal.';

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
  /** Gesetzt, sobald der Kommentar gespeichert ist. */
  responseId = '';
  /** ID eines schon vorhandenen, sehr aehnlichen Kommentars; dann wurde nichts angelegt. */
  dublette: string | null = null;
  readonly dublettenHinweis = DUBLETTE_HINWEIS;

  private vorschauCache?: { titel: string; text: string; quellen: unknown; aussage: string; karte: KartenDaten };

  constructor(
    fb: FormBuilder,
    private commentaryService: CommentaryService,
    private logger: LoggingService,
    private dialog: MatDialog,
    private beitragAnsehen: BeitragAnsehenService,
  ) {
    this.commentaryForm = fb.group({
      title: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(TITEL_MAX)]],
      text: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(TEXT_MAX)]],
      references: [[]],
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
    // Noch nicht bestaetigte Herkunft uebernehmen, bevor der Formularwert gelesen
    // wird - sonst geht sie beim Speichern stumm verloren.
    this.referenceInput?.flushPendingInput();

    if (this.commentaryForm.invalid || this.aussageZuKurz) {
      this.commentaryForm.markAllAsTouched();
      return;
    }
    if (this.speichert) {
      return;
    }

    this.speichert = true;
    this.fehler = null;
    this.dublette = null;

    const { text, references } = this.commentaryForm.value;
    // Ein Satz: eingefuegte Umbrueche werden zu Leerzeichen (Enter selbst bricht nicht um).
    const title = einzeilig(this.commentaryForm.value.title);
    const request: AddCommentaryRequest = {
      commentary: { title, text, references: [] },
      // Die Herkunft als Text; das Backend legt sie an oder findet sie wieder.
      references: references || [],
      ...this.aussageFuerAnfrage(),
    };

    this.commentaryService.addCommentary(request).subscribe({
      next: (antwort) => {
        this.speichert = false;
        if (antwort.duplikat) {
          // Nichts angelegt: Das Formular bleibt, der Hinweis zeigt den vorhandenen.
          this.dublette = antwort.id;
          return;
        }
        this.responseId = antwort.id;
        this.success.emit(this.ergebnisAus(request, antwort));
      },
      error: (error: Error) => {
        // Die Eingaben bleiben stehen; "Erneut versuchen" speichert dasselbe noch einmal.
        this.logger.error('Error saving commentary', error);
        this.speichert = false;
        this.fehler = SPEICHERN_FEHLGESCHLAGEN;
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

  dubletteAnsehen(): void {
    if (this.dublette) {
      this.beitragAnsehen.oeffnen(this.dublette, 'commentary');
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
  }
}
