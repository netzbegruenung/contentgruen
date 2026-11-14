import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { TextFieldModule } from '@angular/cdk/text-field';
import { MatSelectModule } from '@angular/material/select';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { PostService, AddPostRequest } from '../services/post.service';
import { LoggingService } from '../services/logging.service';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenDaten, ausSuchergebnis } from '../beitragskarte/karten-daten';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import type { Vorbefuellung } from '../destillieren/destillier-uebergabe.service';
import { Cc0HinweisComponent } from '../shared/cc0-hinweis/cc0-hinweis.component';
import { typFarbe } from '../shared/content-type-registry';
import { PLATTFORMEN, Plattform, plattformAusUrl, plattformName } from '../shared/plattform';
import { einzeilig } from '../beitragsformular/einzeilig';
import { validierungsMeldung } from '../beitragsformular/speicherfehler';
import { EinwilligungHinweisComponent } from '../einwilligung/einwilligung-hinweis.component';
import { einwilligungFehlt } from '../services/art9-einwilligung.service';
import { Art9EinwilligungZustand } from '../services/art9-einwilligung-zustand';
import { FormularHilfeComponent } from '../beitragsformular/formular-hilfe/formular-hilfe.component';
import { GegenlesenComponent } from '../beitragsformular/gegenlesen/gegenlesen.component';
import { SprachhinweisComponent } from '../shared/components/sprachhinweis/sprachhinweis.component';
import { FormularLeisteComponent } from '../beitragsformular/formular-leiste/formular-leiste.component';
import type { BeitragGespeichert } from '../beitragsformular/beitrag-gespeichert/gespeichert-adresse';
import {
  AntwortAuf,
  AntwortAufComponent,
  OHNE_AUSSAGE,
  zuKurz,
} from '../beitragsformular/antwort-auf/antwort-auf.component';
import { alsGespeichert, aussageFuerAnfrage } from '../beitragsformular/aussage-fuer-anfrage';
import { ThemenWahl } from '../beitragsformular/themen-wahl';
import { ThemenAuswahlComponent } from '../shared/themen/themen-auswahl.component';
import { einspaltig } from '../beitragsformular/gegenlesen/einspaltig';

/**
 * Wie beim Bild: Der Post-Titel beschreibt, er folgt der Behauptungsregel fuer
 * Kommentar und Hintergrundinfo nicht (CODING_STANDARDS.md). Das Backend erlaubt 500; die
 * Titelbox der Karte kuerzt Laengeres ohnehin nach drei Zeilen.
 */
export const TITEL_MAX = 200;
export const TEXT_MAX = 2000;
/** Ein Konto-Name oder Handle, kein Text. */
export const AUTOR_MAX = 200;

export const SPEICHERN_FEHLGESCHLAGEN =
  'Speichern hat nicht geklappt. Deine Eingaben sind noch da – versuch es gleich noch einmal.';

/**
 * Das Post-Formular: Link, Plattform, wer ihn gepostet hat, Titel und in eigenen
 * Worten, worum es geht - daneben (am Handy darunter) die Vorschau.
 *
 * Der Link fuehrt zum Post selbst; die Plattform folgt ihm, bis die Person sie
 * selbst waehlt. Ein eigenes Herkunft-Feld hat das Formular nicht: Der Link ist
 * der Post selbst (Fachfrage in #338). Wie Kommentar und Hintergrundinfo kann ein
 * Post auf eine Aussage antworten (optional, #619); eine Dublettenpruefung kennt er
 * nicht. Nach dem Speichern meldet `success` ID, Aussage und ob verknuepft wurde;
 * wohin es weitergeht, entscheidet der Workflow.
 */
@Component({
  standalone: true,
  selector: 'app-add-post',
  templateUrl: './add-post.component.html',
  styleUrls: ['./add-post.component.scss'],
  imports: [
    ...SHARED_IMPORTS,
    EinwilligungHinweisComponent,
    CommonModule,
    ReactiveFormsModule,
    TextFieldModule,
    MatSelectModule,
    BeitragskarteComponent,
    FormularHilfeComponent,
    AntwortAufComponent,
    ThemenAuswahlComponent,
    GegenlesenComponent,
    SprachhinweisComponent,
    FormularLeisteComponent,
    Cc0HinweisComponent,
  ],
})
export class AddPostComponent implements OnChanges {
  private readonly einwilligungZustand = inject(Art9EinwilligungZustand);
  /** Einspaltig steht das Gegenlesen kompakt unter dem Textfeld (Nutzerfuehrung 13.11.). */
  readonly einspaltig = einspaltig();
  /** Streifen ueber dem Formular in der Farbe des Kartenbands. */
  readonly typFarbe = typFarbe('post');
  readonly plattformen = PLATTFORMEN;
  readonly titelMax = TITEL_MAX;
  readonly textMax = TEXT_MAX;
  readonly autorMax = AUTOR_MAX;

  /** Aus dem Destillier-Ablauf: Satz als Titel, Link des Einwurfs, der Einwurf als Kopf. */
  @Input() vorbefuellung: Vorbefuellung | null = null;
  @Output() success = new EventEmitter<BeitragGespeichert>();

  readonly postForm: FormGroup;
  /** Die Themen einer neuen Aussage (#455). */
  readonly themenWahl: ThemenWahl;

  /** Was im Antwort-auf-Block gilt. */
  aussage: AntwortAuf = OHNE_AUSSAGE;

