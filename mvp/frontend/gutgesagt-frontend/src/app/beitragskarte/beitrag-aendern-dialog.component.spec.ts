import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { provideRouter } from '@angular/router';
import { NEVER, of, Subject, throwError } from 'rxjs';

import { BeitragAendernDialogComponent, aendernFehlertext } from './beitrag-aendern-dialog.component';
import { KartenDaten } from './karten-daten';
import { MeineBeitraegeService } from '../services/meine-beitraege.service';
import { ReferenceService } from '../services/reference.service';

describe('BeitragAendernDialogComponent', () => {
  let fixture: ComponentFixture<BeitragAendernDialogComponent>;
  let komponente: BeitragAendernDialogComponent;
  let dialogRef: jasmine.SpyObj<MatDialogRef<BeitragAendernDialogComponent>>;
  let beitraege: jasmine.SpyObj<MeineBeitraegeService>;

  const daten: KartenDaten = {
    id: 'b-1',
    typ: 'commentary',
    titel: 'Wärmepumpen rechnen sich im Altbau',
    text: 'Mit Förderung liegt die Wärmepumpe nach zehn Jahren vorn.',
    erstellt: '2026-09-12T10:00:00',
    autor: 'user-001',
    autorName: null,
    nutzung: 3,
    quellen: [
      { id: 'r-1', url: 'https://example.org/studie', beschreibung: 'Feldtest', notiz: 'Feldtest' },
      // Ohne eigene Notiz zeigt die Karte den Text der Herkunft; der wird keine Notiz.
      { id: 'r-2', url: 'https://example.org/zweite', beschreibung: 'Text einer anderen Person' },
    ],
  };

  function erstellen(karte: KartenDaten = daten): void {
    TestBed.overrideProvider(MAT_DIALOG_DATA, { useValue: karte });
    fixture = TestBed.createComponent(BeitragAendernDialogComponent);
    komponente = fixture.componentInstance;
    fixture.detectChanges();
  }

  function speichernKnopf(): HTMLButtonElement {
    return fixture.nativeElement.querySelector('.speichern-knopf');
  }

  beforeEach(() => {
    dialogRef = jasmine.createSpyObj('MatDialogRef', ['close']);
    beitraege = jasmine.createSpyObj('MeineBeitraegeService', ['beitragAendern']);

    TestBed.configureTestingModule({
      imports: [BeitragAendernDialogComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: MAT_DIALOG_DATA, useValue: daten },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: MeineBeitraegeService, useValue: beitraege },
        { provide: ReferenceService, useValue: jasmine.createSpyObj('ReferenceService', ['addReference', 'isValidUrl']) },
      ],
    });
  });

  it('füllt Titel, Text und Herkunft aus dem Beitrag vor', () => {
    erstellen();

    expect(komponente.formular.value).toEqual({
      title: daten.titel!,
      text: daten.text!,
      references: [
        { reference_string: 'https://example.org/studie', description: 'Feldtest' },
        { reference_string: 'https://example.org/zweite', description: undefined },
      ],
    });
  });

  it('nimmt beim Kommentar die Grenze des Formulars: 500 Zeichen', () => {
    erstellen();
    komponente.formular.controls.text.setValue('x'.repeat(501));

    expect(komponente.formular.valid).toBeFalse();
  });

  it('nimmt bei der Hintergrundinfo die Grenze des Formulars: 2000 Zeichen', () => {
    erstellen({ ...daten, typ: 'generictext' });
    komponente.formular.controls.text.setValue('x'.repeat(501));
    expect(komponente.formular.valid).toBeTrue();

    komponente.formular.controls.text.setValue('x'.repeat(2001));
    expect(komponente.formular.valid).toBeFalse();
  });

  it('speichert Titel, Text und Herkunft und schliesst mit true', () => {
    beitraege.beitragAendern.and.returnValue(of(undefined));
    erstellen();
    komponente.formular.controls.title.setValue('  Wärmepumpen sparen auch im Altbau Geld ');

    speichernKnopf().click();

    expect(beitraege.beitragAendern).toHaveBeenCalledOnceWith('b-1', {
      title: 'Wärmepumpen sparen auch im Altbau Geld',
      text: daten.text!,
      references: [
        { reference_string: 'https://example.org/studie', description: 'Feldtest' },
        { reference_string: 'https://example.org/zweite', description: undefined },
      ],
    });
    expect(dialogRef.close).toHaveBeenCalledOnceWith(true);
  });

  it('übernimmt beim Speichern eine getippte, noch nicht bestätigte Herkunft', () => {
    beitraege.beitragAendern.and.returnValue(of(undefined));
    erstellen();
    const herkuenfte = TestBed.inject(ReferenceService) as jasmine.SpyObj<ReferenceService>;
    herkuenfte.isValidUrl.and.returnValue(true);
    herkuenfte.addReference.and.returnValue(NEVER);
    komponente.referenceInput!.urlControl.setValue('https://example.org/dritte');

    speichernKnopf().click();

    const gesendet = beitraege.beitragAendern.calls.mostRecent().args[1];
    expect(gesendet.references.map((h) => h.reference_string)).toEqual([
      'https://example.org/studie',
      'https://example.org/zweite',
      'https://example.org/dritte',
    ]);
  });

  it('zeigt über dem Speichern-Knopf den CC0-Hinweis', () => {
    erstellen();

    expect(fixture.nativeElement.querySelector('p[appCc0Hinweis]').textContent).toContain('CC0');
  });

  it('speichert nicht mit einem Text unter 10 Zeichen, wie beim Anlegen', () => {
    erstellen();
    komponente.formular.controls.text.setValue('Zu kurz');
    fixture.detectChanges();

    expect(speichernKnopf().disabled).toBeTrue();
  });

  it('speichert nicht mit einem Titel unter 3 Zeichen', () => {
    erstellen();
    komponente.formular.controls.title.setValue('ab');
    fixture.detectChanges();

    expect(speichernKnopf().disabled).toBeTrue();
  });

  it('bleibt offen und zeigt den Fehler, wenn Speichern scheitert', () => {
    beitraege.beitragAendern.and.returnValue(
      throwError(() => ({ status: 400, error: { detail: 'Ungültige Adresse' } })),
    );
    erstellen();

    speichernKnopf().click();
    fixture.detectChanges();

    expect(dialogRef.close).not.toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector('.fehler').textContent).toContain('Ungültige Adresse');
    expect(speichernKnopf().disabled).toBeFalse();
  });

  it('speichert bei zweitem Klick nicht doppelt, solange die Anfrage läuft', () => {
    const laeuft = new Subject<void>();
    beitraege.beitragAendern.and.returnValue(laeuft);
    erstellen();

    speichernKnopf().click();
    fixture.detectChanges();
    speichernKnopf().click();

    expect(beitraege.beitragAendern).toHaveBeenCalledTimes(1);
    expect(speichernKnopf().disabled).toBeTrue();
  });

  describe('aendernFehlertext', () => {
    it('nennt bei 400 den Grund des Servers', () => {
      expect(aendernFehlertext({ status: 400, error: { detail: 'Der Text ist zu lang' } })).toBe(
        'Der Text ist zu lang',
      );
    });

    it('rät bei 403 und 404 nicht zum erneuten Versuch', () => {
      expect(aendernFehlertext({ status: 403 })).toBe('Ändern kann nur der Autor des Beitrags.');
      expect(aendernFehlertext({ status: 404 })).toBe('Den Beitrag gibt es nicht mehr.');
    });

    it('nennt bei 422 die Grenzen von Titel, Text und Herkunft', () => {
      const text = aendernFehlertext({ status: 422 });
      expect(text).toContain('3 bis 120 Zeichen');
      expect(text).toContain('höchstens 10 Herkünfte');
    });

    it('rät sonst zum erneuten Versuch', () => {
      expect(aendernFehlertext({ status: 500 })).toBe('Speichern hat nicht geklappt. Versuch es gleich noch einmal.');
    });
  });
});
