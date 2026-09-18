import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter, Router } from '@angular/router';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatBottomSheet } from '@angular/material/bottom-sheet';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';

import { LADE_GROESSE, RawInputListComponent } from './raw-input-list.component';
import { FILTER_SCHLUESSEL } from './fangkorb-filter';
import { EinwurfBeitragSheetComponent } from './einwurf-beitrag-sheet.component';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { PLATTFORMEN } from '../shared/plattform';
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

function link(draft_id: string | null, content_type: string | null = 'commentary', content_id = `c-${draft_id}`): RawInputLink {
  return {
    content_id,
    content_type,
    draft_id,
    processed_by: 'carol',
    processed_at: '2026-09-13T13:00:00Z',
  };
}

/** Ein Einwurf je Tab, damit jeder Tab etwas zu zeigen hat. */
function jeTab(): RawInput[] {
  return [
    einwurf({ id: 'roh' }),
    einwurf({ id: 'satz', status: 'in_progress', drafts: [satz('s-1', 'bob', 'Ein Satz')] }),
    einwurf({
      id: 'fertig',
      status: 'processed',
      drafts: [satz('s-2', 'bob', 'Genommen')],
      links: [link('s-2')],
    }),
    einwurf({ id: 'weg', status: 'discarded' }),
  ];
}

function antwort(results: RawInput[], gesamt = results.length): GetRawInputsResponse {
  return { results_count: results.length, results, total_records_count: gesamt };
}

