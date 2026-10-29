import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';
import { ContentModerationComponent } from './content-moderation.component';
import { ContentReport, ModerationService } from '../../services/moderation.service';
import { MELDEGRUENDE } from '../../shared/meldegruende';
import { SperreFuerAdmins } from '../../services/moderation.service';
import { SperrenDialogErgebnis } from './sperren-dialog.component';

function sperre(overrides: Partial<SperreFuerAdmins> = {}): SperreFuerAdmins {
  return {
    id: 'sperre-1',
    sperrgrund: 'unterstellung',
    begruendung: 'Unterstellt Bosheit.',
    gesperrt_am: '2026-10-29T10:00:00+00:00',
    ohne_kontaktdaten: false,
    widerspruch: null,
    widerspruch_am: null,
    widerspruch_offen: false,
    pruefergebnis: null,
    pruefung_begruendung: null,
    geprueft_am: null,
    ...overrides
  };
}

function meldung(overrides: Partial<ContentReport> = {}): ContentReport {
  return {
    id: 'report-1',
    content_id: 'beitrag-1',
    content_type: 'commentary',
    reason: 'inappropriate',
    description: null,
    reported_by_user_id: null,
    reported_by_session_id: 'sess-123456789',
    created: '2026-10-26T10:00:00',
    status: 'pending',
    content: { status: 'visible', title: 'Titel', text: 'Text' },
    ...overrides
  };
}

