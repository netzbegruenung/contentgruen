import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { Subject, of, throwError } from 'rxjs';

import { MatBottomSheet } from '@angular/material/bottom-sheet';

import {
  AddRawInputComponent,
  LINK_PRUEFEN_NACH_MS,
  SEITENTITEL_PRAEFIX,
  hinweisVorschlag,
} from './add-raw-input.component';
import { Einwurf, EinwurfService } from '../services/einwurf.service';
import { EinwurfBeitragSheetComponent } from '../raw-input-list/einwurf-beitrag-sheet.component';
import { SHARE_FELDER_SCHLUESSEL } from '../share-target/share-target.guard';
import { LoggingService } from '../services/logging.service';
import { CONSENT_HINWEIS } from '../shared/consent-hinweis';
import { FANGKORB_BESCHREIBUNG } from '../shared/fangkorb-texte';

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

describe('AddRawInputComponent', () => {
  let component: AddRawInputComponent;
  let fixture: ComponentFixture<AddRawInputComponent>;
  let einwurfService: jasmine.SpyObj<EinwurfService>;

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

    const serviceSpy = jasmine.createSpyObj('EinwurfService', ['einwerfen', 'mitGleichemLink']);
    serviceSpy.einwerfen.and.returnValue(of({ id: 'neue-id' }));
    serviceSpy.mitGleichemLink.and.returnValue(of([]));

    await TestBed.configureTestingModule({
      imports: [AddRawInputComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: EinwurfService, useValue: serviceSpy },
        {
          provide: LoggingService,
          useValue: jasmine.createSpyObj('LoggingService', ['debug', 'error', 'warn']),
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AddRawInputComponent);
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

    it('verlinkt die Nutzungsbedingungen ueber dem Absenden-Knopf', () => {
      const link: HTMLAnchorElement | null = fixture.nativeElement.querySelector(
        'a[href="/nutzungsbedingungen"]',
      );

      expect(link).toBeTruthy();
      expect(link!.target).toBe('_blank');
      expect(link!.closest('p')!.classList).toContain('submit-hint');
      expect(link!.closest('p')!.textContent!.replace(/\s+/g, ' ').trim()).toBe(
        `${CONSENT_HINWEIS.vorLink}${CONSENT_HINWEIS.link}${CONSENT_HINWEIS.nachLink}`,
      );
    });

    it('zeigt oben eine Hinweisbox mit der Fangkorb-Beschreibung, ohne eigenen Titel', () => {
      const kopf: HTMLElement = fixture.nativeElement.querySelector('.einwurf-kopf');

      expect(kopf.querySelector('.hinweis-box')).toBeTruthy();
      expect(kopf.querySelector('h2')).toBeNull();
      expect(kopf.textContent).toContain(FANGKORB_BESCHREIBUNG);
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