describe('RawInputListComponent', () => {
  let fixture: ComponentFixture<RawInputListComponent>;
  let component: RawInputListComponent;
  let rawInputService: jasmine.SpyObj<RawInputService>;
  let router: Router;
  let bottomSheet: MatBottomSheet;
  let clipboard: jasmine.SpyObj<Clipboard>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  function erstellen(results: RawInput[], gesamt?: number): void {
    rawInputService.getRawInputs.and.returnValue(of(antwort(results, gesamt)));
    fixture = TestBed.createComponent(RawInputListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  function karten(): HTMLElement[] {
    return Array.from(fixture.nativeElement.querySelectorAll('article.karte--rohling'));
  }

  function kartenKomponenten(): BeitragskarteComponent[] {
    return fixture.debugElement
      .queryAll(By.directive(BeitragskarteComponent))
      .map((eintrag) => eintrag.componentInstance as BeitragskarteComponent);
  }

  function tabKnopf(name: string): HTMLButtonElement {
    const knoepfe: HTMLButtonElement[] = Array.from(fixture.nativeElement.querySelectorAll('button.tab'));
    return knoepfe.find((knopf) => knopf.querySelector('.tab-wort')!.textContent!.trim() === name)!;
  }

  function zaehler(name: string): string {
    return tabKnopf(name).querySelector('.tab-zahl')!.textContent!.trim();
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
    rawInputService = jasmine.createSpyObj('RawInputService', ['getRawInputs', 'updateStatus']);
    clipboard = jasmine.createSpyObj('Clipboard', ['copy']);
    clipboard.copy.and.returnValue(true);
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);

    await TestBed.configureTestingModule({
      imports: [RawInputListComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: RawInputService, useValue: rawInputService },
        { provide: Clipboard, useValue: clipboard },
        { provide: MatSnackBar, useValue: snackBar },
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
    bottomSheet = TestBed.inject(MatBottomSheet);
    spyOn(bottomSheet, 'open');
  });

  afterEach(() => sessionStorage.removeItem(FILTER_SCHLUESSEL));

  describe('Kopf', () => {
    it('zeigt die drei Stufen als Tabs mit Zaehlern, ohne Einwerfen', () => {
      erstellen(jeTab());
      const woerter = Array.from(fixture.nativeElement.querySelectorAll('.tab-wort') as NodeListOf<HTMLElement>).map(
        (wort) => wort.textContent!.trim(),
      );

      expect(woerter).toEqual(['Destillieren', 'Ausformulieren', 'Erledigt']);
      expect(fixture.nativeElement.textContent).not.toContain('Einwerfen →');
      expect(zaehler('Destillieren')).toBe('1');
      expect(zaehler('Ausformulieren')).toBe('1');
      expect(zaehler('Erledigt')).toBe('1');
    });

    it('beginnt beim Destillieren und wechselt auf Tipp', () => {
      erstellen(jeTab());

      expect(tabKnopf('Destillieren').getAttribute('aria-selected')).toBe('true');
      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['roh']);

      klicken(tabKnopf('Erledigt'));

      expect(tabKnopf('Erledigt').getAttribute('aria-selected')).toBe('true');
      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['fertig']);
    });

    it('haelt Tab und Filter in der Sitzung', () => {
      erstellen(jeTab());
      klicken(tabKnopf('Ausformulieren'));
      klicken(filterKnopf('nur meine'));
      fixture.destroy();

      erstellen(jeTab());

      expect(component.filter.tab).toBe('ausformulieren');
      expect(component.filter.nurMeine).toBeTrue();
    });

    it('fuehrt mit dem schwebenden Knopf zum Einwerfen und zeigt die Erklaerung erst auf Tipp', () => {
      erstellen([]);
      const fab: HTMLButtonElement = fixture.nativeElement.querySelector('button.einwerfen-fab');

      expect(fixture.nativeElement.querySelector('.erklaerung')).toBeNull();
      klicken(fixture.nativeElement.querySelector('.erklaerung-umschalter'));
      expect(fixture.nativeElement.querySelector('.erklaerung')).toBeTruthy();

      klicken(fab);

      expect(router.navigate).toHaveBeenCalledWith(['/einwerfen'], {
        queryParams: { von: 'fangkorb' },
      });
    });

    it('zeigt "nur meine" und die Plattformen, "nur offene" nicht mehr', () => {
      erstellen([]);
      const chips = Array.from(fixture.nativeElement.querySelectorAll('.filter-chip') as NodeListOf<HTMLElement>).map(
        (chip) => chip.textContent!.trim(),
      );

      expect(chips).toEqual(['nur meine', ...PLATTFORMEN.map((eintrag) => eintrag.name)]);
    });
  });

  describe('Tab-Zuordnung', () => {
    it('legt einen Einwurf ohne Satz unter Destillieren', () => {
      erstellen(jeTab());

      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['roh']);
      expect(karten().length).toBe(1);
    });

    it('legt Saetze ohne Beitrag unter Ausformulieren', () => {
      erstellen(jeTab());

      klicken(tabKnopf('Ausformulieren'));

      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['satz']);
    });

    it('legt alles mit Beitrag unter Erledigt, auch ohne Satz', () => {
      erstellen([
        ...jeTab(),
        einwurf({ id: 'alt', status: 'processed', created_at: '2026-09-01T10:00:00Z', links: [link(null, null)] }),
      ]);

      klicken(tabKnopf('Erledigt'));

      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['fertig', 'alt']);
    });

    it('zeigt Verworfenes erst mit dem Chip, und den nur unter Erledigt', () => {
      erstellen(jeTab());
      expect(filterKnopf('verworfen')).toBeUndefined();

      klicken(tabKnopf('Erledigt'));
      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['fertig']);

      klicken(filterKnopf('verworfen'));

      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['fertig', 'weg']);
      expect(zaehler('Erledigt')).toBe('2');
    });

    it('sortiert neueste zuerst, nicht eigene zuerst', () => {
      erstellen([
        einwurf({ id: 'alt', created_at: '2026-09-01T10:00:00Z' }),
        einwurf({ id: 'neu', created_at: '2026-09-14T10:00:00Z' }),
        einwurf({ id: 'mittel', created_at: '2026-09-10T10:00:00Z' }),
      ]);

      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['neu', 'mittel', 'alt']);
    });

    it('sagt in jedem leeren Tab in einer Zeile, dass dort nichts liegt', () => {
      erstellen([einwurf({ id: 'roh' })]);
      klicken(tabKnopf('Ausformulieren'));
      expect(fixture.nativeElement.querySelector('.fangkorb-leer').textContent!.trim()).toBe(
        'Nichts auszuformulieren.',
      );

      klicken(tabKnopf('Erledigt'));
      expect(fixture.nativeElement.querySelector('.fangkorb-leer').textContent!.trim()).toBe(
        'Noch nichts erledigt.',
      );
    });
  });

  describe('Laden', () => {
    it('laedt die Einwuerfe auf einmal, ohne Tabelle und ohne Paginator', () => {
      erstellen(jeTab());

      expect(rawInputService.getRawInputs).toHaveBeenCalledWith(1, LADE_GROESSE);
      expect(fixture.nativeElement.querySelector('table')).toBeNull();
      expect(fixture.nativeElement.querySelector('mat-paginator')).toBeNull();
    });

    it('meldet einen Ladefehler statt still leer zu bleiben', () => {
      rawInputService.getRawInputs.and.returnValue(throwError(() => new Error('kaputt')));
      fixture = TestBed.createComponent(RawInputListComponent);
      fixture.detectChanges();

      expect(fixture.componentInstance.ladefehler).toBeTrue();
      expect(fixture.nativeElement.textContent).toContain('konnte nicht geladen werden');
    });

    it('sagt dazu, dass nur die letzten Einwuerfe geladen sind und die Zaehler nur die meinen', () => {
      erstellen([einwurf()], 150);
      const hinweis: string = fixture.nativeElement.querySelector('.fangkorb-mehr').textContent;

      expect(hinweis).toContain('Von 150 Einwürfen sind die letzten 1 geladen');
      expect(hinweis).toContain('ältere fehlen');
      expect(hinweis).toContain('Zähler oben zählen nur die geladenen');
    });

    it('sagt, wenn der Fangkorb leer ist', () => {
      erstellen([]);

      expect(fixture.nativeElement.textContent).toContain('Noch nichts drin');
    });
  });

  describe('Karte', () => {
    it('zeigt Plattform und Link-Icon im Kopf, die Notiz als Titel, Alter und Knopf im Fuss', () => {
      erstellen([
        einwurf({
          url: 'https://www.instagram.com/reel/ABC/',
          content: 'Gute Antwort in den Kommentaren',
          submitted_by: 'alice',
        }),
      ]);
      const [karte] = karten();

      const linkzeile = karte.querySelector<HTMLAnchorElement>('a.rohling-linkzeile')!;
      expect(linkzeile.getAttribute('href')).toBe('https://www.instagram.com/reel/ABC/');
      expect(linkzeile.getAttribute('target')).toBe('_blank');
      expect(linkzeile.querySelector('.rohling-herkunft')!.textContent!.trim()).toBe('Instagram');
      expect(linkzeile.querySelector('.rohling-adresse')!.textContent!.trim()).toBe(
        'instagram.com/reel/ABC',
      );
      expect(linkzeile.textContent).not.toContain('https://');
      expect(karte.querySelector('.rohling-titel')!.textContent!.trim()).toBe(
        'Gute Antwort in den Kommentaren',
      );
      expect(karte.querySelector('.rohling-alter')!.textContent!.trim()).toBeTruthy();
      expect(karte.querySelector('.rohling-primaer .knopf-wort')!.textContent!.trim()).toBe('Destillieren');
    });

    it('zeigt ohne Notiz keinen Titel - dann traegt die Link-Zeile die Aufschrift', () => {
      erstellen([einwurf({ url: 'https://beispiel-zeitung.de/artikel/1', content: null })]);
      const [karte] = karten();

      expect(karte.querySelector('.rohling-titel')).toBeNull();
      expect(karte.querySelector('.rohling-herkunft')!.textContent!.trim()).toBe('beispiel-zeitung.de');
      expect(karte.querySelector('.rohling-adresse')!.textContent!.trim()).toBe(
        'beispiel-zeitung.de/artikel/1',
      );
    });

    it('zeigt ohne Link keine Link-Zeile', () => {
      erstellen([einwurf({ url: null, content: 'nur eine Notiz' })]);

      expect(karten()[0].querySelector('.rohling-linkzeile')).toBeNull();
      expect(karten()[0].querySelector('.rohling-titel')!.textContent!.trim()).toBe('nur eine Notiz');
    });

    it('nennt den Einwerfer nur, wenn es nicht die angemeldete Person ist', () => {
      erstellen([einwurf({ id: 'fremd', submitted_by: '0f3c2a9e-1111-2222-3333-444455556666' })]);
      expect(karten()[0].querySelector('.rohling-einwerfer')!.textContent!.trim()).toBe(
        'Von: 0f3c2a9e',
      );

      fixture.destroy();
      erstellen([einwurf({ submitted_by: 'alice' })]);

      expect(karten()[0].querySelector('.rohling-einwerfer')).toBeNull();
    });

    it('beschriftet den Primaerknopf nach Zustand und laesst ihn bei Verworfenem weg', () => {
      erstellen(jeTab());
      expect(karten()[0].querySelector('.rohling-primaer .knopf-wort')!.textContent!.trim()).toBe('Destillieren');

      klicken(tabKnopf('Ausformulieren'));
      expect(karten()[0].querySelector('.rohling-primaer .knopf-wort')!.textContent!.trim()).toBe('Ausformulieren');

      klicken(tabKnopf('Erledigt'));
      expect(karten()[0].querySelector('.rohling-primaer .knopf-wort')!.textContent!.trim()).toBe('Ansehen');

      klicken(filterKnopf('verworfen'));
      const verworfen = karten().find((karte) => karte.classList.contains('zustand-verworfen'))!;
      expect(verworfen.querySelector('.rohling-primaer')).toBeNull();
      expect(verworfen.querySelector('.rohling-verworfen')!.textContent!.trim()).toBe('verworfen');
    });
  });

  describe('Saetze in der Karte', () => {
    it('zeigt je Satz den Stand, mehrere Beitraege als Zahl', () => {
      erstellen([
        einwurf({
          status: 'processed',
          drafts: [satz('s-1', 'bob', 'Entwurf geblieben'), satz('s-2', 'bob', 'Zweimal genommen')],
          links: [link('s-2', 'commentary', 'c-1'), link('s-2', 'generic_text', 'c-2')],
        }),
      ]);
      klicken(tabKnopf('Erledigt'));
      const zeilen = Array.from(karten()[0].querySelectorAll('.rohling-satz') as NodeListOf<HTMLElement>);

      expect(zeilen.length).toBe(2);
      expect(zeilen[0].querySelector('.satz-text')!.textContent!.trim()).toBe('Entwurf geblieben');
      expect(zeilen[0].querySelector('.satz-status')!.textContent!.trim()).toBe('Entwurf');
      expect(zeilen[1].querySelector('.satz-status')!.textContent!.trim()).toBe('✓ 2');
    });

    it('zeigt hoechstens drei Saetze und zaehlt den Rest', () => {
      erstellen([
        einwurf({
          status: 'in_progress',
          drafts: ['a', 'b', 'c', 'd', 'e'].map((kennung, i) => satz(`s-${i}`, kennung, `Satz ${kennung}`)),
        }),
      ]);
      klicken(tabKnopf('Ausformulieren'));
      const [karte] = karten();

      expect(karte.querySelectorAll('.rohling-satz').length).toBe(3);
      expect(karte.querySelector('.rohling-mehr')!.textContent!.trim()).toBe('+2 weitere');
    });

    it('zeigt einen einzelnen Beitrag als Haken', () => {
      erstellen([
        einwurf({ status: 'processed', drafts: [satz('s-1', 'bob', 'Genommen')], links: [link('s-1')] }),
      ]);
      klicken(tabKnopf('Erledigt'));

      expect(karten()[0].querySelector('.satz-status')!.textContent!.trim()).toBe('✓');
    });
  });

  describe('Griffe', () => {
    it('fuehrt Destillieren in die Destillier-Ansicht, an den Anfang', () => {
      erstellen(jeTab());

      klicken(karten()[0].querySelector<HTMLButtonElement>('.rohling-primaer')!);

      expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'roh']);
    });

    it('fuehrt Ausformulieren direkt in die Typwahl', () => {
      erstellen(jeTab());
      klicken(tabKnopf('Ausformulieren'));

      klicken(karten()[0].querySelector<HTMLButtonElement>('.rohling-primaer')!);

      // Der Satz steht schon - dann beginnt das Ausformulieren bei der Typwahl.
      expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'satz'], {
        queryParams: { schritt: 'typwahl' },
      });
    });

    it('fuehrt Weiterdestillieren an den Anfang, nicht in die Typwahl', () => {
      erstellen(jeTab());
      klicken(tabKnopf('Erledigt'));

      component.aktionAusfuehren(component.karten[0], 'weiterDestillieren');

      expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'fertig']);
    });

    it('oeffnet mit "Ansehen" das Sheet statt einer Suche', () => {
      erstellen(jeTab());
      klicken(tabKnopf('Erledigt'));

      klicken(karten()[0].querySelector<HTMLButtonElement>('.rohling-primaer')!);

      const [komponente, optionen] = (bottomSheet.open as jasmine.Spy).calls.mostRecent().args;
      expect(komponente).toBe(EinwurfBeitragSheetComponent);
      expect(optionen.data.beitraege).toEqual([
        { contentId: 'c-s-2', typ: 'commentary', satz: 'Genommen' },
      ]);
      expect(router.navigate).not.toHaveBeenCalledWith(['/result'], jasmine.anything());
    });

    it('bietet im Menue Link kopieren und Verwerfen nur dem Einwerfer', () => {
      erstellen([einwurf({ id: 'eigen', submitted_by: 'alice' }), einwurf({ id: 'fremd', submitted_by: 'bob' })]);
      const [eigen, fremd] = kartenKomponenten();

      expect(eigen.menueEintraege.map((eintrag) => eintrag.wort)).toEqual(['Link kopieren', 'Verwerfen']);
      expect(fremd.menueEintraege.map((eintrag) => eintrag.wort)).toEqual(['Link kopieren']);
    });

    it('bietet bei Erledigtem und Verworfenem Weiterarbeiten statt Verwerfen', () => {
      erstellen(jeTab());
      klicken(tabKnopf('Erledigt'));
      expect(kartenKomponenten()[0].menueEintraege.map((eintrag) => eintrag.wort)).toEqual([
        'Link kopieren',
        'Weiter destillieren',
      ]);

      klicken(filterKnopf('verworfen'));
      const verworfen = kartenKomponenten().find((karte) => karte.daten.rohling!.zustand === 'verworfen')!;

      expect(verworfen.menueEintraege.map((eintrag) => eintrag.wort)).toEqual([
        'Link kopieren',
        'Trotzdem destillieren',
      ]);
    });

    it('kopiert den Link und sagt es', () => {
      erstellen([einwurf({ url: 'https://example.org/post' })]);

      component.aktionAusfuehren(component.karten[0], 'linkKopieren');

      expect(clipboard.copy).toHaveBeenCalledWith('https://example.org/post');
      expect(snackBar.open).toHaveBeenCalledWith('Link kopiert.', undefined, { duration: 3000 });
    });

    it('verwirft und laedt die Liste neu', () => {
      erstellen([einwurf({ id: 'eigen' })]);
      rawInputService.updateStatus.and.returnValue(of(einwurf({ id: 'eigen', status: 'discarded' })));

      component.aktionAusfuehren(component.karten[0], 'verwerfen');

      expect(rawInputService.updateStatus).toHaveBeenCalledWith('eigen', 'discarded');
      expect(rawInputService.getRawInputs).toHaveBeenCalledTimes(2);
    });

    it('sagt es, wenn das Verwerfen scheitert', () => {
      erstellen([einwurf({ id: 'eigen' })]);
      rawInputService.updateStatus.and.returnValue(throwError(() => ({ status: 403 })));

      component.aktionAusfuehren(component.karten[0], 'verwerfen');

      expect(snackBar.open).toHaveBeenCalledWith(
        'Verwerfen kann nur, wer den Einwurf eingeworfen hat.',
        'OK',
        { duration: 6000 },
      );
    });

    it('nennt bei 409 den wahren Grund statt "versuche es erneut"', () => {
      erstellen([einwurf({ id: 'eigen' })]);
      rawInputService.updateStatus.and.returnValue(throwError(() => ({ status: 409 })));

      component.aktionAusfuehren(component.karten[0], 'verwerfen');

      expect(snackBar.open).toHaveBeenCalledWith(
        'Aus diesem Einwurf ist schon ein Beitrag entstanden; verwerfen geht nicht mehr.',
        'OK',
        { duration: 6000 },
      );
    });

    it('fuehrt Weiterdestillieren in die Destillier-Ansicht', () => {
      erstellen(jeTab());
      klicken(tabKnopf('Erledigt'));

      component.aktionAusfuehren(component.karten[0], 'weiterDestillieren');

      expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'fertig']);
    });
  });
});
