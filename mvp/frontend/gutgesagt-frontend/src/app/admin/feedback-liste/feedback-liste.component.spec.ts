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

    it('meldet einen Ladefehler', () => {
      http.expectOne(OFFEN).flush('kaputt', { status: 500, statusText: 'Server Error' });
      fixture.detectChanges();

      expect(text()).toContain('konnte nicht geladen werden');
    });
  });

  describe('Filter offen/erledigt', () => {
    it('lädt beim Umschalten das erledigte Feedback', () => {
      laden(OFFEN, [eintrag()]);

      knopf('Erledigt', element().querySelector('[data-testid="feedback-filter"]')!)!.click();
      laden(ERLEDIGT, [eintrag({ id: 'c', text: 'Schon beantwortet', erledigt: true })]);

      expect(zeilen().map((z) => z[1])).toEqual(['Schon beantwortet']);
    });

    it('sagt, wenn kein erledigtes Feedback da ist', () => {
      laden(OFFEN, []);

      knopf('Erledigt', element().querySelector('[data-testid="feedback-filter"]')!)!.click();
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

      knopf('Erledigt', zeile())!.click();
      const anfrage = http.expectOne(`${URL}/a`);
      expect(anfrage.request.method).toBe('PATCH');
      expect(anfrage.request.body).toEqual({ erledigt: true });
      anfrage.flush(eintrag({ erledigt: true }));
      fixture.detectChanges();

      expect(zeilen()).toEqual([]);
    });

    it('nimmt erledigt zurück', () => {
      laden(OFFEN, []);
      knopf('Erledigt', element().querySelector('[data-testid="feedback-filter"]')!)!.click();
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

      knopf('Erledigt', zeile())!.click();
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
