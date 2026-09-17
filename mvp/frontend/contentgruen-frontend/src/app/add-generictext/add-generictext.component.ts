import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { TextFieldModule } from '@angular/cdk/text-field';
import { MatDialog } from '@angular/material/dialog';
import { filter } from 'rxjs/operators';

import { GenericTextService } from '../services/generic-text.service';
import { LoggingService } from '../services/logging.service';
import { AddGenericTextRequest } from '../services/dtos/generictextDtos';
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
import {
  BestaetigungsDialogComponent,
  BestaetigungsDialogDaten,
} from '../shared/components/bestaetigungs-dialog/bestaetigungs-dialog.component';

export const TITEL_MAX = 120;
/** Wie im AddGenericTextRequest; laenger ist keine Hintergrundinfo mehr, sondern ein Artikel. */
export const TEXT_MAX = 2000;

export const SPEICHERN_FEHLGESCHLAGEN =
  'Speichern hat nicht geklappt. Deine Eingaben sind noch da – versuch es gleich noch einmal.';

const ZURUECKSETZEN_FRAGE: BestaetigungsDialogDaten = {
  titel: 'Formular zurücksetzen?',
  text: 'Titel, Text, Aussage und Herkunft werden geleert.',
  ja: 'Zurücksetzen',
  nein: 'Abbrechen',
};

/**
 * Das Hintergrundinfo-Formular, gleich gebaut wie das Kommentarformular: Antwort
 * auf, Titel, Text, Herkunft, Leiste - und daneben (am Handy darunter) die Vorschau.
 *
 * Gespeichert wird in einem Aufruf, samt Aussage. Danach meldet `success` ID,
 * Aussage und ob verknuepft wurde; wohin es weitergeht, entscheidet der Workflow.
 */
@Component({
  standalone: true,
  selector: 'app-add-generictext',
  templateUrl: './add-generictext.component.html',
  styleUrls: ['./add-generictext.component.scss'],
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
export class AddGenerictextComponent implements OnChanges {
  readonly consentHinweis = CONSENT_HINWEIS;
  /** Streifen ueber dem Formular in der Farbe des Kartenbands. */
  readonly typFarbe = typFarbe('generictext');
  readonly titelMax = TITEL_MAX;
  readonly textMax = TEXT_MAX;

  @Input() statementText = '';
  @Input() statementId = '';
  /** Die Aussage aus der Adresse war nicht ladbar: Hinweis zeigen, Feld leer. */
  @Input() aussageHinweis: string | null = null;
  /** Aus dem Destillier-Ablauf: Satz als Titel, Link als Herkunft, der Einwurf als Kopf. */
  @Input() vorbefuellung: Vorbefuellung | null = null;
  @Output() success = new EventEmitter<BeitragGespeichert>();

  @ViewChild(ReferenceInputComponent) referenceInput?: ReferenceInputComponent;
  @ViewChild(AntwortAufComponent) antwortAuf?: AntwortAufComponent;

  readonly generictextForm: FormGroup;

  /** Die Aussage aus der Adresse, fuer den Antwort-auf-Block. */
  aussageAusAdresse: AntwortAuf = OHNE_AUSSAGE;
  /** Was im Antwort-auf-Block gerade gilt. */
  aussage: AntwortAuf = OHNE_AUSSAGE;

  showReferences = false;
  speichert = false;
  fehler: string | null = null;
  /** Die knappe Validierungsmeldung des Backends bei 422, sonst null. */
  validierung: string | null = null;
  /** Gesetzt, sobald die Hintergrundinfo gespeichert ist. */
  responseId = '';

  private vorschauCache?: { titel: string; text: string; quellen: unknown; aussage: string; karte: KartenDaten };

  constructor(
    fb: FormBuilder,
    private genericTextService: GenericTextService,
    private logger: LoggingService,
    private dialog: MatDialog,
  ) {
    this.generictextForm = fb.group({
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
    this.generictextForm.patchValue({
      title: vorbefuellung.titel,
      references: vorbefuellung.url ? [{ reference_string: vorbefuellung.url }] : [],
    });
    if (vorbefuellung.url) {
      this.showReferences = true;
    }
  }

  get titelLaenge(): number {
    return this.generictextForm.get('title')?.value?.length ?? 0;
  }

  get textLaenge(): number {
    return this.generictextForm.get('text')?.value?.length ?? 0;
  }

  /** Irgendetwas eingetragen oder vorbelegt - dann fragt Zuruecksetzen nach. */
  get hatEingaben(): boolean {
    const { title, text, references } = this.generictextForm.value;
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
    const { title, text, references } = this.generictextForm.value;
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
      generictext_result: {
        id: 'vorschau',
        content_type: 'generic_text',
        title: title || 'Titel',
        text: text || 'Deine Hintergrundinfo',
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

    if (this.generictextForm.invalid || this.aussageZuKurz) {
      this.generictextForm.markAllAsTouched();
      return;
    }
    if (this.speichert) {
      return;
    }

    this.speichert = true;
    this.fehler = null;
    this.validierung = null;

    const { text, references } = this.generictextForm.value;
    // Ein Satz: eingefuegte Umbrueche werden zu Leerzeichen (Enter selbst bricht nicht um).
    const title = einzeilig(this.generictextForm.value.title);
    const request: AddGenericTextRequest = {
      generictext: { title, text },
      // Die Herkunft als Text; das Backend legt sie an oder findet sie wieder.
      references: references || [],
      ...this.aussageFuerAnfrage(),
    };

    this.genericTextService.addGenericText(request).subscribe({
      next: (antwort) => {
        this.speichert = false;
        this.responseId = antwort.id;
        this.success.emit(this.ergebnisAus(request, antwort));
      },
      error: (error: Error) => {
        // Die Eingaben bleiben stehen; "Erneut versuchen" speichert dasselbe noch einmal.
        this.logger.error('Error saving generic text', error);
        this.speichert = false;
        // Bei 422 sagt das Backend, was nicht passt - das ist hilfreicher als "nicht geklappt".
        this.validierung = validierungsMeldung(error);
        this.fehler = this.validierung ?? SPEICHERN_FEHLGESCHLAGEN;
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
  aussageFuerAnfrage(): Pick<AddGenericTextRequest, 'statement_id' | 'statement_text'> {
    if (this.aussage.id) {
      return { statement_id: this.aussage.id };
    }
    return this.aussage.text ? { statement_text: this.aussage.text } : {};
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
    this.generictextForm.reset({ title: '', text: '', references: [] });
    this.antwortAuf?.leeren();
    this.aussage = OHNE_AUSSAGE;
    this.showReferences = false;
    this.fehler = null;
  }
}
