import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { Subject, of, throwError } from 'rxjs';

import { MatBottomSheet } from '@angular/material/bottom-sheet';

import {
  EinwerfenComponent,
  LINK_PRUEFEN_NACH_MS,
  SEITENTITEL_PRAEFIX,
  hinweisVorschlag,
} from './einwerfen.component';
import { Einwurf, EinwurfSeite, EinwurfService } from '../services/einwurf.service';
import { EinwurfBeitragSheetComponent } from '../fangkorb/einwurf-beitrag-sheet.component';
import { SHARE_FELDER_SCHLUESSEL } from '../share-target/share-target.guard';
import { LoggingService } from '../services/logging.service';
import { MeilensteinHinweisService } from '../meine-beitraege/meilenstein-hinweis.service';
import { Meilenstein } from '../services/usage-tracking.service';
import { erwarteCc0Hinweis } from '../shared/cc0-hinweis/cc0-hinweis.testing';
import { FANGKORB_BESCHREIBUNG } from '../shared/fangkorb-texte';
import { Art9EinwilligungZustand } from '../services/art9-einwilligung-zustand';

describe('hinweisVorschlag', () => {
  it('stellt den Seitentitel mit Praefix voran', () => {
    expect(hinweisVorschlag({ url: 'https://example.org/a', titel: 'Ein Titel', text: null })).toBe(
      `${SEITENTITEL_PRAEFIX}Ein Titel`,
    );
  });

  it('nimmt uebrigen Text dazu', () => {
    expect(hinweisVorschlag({ url: null, titel: 'Ein Titel', text: 'noch was' })).toBe(
      'Seitentitel: Ein Titel\nnoch was',
    );
  });

  it('hat ohne Titel und Text keinen Vorschlag', () => {
    expect(hinweisVorschlag({ url: 'https://example.org/a', titel: null, text: null })).toBeNull();
  });
});

