import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter, Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import { LADE_GROESSE, RawInputListComponent } from './raw-input-list.component';
import { FILTER_SCHLUESSEL } from './fangkorb-filter';
import {
  GetRawInputsResponse,
  RawInput,
  RawInputDraft,
  RawInputService,
} from '../services/raw-input.service';
import { AuthService } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';

function einwurf(overrides: Partial<RawInput> = {}): RawInput {
  return {
    id: 'id-1',
    content: null,
    url: 'https://example.org/post',
    image_url: null,
    submitted_by: 'alice',
    source_channel: 'web',
    status: 'open',
    created_at: '2026-09-13T12:00:00Z',
    destilled_by: null,
    own_draft: null,
    drafts: [],
    links: [],
    ...overrides,
  };
}

function satz(id: string, user_id: string, sentence: string): RawInputDraft {
  return { id, user_id, sentence, updated_at: '2026-09-13T12:00:00Z' };
}

function antwort(results: RawInput[], gesamt = results.length): GetRawInputsResponse {
  return { results_count: results.length, results, total_records_count: gesamt };
}

describe('RawInputListComponent', () => {
  let fixture: ComponentFixture<RawInputListComponent>;
  let component: RawInputListComponent;
  let rawInputService: jasmine.SpyObj<RawInputService>;
  let router: Router;

  function erstellen(results: RawInput[], gesamt?: number): void {
    rawInputService.getRawInputs.and.returnValue(of(antwort(results, gesamt)));
    fixture = TestBed.createComponent(RawInputListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  function karten(): HTMLElement[] {
    return Array.from(fixture.nativeElement.querySelectorAll('article.einwurf-karte'));
  }

  function filterKnopf(beschriftung: string): HTMLButtonElement {
    const knoepfe: HTMLButtonElement[] = Array.from(
      fixture.nativeElement.querySelectorAll('button.filter-chip'),
    );
    return knoepfe.find((knopf) => knopf.textContent!.trim() === beschriftung)!;
  }

  function klicken(knopf: HTMLElement): void {
    knopf.click();
    fixture.detectChanges();
  }

  beforeEach(async () => {
    sessionStorage.removeItem(FILTER_SCHLUESSEL);
    rawInputService = jasmine.createSpyObj('RawInputService', ['getRawInputs']);

    await TestBed.configureTestingModule({
      imports: [RawInputListComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: RawInputService, useValue: rawInputService },
        {
          provide: AuthService,
          useValue: {
            getCurrentUserId: () => 'alice',
            fetchUserInfo: () => of({ userId: 'alice' }),
          },
        },
        {
          provide: LoggingService,
          useValue: jasmine.createSpyObj('LoggingService', ['debug', 'error', 'warn']),
        },
      ],
    }).compileComponents();

    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
  });

  afterEach(() => sessionStorage.removeItem(FILTER_SCHLUESSEL));

  describe('Laden', () => {
    it('laedt die Einwuerfe auf einmal und zeigt Karten statt einer Tabelle', () => {
      erstellen([einwurf(), einwurf({ id: 'id-2' })]);

      expect(rawInputService.getRawInputs).toHaveBeenCalledWith(1, LADE_GROESSE);
      expect(karten().length).toBe(2);
      expect(fixture.nativeElement.querySelector('table')).toBeNull();
      expect(fixture.nativeElement.querySelector('mat-paginator')).toBeNull();
    });

    it('meldet einen Ladefehler statt still leer zu bleiben', () => {
      rawInputService.getRawInputs.and.returnValue(throwError(() => new Error('kaputt')));
      fixture = TestBed.createComponent(RawInputListComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();

      expect(component.ladefehler).toBeTrue();
      expect(fixture.nativeElement.textContent).toContain('konnte nicht geladen werden');
    });

    it('sagt dazu, wenn nicht alle Einwuerfe geladen sind', () => {
      erstellen([einwurf()], 150);

      expect(fixture.nativeElement.textContent).toContain('Angezeigt werden 1 von 150');
    });

    it('sagt, wenn der Fangkorb leer ist', () => {
      erstellen([]);

      expect(fixture.nativeElement.textContent).toContain('Noch nichts drin');
    });
  });

  describe('Zustaende', () => {
    it('zeigt eine offene Karte blanko mit Link, Plattform, Hinweis und Einwerfer', () => {
      erstellen([
        einwurf({
          url: 'https://www.instagram.com/reel/ABC/',
          content: 'Gute Antwort in den Kommentaren',
          submitted_by: '0f3c2a9e-1111-2222-3333-444455556666',
        }),
      ]);
      const [karte] = karten();

      expect(karte.classList).toContain('zustand-offen');
      expect(karte.querySelector('a.einwurf-link')!.getAttribute('href')).toBe(
        'https://www.instagram.com/reel/ABC/',
      );
      expect(karte.querySelector('.plattform-chip')!.textContent!.trim()).toBe('Instagram');
      expect(karte.querySelector('.einwurf-hinweis')!.textContent).toContain(
        'Gute Antwort in den Kommentaren',
      );
      const einwerfer = karte.querySelector('.personen .person')!;
      expect(einwerfer.textContent!.trim()).toBe('0f3c2a9e');
      expect(einwerfer.getAttribute('title')).toBe('0f3c2a9e-1111-2222-3333-444455556666');
      expect(karte.querySelector('.saetze')).toBeNull();
    });

    it('zeigt ohne Link keinen Plattform-Chip', () => {
      erstellen([einwurf({ url: null, content: 'nur ein Satz' })]);

      expect(karten()[0].querySelector('.plattform-chip')).toBeNull();
    });

    it('wiederholt den Link nicht als Hinweis', () => {
      erstellen([einwurf({ content: 'https://example.org/post' })]);

      expect(karten()[0].querySelector('.einwurf-hinweis')).toBeNull();
    });

    it('zeigt auf einer destillierten Karte alle Saetze mit Person', () => {
      erstellen([
        einwurf({
          status: 'in_progress',
          destilled_by: 'bob',
          drafts: [satz('s-1', 'bob', 'Satz von Bob'), satz('s-2', 'carol', 'Satz von Carol')],
        }),
      ]);
      const [karte] = karten();
      const saetze = Array.from(karte.querySelectorAll('.saetze .satz'));

      expect(karte.classList).toContain('zustand-destilliert');
      expect(saetze.length).toBe(2);
      expect(saetze[0].textContent).toContain('Satz von Bob');
      expect(saetze[0].textContent).toContain('bob');
      expect(saetze[1].textContent).toContain('Satz von Carol');
      expect(karte.getAttribute('aria-label')).toContain('destilliert');
    });

    it('faerbt eine ausformulierte Karte nach dem Beitragstyp', () => {
      erstellen([
        einwurf({
          id: 'kommentar',
          status: 'processed',
          destilled_by: 'bob',
          processed_by: 'carol',
          drafts: [satz('s-1', 'bob', 'Nicht genommen'), satz('s-2', 'carol', 'Genommen')],
          links: [
            {
              content_id: 'c-1',
              content_type: 'commentary',
              draft_id: 's-2',
              processed_by: 'carol',
              processed_at: '2026-09-13T13:00:00Z',
            },
          ],
        }),
        einwurf({
          id: 'hintergrund',
          status: 'processed',
          links: [
            {
              content_id: 'c-2',
              content_type: 'generic_text',
              draft_id: null,
              processed_by: 'bob',
              processed_at: '2026-09-13T13:00:00Z',
            },
          ],
        }),
        einwurf({
          id: 'alt',
          status: 'processed',
          links: [
            {
              content_id: 'c-3',
              content_type: null,
              draft_id: null,
              processed_by: 'bob',
              processed_at: '2026-09-13T13:00:00Z',
            },
          ],
        }),
      ]);
      const [kommentar, hintergrund, alt] = karten();

      expect(kommentar.classList).toContain('typ-commentary');
      expect(hintergrund.classList).toContain('typ-generic_text');
      expect(alt.classList).toContain('typ-unbekannt');

      const saetze = Array.from(kommentar.querySelectorAll('.saetze .satz'));
      expect(saetze.length).toBe(1);
      expect(saetze[0].textContent).toContain('Genommen');
      expect(kommentar.querySelector('.personen')!.textContent).toContain('destilliert von');
      expect(kommentar.querySelector('.personen')!.textContent).toContain('ausformuliert von');
      expect(kommentar.textContent).not.toContain('eingeworfen von');

      const link = kommentar.querySelector('a.beitrag-link')!;
      expect(link.textContent!.trim()).toBe('In der Suche anzeigen');
      expect(link.getAttribute('href')).toBe('/result?searchQuery=Genommen');
    });

    it('dimmt eine verworfene Karte ab und sagt es dazu', () => {
      erstellen([einwurf({ status: 'discarded' })]);
      const [karte] = karten();

      expect(karte.classList).toContain('zustand-verworfen');
      expect(karte.querySelector('.verworfen-hinweis')!.textContent!.trim()).toBe('verworfen');
    });
  });

  describe('Tippen', () => {
    it('oeffnet eine offene Karte zum Destillieren', () => {
      erstellen([einwurf({ id: 'id-7' })]);

      karten()[0].click();

      expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'id-7']);
    });

    it('oeffnet eine ausformulierte Karte in der Suche', () => {
      erstellen([
        einwurf({
          status: 'processed',
          drafts: [satz('s-1', 'bob', 'Waermepumpe lohnt sich auch im Altbau')],
          links: [
            {
              content_id: 'c-1',
              content_type: 'commentary',
              draft_id: 's-1',
              processed_by: 'bob',
              processed_at: '2026-09-13T13:00:00Z',
            },
          ],
        }),
      ]);

      karten()[0].click();

      expect(router.navigate).toHaveBeenCalledWith(['/result'], {
        queryParams: { searchQuery: 'Waermepumpe lohnt sich auch im Altbau' },
      });
    });

    it('oeffnet den Link, ohne die Karte mitzuklicken', () => {
      erstellen([einwurf({ id: 'id-7', url: 'https://example.org/p' })]);
      const link: HTMLAnchorElement = karten()[0].querySelector('a.einwurf-link')!;
      link.addEventListener('click', (event) => event.preventDefault());

      link.click();

      expect(router.navigate).not.toHaveBeenCalled();
    });
  });

  describe('Filter', () => {
    const gemischt = () => [
      einwurf({ id: 'insta', url: 'https://www.instagram.com/reel/A/', submitted_by: 'bob' }),
      einwurf({ id: 'yt', url: 'https://youtu.be/1', status: 'in_progress' }),
      einwurf({ id: 'ohne-link', url: null, content: 'nur Text', status: 'processed' }),
      einwurf({ id: 'web', status: 'discarded', submitted_by: 'bob' }),
    ];

    function sichtbareIds(): string[] {
      return component.sichtbar.map((e) => e.id);
    }

    it('blendet eine abgewaehlte Plattform aus, Einwuerfe ohne Link bleiben', () => {
      erstellen(gemischt());

      klicken(filterKnopf('Instagram'));

      expect(sichtbareIds()).toEqual(['yt', 'ohne-link', 'web']);
      expect(filterKnopf('Instagram').getAttribute('aria-pressed')).toBe('false');
      expect(karten().length).toBe(3);
    });

    it('zeigt bei "nur offene" auch Destilliertes', () => {
      erstellen(gemischt());

      klicken(filterKnopf('nur offene'));

      expect(sichtbareIds()).toEqual(['insta', 'yt']);
    });

    it('zeigt bei "nur meine" nur selbst Eingeworfenes', () => {
      erstellen(gemischt());

      klicken(filterKnopf('nur meine'));

      expect(sichtbareIds()).toEqual(['yt', 'ohne-link']);
    });

    it('sagt, wenn der Filter alles ausblendet', () => {
      erstellen([einwurf({ submitted_by: 'bob' })]);

      klicken(filterKnopf('nur meine'));

      expect(fixture.nativeElement.textContent).toContain('Keine Einwürfe für diese Filter');
    });

    it('haelt den Filter in der Sitzung', () => {
      erstellen(gemischt());
      klicken(filterKnopf('nur offene'));
      klicken(filterKnopf('TikTok'));
      fixture.destroy();

      erstellen(gemischt());

      expect(component.filter.nurOffene).toBeTrue();
      expect(component.filter.plattformen).toEqual(['instagram', 'youtube', 'web']);
      expect(filterKnopf('nur offene').getAttribute('aria-pressed')).toBe('true');
    });
  });
});
