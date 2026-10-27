import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { HierFehltEineAntwortComponent } from './hier-fehlt-eine-antwort.component';
import { environment } from '../../environments/environment';

const LISTE_URL = `${environment.baseUrl}/api/v1/statement/unbeantwortet`;
const VORAB_URL = `${environment.baseUrl}/api/v1/statement/vorab`;

describe('HierFehltEineAntwortComponent', () => {
  let fixture: ComponentFixture<HierFehltEineAntwortComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HierFehltEineAntwortComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        provideNoopAnimations(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(HierFehltEineAntwortComponent);
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

  function aussagen(): HTMLElement[] {
    return Array.from(element().querySelectorAll('[data-testid="unbeantwortete-aussage"]'));
  }

  function liefern(liste: Array<{ statement_id: string; statement_text: string; ohne_treffer_gesucht: boolean }>) {
    http.expectOne(LISTE_URL).flush({ aussagen: liste });
    fixture.detectChanges();
  }

  it('zeigt die unbeantworteten Aussagen in der gelieferten Reihenfolge', () => {
    liefern([
      { statement_id: 'a-1', statement_text: 'Wärmepumpen sind zu teuer', ohne_treffer_gesucht: true },
      { statement_id: 'a-2', statement_text: 'Windräder sind hässlich', ohne_treffer_gesucht: false },
    ]);

    const zeilen = aussagen();
    expect(zeilen.length).toBe(2);
    expect(zeilen[0].textContent).toContain('Wärmepumpen sind zu teuer');
    expect(zeilen[1].textContent).toContain('Windräder sind hässlich');
  });

  it('markiert, wonach ohne Treffer gesucht wurde, ohne Zahlen', () => {
    liefern([
      { statement_id: 'a-1', statement_text: 'Wärmepumpen sind zu teuer', ohne_treffer_gesucht: true },
      { statement_id: 'a-2', statement_text: 'Windräder sind hässlich', ohne_treffer_gesucht: false },
    ]);

    const [gesucht, ohneKommentar] = aussagen();
    expect(gesucht.querySelector('.gesucht')?.textContent).toContain('ohne Treffer gesucht');
    expect(ohneKommentar.querySelector('.gesucht')).toBeNull();
  });

  it('"Selbst beantworten" führt ins Kommentarformular mit gesetzter Aussage', () => {
    liefern([{ statement_id: 'a-1', statement_text: 'Wärmepumpen sind zu teuer', ohne_treffer_gesucht: false }]);

    const knopf = aussagen()[0].querySelector('a.selbst-beantworten') as HTMLAnchorElement;
    expect(knopf.textContent).toContain('Selbst beantworten');
    expect(knopf.getAttribute('href')).toBe('/workflow/add-commentary?aussage=a-1&von=hier-fehlt-eine-antwort');
  });

  it('sagt, wenn gerade nichts fehlt', () => {
    liefern([]);

    expect(aussagen().length).toBe(0);
    expect(text()).toContain('Gerade fehlt keine Antwort');
  });

  it('meldet einen Ladefehler', () => {
    http.expectOne(LISTE_URL).flush('kaputt', { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(text()).toContain('konnten nicht geladen werden');
  });

  describe('Aussage vorab anlegen', () => {
    function eingeben(wert: string) {
      const feld = element().querySelector('textarea[name="aussage"]') as HTMLTextAreaElement;
      feld.value = wert;
      feld.dispatchEvent(new Event('input'));
      fixture.detectChanges();
    }

    function anlegen() {
      (element().querySelector('button.aussage-anlegen') as HTMLButtonElement).click();
      fixture.detectChanges();
    }

    beforeEach(() => liefern([]));

    it('legt die Aussage an und lädt die Liste neu', () => {
      eingeben('  Das Heizungsgesetz enteignet uns  ');
      anlegen();

      const anfrage = http.expectOne(VORAB_URL);
      expect(anfrage.request.method).toBe('POST');
      expect(anfrage.request.body).toEqual({ text: 'Das Heizungsgesetz enteignet uns' });
      anfrage.flush({
        statement_was_new: true,
        statement_id: 'neu-1',
        statement_text: 'Das Heizungsgesetz enteignet uns',
      });
      fixture.detectChanges();

      liefern([{ statement_id: 'neu-1', statement_text: 'Das Heizungsgesetz enteignet uns', ohne_treffer_gesucht: false }]);
      expect(text()).toContain('Aussage angelegt');
      expect((element().querySelector('textarea[name="aussage"]') as HTMLTextAreaElement).value).toBe('');
      expect(aussagen().length).toBe(1);
    });

    it('nennt eine schon vorhandene ähnliche Aussage', () => {
      eingeben('Das Heizungsgesetz enteignet uns');
      anlegen();

      http.expectOne(VORAB_URL).flush({
        statement_was_new: false,
        statement_id: 'alt-1',
        statement_text: 'Heizungsgesetz = Enteignung',
      });
      fixture.detectChanges();
      liefern([]);

      expect(text()).toContain('gibt es schon');
      expect(text()).toContain('Heizungsgesetz = Enteignung');
    });

    it('schickt zu kurze Aussagen nicht ab', () => {
      eingeben('ab');

      expect((element().querySelector('button.aussage-anlegen') as HTMLButtonElement).disabled).toBeTrue();
    });

    it('meldet, wenn das Anlegen scheitert, und behält den Text', () => {
      eingeben('Das Heizungsgesetz enteignet uns');
      anlegen();

      http.expectOne(VORAB_URL).flush('kaputt', { status: 500, statusText: 'Server Error' });
      fixture.detectChanges();

      expect(text()).toContain('konnte nicht angelegt werden');
      expect((element().querySelector('textarea[name="aussage"]') as HTMLTextAreaElement).value)
        .toBe('Das Heizungsgesetz enteignet uns');
    });
  });
});
