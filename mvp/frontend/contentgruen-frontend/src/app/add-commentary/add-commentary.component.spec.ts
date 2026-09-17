import { ComponentFixture, TestBed, fakeAsync, flush } from '@angular/core/testing';
import { SimpleChange } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialog } from '@angular/material/dialog';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { AddCommentaryComponent, SPEICHERN_FEHLGESCHLAGEN } from './add-commentary.component';
import { CommentaryService } from '../services/commentary.service';
import { AddCommentaryRequest, AddCommentaryResponse } from '../services/dtos/commentaryDtos';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { BeitragskarteStubComponent } from '../beitragskarte/beitragskarte.stub';
import { AntwortAufComponent } from '../beitragsformular/antwort-auf/antwort-auf.component';

describe('AddCommentaryComponent', () => {
  let component: AddCommentaryComponent;
  let fixture: ComponentFixture<AddCommentaryComponent>;
  let dialog: { open: jasmine.Spy };

  const ID = '5f0c4a8e-1b2c-4d3e-8f90-123456789abc';

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AddCommentaryComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    })
      .overrideComponent(AddCommentaryComponent, {
        remove: { imports: [BeitragskarteComponent] },
        add: { imports: [BeitragskarteStubComponent] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(AddCommentaryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    // MatDialog kommt ueber die Imports der Komponente, nicht aus dem TestBed.
    dialog = { open: spyOn(fixture.debugElement.injector.get(MatDialog), 'open') };
  });

  function seite(): HTMLElement {
    return fixture.nativeElement;
  }

  function ausfuellen(): void {
    component.commentaryForm.patchValue({ title: 'Wärmepumpe lohnt sich im Altbau', text: 'Ein ausreichend langer Text.' });
    fixture.detectChanges();
  }

  function speichernMit(antwort: Partial<AddCommentaryResponse> = {}): jasmine.Spy {
    return spyOn(TestBed.inject(CommentaryService), 'addCommentary').and.returnValue(
      of({ id: 'k-1', ...antwort } as AddCommentaryResponse),
    );
  }

  function aussageAusAdresse(text: string, id = ''): void {
    component.statementText = text;
    component.statementId = id;
    component.ngOnChanges({ statementText: new SimpleChange('', text, true) });
    fixture.detectChanges();
  }

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('Aufbau', () => {
    it('hat kein Typband, keine Schrittnummern und keine Text-Varianten mehr', () => {
      expect(seite().querySelector('.content-type-indicator')).toBeNull();
      expect(seite().querySelector('.step-indicator')).toBeNull();
      expect(seite().querySelector('.optional-toggle')).toBeNull();
      expect(seite().querySelector('[formControlName="long_text"]')).toBeNull();
      expect(component.commentaryForm.get('long_text')).toBeNull();
    });

    it('zeigt die Qualitaetszeile mit dem ?, anfangs zugeklappt', () => {
      expect(seite().querySelector('.hilfe-zeile')!.textContent).toContain('So formuliert, dass auch eine unentschiedene Nachbarin mitgeht.');
      expect(seite().querySelector('.hilfe-panel')).toBeNull();

      (seite().querySelector('.erklaerung-umschalter') as HTMLButtonElement).click();
      fixture.detectChanges();

      expect(seite().querySelector('.hilfe-panel')!.textContent).toContain('Nimmt die Sorge hinter der Aussage ernst');
    });

    it('beschriftet Titel und Kommentar mit je einem Pflichtzeichen', () => {
      const labels = Array.from(seite().querySelectorAll('mat-label')).map((l) => l.textContent!.trim());
      expect(labels).toContain('Titel');
      expect(labels).toContain('Kommentar');
      expect(seite().textContent).not.toContain('Haupttext');
      expect(seite().textContent).not.toContain('Titel*');
    });

    it('fragt im Titelfeld nach dem Punkt in einem Satz', () => {
      const input: HTMLTextAreaElement = seite().querySelector('textarea#title')!;
      expect(input.placeholder).toBe('Was ist der Punkt? Ein Satz.');
    });

    it('verlinkt die Nutzungsbedingungen ueber dem Absenden-Knopf', () => {
      const link: HTMLAnchorElement | null = seite().querySelector('a[href="/nutzungsbedingungen"]');

      expect(link).toBeTruthy();
      expect(link!.target).toBe('_blank');
    });

    it('beschriftet den Knopf mit "Kommentar speichern" und zeigt kein Info-Icon an der Vorschau', () => {
      expect(seite().querySelector('.submit-btn')!.textContent).toContain('Kommentar speichern');
      expect(seite().querySelector('.preview-header mat-icon')).toBeNull();
    });
  });

  describe('Titel und Kartenbezug', () => {
    it('ist zweizeilig, waechst mit und bricht bei Enter nicht um', () => {
      const titel: HTMLTextAreaElement = seite().querySelector('textarea#title')!;
      expect(titel.hasAttribute('cdktextareaautosize')).toBeTrue();
      expect(titel.getAttribute('cdkautosizeminrows')).toBe('2');

      const enter = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true, bubbles: true });
      titel.dispatchEvent(enter);
      expect(enter.defaultPrevented).toBeTrue();
    });

    it('zeigt Streifen in der Typfarbe und das Typ-Emoji vor der Hilfezeile', () => {
      const bereich: HTMLElement = seite().querySelector('.formular-bereich')!;
      expect(bereich.style.getPropertyValue('--typ-farbe')).toBe('var(--commentary-bg)');
      expect(seite().querySelector('.hilfe-emoji')!.textContent!.trim()).toBe('💬');
    });
  });

  describe('Grenzen und Zaehler', () => {
    // Titel = Behauptung in einem Satz. Das Limit ist auf die Titelbox der
    // Suchkarte ausgemessen und muss mit dem Backend-Modell uebereinstimmen.
    it('begrenzt den Titel auf 120 und den Kommentar auf 500 Zeichen', () => {
      for (const [feld, limit] of [['title', 120], ['text', 500]] as const) {
        const control = component.commentaryForm.get(feld)!;
        control.setValue('a'.repeat(limit));
        expect(control.hasError('maxlength')).withContext(feld).toBeFalse();
        control.setValue('a'.repeat(limit + 1));
        expect(control.hasError('maxlength')).withContext(feld).toBeTrue();
      }
      expect((seite().querySelector('textarea#title') as HTMLTextAreaElement).maxLength).toBe(120);
      expect((seite().querySelector('textarea#text') as HTMLTextAreaElement).maxLength).toBe(500);
    });

    it('zaehlt einheitlich "x / max"', () => {
      component.commentaryForm.patchValue({ title: 'abc', text: 'abcdefghij' });
      fixture.detectChanges();

      const hinweise = Array.from(seite().querySelectorAll('mat-hint')).map((h) => h.textContent!.trim());
      expect(hinweise).toContain('3 / 120');
      expect(hinweise).toContain('10 / 500');
    });

    it('sagt bis 280 Zeichen "passt auf X/Bluesky", darueber "zu lang", ohne Fehler', () => {
      component.commentaryForm.patchValue({ text: 'a'.repeat(280) });
      fixture.detectChanges();
      expect(seite().querySelector('.plattform-hinweis')!.textContent).toContain('passt auf X/Bluesky');

      component.commentaryForm.patchValue({ text: 'a'.repeat(281) });
      fixture.detectChanges();
      const hinweis = seite().querySelector('.plattform-hinweis')!;
      expect(hinweis.textContent).toContain('zu lang für X/Bluesky');
      expect(component.commentaryForm.get('text')!.valid).toBeTrue();
    });

    it('laesst das Kommentarfeld mitwachsen', () => {
      expect(seite().querySelector('textarea#text')!.hasAttribute('cdktextareaautosize')).toBeTrue();
    });
  });

  describe('Speichern', () => {
    it('schickt Titel, Text und Herkunft ohne Lang- und Kurztext', fakeAsync(() => {
      const hinzufuegen = speichernMit();
      ausfuellen();

      component.speichern();
      flush();

      const anfrage: AddCommentaryRequest = hinzufuegen.calls.mostRecent().args[0];
      expect(anfrage.commentary).toEqual({
        title: 'Wärmepumpe lohnt sich im Altbau',
        text: 'Ein ausreichend langer Text.',
        references: [],
      });
      expect('long_text' in anfrage.commentary).toBeFalse();
      expect(anfrage.statement_id).toBeUndefined();
      expect(anfrage.statement_text).toBeUndefined();
    }));

    it('speichert eingefuegte Umbrueche im Titel als Leerzeichen', fakeAsync(() => {
      const hinzufuegen = speichernMit();
      ausfuellen();
      component.commentaryForm.patchValue({ title: 'Wärmepumpen\nlohnen sich\r\n im Altbau' });

      component.speichern();
      flush();

      expect(hinzufuegen.calls.mostRecent().args[0].commentary.title).toBe('Wärmepumpen lohnen sich im Altbau');
    }));

    it('meldet nach dem Speichern ID, Aussage und Verknuepfung', fakeAsync(() => {
      speichernMit();
      const erfolg = spyOn(component.success, 'emit');
      ausfuellen();

      component.speichern();
      flush();

      expect(erfolg).toHaveBeenCalledOnceWith({ id: 'k-1', aussage: { id: '', text: '' }, verknuepft: true });
    }));

    it('behaelt bei einem Fehler die Eingaben, und "Erneut versuchen" speichert dasselbe noch einmal', fakeAsync(() => {
      const hinzufuegen = spyOn(TestBed.inject(CommentaryService), 'addCommentary').and.returnValues(
        throwError(() => new Error('500')),
        of({ id: 'k-1' } as AddCommentaryResponse),
      );
      const erfolg = spyOn(component.success, 'emit');
      ausfuellen();

      component.speichern();
      flush();
      fixture.detectChanges();

      expect(seite().querySelector('.speicher-fehler')!.textContent).toContain(SPEICHERN_FEHLGESCHLAGEN);
      // Knapp auch in der Leiste: am Handy laege die Meldung im Formular hinter ihr.
      expect(seite().querySelector('app-formular-leiste .leiste-fehler')!.textContent).toContain('Speichern hat nicht geklappt.');
      expect(component.commentaryForm.value.title).toBe('Wärmepumpe lohnt sich im Altbau');
      const knopf: HTMLButtonElement = seite().querySelector('.submit-btn')!;
      expect(knopf.textContent).toContain('Erneut versuchen');

      knopf.click();
      flush();

      expect(hinzufuegen).toHaveBeenCalledTimes(2);
      expect(hinzufuegen.calls.argsFor(1)[0]).toEqual(hinzufuegen.calls.argsFor(0)[0]);
      expect(erfolg).toHaveBeenCalledOnceWith(jasmine.objectContaining({ id: 'k-1' }));
    }));
  });

  describe('Antwort auf eine Aussage', () => {
    function antwortAuf(): AntwortAufComponent {
      return fixture.debugElement.query((el) => el.componentInstance instanceof AntwortAufComponent)
        .componentInstance;
    }

    it('schickt die Aussage aus der Adresse per ID', fakeAsync(() => {
      const hinzufuegen = speichernMit({ statement_id: ID, verknuepft: true });
      aussageAusAdresse('Wärmepumpen sind zu teuer', ID);
      ausfuellen();

      component.speichern();
      flush();

      const anfrage: AddCommentaryRequest = hinzufuegen.calls.mostRecent().args[0];
      expect(anfrage.statement_id).toBe(ID);
      expect(anfrage.statement_text).toBeUndefined();
      expect(seite().querySelector('.gewaehlt-karte')).toBeTruthy();
    }));

    it('schickt nur den Text, wenn die Aussage keine gueltige ID hat', fakeAsync(() => {
      const hinzufuegen = speichernMit();
      aussageAusAdresse('Wärmepumpen sind zu teuer', 'None');
      ausfuellen();

      component.speichern();
      flush();

      const anfrage: AddCommentaryRequest = hinzufuegen.calls.mostRecent().args[0];
      expect(anfrage.statement_id).toBeUndefined();
      expect(anfrage.statement_text).toBe('Wärmepumpen sind zu teuer');
    }));

    it('schickt nichts, wenn die gewaehlte Aussage entfernt wurde', fakeAsync(() => {
      const hinzufuegen = speichernMit();
      aussageAusAdresse('Wärmepumpen sind zu teuer', ID);
      antwortAuf().entfernen();
      ausfuellen();

      component.speichern();
      flush();

      const anfrage: AddCommentaryRequest = hinzufuegen.calls.mostRecent().args[0];
      expect(anfrage.statement_id).toBeUndefined();
      expect(anfrage.statement_text).toBeUndefined();
    }));

    it('legt beim Oeffnen und Tippen keine Aussage an', () => {
      const http = TestBed.inject(HttpTestingController);

      aussageAusAdresse('Wärmepumpen sind zu teuer');
      const feld: HTMLTextAreaElement = seite().querySelector('.antwort-eingabe')!;
      feld.value = 'Ganz andere Aussage';
      feld.dispatchEvent(new Event('input'));
      feld.dispatchEvent(new Event('blur'));

      http.expectNone((r) => r.url.includes('/statement/addStatement') || r.url.includes('addReplysuggestion'));
      expect(component.aussage).toEqual({ id: '', text: 'Ganz andere Aussage' });
    });

    it('reicht eine gescheiterte Verknuepfung an die Ergebnisseite weiter', fakeAsync(() => {
      speichernMit({ verknuepft: false });
      const erfolg = spyOn(component.success, 'emit');
      aussageAusAdresse('Wärmepumpen sind zu teuer', ID);
      ausfuellen();

      component.speichern();
      flush();

      expect(erfolg).toHaveBeenCalledOnceWith({
        id: 'k-1',
        aussage: { id: ID, text: 'Wärmepumpen sind zu teuer' },
        verknuepft: false,
      });
    }));
  });

  describe('Vorschau', () => {
    it('zeigt weder Nutzung noch Neu-Datum', () => {
      ausfuellen();

      expect(component.vorschauKarte.nutzung).toBeNull();
      expect(component.vorschauKarte.erstellt).toBe('');
      expect(component.vorschauKarte.titel).toBe('Wärmepumpe lohnt sich im Altbau');
    });

    it('bleibt dieselbe Karte, solange sich nichts aendert', () => {
      ausfuellen();
      expect(component.vorschauKarte).toBe(component.vorschauKarte);
    });
  });

  describe('Zuruecksetzen', () => {
    it('fragt nach, sobald etwas eingetragen ist, und leert erst nach Ja', () => {
      ausfuellen();
      dialog.open.and.returnValue({ afterClosed: () => of(false) } as any);

      component.zuruecksetzen();
      expect(dialog.open).toHaveBeenCalledTimes(1);
      expect(component.commentaryForm.value.title).toBe('Wärmepumpe lohnt sich im Altbau');

      dialog.open.and.returnValue({ afterClosed: () => of(true) } as any);
      component.zuruecksetzen();
      expect(component.commentaryForm.value.title).toBe('');
      expect(component.aussage).toEqual({ id: '', text: '' });
    });

    it('fragt nach, wenn nur eine Aussage vorbelegt ist', () => {
      aussageAusAdresse('Wärmepumpen sind zu teuer', ID);
      dialog.open.and.returnValue({ afterClosed: () => of(true) } as any);

      component.zuruecksetzen();

      expect(dialog.open).toHaveBeenCalled();
      expect(component.aussage).toEqual({ id: '', text: '' });
    });

    it('fragt bei leerem Formular nicht nach', () => {
      component.zuruecksetzen();
      expect(dialog.open).not.toHaveBeenCalled();
    });
  });

  describe('Vorbefuellung aus dem Destillier-Ablauf', () => {
    function vorbefuellen(url: string | null): void {
      component.vorbefuellung = { rohinputId: 'id-1', titel: 'Wärmepumpe lohnt sich auch im Altbau', url, kopf: {} as any };
      component.ngOnChanges({ vorbefuellung: new SimpleChange(null, component.vorbefuellung, true) });
    }

    it('uebernimmt den Satz als Titel und den Link als Herkunft', () => {
      vorbefuellen('https://example.org/p');

      expect(component.commentaryForm.value.title).toBe('Wärmepumpe lohnt sich auch im Altbau');
      expect(component.commentaryForm.value.references).toEqual([{ reference_string: 'https://example.org/p' }]);
      expect(component.showReferences).toBeTrue();
    });

    it('laesst die Herkunft zu, wenn der Einwurf keinen Link hat', () => {
      vorbefuellen(null);

      expect(component.commentaryForm.value.title).toBe('Wärmepumpe lohnt sich auch im Altbau');
      expect(component.commentaryForm.value.references).toEqual([]);
      expect(component.showReferences).toBeFalse();
      fixture.detectChanges();
      expect(seite().querySelector('.herkunft-link')!.textContent).toContain('+ Herkunft');
    });

    it('zeigt den Einwurf als Kopf ueber dem Formular', () => {
      component.vorbefuellung = {
        rohinputId: 'id-1',
        titel: 'Satz',
        url: null,
        kopf: { id: 'id-1', typ: null, titel: 'Notiz', text: null, erstellt: '', autor: null, autorName: null, nutzung: null, quellen: [] },
      };
      component.ngOnChanges({ vorbefuellung: new SimpleChange(null, component.vorbefuellung, true) });
      fixture.detectChanges();

      expect(seite().querySelector('.einwurf-kopf')!.textContent).toContain('Notiz');
    });

    it('zeigt die Herkunft kompakt', () => {
      vorbefuellen('https://example.org/p');
      fixture.detectChanges();

      expect(seite().querySelector('.reference-input-container.kompakt')).toBeTruthy();
      expect(seite().querySelectorAll('.herkunft-link').length).toBe(0);
    });
  });
});
