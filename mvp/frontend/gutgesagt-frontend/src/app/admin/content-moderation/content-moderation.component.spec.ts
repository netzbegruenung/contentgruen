import { ComponentFixture, TestBed, discardPeriodicTasks, fakeAsync, flushMicrotasks, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, Subject } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';
import { ContentModerationComponent } from './content-moderation.component';
import { ContentReport, ModerationService, PendingReportsResponse } from '../../services/moderation.service';
import { MELDEGRUENDE } from '../../shared/meldegruende';
import { SperreFuerAdmins } from '../../services/moderation.service';
import { SperrenDialogErgebnis } from './sperren-dialog.component';
import { kurzeKennung } from './kennung';
import { MELDUNG_ERLEDIGT } from './content-moderation.component';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NACHLADEN_MS } from '../../shared/selbst-nachladen';
// Ausserhalb von /admin (wie im Testlauf) fragt der ZuTunService alle 120 s.
import { KOPF_NACHLADEN_MS } from '../../services/zu-tun.service';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { throwError } from 'rxjs';
import { SuchanfragenFreigabeService } from '../../services/suchanfragen-freigabe.service';

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
  let suchanfragen: jasmine.SpyObj<SuchanfragenFreigabeService>;

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
    moderation = jasmine.createSpyObj('ModerationService', ['getReports', 'getGesperrte', 'sperren', 'entsperren', 'sperreBestaetigen', 'dismissReport', 'getLoeschauftraege', 'loeschauftragAusfuehren', 'meldungSchliessen']);
    moderation.sperren.and.returnValue(of({ success: true, message: '' }));
    moderation.entsperren.and.returnValue(of({ success: true, message: '' }));
    moderation.sperreBestaetigen.and.returnValue(of({ success: true, message: '' }));
    moderation.getGesperrte.and.returnValue(of({ total: 0, beitraege: [] }));
    moderation.getLoeschauftraege.and.returnValue(of({ frist_tage: 7, auftraege: [] }));
    dialog = jasmine.createSpyObj('MatDialog', ['open']);
    suchanfragen = jasmine.createSpyObj('SuchanfragenFreigabeService', ['zuPruefen', 'anzahl', 'freigeben', 'ablehnen']);
    suchanfragen.zuPruefen.and.returnValue(of({ suchanfragen: [] }));
    suchanfragen.anzahl.and.returnValue(of({ anzahl: 0 }));

    TestBed.configureTestingModule({
      imports: [ContentModerationComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: ModerationService, useValue: moderation },
        { provide: SuchanfragenFreigabeService, useValue: suchanfragen }
      ]
    });
    // Die Komponente importiert MatDialogModule selbst; deshalb hier überschreiben.
    TestBed.overrideProvider(MatDialog, { useValue: dialog });
  });

  describe('anonyme Melder (#446)', () => {
    function melder(): string {
      return (fixture.nativeElement.querySelector('.anonymous')?.textContent ?? '').replace(/\s+/g, ' ').trim();
    }

    it('zeigt bei einer erledigten Meldung (Zufallswert) nur „Anonym“', () => {
      mitMeldungen([meldung({ reported_by_session_id: 'anon:3f2504e0-4f89-41d3-9a0c-0305e82c3301' })]);

      expect(melder()).toBe('Anonym');
    });

    it('zeigt bei einer offenen Meldung den Anfang des Tagespseudonyms als Quelle', () => {
      mitMeldungen([meldung({ reported_by_session_id: 'besucher:' + '9f86d081'.padEnd(64, '0') })]);

      expect(melder()).toBe('Anonym (Quelle 9f86d081)');
    });

    it('zeigt bei einer alten Sitzungskennung weiter ihren Anfang', () => {
      mitMeldungen([meldung({ reported_by_session_id: '3f2504e0-4f89-41d3-9a0c-0305e82c3301' })]);

      expect(melder()).toBe('Anonym (3f2504e0)');
    });
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
    // Die Liste fragt mit Ansicht und Grenze; die Zahl der offenen (ZuTunService) zusätzlich still.
    expect(moderation.getReports.calls.allArgs().filter((args) => args[3] !== true).length).toBe(2);
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

  it('zeigt unter „Nach Person“ die Suche nach Name oder E-Mail-Adresse statt der Meldungsliste (#494)', () => {
    mitMeldungen([meldung()]);
    moderation.getReports.calls.reset();

    fixture.componentInstance.onStatusFilterChange('person');
    fixture.detectChanges();

    expect(moderation.getReports).not.toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector('app-meldungen-einer-person')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('.reports-table')).toBeNull();
    expect(fixture.nativeElement.textContent).not.toContain('Keine Meldungen');
  });

  it('zählt die Suchanfragen, die auf Freigabe warten, am Umschalter und zeigt sie statt der Meldungen', fakeAsync(() => {
    suchanfragen.zuPruefen.and.returnValue(of({
      suchanfragen: [{ statement_id: 'a-1', statement_text: 'Sind Wärmepumpen laut?', personen_ohne_treffer: 3 }]
    }));
    suchanfragen.anzahl.and.returnValue(of({ anzahl: 1 }));
    mitMeldungen([meldung()]);
    flushMicrotasks();
    fixture.detectChanges();

    expect(fixture.componentInstance.zuPruefendeSuchanfragen).toBe(1);
    expect(fixture.nativeElement.textContent).not.toContain('Sind Wärmepumpen laut?');

    moderation.getReports.calls.reset();
    fixture.componentInstance.onStatusFilterChange('suchanfragen');
    fixture.detectChanges();

    expect(moderation.getReports).not.toHaveBeenCalled();
    expect(fixture.nativeElement.textContent).toContain('Sind Wärmepumpen laut?');
    expect(fixture.nativeElement.querySelector('.reports-table')).toBeNull();
    expect(knopf('Aktualisieren')).toBeUndefined();
    discardPeriodicTasks();
  }));

  it('zeigt unter „Nach Person“ keinen Fehler einer Liste, die vorher noch lud (#494)', () => {
    const liste = new Subject<PendingReportsResponse>();
    moderation.getReports.and.returnValue(liste);
    fixture = TestBed.createComponent(ContentModerationComponent);
    fixture.detectChanges();

    fixture.componentInstance.onStatusFilterChange('person');
    liste.error(new Error('zu spät'));
    fixture.detectChanges();

    expect(fixture.componentInstance.error).toBeNull();
    expect(fixture.nativeElement.textContent).not.toContain('Fehler beim Laden der Meldungen');
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

  it('zeigt Name und E-Mail-Adresse der meldenden Person, damit Admins die Entscheidung mitteilen können (#438)', () => {
    mitMeldungen([meldung({ melder_name: 'Anna Beispiel', melder_email: 'anna@example.org', guter_glaube: true })]);

    const zelle: HTMLElement = fixture.nativeElement.querySelector('.reporter-cell');
    expect(zelle.textContent).toContain('Anna Beispiel');
    const link = zelle.querySelector('a') as HTMLAnchorElement;
    expect(link.textContent).toContain('anna@example.org');
    expect(link.getAttribute('href')).toBe('mailto:anna@example.org');
    expect(zelle.textContent).toContain('in gutem Glauben');
  });

  it('hängt über die E-Mail-Adresse keine weiteren Empfänger an den mailto-Link', () => {
    mitMeldungen([meldung({ melder_email: 'anna?cc=b@example.org', guter_glaube: true })]);

    const link = fixture.nativeElement.querySelector('.reporter-cell a') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('mailto:anna%3Fcc%3Db@example.org');
  });

  it('vermerkt bei alten Meldungen, dass die Erklärung guten Glaubens fehlt', () => {
    mitMeldungen([meldung({ guter_glaube: null })]);

    const zelle: HTMLElement = fixture.nativeElement.querySelector('.reporter-cell');
    expect(zelle.textContent).toContain('ohne Erklärung guten Glaubens');
    expect(zelle.querySelector('a')).toBeNull();
  });

  describe('Löschaufträge (DSFA R9b)', () => {
    const auftrag = {
      id: 'auftrag-1',
      user_id: 'person-1',
      anzeigename: 'Anna B.',
      widerrufen_am: '2026-11-01T10:00:00Z',
      angelegt_am: '2026-11-01T10:00:00Z',
      frist: '2026-11-08T10:00:00Z',
      ueberfaellig: true,
      neu_eingewilligt_am: null,
    };

    it('zählt die offenen Aufträge am Umschalter', () => {
      moderation.getLoeschauftraege.and.returnValue(of({ frist_tage: 7, auftraege: [auftrag] }));
      mitMeldungen([]);

      expect(fixture.componentInstance.offeneLoeschauftraege).toBe(1);
      const umschalter = Array.from(fixture.nativeElement.querySelectorAll('mat-button-toggle')) as HTMLElement[];
      const loeschauftraege = umschalter.find((u) => u.textContent?.includes('Löschaufträge'))!;
      expect(loeschauftraege.querySelector('[aria-label]')?.getAttribute('aria-label')).toBe('Löschaufträge, 1 offen');
    });

    it('lädt die Zahl am Umschalter im Takt nach, solange sichtbar, auch in anderen Ansichten', fakeAsync(() => {
      let sichtbarkeit: DocumentVisibilityState = 'visible';
      spyOnProperty(document, 'visibilityState', 'get').and.callFake(() => sichtbarkeit);
      mitMeldungen([]);
      expect(fixture.componentInstance.offeneLoeschauftraege).toBe(0);

      moderation.getLoeschauftraege.and.returnValue(of({ frist_tage: 7, auftraege: [auftrag] }));
      tick(KOPF_NACHLADEN_MS);
      expect(fixture.componentInstance.offeneLoeschauftraege).toBe(1);

      sichtbarkeit = 'hidden';
      tick(KOPF_NACHLADEN_MS);
      expect(moderation.getLoeschauftraege).toHaveBeenCalledTimes(2);

      sichtbarkeit = 'visible';
      document.dispatchEvent(new Event('visibilitychange'));
      expect(moderation.getLoeschauftraege).toHaveBeenCalledTimes(3);

      fixture.destroy();
      tick(KOPF_NACHLADEN_MS);
      expect(moderation.getLoeschauftraege).toHaveBeenCalledTimes(3);
    }));

    it('zeigt die Liste ohne „Aktualisieren“: sie lädt selbst nach', () => {
      mitMeldungen([]);

      fixture.componentInstance.onStatusFilterChange('loeschauftraege');
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('app-loeschauftraege')).not.toBeNull();
      expect(knopf('Aktualisieren')).toBeUndefined();
      expect(fixture.nativeElement.textContent).not.toContain('Keine Meldungen');
      fixture.destroy();
    });
  });
  describe('lädt selbst nach (Grundsatz 13.11.2026)', () => {
    it('behält beim Nachladen Zeilen und Fokus: ein fokussierter Knopf bleibt fokussiert', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      mitMeldungen([meldung()]);
      document.body.appendChild(fixture.nativeElement);
      const abweisen = knopf('Abweisen')!;
      abweisen.focus();
      expect(document.activeElement).toBe(abweisen);

      // Neue Objekte mit denselben Kennungen, wie sie der Dienst liefert
      moderation.getReports.and.returnValue(of({ total: 1, reports: [meldung({ description: 'neu geladen' })] }));
      document.dispatchEvent(new Event('visibilitychange'));
      fixture.detectChanges();

      expect(fixture.nativeElement.textContent).toContain('neu geladen');
      expect(knopf('Abweisen')).toBe(abweisen);
      expect(document.activeElement).toBe(abweisen);
      fixture.destroy();
    }));

    it('schiebt neue Meldungen nicht unter den Zeiger, sondern kündigt sie an', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      mitMeldungen([meldung()]);
      moderation.getReports.and.returnValue(of({ total: 2, reports: [meldung({ id: 'report-neu' }), meldung()] }));

      document.dispatchEvent(new Event('visibilitychange'));
      fixture.detectChanges();

      expect(fixture.componentInstance.reports.map((r) => r.id)).toEqual(['report-1']);
      const ankuendigung = knopf('neue Meldung')!;
      expect(ankuendigung.textContent!.trim()).toBe('1 neue Meldung anzeigen');

      ankuendigung.click();
      fixture.detectChanges();
      expect(fixture.componentInstance.reports.map((r) => r.id)).toEqual(['report-neu', 'report-1']);
      expect(knopf('neue Meldung')).toBeUndefined();
      fixture.destroy();
    }));

    it('fragt in „Gesperrt“ die Widersprüche nicht extra, sie stehen in den Daten', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      mitMeldungen([]);
      fixture.componentInstance.onStatusFilterChange('gesperrt');
      moderation.getGesperrte.calls.reset();

      document.dispatchEvent(new Event('visibilitychange'));

      expect(moderation.getGesperrte).toHaveBeenCalledOnceWith(true);
      fixture.destroy();
    }));

    it('verwirft ein stilles Nachladen, das eine Aktion überholt hat (umgekehrte Antwortreihenfolge)', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      moderation.dismissReport.and.returnValue(of({}));
      dialog.open.and.returnValue({ afterClosed: () => of('Kein Verstoß gegen die Nutzungsbedingungen') } as any);
      mitMeldungen([meldung(), meldung({ id: 'report-2' })]);
      const alt = new Subject<PendingReportsResponse>();
      moderation.getReports.and.returnValue(alt);

      // Das stille Nachladen geht los, antwortet aber erst nach der Aktion.
      document.dispatchEvent(new Event('visibilitychange'));
      moderation.getReports.and.returnValue(of({ total: 1, reports: [meldung({ id: 'report-2' })] }));
      fixture.componentInstance.dismissReport(meldung());
      fixture.detectChanges();
      expect(fixture.componentInstance.reports.map((r) => r.id)).toEqual(['report-2']);

      alt.next({ total: 2, reports: [meldung(), meldung({ id: 'report-2' })] });
      alt.complete();
      fixture.detectChanges();

      // Die abgewiesene erscheint nicht wieder als „neu“, und ZuTun bekommt nicht den alten Stand.
      expect(fixture.componentInstance.reports.map((r) => r.id)).toEqual(['report-2']);
      expect(fixture.componentInstance.neueMeldungen).toBe(0);
      expect(fixture.componentInstance.offeneMeldungen).toBe(1);
      fixture.destroy();
    }));

    it('lässt eine beim Nachladen erledigte Meldung ausgegraut mit gesperrten Knöpfen stehen', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      mitMeldungen([meldung(), meldung({ id: 'report-2' })]);
      fixture.componentInstance.toggleExpand(meldung());
      moderation.getReports.and.returnValue(of({ total: 1, reports: [meldung({ id: 'report-2' })] }));

      document.dispatchEvent(new Event('visibilitychange'));
      fixture.detectChanges();

      const zeilen = Array.from(fixture.nativeElement.querySelectorAll('tr.report-row')) as HTMLElement[];
      expect(zeilen.length).toBe(2);
      expect(zeilen[0].classList).toContain('erledigt');
      expect(zeilen[0].textContent).toContain('erledigt');
      const knoepfe = Array.from(zeilen[0].querySelectorAll('.action-buttons button')) as HTMLButtonElement[];
      expect(knoepfe.length).toBeGreaterThan(0);
      // Gesperrt, aber fokussierbar (disabledInteractive): aria-disabled statt disabled
      expect(knoepfe.every((k) => k.getAttribute('aria-disabled') === 'true')).toBeTrue();
      expect(zeilen[1].classList).not.toContain('erledigt');

      // Ein Klick auf die gesperrten Knöpfe löst nichts aus (disabledInteractive lässt Klicks durch).
      knoepfe.forEach((k) => k.click());
      expect(moderation.dismissReport).not.toHaveBeenCalled();
      expect(moderation.sperren).not.toHaveBeenCalled();
      expect(moderation.entsperren).not.toHaveBeenCalled();
      expect(dialog.open).not.toHaveBeenCalled();

      // Weg erst beim nächsten ausdrücklichen Laden; die aufgeklappte Zeile auch.
      fixture.componentInstance.loadReports();
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelectorAll('tr.report-row').length).toBe(1);
      expect(fixture.componentInstance.isExpanded(meldung())).toBeFalse();
      fixture.destroy();
    }));

    it('hält die Statuszeile immer frei, damit Hinweise die Zeilen nicht verschieben', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      mitMeldungen([meldung()]);
      const zeile = fixture.nativeElement.querySelector('.statuszeile') as HTMLElement;
      expect(zeile).not.toBeNull();

      moderation.getReports.and.returnValue(of({ total: 2, reports: [meldung({ id: 'report-neu' }), meldung()] }));
      document.dispatchEvent(new Event('visibilitychange'));
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('.statuszeile')).toBe(zeile);
      expect(zeile.querySelector('.neue-meldungen')).not.toBeNull();
      fixture.destroy();
    }));

    it('zeigt nach 401 beim Nachladen „Sitzung abgelaufen – Anmelden“ und fragt nicht weiter', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      mitMeldungen([meldung()]);
      moderation.getReports.and.returnValue(throwError(() => ({ status: 401 })));
      moderation.getGesperrte.and.returnValue(of({ total: 0, beitraege: [] }));

      document.dispatchEvent(new Event('visibilitychange'));
      fixture.detectChanges();
      const link: HTMLAnchorElement = fixture.nativeElement.querySelector('.sitzung-abgelaufen');
      expect(link.textContent!.trim()).toBe('Sitzung abgelaufen – Anmelden');
      expect(link.getAttribute('href')).toContain('/login');
      expect(fixture.nativeElement.textContent).not.toContain('neuer Versuch in Kürze');

      // Das stille Nachladen der Moderation fragt nicht weiter; erkennbar an ihrer stillen
      // Zählung der Widersprüche (getGesperrte(true)), die nur sie stellt.
      const anfragen = moderation.getGesperrte.calls.allArgs().filter((args) => args[0] === true).length;
      tick(NACHLADEN_MS * 8);
      document.dispatchEvent(new Event('visibilitychange'));
      expect(moderation.getGesperrte.calls.allArgs().filter((args) => args[0] === true).length).toBe(anfragen);
      fixture.destroy();
    }));

    it('kürzt bei 328 px den Hinweis mit Auslassungszeichen; der Knopf bleibt ganz, die Zeile 40 px hoch', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      mitMeldungen([meldung()]);
      document.body.appendChild(fixture.nativeElement);
      fixture.componentInstance.nachladefehler = true;
      fixture.componentInstance.neueMeldungen = 1;
      (fixture.componentInstance as any).wartendeListe = [meldung(), meldung({ id: 'report-neu' })];
      fixture.detectChanges();

      const zeile = fixture.nativeElement.querySelector('.statuszeile') as HTMLElement;
      zeile.style.width = '328px';
      const knopf = zeile.querySelector('.neue-meldungen') as HTMLElement;
      const text = zeile.querySelector('.nachladefehler-text.lang') as HTMLElement;

      expect(zeile.getBoundingClientRect().height).toBeCloseTo(40, 0);
      expect(knopf.getBoundingClientRect().right).toBeLessThanOrEqual(zeile.getBoundingClientRect().right + 0.5);
      expect(knopf.scrollWidth).toBeLessThanOrEqual(knopf.clientWidth + 1);
      expect(getComputedStyle(text).textOverflow).toBe('ellipsis');
      expect(text.scrollWidth).toBeGreaterThan(text.clientWidth);
      fixture.destroy();
    }));

    it('läuft nach 401 wieder an, sobald ausdrücklich geladen wird', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      mitMeldungen([meldung()]);
      moderation.getReports.and.returnValue(throwError(() => ({ status: 401 })));
      document.dispatchEvent(new Event('visibilitychange'));
      fixture.detectChanges();
      expect(fixture.componentInstance.sitzungAbgelaufen).toBeTrue();

      // Wieder angemeldet: Ein ausdrückliches Laden klappt und setzt das Nachladen fort.
      moderation.getReports.and.returnValue(of({ total: 1, reports: [meldung()] }));
      fixture.componentInstance.loadReports();
      fixture.detectChanges();
      expect(fixture.componentInstance.sitzungAbgelaufen).toBeFalse();
      expect(fixture.nativeElement.querySelector('.sitzung-abgelaufen')).toBeNull();

      const vorher = moderation.getGesperrte.calls.allArgs().filter((args) => args[0] === true).length;
      tick(NACHLADEN_MS);
      expect(moderation.getGesperrte.calls.allArgs().filter((args) => args[0] === true).length).toBe(vorher + 1);
      fixture.destroy();
    }));

    it('zeigt bei 403 auf ein ausdrückliches Laden nur den Link, ohne „neuer Versuch“ und ohne „Keine Meldungen“', () => {
      moderation.getReports.and.returnValue(throwError(() => ({ status: 403 })));
      fixture = TestBed.createComponent(ContentModerationComponent);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('.sitzung-abgelaufen').textContent.trim()).toBe('Sitzung abgelaufen – Anmelden');
      expect(fixture.nativeElement.querySelector('.error')).toBeNull();
      expect(fixture.nativeElement.textContent).not.toContain('neuer Versuch');
      expect(fixture.nativeElement.textContent).not.toContain('Keine Meldungen');
      fixture.destroy();
    });

    it('zeigt in „Gesperrt“ bei 403 nur den Link, nicht „Keine gesperrten Beiträge“', () => {
      mitMeldungen([]);
      moderation.getGesperrte.and.returnValue(throwError(() => ({ status: 403 })));
      fixture.componentInstance.onStatusFilterChange('gesperrt');
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('.sitzung-abgelaufen')).not.toBeNull();
      expect(fixture.nativeElement.textContent).not.toContain('Keine gesperrten Beiträge');
      expect(fixture.nativeElement.textContent).not.toContain('neuer Versuch');
    });

    it('läuft auch an, wenn ein ausdrückliches Laden sitzungAbgelaufen zwischendurch zurückgesetzt hat', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      mitMeldungen([meldung()]);
      // Ein stiller Lauf ist unterwegs …
      const still = new Subject<PendingReportsResponse>();
      moderation.getReports.and.returnValue(still);
      document.dispatchEvent(new Event('visibilitychange'));
      // … ein ausdrückliches Laden startet (Sitzung noch gültig, kein Anstoß) …
      const ausdruecklich = new Subject<PendingReportsResponse>();
      moderation.getReports.and.returnValue(ausdruecklich);
      fixture.componentInstance.loadReports();
      // … der stille Lauf kommt mit 401 zurück, das Laden gelingt danach.
      still.error({ status: 401 });
      ausdruecklich.next({ total: 1, reports: [meldung()] });
      ausdruecklich.complete();
      expect(fixture.componentInstance.sitzungAbgelaufen).toBeFalse();

      // Erst belegen, dass das Nachladen wirklich steht …
      const stillGezaehlt = () => moderation.getGesperrte.calls.allArgs().filter((args) => args[0] === true).length;
      const gestoppt = stillGezaehlt();
      tick(NACHLADEN_MS * 4);
      expect(stillGezaehlt()).toBe(gestoppt);

      // … dann stößt das nächste ausdrückliche Laden es wieder an.
      moderation.getReports.and.returnValue(of({ total: 1, reports: [meldung()] }));
      fixture.componentInstance.loadReports();
      const vorher = moderation.getGesperrte.calls.allArgs().filter((args) => args[0] === true).length;
      tick(NACHLADEN_MS);
      expect(moderation.getGesperrte.calls.allArgs().filter((args) => args[0] === true).length).toBe(vorher + 1);
      fixture.destroy();
    }));

    it('markiert in anderen Ansichten nichts als erledigt; Fehlendes geht leise mit „neue anzeigen“', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      mitMeldungen([]);
      moderation.getReports.and.returnValue(of({ total: 2, reports: [meldung({ id: 'a', status: 'reviewed' }), meldung({ id: 'b', status: 'reviewed' })] }));
      fixture.componentInstance.onStatusFilterChange('reviewed');
      fixture.detectChanges();

      moderation.getReports.and.returnValue(of({ total: 1, reports: [meldung({ id: 'b', status: 'reviewed' })] }));
      document.dispatchEvent(new Event('visibilitychange'));
      fixture.detectChanges();

      expect(fixture.componentInstance.erledigt.size).toBe(0);
      expect(fixture.componentInstance.reports.map((r) => r.id)).toEqual(['a', 'b']);
      // Ohne neue Meldungen heißt der Knopf „Liste aktualisieren“ und räumt die fehlende Zeile weg.
      knopf('Liste aktualisieren')!.click();
      fixture.detectChanges();
      expect(fixture.componentInstance.reports.map((r) => r.id)).toEqual(['b']);
      expect(knopf('Liste aktualisieren')).toBeUndefined();
      fixture.destroy();
    }));

    it('markiert an der 100er-Grenze nichts als erledigt: die Zeile kann nur dahinter liegen', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      mitMeldungen([meldung({ id: 'alt' })]);
      const hundert = Array.from({ length: 100 }, (_, i) => meldung({ id: 'neu-' + i }));
      moderation.getReports.and.returnValue(of({ total: 100, reports: hundert }));

      document.dispatchEvent(new Event('visibilitychange'));

      expect(fixture.componentInstance.erledigt.size).toBe(0);
      expect(fixture.componentInstance.neueMeldungen).toBe(100);
      fixture.destroy();
    }));

    it('bricht Abweisen und Sperren ab, wenn die Meldung erledigt wurde, während der Dialog offen war', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      const snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
      TestBed.overrideProvider(MatSnackBar, { useValue: snackBar });
      const dialogZu = new Subject<any>();
      dialog.open.and.returnValue({ afterClosed: () => dialogZu } as any);
      mitMeldungen([meldung(), meldung({ id: 'report-2' })]);

      fixture.componentInstance.dismissReport(meldung());
      moderation.getReports.and.returnValue(of({ total: 1, reports: [meldung({ id: 'report-2' })] }));
      document.dispatchEvent(new Event('visibilitychange'));
      dialogZu.next('Kein Verstoß gegen die Nutzungsbedingungen');

      expect(moderation.dismissReport).not.toHaveBeenCalled();
      expect(snackBar.open).toHaveBeenCalledWith(MELDUNG_ERLEDIGT, 'OK', jasmine.anything());

      const sperrDialog = new Subject<any>();
      dialog.open.and.returnValue({ afterClosed: () => sperrDialog } as any);
      fixture.componentInstance.sperren(meldung({ id: 'report-2' }));
      fixture.componentInstance.erledigt.add('report-2');
      sperrDialog.next({ sperrgrund: 'unterstellung', begruendung: 'x' });
      expect(moderation.sperren).not.toHaveBeenCalled();
      fixture.destroy();
    }));

    it('schließt eine Meldung zu einem gesperrten Beitrag über den eigenen Endpunkt', () => {
      const snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
      TestBed.overrideProvider(MatSnackBar, { useValue: snackBar });
      moderation.meldungSchliessen.and.returnValue(of({}));
      const gesperrt = meldung({ content: { status: 'blocked', title: 'T', text: 'T' } });
      mitMeldungen([gesperrt]);
      const vorher = moderation.getReports.calls.count();

      const schliessen = knopf('Meldung schließen')!;
      schliessen.click();

      expect(moderation.meldungSchliessen).toHaveBeenCalledWith('report-1');
      expect(moderation.sperren).not.toHaveBeenCalled();
      expect(snackBar.open).toHaveBeenCalledWith('Meldung geschlossen, Beitrag bleibt gesperrt', 'OK', jasmine.anything());
      expect(moderation.getReports.calls.count()).toBeGreaterThan(vorher);
    });

    it('bietet „Meldung schließen“ nur bei gesperrtem Beitrag an', () => {
      mitMeldungen([meldung()]);

      expect(knopf('Meldung schließen')).toBeUndefined();
      expect(knopf('Abweisen')).toBeDefined();
    });

    it('bietet bei einem gesperrten Beitrag kein Abweisen an', () => {
      mitMeldungen([meldung({ content: { status: 'blocked', title: 'T', text: 'T' } })]);

      expect(knopf('Abweisen')).toBeUndefined();
      fixture.componentInstance.dismissReport(meldung({ content: { status: 'blocked', title: 'T', text: 'T' } }));
      expect(dialog.open).not.toHaveBeenCalled();
    });

    it('meldet 409 „beitrag_gesperrt“ beim Abweisen mit dem vorhandenen Satz und lädt neu', () => {
      const snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
      TestBed.overrideProvider(MatSnackBar, { useValue: snackBar });
      moderation.dismissReport.and.returnValue(throwError(() => ({ status: 409, error: { detail: 'beitrag_gesperrt' } })));
      dialog.open.and.returnValue({ afterClosed: () => of('Kein Verstoß gegen die Nutzungsbedingungen') } as any);
      mitMeldungen([meldung()]);

      fixture.componentInstance.dismissReport(meldung());

      expect(snackBar.open).toHaveBeenCalledWith('Der Beitrag ist schon gesperrt', 'OK', jasmine.anything());
    });

    it('meldet 409 beim Abweisen als „inzwischen erledigt“ und lädt neu', () => {
      const snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
      TestBed.overrideProvider(MatSnackBar, { useValue: snackBar });
      moderation.dismissReport.and.returnValue(throwError(() => ({ status: 409 })));
      dialog.open.and.returnValue({ afterClosed: () => of('Schon entschieden (doppelte Meldung)') } as any);
      mitMeldungen([meldung()]);
      const vorher = moderation.getReports.calls.count();

      fixture.componentInstance.dismissReport(meldung());

      expect(snackBar.open).toHaveBeenCalledWith(MELDUNG_ERLEDIGT, 'OK', jasmine.anything());
      expect(moderation.getReports.calls.count()).toBeGreaterThan(vorher);
    });

    it('verwirft eine Widerspruchszählung, die ein Laden überholt hat', () => {
      const alt = new Subject<any>();
      moderation.getGesperrte.and.returnValue(alt);
      mitMeldungen([]);
      moderation.getGesperrte.and.returnValue(of({ total: 0, beitraege: [] }));
      fixture.componentInstance.onStatusFilterChange('gesperrt');

      alt.next({ total: 1, beitraege: [{ id: 'x', content_type: 'commentary', status: 'blocked', sperre: sperre({ widerspruch_offen: true }) }] });

      expect(fixture.componentInstance.offeneWidersprueche).toBe(0);
    });

    it('fragt in „Nach Person“ beim Nachladen nichts', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      mitMeldungen([]);
      fixture.componentInstance.onStatusFilterChange('person');
      moderation.getGesperrte.calls.reset();
      moderation.getReports.calls.reset();

      document.dispatchEvent(new Event('visibilitychange'));

      expect(moderation.getGesperrte).not.toHaveBeenCalled();
      // Nur die Zahl am Kopf (ZuTunService) fragt, still.
      expect(moderation.getReports.calls.allArgs().every((args) => args[3] === true)).toBeTrue();
      fixture.destroy();
    }));

    it('hat keinen Knopf „Aktualisieren“ mehr, auch nicht in der Meldungsliste', () => {
      mitMeldungen([meldung()]);

      expect(knopf('Aktualisieren')).toBeUndefined();
    });

    it('lädt still nach: ohne Spinner, aufgeklappte Zeilen bleiben offen', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      mitMeldungen([meldung()]);
      fixture.componentInstance.toggleExpand(meldung());
      const neu = new Subject<PendingReportsResponse>();
      moderation.getReports.and.returnValue(neu);

      tick(NACHLADEN_MS);
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector('.loading')).toBeNull();
      expect(fixture.componentInstance.isExpanded(meldung())).toBeTrue();

      neu.next({ total: 2, reports: [meldung(), meldung({ id: 'report-2' })] });
      fixture.detectChanges();
      // Die neue wird angekündigt, nicht eingeschoben.
      expect(fixture.componentInstance.reports.length).toBe(1);
      expect(fixture.componentInstance.neueMeldungen).toBe(1);
      expect(fixture.componentInstance.isExpanded(meldung())).toBeTrue();
      fixture.destroy();
    }));

    it('lässt bei einem Fehler im Nachladen die Liste stehen und sagt, dass es neu versucht', fakeAsync(() => {
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
      mitMeldungen([meldung()]);
      moderation.getReports.and.returnValue(throwError(() => new Error('weg')));

      document.dispatchEvent(new Event('visibilitychange'));
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('.reports-table')).not.toBeNull();
      expect(fixture.nativeElement.textContent).toContain('Aktualisieren gerade nicht möglich, neuer Versuch in Kürze');
      fixture.destroy();
    }));

    it('ersetzt „Fehler beim Laden“ durch Spinner und neuen Versuch', () => {
      moderation.getReports.and.returnValue(throwError(() => new Error('weg')));
      fixture = TestBed.createComponent(ContentModerationComponent);
      fixture.detectChanges();

      const fehler: HTMLElement = fixture.nativeElement.querySelector('.error');
      expect(fehler.querySelector('mat-spinner')).not.toBeNull();
      expect(fehler.textContent).toContain('Meldungen gerade nicht erreichbar, neuer Versuch in Kürze');
      fixture.destroy();
    });

    it('zeigt die Zahl offener Meldungen am Umschalter „Offen“', () => {
      moderation.getReports.and.callFake(((status: string) =>
        of({ total: 2, reports: status === 'pending' ? [meldung(), meldung({ id: 'report-2' })] : [] })) as any);
      fixture = TestBed.createComponent(ContentModerationComponent);
      fixture.detectChanges();

      const umschalter = Array.from(fixture.nativeElement.querySelectorAll('mat-button-toggle')) as HTMLElement[];
      const offen = umschalter.find((u) => u.textContent?.includes('Offen'))!;
      expect(offen.querySelector('[aria-label]')?.getAttribute('aria-label')).toBe('Offen, 2 Meldungen');
      fixture.destroy();
    });
  });

  describe('Persona-Test 13.11.2026', () => {
    it('weist erst nach dem Dialog ab und schickt die Begründung als notes', () => {
      moderation.dismissReport.and.returnValue(of({}));
      dialog.open.and.returnValue({ afterClosed: () => of('Zulässige Meinungsäußerung: Zuspitzung, kein Angriff') } as any);
      mitMeldungen([meldung({ melder_email: 'a@example.org' })]);

      knopf('Abweisen')!.click();

      const daten = dialog.open.calls.mostRecent().args[1]!.data as any;
      expect(daten).toEqual(jasmine.objectContaining({ titel: 'Titel', mitMail: true }));
      expect(moderation.dismissReport).toHaveBeenCalledWith('report-1', 'Zulässige Meinungsäußerung: Zuspitzung, kein Angriff');
    });

    it('weist nicht ab, wenn der Dialog abgebrochen wird', () => {
      dialog.open.and.returnValue({ afterClosed: () => of(undefined) } as any);
      mitMeldungen([meldung()]);

      knopf('Abweisen')!.click();

      expect(moderation.dismissReport).not.toHaveBeenCalled();
    });

    it('zeigt bei „Gemeldet von“ und „Bearbeitet von“ den Anzeigenamen, wenn es einen gibt', () => {
      mitMeldungen([]);
      moderation.getReports.and.returnValue(of({ total: 1, reports: [meldung({
        status: 'reviewed', reported_by_session_id: null,
        reported_by_user_id: 'f3a9c1d2-7b4e-4c55-9a10-2e8d6b0c7f11', reported_by_name: 'Anna B.',
        reviewed_by: 'admin-kennung-0123456789', reviewed_by_name: 'Henrike P.',
      })] }));
      fixture.componentInstance.onStatusFilterChange('reviewed');
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('.reporter-cell span').textContent.trim()).toBe('Anna B.');
      const bearbeitet = fixture.nativeElement.querySelector('td[data-label="Bearbeitet von"] span');
      expect(bearbeitet.textContent.trim()).toBe('Henrike P.');
      expect(bearbeitet.getAttribute('title')).toBe('admin-kennung-0123456789');
    });

    it('zeigt statt langer Kennungen eine kurze Form, die volle im Tooltip', () => {
      mitMeldungen([meldung({ reported_by_user_id: 'f3a9c1d2-7b4e-4c55-9a10-2e8d6b0c7f11', reported_by_session_id: null })]);

      const melder: HTMLElement = fixture.nativeElement.querySelector('.reporter-cell span');
      expect(melder.textContent!.trim()).toBe(kurzeKennung('f3a9c1d2-7b4e-4c55-9a10-2e8d6b0c7f11'));
      expect(melder.textContent!.trim()).toMatch(/^Person [0-9a-f]{8}$/);
      expect(melder.getAttribute('title')).toBe('f3a9c1d2-7b4e-4c55-9a10-2e8d6b0c7f11');
    });

    it('beschriftet jede Angabe für die Kartenansicht am Handy', () => {
      mitMeldungen([meldung()]);

      const labels = Array.from(fixture.nativeElement.querySelectorAll('tr.report-row td[data-label]')).map((td: any) => td.getAttribute('data-label'));
      expect(labels).toEqual(['Typ', 'Grund', 'Gemeldet von', 'Datum']);
    });

    it('zeigt in „Gesperrt“ den Text zum Aufklappen und gibt Text und Widerspruch an den Dialog', () => {
      moderation.getGesperrte.and.returnValue(of({
        total: 1,
        beitraege: [{
          id: 'b-1', content_type: 'commentary', status: 'blocked', title: 'Titel', text: 'Der gesperrte Text',
          sperre: sperre({ widerspruch: 'Das ist keine Unterstellung.', widerspruch_am: '2026-11-12T10:00:00Z', widerspruch_offen: true }),
        }],
      }));
      dialog.open.and.returnValue({ afterClosed: () => of(undefined) } as any);
      mitMeldungen([]);
      fixture.componentInstance.onStatusFilterChange('gesperrt');
      fixture.detectChanges();

      expect(fixture.nativeElement.textContent).not.toContain('Der gesperrte Text');
      knopf('Text anzeigen')!.click();
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector('.gesperrter-beitragstext').textContent).toContain('Der gesperrte Text');

      knopf('Sperre bestätigen')!.click();
      expect(dialog.open.calls.mostRecent().args[1]!.data).toEqual(jasmine.objectContaining({
        art: 'bestaetigen', text: 'Der gesperrte Text', widerspruch: 'Das ist keine Unterstellung.',
      }));
    });

    it('nennt die interne Begründung einer Entscheidung, alte englische Platzhalter als „ohne Begründung“', () => {
      const c = TestBed.createComponent(ContentModerationComponent).componentInstance;
      expect(c.entscheidungsBegruendung(meldung({ status: 'dismissed', resolution_notes: 'Dismissed by admin' }))).toBe('ohne Begründung');
      expect(c.entscheidungsBegruendung(meldung({ status: 'dismissed', resolution_notes: 'Schon entschieden (doppelte Meldung)' }))).toBe('Schon entschieden (doppelte Meldung)');
    });
  });

  it('beschriftet den Knopf zum Aufklappen, statt nur ein Pfeil-Symbol zu zeigen', () => {
    mitMeldungen([meldung()]);
    const auf: HTMLButtonElement = fixture.nativeElement.querySelector('td button[mat-icon-button]');

    expect(auf.getAttribute('aria-label')).toBe('Beitrag aufklappen');
    expect(auf.getAttribute('aria-expanded')).toBe('false');
    auf.click();
    fixture.detectChanges();
    expect(auf.getAttribute('aria-label')).toBe('Beitrag zuklappen');
    expect(auf.getAttribute('aria-expanded')).toBe('true');
  });

  it('öffnet die Ansicht aus der Adresse, etwa aus „Zu tun“', () => {
    TestBed.overrideProvider(ActivatedRoute, {
      useValue: {
        snapshot: { queryParamMap: convertToParamMap({ ansicht: 'loeschauftraege' }) },
        queryParamMap: of(convertToParamMap({ ansicht: 'loeschauftraege' })),
      },
    });
    mitMeldungen([]);

    expect(fixture.componentInstance.selectedStatus).toBe('loeschauftraege');
    expect(fixture.nativeElement.querySelector('app-loeschauftraege')).not.toBeNull();
    fixture.destroy();
  });
});