describe('EinwerfenComponent', () => {
  let component: EinwerfenComponent;
  let fixture: ComponentFixture<EinwerfenComponent>;
  let einwurfService: jasmine.SpyObj<EinwurfService>;
  let meilensteinHinweis: jasmine.SpyObj<MeilensteinHinweisService>;
  let eigeneEinwuerfe = 1;
  let neueMeilensteine: Meilenstein[] = [];

  /**
   * Die Vorbelegung passiert in ngOnInit, also muss eine Ablage liegen, bevor die
   * Komponente entsteht -- deshalb baut jeder Test die Komponente selbst.
   */
  async function erstellen(ablage: string | null = null): Promise<void> {
    if (ablage === null) {
      sessionStorage.removeItem(SHARE_FELDER_SCHLUESSEL);
    } else {
      sessionStorage.setItem(SHARE_FELDER_SCHLUESSEL, ablage);
    }

    const serviceSpy = jasmine.createSpyObj('EinwurfService', ['einwerfen', 'mitGleichemLink', 'eigeneLaden']);
    serviceSpy.eigeneLaden.and.returnValue(of({ results_count: 1, results: [], total_records_count: eigeneEinwuerfe }));
    serviceSpy.einwerfen.and.returnValue(of({ id: 'neue-id' }));
    serviceSpy.mitGleichemLink.and.returnValue(of([]));
    meilensteinHinweis = jasmine.createSpyObj<MeilensteinHinweisService>('MeilensteinHinweisService', ['neueErreichte', 'merken']);
    meilensteinHinweis.neueErreichte.and.returnValue(of(neueMeilensteine));

    await TestBed.configureTestingModule({
      imports: [EinwerfenComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: EinwurfService, useValue: serviceSpy },
        { provide: MeilensteinHinweisService, useValue: meilensteinHinweis },
        {
          provide: LoggingService,
          useValue: jasmine.createSpyObj('LoggingService', ['debug', 'error', 'warn']),
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(EinwerfenComponent);
    component = fixture.componentInstance;
    einwurfService = TestBed.inject(EinwurfService) as jasmine.SpyObj<EinwurfService>;
    fixture.detectChanges();
  }

  function eingeben(link: string, hinweis: string): void {
    component.einwurfForm.setValue({ link, hinweis });
    fixture.detectChanges();
  }

  function text(): string {
    return fixture.nativeElement.textContent;
  }

  beforeEach(() => TestBed.resetTestingModule());
  afterEach(() => sessionStorage.removeItem(SHARE_FELDER_SCHLUESSEL));

  describe('Felder', () => {
    beforeEach(() => erstellen());

    it('hat genau zwei Felder: Link und Hinweis fuer andere', () => {
      const labels = Array.from(fixture.nativeElement.querySelectorAll('mat-label')).map((l) =>
        (l as HTMLElement).textContent!.trim(),
      );

      expect(labels).toEqual(['Link', 'Hinweis für andere']);
      expect(fixture.nativeElement.querySelectorAll('input, textarea').length).toBe(2);
      expect(text()).not.toContain('Bild-Adresse');
    });

    it('zeigt über dem Absende-Knopf den CC0-Hinweis mit Links auf CC0 und die Nutzungsbedingungen (#415)', () => {
      erwarteCc0Hinweis(fixture.nativeElement);
    });

    it('zeigt oben eine Hinweisbox mit der Fangkorb-Beschreibung, ohne eigenen Titel', () => {
      const kopf: HTMLElement = fixture.nativeElement.querySelector('.einwurf-kopf');

      expect(kopf.querySelector('.hinweis-box')).toBeTruthy();
      expect(kopf.querySelector('h2')).toBeNull();
      expect(kopf.textContent).toContain(FANGKORB_BESCHREIBUNG);
    });

    it('führt mit einem Text-Link unter dem Formular in den Fangkorb; "Einwerfen" bleibt der einzige Knopf (#645)', () => {
      const seite: HTMLElement = fixture.nativeElement;
      const link = seite.querySelector('a.fangkorb-link') as HTMLAnchorElement;

      expect(link.textContent?.trim()).toContain('Fangkorb ansehen');
      expect(link.getAttribute('href')).toBe('/fangkorb');
      expect(link.closest('form')).toBeNull();
      const knoepfe = Array.from(seite.querySelectorAll('.einwurf-aktionen button'));
      expect(knoepfe.length).toBe(1);
      expect(knoepfe[0].textContent).toContain('Einwerfen');
    });

    it('laesst das Hinweis-Feld mit dem Text wachsen, von zwei bis acht Zeilen', () => {
      const feld: HTMLTextAreaElement = fixture.nativeElement.querySelector('#einwurf-hinweis');

      expect(feld.classList).toContain('cdk-textarea-autosize');
      expect(feld.getAttribute('cdkAutosizeMinRows')).toBe('2');
      expect(feld.getAttribute('cdkAutosizeMaxRows')).toBe('8');
    });

    it('wirft nichts ein, solange nichts dasteht', () => {
      eingeben('  ', '   ');

      component.einwerfen();

      expect(einwurfService.einwerfen).not.toHaveBeenCalled();
    });

    it('nimmt einen Hinweis ohne Link an', () => {
      eingeben('', 'Waermepumpen-Foerderung wurde gekuerzt');

      component.einwerfen();

      expect(einwurfService.einwerfen).toHaveBeenCalledWith({
        content: 'Waermepumpen-Foerderung wurde gekuerzt',
      });
    });

    it('nimmt einen Link ohne Hinweis an', () => {
      eingeben('https://example.org/post', '');

      component.einwerfen();

      expect(einwurfService.einwerfen).toHaveBeenCalledWith({ url: 'https://example.org/post' });
    });

    it('schickt Link und Hinweis getrennt', () => {
      eingeben(' https://example.org/post ', ' Gute Antwort in den Kommentaren ');

      component.einwerfen();

      expect(einwurfService.einwerfen).toHaveBeenCalledWith({
        url: 'https://example.org/post',
        content: 'Gute Antwort in den Kommentaren',
      });
    });

    it('weist im Link-Feld alles ab, was nicht nur ein Link ist', () => {
      eingeben('Guter Thread https://example.org/p', '');
      component.einwurfForm.get('link')!.markAsTouched();
      fixture.detectChanges();

      component.einwerfen();

      expect(einwurfService.einwerfen).not.toHaveBeenCalled();
      expect(component.kannEinwerfen).toBeFalse();
      expect(text()).toContain('Bitte nur einen Link');
    });

    it('entfernt Tracking-Parameter aus dem Link und aus Adressen im Hinweis', () => {
      eingeben(
        'https://www.instagram.com/reel/ABC/?stkn=xyz',
        'siehe auch https://example.org/b?utm_source=x',
      );

      component.einwerfen();

      expect(einwurfService.einwerfen).toHaveBeenCalledWith({
        url: 'https://www.instagram.com/reel/ABC/',
        content: 'siehe auch https://example.org/b',
      });
    });

    it('laesst das Formular nach dem Einwerfen offen und leer und zaehlt mit', () => {
      eingeben('https://example.org/a', 'eins');
      component.einwerfen();
      eingeben('', 'zwei');
      component.einwerfen();

      expect(component.einwurfForm.value).toEqual({ link: '', hinweis: '' });
      expect(component.eingeworfen).toBe(2);
      expect(component.fehler).toBeNull();
    });

    it('meldet einen abgewiesenen Einwurf verstaendlich', () => {
      einwurfService.einwerfen.and.returnValue(throwError(() => ({ status: 422 })));
      eingeben('https://example.org/a', '');

      component.einwerfen();

      expect(component.fehler).toContain('Link');
      expect(component.wirdGespeichert).toBeFalse();
    });

    // UX-Review B4: Ohne Einwilligung kein "versuche es erneut", sondern der Hinweiskasten
    it('zeigt bei fehlender Einwilligung (403) keinen Fehler, sondern den Hinweiskasten, und behaelt die Eingabe', () => {
      einwurfService.einwerfen.and.returnValue(
        throwError(() => ({ status: 403, error: { detail: 'art9_einwilligung_fehlt' } })),
      );
      eingeben('https://example.org/a', 'nicht verlieren');

      component.einwerfen();
      TestBed.inject(Art9EinwilligungZustand).setzen('fehlt'); // setzt sonst der Interceptor
      fixture.detectChanges();

      expect(component.fehler).toBeNull();
      expect(component.wirdGespeichert).toBeFalse();
      expect(component.einwurfForm.value.hinweis).toBe('nicht verlieren');
      const element = fixture.nativeElement as HTMLElement;
      expect(element.querySelector('[data-testid=einwilligung-hinweis]')).not.toBeNull();
      expect(element.textContent).not.toContain('versuche es erneut');
    });

    it('behaelt die Eingabe, wenn das Speichern fehlschlaegt', () => {
      einwurfService.einwerfen.and.returnValue(throwError(() => ({ status: 500 })));
      eingeben('https://example.org/a', 'nicht verlieren');

      component.einwerfen();

      expect(component.einwurfForm.value).toEqual({
        link: 'https://example.org/a',
        hinweis: 'nicht verlieren',
      });
      expect(component.eingeworfen).toBe(0);
    });
  });

  describe('Erfolgskarte (#351)', () => {
    const EINWURF_1: Meilenstein = {
      kennung: 'einwurf-1', name: 'Erster Einwurf', untertitel: 'Fundstück', beschreibung: '',
      bild: 'meilensteine/korb.svg', bildnachweis: '', art: 'weg', schwelle: 1, stand: 1, erreicht: true,
    };

    afterEach(() => {
      eigeneEinwuerfe = 1;
      neueMeilensteine = [];
    });

    function karte(): HTMLElement | null {
      fixture.detectChanges();
      return (fixture.nativeElement as HTMLElement).querySelector('.erfolg-karte');
    }

    it('erklaert beim allerersten Einwurf, wo man das Ergebnis sieht', async () => {
      await erstellen();
      eingeben('', 'Waermepumpen-Foerderung wurde gekuerzt');

      component.einwerfen();

      expect(einwurfService.eigeneLaden).toHaveBeenCalledWith(1, 1);
      expect(karte()?.textContent).toContain('Dein erster Einwurf liegt im Fangkorb');
      expect(karte()?.textContent).toContain('Meine Einwürfe');
      expect(karte()?.textContent).not.toContain('Meilenstein');
    });

    it('ist kurz, wenn es nicht der erste Einwurf der Person ist', async () => {
      eigeneEinwuerfe = 7;
      await erstellen();
      eingeben('', 'eins');

      component.einwerfen();

      expect(karte()?.textContent).toContain('Liegt im Fangkorb');
      expect(karte()?.textContent).not.toContain('erster');
    });

    it('fragt ab dem zweiten in der Sitzung nicht mehr nach und zaehlt mit', async () => {
      await erstellen();
      eingeben('', 'eins');
      component.einwerfen();
      eingeben('', 'zwei');
      component.einwerfen();

      expect(einwurfService.eigeneLaden).toHaveBeenCalledTimes(1);
      expect(karte()?.textContent).toContain('2 in dieser Sitzung');
    });

    it('nennt mit eingeschalteten Punkten den erreichten Meilenstein', async () => {
      neueMeilensteine = [EINWURF_1];
      await erstellen();
      eingeben('', 'eins');

      component.einwerfen();

      expect(karte()?.querySelector('.erfolg-meilenstein')?.textContent).toContain('Meilenstein erreicht: Erster Einwurf');
      // Gemerkt wird erst, was die Karte angezeigt hat.
      expect(meilensteinHinweis.merken).toHaveBeenCalledOnceWith([EINWURF_1]);
    });

    it('steht sofort; die Zeile zum ersten Einwurf kommt nach', async () => {
      await erstellen();
      const antwort = new Subject<EinwurfSeite>();
      einwurfService.eigeneLaden.and.returnValue(antwort.asObservable());
      eingeben('', 'eins');

      component.einwerfen();

      expect(karte()?.textContent).toContain('Drin.');
      expect(karte()?.querySelector('.erfolg-text')).toBeNull();
      antwort.next({ results_count: 1, results: [], total_records_count: 1 });
      expect(karte()?.textContent).toContain('Dein erster Einwurf');
    });

    it('hat im role="status" nur den Text, nicht die Knöpfe', async () => {
      await erstellen();
      eingeben('', 'eins');

      component.einwerfen();
      fixture.detectChanges();

      const status = (fixture.nativeElement as HTMLElement).querySelector('.einwurf-rueckmeldung [role="status"]')!;
      expect(status.textContent).toContain('Drin.');
      expect(status.querySelector('button')).toBeNull();
    });

    it('"Noch einen einwerfen" schliesst die Karte und setzt den Fokus ins Link-Feld', async () => {
      await erstellen();
      document.body.appendChild(fixture.nativeElement);
      eingeben('', 'eins');
      component.einwerfen();
      const knopf = Array.from(karte()!.querySelectorAll('button')).find((b) => b.textContent?.includes('Noch einen'))!;

      knopf.click();

      expect(karte()).toBeNull();
      expect(document.activeElement?.id).toBe('einwurf-link');
      (fixture.nativeElement as HTMLElement).remove();
    });
  });

  describe('Uebernahme aus dem Teilen-Menue', () => {
    const vomBrowser = JSON.stringify({
      url: 'https://www.tagesschau.de/inland/x-100.html',
      titel: 'AfD klar vor SPD | tagesschau.de',
      text: null,
    });

    it('fuellt bei Instagram nur den Link', async () => {
      await erstellen(
        JSON.stringify({ url: 'https://www.instagram.com/reel/ABC/', titel: null, text: null }),
      );

      expect(component.einwurfForm.value).toEqual({
        link: 'https://www.instagram.com/reel/ABC/',
        hinweis: '',
      });
      expect(component.ausShare).toBeTrue();
      expect(component.istVorbelegt).toBeFalse();
    });

    it('legt den Seitentitel als markierte Vorbelegung ins Hinweis-Feld', async () => {
      await erstellen(vomBrowser);

      expect(component.einwurfForm.value.link).toBe('https://www.tagesschau.de/inland/x-100.html');
      expect(component.einwurfForm.value.hinweis).toBe(
        'Seitentitel: AfD klar vor SPD | tagesschau.de',
      );
      expect(component.istVorbelegt).toBeTrue();
      expect(fixture.nativeElement.querySelector('.hinweis-feld.vorbelegt')).toBeTruthy();
      expect(text()).toContain('Vorschlag aus dem Teilen');
    });

    it('uebernimmt den Vorschlag, wenn er stehen bleibt', async () => {
      await erstellen(vomBrowser);

      component.einwerfen();

      expect(einwurfService.einwerfen).toHaveBeenCalledWith({
        url: 'https://www.tagesschau.de/inland/x-100.html',
        content: 'Seitentitel: AfD klar vor SPD | tagesschau.de',
        source_channel: 'share',
      });
    });

    it('entfernt den Vorschlag mit einem Griff', async () => {
      await erstellen(vomBrowser);
      const knopf: HTMLButtonElement = fixture.nativeElement.querySelector(
        'button.vorbelegung-entfernen',
      );

      knopf.click();
      fixture.detectChanges();
      component.einwerfen();

      expect(fixture.nativeElement.querySelector('button.vorbelegung-entfernen')).toBeNull();
      expect(einwurfService.einwerfen).toHaveBeenCalledWith({
        url: 'https://www.tagesschau.de/inland/x-100.html',
        source_channel: 'share',
      });
    });

    it('markiert einen bearbeiteten Vorschlag nicht mehr als Vorbelegung', async () => {
      await erstellen(vomBrowser);

      eingeben('https://www.tagesschau.de/inland/x-100.html', 'Umfrage, lohnt eine Antwort');

      expect(component.istVorbelegt).toBeFalse();
      expect(fixture.nativeElement.querySelector('.hinweis-feld.vorbelegt')).toBeNull();
    });

    it('raeumt die Ablage weg, damit der naechste Aufruf leer beginnt', async () => {
      await erstellen(vomBrowser);

      expect(sessionStorage.getItem(SHARE_FELDER_SCHLUESSEL)).toBeNull();
    });

    it('zaehlt den naechsten Einwurf wieder als web', async () => {
      await erstellen(vomBrowser);
      component.einwerfen();

      eingeben('', 'von Hand getippt');
      component.einwerfen();

      expect(einwurfService.einwerfen.calls.mostRecent().args[0]).toEqual({
        content: 'von Hand getippt',
      });
    });

    it('befuellt nichts, wenn nichts abgelegt wurde', async () => {
      await erstellen(null);

      expect(component.einwurfForm.value).toEqual({ link: '', hinweis: '' });
      expect(component.ausShare).toBeFalse();
    });

    it('versteht noch die Klartext-Ablage einer aelteren Version', async () => {
      await erstellen('Ein Seitentitel\nhttps://example.org/a');

      expect(component.einwurfForm.value).toEqual({
        link: 'https://example.org/a',
        hinweis: 'Ein Seitentitel',
      });
    });
  });
  describe('Anzeige bei gleichem Link (#263)', () => {
    function vorhandenerEinwurf(overrides: Partial<Einwurf> = {}): Einwurf {
      return {
        id: 'vorhanden',
        content: null,
        url: 'https://example.org/a',
        image_url: null,
        submitted_by: 'jemand',
        source_channel: 'web',
        status: 'open',
        created_at: '2026-10-01T12:00:00Z',
        drafts: [],
        links: [],
        ...overrides,
      };
    }

    const ausformuliert = vorhandenerEinwurf({
      status: 'processed',
      drafts: [
        { id: 's1', user_id: 'jemand', sentence: 'Der Satz', updated_at: '2026-10-02T12:00:00Z' },
      ],
      links: [
        {
          content_id: 'beitrag-1',
          content_type: 'commentary',
          draft_id: 's1',
          processed_by: 'jemand',
          processed_at: '2026-10-03T12:00:00Z',
        },
      ],
    });

    /** Link tippen und die Wartezeit bis zur Pruefung verstreichen lassen. */
    function linkTippen(link: string): void {
      eingeben(link, '');
      tick(LINK_PRUEFEN_NACH_MS);
      fixture.detectChanges();
    }

    function gleicherLinkBox(): HTMLElement | null {
      return fixture.nativeElement.querySelector('.gleicher-link');
    }

    it('fragt nach kurzer Pause mit dem bereinigten Link', fakeAsync(() => {
      erstellen();
      flushMicrotasks();

      linkTippen('https://example.org/a?utm_source=x');

      expect(einwurfService.mitGleichemLink).toHaveBeenCalledOnceWith('https://example.org/a');
    }));

    it('zeigt die Stufe des vorhandenen Einwurfs', fakeAsync(() => {
      erstellen();
      flushMicrotasks();
      einwurfService.mitGleichemLink.and.returnValue(
        of([vorhandenerEinwurf({ drafts: [{ id: 's', user_id: 'x', sentence: 'S', updated_at: '' }] })]),
      );

      linkTippen('https://example.org/a');

      expect(gleicherLinkBox()?.textContent).toContain('Diesen Link gibt es schon im Fangkorb');
      expect(gleicherLinkBox()?.textContent).toContain('Destilliert');
      expect(gleicherLinkBox()?.querySelector('button.beitrag-ansehen')).toBeNull();
    }));

    it('oeffnet bei ausformuliertem Einwurf den Beitrag', fakeAsync(() => {
      erstellen();
      flushMicrotasks();
      const sheet = spyOn(TestBed.inject(MatBottomSheet), 'open');
      einwurfService.mitGleichemLink.and.returnValue(of([ausformuliert]));

      linkTippen('https://example.org/a');
      expect(gleicherLinkBox()?.textContent).toContain('Ausformuliert');
      (gleicherLinkBox()!.querySelector('button.beitrag-ansehen') as HTMLButtonElement).click();

      expect(sheet).toHaveBeenCalledTimes(1);
      const [komponente, konfiguration] = (sheet as jasmine.Spy).calls.mostRecent().args;
      expect(komponente).toBe(EinwurfBeitragSheetComponent);
      expect(konfiguration?.data).toEqual({
        beitraege: [{ contentId: 'beitrag-1', typ: 'commentary', satz: 'Der Satz' }],
      });
    }));

    // #507: statt "Ausformuliert" der Zustand des Beitrags, ohne "Beitrag ansehen".
    for (const [zustand, wort] of [
      ['gesperrt', 'Beitrag gesperrt'],
      ['geloescht', 'Beitrag gelöscht'],
    ] as const) {
      it(`zeigt "${wort}" ohne Knopf, wenn der Beitrag ${zustand} ist`, fakeAsync(() => {
        erstellen();
        flushMicrotasks();
        const links = ausformuliert.links!.map((link) => ({ ...link, zustand }));
        einwurfService.mitGleichemLink.and.returnValue(of([{ ...ausformuliert, links }]));

        linkTippen('https://example.org/a');

        expect(gleicherLinkBox()?.querySelector('.gleicher-link-stufe')?.textContent).toContain(wort);
        expect(gleicherLinkBox()?.textContent).not.toContain('Ausformuliert');
        expect(gleicherLinkBox()?.querySelector('button.beitrag-ansehen')).toBeNull();
      }));
    }

    it('kuendigt die Anzeige in einer Live-Region an, die schon vorher dasteht', fakeAsync(() => {
      erstellen();
      flushMicrotasks();
      const region = fixture.nativeElement.querySelector('.gleicher-link-region');
      expect(region?.getAttribute('role')).toBe('status');
      expect(region?.textContent?.trim()).toBe('');
      einwurfService.mitGleichemLink.and.returnValue(of([ausformuliert]));

      linkTippen('https://example.org/a');

      expect(fixture.nativeElement.querySelector('.gleicher-link-region')).toBe(region);
      expect(region.textContent).toContain('Diesen Link gibt es schon im Fangkorb');
    }));

    it('unterscheidet die Beitrag-Knoepfe bei mehreren Einwuerfen', fakeAsync(() => {
      erstellen();
      flushMicrotasks();
      einwurfService.mitGleichemLink.and.returnValue(
        of([ausformuliert, { ...ausformuliert, id: 'zweiter', status: 'discarded' }]),
      );

      linkTippen('https://example.org/a');

      const knoepfe = gleicherLinkBox()!.querySelectorAll('button.beitrag-ansehen');
      expect(Array.from(knoepfe).map((knopf) => knopf.getAttribute('aria-label'))).toEqual([
        'Beitrag ansehen, Einwurf 1 von 2, Ausformuliert',
        'Beitrag ansehen, Einwurf 2 von 2, Verworfen',
      ]);
    }));

    it('laesst trotzdem einwerfen', fakeAsync(() => {
      erstellen();
      flushMicrotasks();
      einwurfService.mitGleichemLink.and.returnValue(of([ausformuliert]));

      linkTippen('https://example.org/a');
      expect(gleicherLinkBox()?.textContent).toContain('Du kannst ihn trotzdem einwerfen');
      expect(component.kannEinwerfen).toBeTrue();
      component.einwerfen();
      tick(LINK_PRUEFEN_NACH_MS);
      fixture.detectChanges();

      expect(einwurfService.einwerfen).toHaveBeenCalledWith({ url: 'https://example.org/a' });
      // Das Formular ist danach leer, die Anzeige gehoert zum alten Link.
      expect(gleicherLinkBox()).toBeNull();
    }));

    it('zeigt keine spaete Antwort zu einem Link, der nicht mehr dasteht', fakeAsync(() => {
      erstellen();
      flushMicrotasks();
      const antwort = new Subject<Einwurf[]>();
      einwurfService.mitGleichemLink.and.returnValue(antwort);

      linkTippen('https://example.org/a');
      component.einwerfen();
      antwort.next([ausformuliert]);
      tick(LINK_PRUEFEN_NACH_MS);
      fixture.detectChanges();

      expect(gleicherLinkBox()).toBeNull();
    }));

    it('fragt nicht, solange kein Link dasteht', fakeAsync(() => {
      erstellen();
      flushMicrotasks();

      linkTippen('example.org/a');
      linkTippen('');

      expect(einwurfService.mitGleichemLink).not.toHaveBeenCalled();
      expect(gleicherLinkBox()).toBeNull();
    }));

    it('zeigt nichts, wenn die Pruefung scheitert', fakeAsync(() => {
      erstellen();
      flushMicrotasks();
      einwurfService.mitGleichemLink.and.returnValue(throwError(() => ({ status: 500 })));

      linkTippen('https://example.org/a');

      expect(gleicherLinkBox()).toBeNull();
      expect(component.fehler).toBeNull();
    }));

    it('prueft auch den Link aus dem Teilen-Menue', fakeAsync(() => {
      erstellen(JSON.stringify({ url: 'https://example.org/a', titel: null, text: null }));
      flushMicrotasks();
      tick(LINK_PRUEFEN_NACH_MS);

      expect(einwurfService.mitGleichemLink).toHaveBeenCalledOnceWith('https://example.org/a');
    }));
  });
});
