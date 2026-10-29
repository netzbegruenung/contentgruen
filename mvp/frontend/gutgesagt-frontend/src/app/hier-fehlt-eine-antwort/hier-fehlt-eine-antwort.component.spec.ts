import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { HierFehltEineAntwortComponent } from './hier-fehlt-eine-antwort.component';
import { environment } from '../../environments/environment';

const LISTE_URL = `${environment.baseUrl}/api/v1/statement/unbeantwortet`;
const VORAB_URL = `${environment.baseUrl}/api/v1/statement/vorab`;
const THEMEN_URL = `${environment.baseUrl}/api/v1/statement/themen`;
const ZUORDNEN_URL = `${THEMEN_URL}/zuordnen`;
const THEMEN = [
  { schluessel: 'klima', name: 'Klima' },
  { schluessel: 'energie-heizen', name: 'Energie und Heizen' },
  { schluessel: 'verkehr', name: 'Verkehr' },
];

type Zeile = {
  statement_id: string;
  statement_text: string;
  personen_ohne_treffer: number;
  themen?: Array<{ schluessel: string; name: string }>;
};

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
    http.expectOne(THEMEN_URL).flush({ themen: THEMEN });
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

  function liefern(liste: Zeile[], url = LISTE_URL) {
    http.expectOne(url).flush({ aussagen: liste.map((z) => ({ themen: [], ...z })) });
    fixture.detectChanges();
  }

  function knopf(bereich: Element, name: string): HTMLButtonElement {
    const knoepfe = Array.from(bereich.querySelectorAll('button')) as HTMLButtonElement[];
    return knoepfe.find((k) => k.textContent?.trim() === name)!;
  }

  it('zeigt die unbeantworteten Aussagen in der gelieferten Reihenfolge', () => {
    liefern([
      { statement_id: 'a-1', statement_text: 'Wärmepumpen sind zu teuer', personen_ohne_treffer: 3 },
      { statement_id: 'a-2', statement_text: 'Windräder sind hässlich', personen_ohne_treffer: 0 },
    ]);

    const zeilen = aussagen();
    expect(zeilen.length).toBe(2);
    expect(zeilen[0].textContent).toContain('Wärmepumpen sind zu teuer');
    expect(zeilen[1].textContent).toContain('Windräder sind hässlich');
  });

  it('markiert, wonach ohne Treffer gesucht wurde, mit der Zahl der Personen', () => {
    liefern([
      { statement_id: 'a-1', statement_text: 'Wärmepumpen sind zu teuer', personen_ohne_treffer: 3 },
      { statement_id: 'a-2', statement_text: 'Windräder sind hässlich', personen_ohne_treffer: 0 },
    ]);

    const [gesucht, ohneKommentar] = aussagen();
    expect(gesucht.querySelector('.gesucht')?.textContent?.trim()).toBe(
      'Danach wurde ohne Treffer gesucht: 3 Personen',
    );
    expect(ohneKommentar.querySelector('.gesucht')).toBeNull();
  });

  it('zeigt eine einzelne Person im Singular', () => {
    liefern([{ statement_id: 'a-1', statement_text: 'Wärmepumpen sind zu teuer', personen_ohne_treffer: 1 }]);

    expect(aussagen()[0].querySelector('.gesucht')?.textContent?.trim()).toBe(
      'Danach wurde ohne Treffer gesucht: 1 Person',
    );
  });

  it('"Selbst beantworten" führt ins Kommentarformular mit gesetzter Aussage', () => {
    liefern([{ statement_id: 'a-1', statement_text: 'Wärmepumpen sind zu teuer', personen_ohne_treffer: 0 }]);

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

  describe('Themen', () => {
    it('filtert nach einem Thema und lädt die Liste dafür neu', () => {
      liefern([{ statement_id: 'a-1', statement_text: 'Wärmepumpen sind zu teuer', personen_ohne_treffer: 0 }]);

      knopf(element().querySelector('app-themen-filter')!, 'Verkehr').click();
      fixture.detectChanges();

      liefern([], `${LISTE_URL}?thema=verkehr`);
      expect(text()).toContain('Zu diesem Thema fehlt gerade keine Antwort');
    });

    it('zeigt die Themen jeder Aussage', () => {
      liefern([
        {
          statement_id: 'a-1',
          statement_text: 'Wärmepumpen sind zu teuer',
          personen_ohne_treffer: 0,
          themen: [THEMEN[1]],
        },
      ]);

      const marken = Array.from(aussagen()[0].querySelectorAll('.thema-marke')).map((m) => m.textContent?.trim());
      expect(marken).toEqual(['Energie und Heizen']);
      expect(knopf(aussagen()[0], 'Themen ändern')).toBeTruthy();
    });

    it('ordnet einer vorhandenen Aussage nachträglich ein Thema zu', () => {
      liefern([{ statement_id: 'a-1', statement_text: 'Wärmepumpen sind zu teuer', personen_ohne_treffer: 0 }]);

      knopf(aussagen()[0], 'Themen zuordnen').click();
      fixture.detectChanges();
      knopf(aussagen()[0].querySelector('app-themen-auswahl')!, 'Energie und Heizen').click();

      const anfrage = http.expectOne(ZUORDNEN_URL);
      expect(anfrage.request.method).toBe('PUT');
      expect(anfrage.request.body).toEqual({ statement_id: 'a-1', themen: ['energie-heizen'] });
      anfrage.flush({ statement_id: 'a-1', themen: [THEMEN[1]] });
      fixture.detectChanges();

      expect(aussagen()[0].querySelector('.thema-marke')?.textContent?.trim()).toBe('Energie und Heizen');
    });

    it('meldet, wenn das Zuordnen scheitert', () => {
      liefern([{ statement_id: 'a-1', statement_text: 'Wärmepumpen sind zu teuer', personen_ohne_treffer: 0 }]);

      knopf(aussagen()[0], 'Themen zuordnen').click();
      fixture.detectChanges();
      knopf(aussagen()[0].querySelector('app-themen-auswahl')!, 'Klima').click();
      http.expectOne(ZUORDNEN_URL).flush('kaputt', { status: 500, statusText: 'Server Error' });
      fixture.detectChanges();

      expect(text()).toContain('Die Themen konnten nicht gespeichert werden');
      expect(aussagen()[0].querySelector('.thema-marke')).toBeNull();
    });
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
      expect(anfrage.request.body).toEqual({ text: 'Das Heizungsgesetz enteignet uns', themen: [] });
      anfrage.flush({
        statement_was_new: true,
        statement_id: 'neu-1',
        statement_text: 'Das Heizungsgesetz enteignet uns',
      });
      fixture.detectChanges();

      liefern([{ statement_id: 'neu-1', statement_text: 'Das Heizungsgesetz enteignet uns', personen_ohne_treffer: 0 }]);
      expect(text()).toContain('Aussage angelegt');
      expect((element().querySelector('textarea[name="aussage"]') as HTMLTextAreaElement).value).toBe('');
      expect(aussagen().length).toBe(1);
    });

    it('schickt die gewählten Themen mit', () => {
      eingeben('Das Heizungsgesetz enteignet uns');
      const auswahl = element().querySelector('.vorab app-themen-auswahl')!;
      knopf(auswahl, 'Energie und Heizen').click();
      fixture.detectChanges();
      anlegen();

      const anfrage = http.expectOne(VORAB_URL);
      expect(anfrage.request.body).toEqual({
        text: 'Das Heizungsgesetz enteignet uns',
        themen: ['energie-heizen'],
      });
      anfrage.flush({ statement_was_new: true, statement_id: 'neu-1', statement_text: 'x' });
      fixture.detectChanges();
      liefern([]);
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