describe('ContentModerationComponent', () => {
  let fixture: ComponentFixture<ContentModerationComponent>;
  let moderation: jasmine.SpyObj<ModerationService>;
  let dialog: jasmine.SpyObj<MatDialog>;

  /** Der Dialog schließt mit diesem Ergebnis; undefined heißt abgebrochen. */
  function dialogErgebnis(ergebnis: SperrenDialogErgebnis | undefined) {
    dialog.open.and.returnValue({ afterClosed: () => of(ergebnis) } as any);
  }

  function mitMeldungen(meldungen: ContentReport[]) {
    moderation.getReports.and.returnValue(of({ total: meldungen.length, reports: meldungen }));
    fixture = TestBed.createComponent(ContentModerationComponent);
    fixture.detectChanges();
  }

  function knopf(text: string): HTMLButtonElement | undefined {
    const knoepfe = Array.from(fixture.nativeElement.querySelectorAll('button')) as HTMLButtonElement[];
    return knoepfe.find((b) => b.textContent?.includes(text));
  }

  beforeEach(() => {
    moderation = jasmine.createSpyObj('ModerationService', ['getReports', 'getGesperrte', 'sperren', 'entsperren', 'sperreBestaetigen', 'dismissReport']);
    moderation.sperren.and.returnValue(of({ success: true, message: '' }));
    moderation.entsperren.and.returnValue(of({ success: true, message: '' }));
    moderation.sperreBestaetigen.and.returnValue(of({ success: true, message: '' }));
    moderation.getGesperrte.and.returnValue(of({ total: 0, beitraege: [] }));
    dialog = jasmine.createSpyObj('MatDialog', ['open']);

    TestBed.configureTestingModule({
      imports: [ContentModerationComponent, NoopAnimationsModule],
      providers: [{ provide: ModerationService, useValue: moderation }]
    });
    // Die Komponente importiert MatDialogModule selbst; deshalb hier überschreiben.
    TestBed.overrideProvider(MatDialog, { useValue: dialog });
  });

  it('bietet zu einer offenen Meldung Sperren statt Löschen an', () => {
    mitMeldungen([meldung()]);

    expect(knopf('Sperren')).toBeTruthy();
    expect(knopf('Löschen')).toBeUndefined();
    expect(knopf('Entsperren')).toBeUndefined();
  });

  it('sperrt mit Sperrgrund und Begründung aus dem Dialog und lädt die Meldungen neu', () => {
    dialogErgebnis({ sperrgrund: 'unterstellung', begruendung: 'Unterstellt Bosheit.' });
    mitMeldungen([meldung()]);

    knopf('Sperren')!.click();

    expect(dialog.open).toHaveBeenCalled();
    expect(moderation.sperren).toHaveBeenCalledWith('beitrag-1', 'unterstellung', 'Unterstellt Bosheit.');
    expect(moderation.getReports).toHaveBeenCalledTimes(2);
  });

  it('sperrt nicht, wenn der Dialog abgebrochen wird', () => {
    dialogErgebnis(undefined);
    mitMeldungen([meldung()]);

    knopf('Sperren')!.click();

    expect(moderation.sperren).not.toHaveBeenCalled();
  });

  it('bietet zu einem gesperrten Beitrag Entsperren an', () => {
    mitMeldungen([meldung({ status: 'reviewed', content: { status: 'blocked', title: 'T', text: 'T' } })]);
    fixture.componentInstance.onStatusFilterChange('reviewed');
    fixture.detectChanges();

    expect(knopf('Sperren')).toBeUndefined();
    knopf('Entsperren')!.click();

    expect(moderation.entsperren).toHaveBeenCalledWith('beitrag-1');
  });

  it('listet gesperrte Beiträge auch ohne Meldung und entsperrt sie', () => {
    moderation.getGesperrte.and.returnValue(of({
      total: 1,
      beitraege: [{ id: 'beitrag-2', content_type: 'commentary', status: 'blocked', title: 'Gesperrter Titel' }]
    }));
    mitMeldungen([]);

    fixture.componentInstance.onStatusFilterChange('gesperrt');
    fixture.detectChanges();

    expect(moderation.getGesperrte).toHaveBeenCalled();
    expect(fixture.nativeElement.textContent).toContain('Gesperrter Titel');
    expect(fixture.nativeElement.textContent).not.toContain('Keine Meldungen');

    knopf('Entsperren')!.click();

    expect(moderation.entsperren).toHaveBeenCalledWith('beitrag-2');
    // Einmal zum Zählen der Widersprüche, dann Ansicht und Neuladen.
    expect(moderation.getGesperrte).toHaveBeenCalledTimes(3);
  });

  it('zeigt Sperrgrund, Begründung und einen offenen Widerspruch zuerst', () => {
    moderation.getGesperrte.and.returnValue(of({
      total: 2,
      beitraege: [
        { id: 'ohne', content_type: 'commentary', status: 'blocked', title: 'Ohne Widerspruch', sperre: sperre({ id: 's-0' }) },
        {
          id: 'mit', content_type: 'commentary', status: 'blocked', title: 'Mit Widerspruch',
          sperre: sperre({ widerspruch: 'Das ist belegt.', widerspruch_am: '2026-10-29T11:00:00+00:00', widerspruch_offen: true })
        }
      ]
    }));
    mitMeldungen([]);
    fixture.componentInstance.onStatusFilterChange('gesperrt');
    fixture.detectChanges();

    const eintraege = fixture.nativeElement.querySelectorAll('.gesperrter-beitrag');
    expect(eintraege[0].textContent).toContain('Mit Widerspruch');
    expect(eintraege[0].textContent).toContain('Das ist belegt.');
    expect(eintraege[0].textContent).toContain('Unterstellung über Motive');
    expect(eintraege[0].textContent).toContain('Unterstellt Bosheit.');
    expect(eintraege[1].textContent).not.toContain('Sperre bestätigen');
    expect(fixture.componentInstance.offeneWidersprueche).toBe(1);
  });

  it('bestätigt die Sperre nach einem Widerspruch mit Begründung', () => {
    dialogErgebnis({ sperrgrund: null, begruendung: 'Bleibt eine Unterstellung.' });
    moderation.getGesperrte.and.returnValue(of({
      total: 1,
      beitraege: [{
        id: 'mit', content_type: 'commentary', status: 'blocked', title: 'Mit Widerspruch',
        sperre: sperre({ widerspruch_am: '2026-10-29T11:00:00+00:00', widerspruch_offen: true })
      }]
    }));
    mitMeldungen([]);
    fixture.componentInstance.onStatusFilterChange('gesperrt');
    fixture.detectChanges();

    knopf('Sperre bestätigen')!.click();

    expect(moderation.sperreBestaetigen).toHaveBeenCalledWith('sperre-1', 'Bleibt eine Unterstellung.');
  });

  it('vermerkt, wenn niemand die Sperrnachricht sieht', () => {
    moderation.getGesperrte.and.returnValue(of({
      total: 1,
      beitraege: [{ id: 'x', content_type: 'commentary', status: 'blocked', title: 'T', sperre: sperre({ ohne_kontaktdaten: true }) }]
    }));
    mitMeldungen([]);
    fixture.componentInstance.onStatusFilterChange('gesperrt');
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('keine Kontaktdaten');
  });

  it('zeigt die ID als Beitrags-ID, nicht als Content-ID', () => {
    mitMeldungen([meldung()]);
    fixture.componentInstance.toggleExpand(fixture.componentInstance.reports[0]);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Beitrags-ID');
    expect(fixture.nativeElement.textContent).not.toContain('Content-ID');
  });

  it('nennt die Meldungsstufen wie das Glossar', () => {
    mitMeldungen([]);
    const c = fixture.componentInstance;

    expect([c.getStatusLabel('pending'), c.getStatusLabel('reviewed'), c.getStatusLabel('dismissed')])
      .toEqual(['Offen', 'Bearbeitet', 'Abgewiesen']);
  });

  it('zeigt eine Meldung mit dem Grund „Erfunden oder sachlich falsch“', () => {
    mitMeldungen([meldung({ reason: 'fabricated_or_false', description: 'Die Zahl stimmt nicht' })]);

    const zelle = fixture.nativeElement.querySelector('.reason-cell').textContent;
    expect(zelle).toContain('Erfunden oder sachlich falsch');
    expect(zelle).toContain('Die Zahl stimmt nicht');
  });

  it('beschriftet jeden Grund wie der Meldedialog', () => {
    mitMeldungen([]);
    const c = fixture.componentInstance;

    for (const grund of MELDEGRUENDE) {
      expect(c.getReasonLabel(grund.value)).toBe(grund.label);
    }
  });

  it('zeigt einen unbekannten Grund unverändert', () => {
    mitMeldungen([]);

    expect(fixture.componentInstance.getReasonLabel('etwas_altes')).toBe('etwas_altes');
  });
});
