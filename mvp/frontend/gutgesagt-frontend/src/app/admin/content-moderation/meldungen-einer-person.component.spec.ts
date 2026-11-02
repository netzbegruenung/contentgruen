import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MeldungenEinerPersonComponent } from './meldungen-einer-person.component';
import { ContentReport, ModerationService } from '../../services/moderation.service';

function meldung(overrides: Partial<ContentReport> = {}): ContentReport {
  return {
    id: 'report-1',
    content_id: 'beitrag-1',
    content_type: 'commentary',
    reason: 'other',
    description: 'Nennt meine Adresse',
    reported_by_user_id: null,
    reported_by_session_id: 'besucher:abc',
    created: '2026-10-30T10:00:00',
    status: 'pending',
    melder_name: 'Anna Beispiel',
    melder_email: 'anna@example.org',
    guter_glaube: true,
    ...overrides,
  };
}

describe('MeldungenEinerPersonComponent', () => {
  let fixture: ComponentFixture<MeldungenEinerPersonComponent>;
  let moderation: jasmine.SpyObj<ModerationService>;
  let dialog: jasmine.SpyObj<MatDialog>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  function dialogAntwort(ja: boolean | undefined) {
    dialog.open.and.returnValue({ afterClosed: () => of(ja) } as any);
  }

  function element(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  function eingeben(feld: 'email' | 'name', wert: string) {
    const input = element().querySelector(`input[name="${feld}"]`) as HTMLInputElement;
    input.value = wert;
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  function knopf(text: string): HTMLButtonElement | undefined {
    const knoepfe = Array.from(element().querySelectorAll('button')) as HTMLButtonElement[];
    return knoepfe.find((b) => b.textContent?.includes(text));
  }

  async function suchen() {
    knopf('Suchen')!.click();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  beforeEach(async () => {
    moderation = jasmine.createSpyObj('ModerationService', ['meldungenEinerPerson', 'angabenLoeschen']);
    moderation.meldungenEinerPerson.and.returnValue(of({ total: 1, reports: [meldung()] }));
    moderation.angabenLoeschen.and.returnValue(of({ geloescht: 1, angaben_entfernt: 1 }));
    dialog = jasmine.createSpyObj('MatDialog', ['open']);
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);

    TestBed.configureTestingModule({
      imports: [MeldungenEinerPersonComponent, NoopAnimationsModule],
      providers: [{ provide: ModerationService, useValue: moderation }],
    });
    TestBed.overrideProvider(MatDialog, { useValue: dialog });
    TestBed.overrideProvider(MatSnackBar, { useValue: snackBar });
    fixture = TestBed.createComponent(MeldungenEinerPersonComponent);
    fixture.detectChanges();
    await fixture.whenStable();
  });

  describe('Suchen', () => {
    it('sucht erst, wenn Name oder E-Mail-Adresse angegeben ist', () => {
      expect(knopf('Suchen')!.disabled).toBeTrue();

      eingeben('email', '   ');
      expect(knopf('Suchen')!.disabled).toBeTrue();

      eingeben('email', 'anna@example.org');
      expect(knopf('Suchen')!.disabled).toBeFalse();
    });

    it('schickt die Angaben ohne Rand, leere als null', async () => {
      eingeben('email', ' anna@example.org ');

      await suchen();

      expect(moderation.meldungenEinerPerson).toHaveBeenCalledWith({ email: 'anna@example.org', name: null });
    });

    it('zeigt jede Meldung mit Status, Grund, Beschreibung, Beitrag und den Angaben', async () => {
      moderation.meldungenEinerPerson.and.returnValue(
        of({ total: 2, reports: [meldung(), meldung({ id: 'report-2', status: 'dismissed', description: null })] })
      );
      eingeben('name', 'Anna Beispiel');

      await suchen();

      const text = element().textContent!;
      expect(text).toContain('2 Meldungen');
      expect(text).toContain('Offen');
      expect(text).toContain('Abgewiesen');
      expect(text).toContain('Nennt meine Adresse');
      expect(text).toContain('beitrag-1');
      expect(text).toContain('anna@example.org');
      expect(text).toContain('Anna Beispiel');
    });

    it('sagt, wenn nichts gespeichert ist, und bietet kein Löschen an', async () => {
      moderation.meldungenEinerPerson.and.returnValue(of({ total: 0, reports: [] }));
      eingeben('email', 'niemand@example.org');

      await suchen();

      expect(element().textContent).toContain('Keine Meldungen mit diesen Angaben');
      expect(knopf('Angaben löschen')).toBeUndefined();
    });

    it('meldet einen Fehler, statt "keine Meldungen" zu zeigen', async () => {
      moderation.meldungenEinerPerson.and.returnValue(throwError(() => ({ status: 500 })));
      eingeben('email', 'anna@example.org');

      await suchen();

      expect(element().textContent).toContain('Fehler bei der Suche');
      expect(element().textContent).not.toContain('Keine Meldungen mit diesen Angaben');
    });
  });

  describe('Angaben löschen', () => {
    beforeEach(async () => {
      eingeben('email', 'anna@example.org');
      await suchen();
    });

    it('fragt vorher nach und löscht bei Abbruch nichts', () => {
      dialogAntwort(false);

      knopf('Angaben löschen')!.click();

      expect(dialog.open).toHaveBeenCalled();
      expect(moderation.angabenLoeschen).not.toHaveBeenCalled();
    });

    it('löscht mit den Angaben der gezeigten Suche, nicht mit später Eingetipptem', () => {
      dialogAntwort(true);
      eingeben('email', 'bert@example.org');

      knopf('Angaben löschen')!.click();

      expect(moderation.angabenLoeschen).toHaveBeenCalledWith({ email: 'anna@example.org', name: null }, ['report-1']);
    });

    it('lässt nicht löschen, solange eine neue Suche läuft', () => {
      fixture.componentInstance.suchtGerade = true;
      fixture.detectChanges();

      expect(knopf('Angaben löschen')!.disabled).toBeTrue();
    });

    it('nennt das Ergebnis und sucht danach erneut', () => {
      dialogAntwort(true);
      moderation.meldungenEinerPerson.calls.reset();
      moderation.meldungenEinerPerson.and.returnValue(of({ total: 0, reports: [] }));

      knopf('Angaben löschen')!.click();
      fixture.detectChanges();

      expect(snackBar.open).toHaveBeenCalledWith(
        '1 erledigte Meldung gelöscht, 1 offene ohne Name und E-Mail-Adresse',
        'OK',
        jasmine.any(Object)
      );
      expect(moderation.meldungenEinerPerson).toHaveBeenCalledWith({ email: 'anna@example.org', name: null });
      expect(element().textContent).toContain('Keine Meldungen mit diesen Angaben');
    });
  });
});