  speichert = false;
  fehler: string | null = null;
  /** Die knappe Validierungsmeldung des Backends bei 422; dann nicht "Erneut versuchen". */
  validierung: string | null = null;
  /** Gesetzt, sobald der Post gespeichert ist. */
  responseId = '';

  private vorschauCache?: { werte: unknown; aussage: string; karte: KartenDaten };

  constructor(
    fb: FormBuilder,
    private postService: PostService,
    private logger: LoggingService,
  ) {
    this.postForm = fb.group({
      url: ['', [Validators.required, Validators.pattern(/^https?:\/\/\S+$/)]],
      platform: ['' as Plattform | '', Validators.required],
      author: ['', [Validators.maxLength(AUTOR_MAX)]],
      title: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(TITEL_MAX)]],
      text: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(TEXT_MAX)]],
      themen: [[] as string[]],
    });
    this.themenWahl = new ThemenWahl(this.postForm.get('themen')!);
    // Die Plattform folgt dem Link, bis die Person sie selbst waehlt.
    this.postForm
      .get('url')!
      .valueChanges.pipe(takeUntilDestroyed())
      .subscribe((url: string) => this.plattformAusLink(url));
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['vorbefuellung'] && this.vorbefuellung) {
      this.postForm.patchValue({
        title: this.vorbefuellung.titel,
        ...(this.vorbefuellung.url ? { url: this.vorbefuellung.url } : {}),
      });
    }
  }

  private plattformAusLink(url: string): void {
    const plattform = this.postForm.get('platform')!;
    if (plattform.dirty) {
      return;
    }
    plattform.setValue(plattformAusUrl(url) ?? '');
  }

  /** Was im Antwort-auf-Block gilt; die Themen passen sich an (ThemenWahl). */
  aussageSetzen(aussage: AntwortAuf): void {
    this.aussage = aussage;
    this.themenWahl.anAussageAnpassen(aussage);
  }

  get zeigtThemen(): boolean {
    return this.themenWahl.zeigtFuer(this.aussage);
  }

  /** Aussage ohne Auswahl mit 1-9 Zeichen: Speichern bleibt gesperrt, leer ist erlaubt. */
  get aussageZuKurz(): boolean {
    return !this.aussage.id && zuKurz(this.aussage.text);
  }

  get titelLaenge(): number {
    return this.postForm.get('title')?.value?.length ?? 0;
  }

  get textLaenge(): number {
    return this.postForm.get('text')?.value?.length ?? 0;
  }

  /**
   * Die Vorschau als KartenDaten, zwischengespeichert, solange sich nichts aendert.
   * Ohne Nutzung und Datum: Ueber einen Entwurf sagen sie nichts.
   */
  get vorschauKarte(): KartenDaten {
    const werte = this.postForm.value;
    const cache = this.vorschauCache;
    if (cache && cache.werte === werte && cache.aussage === this.aussage.text) {
      return cache.karte;
    }
    const karte = ausSuchergebnis({
      post_result: {
        id: 'vorschau',
        content_type: 'post',
        title: werte.title || 'Titel',
        text: werte.text || 'Worum es im Post geht',
        platform: werte.platform ? plattformName(werte.platform) : '',
        author: werte.author,
        url: werte.url,
        original_author: 'Du',
      },
      score: 1,
      statement_text: this.aussage.text,
      statement_similarity_score: 0,
      reply_relevance: 0,
    } as any);
    this.vorschauCache = {
      werte,
      aussage: this.aussage.text,
      karte: { ...karte, nutzung: null, erstellt: '', autorName: 'Du' },
    };
    return this.vorschauCache.karte;
  }

  speichern(): void {
    if (this.postForm.invalid || this.aussageZuKurz) {
      this.postForm.markAllAsTouched();
      return;
    }
    if (this.speichert) {
      return;
    }

    this.speichert = true;
    this.fehler = null;
    this.validierung = null;

    const { url, platform, author, text, themen } = this.postForm.value;
    const aussage = aussageFuerAnfrage(this.aussage, themen ?? []);
    const request: AddPostRequest = {
      post: {
        // Ein Titel ist eine Zeile: eingefuegte Umbrueche werden zu Leerzeichen.
        title: einzeilig(this.postForm.value.title),
        text,
        // Gespeichert wird der Name, wie die Karte ihn zeigt.
        platform: plattformName(platform),
        // Optional (#618): leer bleibt leer, damit kein Konto Dritter erfunden wird.
        author: (author ?? '').trim() || null,
        url: url.trim(),
      },
      ...aussage,
    };

    this.postService.addPost(request).subscribe({
      next: (antwort) => {
        this.speichert = false;
        this.responseId = antwort.id;
        this.success.emit(alsGespeichert(antwort.id, this.aussage, aussage, antwort));
      },
      error: (error: Error) => {
        // Die Eingaben bleiben stehen; der Knopf speichert dasselbe noch einmal.
        this.logger.error('Error saving post', error);
        this.speichert = false;
        // Ohne Einwilligung sagt der Hinweiskasten ueber dem Formular, was zu tun ist (B4).
        if (einwilligungFehlt(error)) {
          this.fehler = null;
          this.einwilligungZustand.hinweisZeigen();
          return;
        }
        this.validierung = validierungsMeldung(error);
        this.fehler = this.validierung ?? SPEICHERN_FEHLGESCHLAGEN;
      },
    });
  }
}
