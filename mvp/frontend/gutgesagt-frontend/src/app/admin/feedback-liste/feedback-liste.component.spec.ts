import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import { FeedbackListeComponent } from './feedback-liste.component';
import { FeedbackEintrag } from '../../shared/feedback/feedback.service';
import { environment } from '../../../environments/environment';
import { NACHLADEN_MS } from '../../shared/selbst-nachladen';

const URL = `${environment.baseUrl}/api/v1/feedback`;
const OFFEN = `${URL}?erledigt=false`;
const ERLEDIGT = `${URL}?erledigt=true`;

function eintrag(overrides: Partial<FeedbackEintrag> = {}): FeedbackEintrag {
  return {
    id: 'a',
    text: 'Kopieren klappt mobil nicht',
    kontakt: 'anna@example.org',
    eingegangen_am: '2026-10-27',
    erledigt: false,
    ...overrides,
  };
}

describe('FeedbackListeComponent', () => {
  let fixture: ComponentFixture<FeedbackListeComponent>;
  let http: HttpTestingController;
  let dialog: jasmine.SpyObj<MatDialog>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    dialog = jasmine.createSpyObj('MatDialog', ['open']);
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
    await TestBed.configureTestingModule({
      imports: [FeedbackListeComponent, NoopAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    TestBed.overrideProvider(MatDialog, { useValue: dialog });
    TestBed.overrideProvider(MatSnackBar, { useValue: snackBar });

    fixture = TestBed.createComponent(FeedbackListeComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  function element(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  function text(): string {
    return element().textContent ?? '';
  }

  function zeilen(): string[][] {
    return Array.from(element().querySelectorAll('[data-testid="feedback-eintrag"]')).map((z) =>
      Array.from(z.querySelectorAll('td.inhalt')).map((td) => td.textContent?.trim() ?? '')
    );
  }

  function knopf(beschriftung: string, wurzel: Element = element()): HTMLButtonElement | undefined {
    return (Array.from(wurzel.querySelectorAll('button')) as HTMLButtonElement[]).find((b) =>
      b.textContent?.includes(beschriftung)
    );
  }

  function erledigteZeigen() {
    knopf('Erledigt', element().querySelector('[data-testid="feedback-filter"]')!)!.click();
  }

  function laden(url: string, eintraege: FeedbackEintrag[]) {
    http.expectOne(url).flush({ aufbewahrung_tage: 180, eintraege });
    fixture.detectChanges();
  }

  describe('Liste', () => {
    it('zeigt das offene Feedback mit Tag, Text und Kontakt, wie geliefert', () => {
      laden(OFFEN, [eintrag(), eintrag({ id: 'b', text: 'Gefällt mir', kontakt: null, eingegangen_am: '2026-10-26' })]);

      expect(zeilen()).toEqual([
        ['27.10.2026', 'Kopieren klappt mobil nicht', 'anna@example.org'],
        ['26.10.2026', 'Gefällt mir', '–'],
      ]);
      expect(text()).toContain('180 Tagen');
    });

    it('sagt, wenn kein offenes Feedback da ist', () => {
      laden(OFFEN, []);

      expect(text()).toContain('Kein offenes Feedback');
    });

    it('laedt im Takt still nach, ohne die Liste zu leeren', () => {
      jasmine.clock().install();
      try {
        spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
        // Der Takt startet mit dem ersten Laden; diesen Test neu aufsetzen, damit die Uhr ihn kennt.
        http.expectOne(OFFEN).flush({ eintraege: [], aufbewahrung_tage: 30 });
        fixture.destroy();
        fixture = TestBed.createComponent(FeedbackListeComponent);
        fixture.detectChanges();
        laden(OFFEN, [eintrag()]);

        jasmine.clock().tick(NACHLADEN_MS);
        const nachladen = http.expectOne(OFFEN);
        fixture.detectChanges();
        expect(zeilen().length).toBe(1);

        nachladen.flush({ eintraege: [eintrag(), eintrag({ id: 'b', text: 'Neu' })], aufbewahrung_tage: 30 });
        fixture.detectChanges();
        expect(zeilen().length).toBe(2);
        fixture.destroy();
      } finally {
        jasmine.clock().uninstall();
      }
    });

    it('meldet einen Ladefehler', () => {
      http.expectOne(OFFEN).flush('kaputt', { status: 500, statusText: 'Server Error' });
      fixture.detectChanges();

      expect(text()).toContain('gerade nicht erreichbar, neuer Versuch in Kürze');
    });
  });

  describe('Filter offen/erledigt', () => {
    it('lädt beim Umschalten das erledigte Feedback', () => {
      laden(OFFEN, [eintrag()]);

      erledigteZeigen();
      laden(ERLEDIGT, [eintrag({ id: 'c', text: 'Schon beantwortet', erledigt: true })]);

      expect(zeilen().map((z) => z[1])).toEqual(['Schon beantwortet']);
    });

    it('sagt, wenn kein erledigtes Feedback da ist', () => {
      laden(OFFEN, []);

      erledigteZeigen();
      laden(ERLEDIGT, []);

      expect(text()).toContain('Kein erledigtes Feedback');
    });
  });

  describe('Erledigt setzen', () => {
    function zeile(): Element {
      return element().querySelector('[data-testid="feedback-eintrag"]')!;
    }

    it('markiert offenes Feedback als erledigt und nimmt es aus der Liste', () => {
      laden(OFFEN, [eintrag()]);

      knopf('Als erledigt markieren', zeile())!.click();
      const anfrage = http.expectOne(`${URL}/a`);
      expect(anfrage.request.method).toBe('PATCH');
      expect(anfrage.request.body).toEqual({ erledigt: true });
      anfrage.flush(eintrag({ erledigt: true }));
      fixture.detectChanges();

      expect(zeilen()).toEqual([]);
    });

    it('nennt in den Knöpfen den Eintrag, für Screenreader', () => {
      laden(OFFEN, [eintrag()]);

      const beschriftungen = Array.from(zeile().querySelectorAll('button')).map((b) => b.getAttribute('aria-label'));

      expect(beschriftungen).toEqual([
        'Als erledigt markieren: Feedback vom 27.10.2026',
        'Löschen: Feedback vom 27.10.2026',
      ]);
    });

    it('nimmt erledigt zurück', () => {
      laden(OFFEN, []);
      erledigteZeigen();
      laden(ERLEDIGT, [eintrag({ erledigt: true })]);

      knopf('Wieder offen', zeile())!.click();
      const anfrage = http.expectOne(`${URL}/a`);
      expect(anfrage.request.body).toEqual({ erledigt: false });
      anfrage.flush(eintrag());
      fixture.detectChanges();

      expect(zeilen()).toEqual([]);
    });

    it('lässt den Eintrag bei einem Fehler stehen und sagt es', () => {
      laden(OFFEN, [eintrag()]);

      knopf('Als erledigt markieren', zeile())!.click();
      http.expectOne(`${URL}/a`).flush('kaputt', { status: 500, statusText: 'Server Error' });
      fixture.detectChanges();

      expect(zeilen().length).toBe(1);
      expect(snackBar.open).toHaveBeenCalled();
    });
  });

  describe('Einzeln löschen', () => {
    function loeschenKlicken(ja: boolean) {
      dialog.open.and.returnValue({ afterClosed: () => of(ja) } as any);
      knopf('Löschen', element().querySelector('[data-testid="feedback-eintrag"]')!)!.click();
    }

    it('löscht nichts, wenn die Rückfrage abgebrochen wird', () => {
      laden(OFFEN, [eintrag()]);

      loeschenKlicken(false);

      expect(dialog.open).toHaveBeenCalled();
      http.expectNone(`${URL}/a`);
      expect(zeilen().length).toBe(1);
    });

    it('löscht nach der Rückfrage und nimmt den Eintrag aus der Liste', () => {
      laden(OFFEN, [eintrag()]);

      loeschenKlicken(true);
      const anfrage = http.expectOne(`${URL}/a`);
      expect(anfrage.request.method).toBe('DELETE');
      anfrage.flush(null, { status: 204, statusText: 'No Content' });
      fixture.detectChanges();

      expect(zeilen()).toEqual([]);
    });

    it('lässt den Eintrag bei einem Fehler stehen und sagt es', () => {
      laden(OFFEN, [eintrag()]);

      loeschenKlicken(true);
      http.expectOne(`${URL}/a`).flush('kaputt', { status: 500, statusText: 'Server Error' });
      fixture.detectChanges();

      expect(zeilen().length).toBe(1);
      expect(snackBar.open).toHaveBeenCalled();
    });
  });
});
