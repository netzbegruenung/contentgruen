import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter, Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import { LADE_GROESSE, RawInputListComponent } from './raw-input-list.component';
import { FILTER_SCHLUESSEL } from './fangkorb-filter';
import { PLATTFORMEN } from '../shared/plattform';
import { KETTEN_ICONS } from '../shared/fangkorb-texte';
import {
  GetRawInputsResponse,
  RawInput,
  RawInputDraft,
  RawInputLink,
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

function link(draft_id: string | null, content_type: string | null, processed_by = 'carol'): RawInputLink {
  return {
    content_id: `c-${draft_id}`,
    content_type,
    draft_id,
    processed_by,
    processed_at: '2026-09-13T13:00:00Z',
  };
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

  /** Die Einwurf-Karten, oben in jedem Stapel. */
  function karten(): HTMLElement[] {
    return Array.from(fixture.nativeElement.querySelectorAll('li.stapel > app-beitragskarte article.art-einwurf'));
  }

  /** Die Satz-Karten, eingerueckt unter ihrem Einwurf. */
  function satzKarten(stapel: Element = fixture.nativeElement): HTMLElement[] {
    return Array.from(stapel.querySelectorAll('.stapel-saetze article.art-satz'));
  }

  function stapel(): HTMLElement[] {
    return Array.from(fixture.nativeElement.querySelectorAll('li.stapel'));
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

  describe('Kopf', () => {
    function langfassung(): HTMLElement | null {
      return fixture.nativeElement.querySelector('.erklaerung');
    }

    it('zeigt die drei Schritte als Stepper, die Erklaerung erst ueber das Hilfe-Icon', () => {
      erstellen([]);
      const schritte = Array.from(fixture.nativeElement.querySelectorAll('.stepper-schritt') as NodeListOf<HTMLElement>);
      const pfeile = Array.from(fixture.nativeElement.querySelectorAll('.stepper-pfeil') as NodeListOf<HTMLElement>);

      expect(schritte.map((schritt) => schritt.querySelector('.stepper-emoji')!.textContent!.trim())).toEqual([
        KETTEN_ICONS.einwerfen,
        KETTEN_ICONS.destillieren,
        KETTEN_ICONS.verfassen,
      ]);
      expect(schritte.map((schritt) => schritt.querySelector('.stepper-wort')!.textContent!.trim())).toEqual([
        'Einwerfen',
        'Destillieren',
        'Ausformulieren',
      ]);
      expect(pfeile.map((pfeil) => pfeil.textContent!.trim())).toEqual(['chevron_right', 'chevron_right']);
      expect(langfassung()).toBeNull();
      expect(fixture.nativeElement.textContent).not.toContain('Jeder Schritt kann von jemand anderem kommen.');

      klicken(fixture.nativeElement.querySelector('.fangkorb-kopf .erklaerung-umschalter'));

      expect(langfassung()!.textContent).toContain('Jeder Schritt kann von jemand anderem kommen.');
      const langeSchritte = Array.from(
        langfassung()!.querySelectorAll('.dreiklang li strong') as NodeListOf<HTMLElement>,
      ).map((schritt) => schritt.textContent!.trim());
      expect(langeSchritte).toEqual(['Einwerfen', 'Destillieren', 'Ausformulieren']);
    });

    it('gibt den drei Schritten gleich breite Spalten und dem Hilfe-Icon keinen Knopfrahmen', () => {
      erstellen([]);
      const breiten = Array.from(fixture.nativeElement.querySelectorAll('.stepper-schritt') as NodeListOf<HTMLElement>).map(
        (schritt) => Math.round(schritt.getBoundingClientRect().width),
      );
      const hilfe: HTMLButtonElement = fixture.nativeElement.querySelector('.erklaerung-umschalter');

      expect(new Set(breiten).size).toBe(1);
      expect(hilfe.classList).not.toContain('mat-mdc-icon-button');
      expect(getComputedStyle(hilfe).boxShadow).toBe('none');
      expect(getComputedStyle(hilfe).borderTopStyle).toBe('none');
      expect(hilfe.getAttribute('aria-expanded')).toBe('false');
    });

    it('beginnt auch beim zweiten Oeffnen mit zugeklappter Erklaerung', () => {
      erstellen([]);
      klicken(fixture.nativeElement.querySelector('.erklaerung-umschalter'));
      fixture.destroy();

      erstellen([]);

      expect(langfassung()).toBeNull();
    });

    it('zeigt keinen Erstnutzer-Satz', () => {
      erstellen([]);

      expect(fixture.nativeElement.querySelector('.erstnutzer-satz')).toBeNull();
      expect(fixture.nativeElement.textContent).not.toContain('Gut gesagt ist neu.');
    });

    it('fuehrt mit dem schwebenden Knopf zum Einwerfen', () => {
      erstellen([]);
      const fab: HTMLButtonElement = fixture.nativeElement.querySelector('button.einwerfen-fab');

      expect(fab.getAttribute('aria-label')).toBe('Etwas einwerfen');
      klicken(fab);

      expect(router.navigate).toHaveBeenCalledWith(['/einwerfen']);
    });

    it('stellt nur offene und nur meine vor die Plattform-Chips, in einer Leiste', () => {
      erstellen([]);
      const leiste: HTMLElement = fixture.nativeElement.querySelector('.filterleiste');
      const chips = Array.from(leiste.querySelectorAll('.filter-chip') as NodeListOf<HTMLElement>).map(
        (chip) => chip.textContent!.trim(),
      );

      expect(chips).toEqual(['nur offene', 'nur meine', ...PLATTFORMEN.map((eintrag) => eintrag.name)]);
      expect(leiste.querySelector('.filter-trenner')).toBeTruthy();
    });
  });

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
    it('zeigt einen offenen Einwurf gestrichelt mit Link, Plattform, Hinweis und Einwerfer', () => {
      erstellen([
        einwurf({
          url: 'https://www.instagram.com/reel/ABC/',
          content: 'Gute Antwort in den Kommentaren',
          submitted_by: '0f3c2a9e-1111-2222-3333-444455556666',
        }),
      ]);
      const [karte] = karten();

      expect(karte.classList).toContain('karte--rohling');
      expect(karte.classList).toContain('zustand-offen');
      expect(getComputedStyle(karte).borderTopStyle).toBe('dashed');
      expect(karte.querySelector('a.einwurf-link')!.getAttribute('href')).toBe(
        'https://www.instagram.com/reel/ABC/',
      );
      expect(karte.querySelector('.plattform-chip')!.textContent!.trim()).toBe('Instagram');
      const hinweis = karte.querySelector('.einwurf-hinweis')!;
      expect(hinweis.textContent).toContain('Gute Antwort in den Kommentaren');
      expect(hinweis.classList).toContain('hinweis-box');
      const einwerfer = karte.querySelector('.personen .person')!;
      expect(karte.querySelector('.personen')!.textContent).toContain('eingeworfen von');
      expect(einwerfer.textContent!.trim()).toBe('0f3c2a9e');
      expect(einwerfer.getAttribute('title')).toBe('0f3c2a9e-1111-2222-3333-444455556666');
      expect(satzKarten().length).toBe(0);
    });

    it('zeigt ohne Link keinen Plattform-Chip', () => {
      erstellen([einwurf({ url: null, content: 'nur ein Satz' })]);

      expect(karten()[0].querySelector('.plattform-chip')).toBeNull();
    });

    it('wiederholt den Link nicht als Hinweis', () => {
      erstellen([einwurf({ content: 'https://example.org/post' })]);

      expect(karten()[0].querySelector('.einwurf-hinweis')).toBeNull();
    });

    it('legt unter den Einwurf je Satz eine destillierte Karte mit Satz und Person', () => {
      erstellen([
        einwurf({
          status: 'in_progress',
          destilled_by: 'bob',
          drafts: [satz('s-1', 'bob', 'Satz von Bob'), satz('s-2', 'carol', 'Satz von Carol')],
        }),
      ]);
      const [karte] = karten();
      const saetze = satzKarten(stapel()[0]);

      expect(karte.classList).toContain('zustand-offen');
      expect(saetze.length).toBe(2);
      saetze.forEach((satzKarte) => {
        expect(satzKarte.classList).toContain('zustand-destilliert');
        expect(getComputedStyle(satzKarte).borderTopStyle).toBe('solid');
        expect(satzKarte.querySelector('.beitrag-link')).toBeNull();
      });
      expect(saetze[0].querySelector('.karte-titel')!.textContent).toContain('Satz von Bob');
      expect(saetze[0].querySelector('.personen')!.textContent).toContain('destilliert von');
      expect(saetze[0].querySelector('.personen .person')!.textContent!.trim()).toBe('bob');
      expect(saetze[1].querySelector('.karte-titel')!.textContent).toContain('Satz von Carol');
      expect(saetze[0].getAttribute('aria-label')).toContain('destilliert');
    });

    it('faerbt einen ausformulierten Satz nach seinem Beitragstyp, jeden fuer sich', () => {
      erstellen([
        einwurf({
          id: 'kommentar',
          status: 'processed',
          drafts: [
            satz('s-1', 'bob', 'Nicht genommen'),
            satz('s-2', 'carol', 'Genommen'),
            satz('s-3', 'dave', 'Als Hintergrund'),
          ],
          links: [link('s-2', 'commentary'), link('s-3', 'generic_text', 'erin')],
        }),
      ]);
      const [nicht, kommentar, hintergrund] = satzKarten();

      expect(nicht.classList).toContain('zustand-destilliert');
      expect(kommentar.classList).toContain('zustand-ausformuliert');
      expect(kommentar.classList).toContain('typ-commentary');
      expect(hintergrund.classList).toContain('typ-generictext');
      expect(kommentar.querySelector('.personen')!.textContent).toContain('destilliert von');
      expect(kommentar.querySelector('.personen')!.textContent).toContain('ausformuliert von');
      expect(kommentar.textContent).not.toContain('eingeworfen von');

      const knopf: HTMLButtonElement = kommentar.querySelector('button.beitrag-link')!;
      expect(knopf.textContent!.trim()).toBe('In der Suche anzeigen');
      expect(nicht.querySelector('.beitrag-link')).toBeNull();
    });

    it('laesst Verknuepfungen ohne passenden Satz weg', () => {
      erstellen([
        einwurf({
          status: 'processed',
          drafts: [satz('s-1', 'bob', 'Nie ausformuliert')],
          links: [link('s-geleert', 'commentary'), link(null, 'generic_text')],
        }),
        einwurf({ id: 'alt', status: 'processed', links: [link(null, null)] }),
      ]);
      const [erster, alt] = stapel();

      expect(satzKarten(erster).length).toBe(1);
      expect(satzKarten(erster)[0].classList).toContain('zustand-destilliert');
      expect(satzKarten(erster)[0].querySelector('.beitrag-link')).toBeNull();
      expect(satzKarten(alt).length).toBe(0);
    });

    it('dimmt einen verworfenen Einwurf ab und sagt es dazu', () => {
      erstellen([einwurf({ status: 'discarded' })]);
      const [karte] = karten();

      expect(karte.classList).toContain('zustand-verworfen');
      expect(getComputedStyle(karte).opacity).toBe('0.55');
      expect(karte.querySelector('.verworfen-hinweis')!.textContent!.trim()).toBe('verworfen');
    });
  });

  describe('Tippen', () => {
    const ausformuliert = () =>
      einwurf({
        id: 'id-9',
        status: 'processed',
        drafts: [
          satz('s-0', 'dave', 'Fremder Satz ohne Beitrag'),
          satz('s-1', 'bob', 'Waermepumpe lohnt sich auch im Altbau'),
        ],
        links: [link('s-1', 'commentary', 'bob')],
      });

    it('oeffnet offene, destillierte und ausformulierte Einwuerfe zum Destillieren', () => {
      erstellen([
        einwurf({ id: 'id-7' }),
        einwurf({ id: 'id-8', status: 'in_progress' }),
        ausformuliert(),
      ]);

      karten().forEach((karte) => karte.click());

      expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'id-7']);
      expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'id-8']);
      expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'id-9']);
      expect(router.navigate).toHaveBeenCalledTimes(3);
      karten().forEach((karte) => {
        expect(karte.getAttribute('role')).toBe('link');
        expect(karte.getAttribute('tabindex')).toBe('0');
      });
    });

    it('oeffnet auch von einer Satz-Karte aus den Einwurf, fuer einen weiteren Satz', () => {
      erstellen([ausformuliert()]);
      const [fremd, eigener] = satzKarten();

      fremd.click();
      eigener.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', bubbles: true }));

      expect(router.navigate).toHaveBeenCalledTimes(2);
      expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'id-9']);
      expect(fremd.getAttribute('role')).toBe('link');
    });

    it('laesst einen verworfenen Einwurf samt Saetzen nicht antippen', () => {
      erstellen([einwurf({ id: 'id-7', status: 'discarded', drafts: [satz('s-1', 'bob', 'Satz')] })]);
      const [karte] = karten();
      const [satzKarte] = satzKarten();

      karte.click();
      karte.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', bubbles: true }));
      satzKarte.click();

      expect(router.navigate).not.toHaveBeenCalled();
      expect(karte.getAttribute('role')).toBeNull();
      expect(karte.getAttribute('tabindex')).toBeNull();
      expect(satzKarte.getAttribute('role')).toBeNull();
    });

    it('sucht mit dem Knopf genau den ausformulierten Satz, ohne die Karte zu oeffnen', () => {
      erstellen([ausformuliert()]);
      const knopf: HTMLButtonElement = satzKarten()[1].querySelector('button.beitrag-link')!;

      knopf.click();
      knopf.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', bubbles: true }));

      expect(router.navigate).toHaveBeenCalledOnceWith(['/result'], {
        queryParams: { searchQuery: 'Waermepumpe lohnt sich auch im Altbau' },
      });
    });

    it('oeffnet mit Enter auf dem Link nicht zusaetzlich die Karte', () => {
      erstellen([einwurf({ id: 'id-7', url: 'https://example.org/p' })]);
      const linkElement: HTMLAnchorElement = karten()[0].querySelector('a.einwurf-link')!;

      linkElement.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', bubbles: true }));

      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('oeffnet den Link, ohne die Karte mitzuklicken', () => {
      erstellen([einwurf({ id: 'id-7', url: 'https://example.org/p' })]);
      const linkElement: HTMLAnchorElement = karten()[0].querySelector('a.einwurf-link')!;
      linkElement.addEventListener('click', (event) => event.preventDefault());

      linkElement.click();

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

    it('zeigt ohne Plattform-Filter keinen Chip gefuellt', () => {
      erstellen(gemischt());

      for (const plattform of PLATTFORMEN) {
        const knopf = filterKnopf(plattform.name);
        expect(knopf.classList).not.toContain('aktiv');
        expect(knopf.getAttribute('aria-pressed')).toBe('false');
      }
      expect(karten().length).toBe(4);
    });

    it('zeigt bei gewaehlter Plattform nur deren Einwuerfe, Einwuerfe ohne Link bleiben', () => {
      erstellen(gemischt());

      klicken(filterKnopf('Instagram'));

      expect(sichtbareIds()).toEqual(['insta', 'ohne-link']);
      expect(filterKnopf('Instagram').getAttribute('aria-pressed')).toBe('true');
      expect(filterKnopf('Instagram').classList).toContain('aktiv');
      expect(filterKnopf('YouTube').getAttribute('aria-pressed')).toBe('false');
      expect(karten().length).toBe(2);
    });

    it('nimmt mit einem weiteren Tipp eine Plattform dazu', () => {
      erstellen(gemischt());

      klicken(filterKnopf('Instagram'));
      klicken(filterKnopf('YouTube'));

      expect(sichtbareIds()).toEqual(['insta', 'yt', 'ohne-link']);
    });

    it('hebt den Plattform-Filter auf, wenn die letzte gewaehlte Plattform abgewaehlt wird', () => {
      erstellen(gemischt());

      klicken(filterKnopf('Instagram'));
      klicken(filterKnopf('Instagram'));

      expect(component.filter.plattformen).toEqual(PLATTFORMEN.map((eintrag) => eintrag.wert));
      expect(sichtbareIds()).toEqual(['insta', 'yt', 'ohne-link', 'web']);
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
      expect(component.filter.plattformen).toEqual(['tiktok']);
      expect(filterKnopf('nur offene').getAttribute('aria-pressed')).toBe('true');
    });
  });
});
