import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { Subject, of } from 'rxjs';
import { EinwilligungComponent, WIDERRUF_FRAGE } from './einwilligung.component';
import { Art9EinwilligungService, Art9EinwilligungStand } from '../services/art9-einwilligung.service';
import { environment } from '../../environments/environment';
import { PUNKTE_EINWILLIGUNG_AUS } from '../shared/punkte-einwilligung/punkte-einwilligung.testing';

const URL = `${environment.baseUrl}/api/v1/art9-einwilligung`;
const WORTLAUT = { kennung: '2026-11-05', text: 'Ich willige ausdrücklich ein, dass …' };

function stand(teil: Partial<Art9EinwilligungStand> = {}): Art9EinwilligungStand {
  return {
    eingewilligt: false,
    wortlaut: null,
    eingewilligt_am: null,
    widerrufen_am: null,
    aktueller_wortlaut: WORTLAUT,
    ...teil,
  };
}

/** Die Art.-9-Einwilligung (#489): eigenes Haekchen, nichts vorbelegt, widerrufbar. */
describe('EinwilligungComponent', () => {
  let fixture: ComponentFixture<EinwilligungComponent>;
  let http: HttpTestingController;
  let router: Router;
  let dialog: jasmine.SpyObj<MatDialog>;
  /** Was die Rueckfrage vor dem Widerruf antwortet (B3). */
  let rueckfrage: boolean | undefined;

  function starten(returnUrl: string | null = '/einwerfen') {
    rueckfrage = true;
    dialog = jasmine.createSpyObj('MatDialog', ['open']);
    dialog.open.and.callFake((() => ({ afterClosed: () => of(rueckfrage) })) as any);
    TestBed.configureTestingModule({
      imports: [EinwilligungComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        PUNKTE_EINWILLIGUNG_AUS,
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap(returnUrl ? { returnUrl } : {}) } },
        },
      ],
    });
    TestBed.overrideProvider(MatDialog, { useValue: dialog });
    fixture = TestBed.createComponent(EinwilligungComponent);
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigateByUrl').and.resolveTo(true);
    fixture.detectChanges();
  }

  function standLiefern(s: Art9EinwilligungStand) {
    http.expectOne({ method: 'GET', url: URL }).flush(s);
    fixture.detectChanges();
  }

  function el(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  function knopf(text: string): HTMLButtonElement {
    const treffer = Array.from(el().querySelectorAll('button')).find((b) => b.textContent?.includes(text));
    if (!treffer) {
      throw new Error(`Kein Knopf "${text}"`);
    }
    return treffer as HTMLButtonElement;
  }

  afterEach(() => {
    // "Ohne Einwilligung weiter" geht als POST an den Server (B2); nur der eigene Test prueft ihn.
    http.match({ method: 'POST', url: `${URL}/ohne` }).forEach((r) => r.flush(null, { status: 204, statusText: 'No Content' }));
    http.verify();
  });

  // Eine Seite fuer beides (Entscheidung Maintainer, 20.11.2026): zwei getrennte, nicht
  // vorbelegte Haekchen, die Nutzungsbedingungen Pflicht, die Einwilligung freiwillig.
  describe('mit Nutzungsbedingungen', () => {
    const NB_URL = `${environment.baseUrl}/api/v1/nutzungsbedingungen`;
    const NB_FEHLT = {
      zugestimmt: false,
      stand: null,
      zugestimmt_am: null,
      aktueller_stand: { kennung: '2026-11-19', stand: '19. November 2026' },
    };

    function haekchen(testid: string): HTMLInputElement {
      return el().querySelector(`[data-testid=${testid}] input[type=checkbox]`) as HTMLInputElement;
    }

    /** Template-driven: ngModel meldet sich erst nach einem Takt am Formular an. */
    async function anhaken(testid: string) {
      await fixture.whenStable();
      haekchen(testid).click();
      fixture.detectChanges();
    }

    it('zeigt zwei getrennte Haekchen, keins angehakt, und einen Knopf "Weiter" ohne "Alle annehmen"', async () => {
      starten();
      standLiefern(stand({ nutzungsbedingungen: NB_FEHLT }));

      expect(haekchen('nb-haekchen').checked).toBeFalse();
      expect(haekchen('art9-haekchen').checked).toBeFalse();
      expect(el().querySelector('[data-testid=nb-haekchen]')!.textContent).not.toContain('Einwilligung');
      expect(el().textContent).toContain('Freiwillig, nötig zum Mitmachen');
      expect(el().textContent).toContain('widerrufen');
      expect(el().querySelector('a[href="/nutzungsbedingungen"]')).not.toBeNull();
      expect(knopf('Weiter').disabled).toBeFalse();
      expect(el().textContent).not.toContain('Alle annehmen');
      expect(el().textContent).not.toContain('Ohne Einwilligung weiter');
    });

    it('ohne Haekchen der Nutzungsbedingungen: Fehlermeldung am Haekchen, Fokus dorthin, nichts gesendet', async () => {
      starten();
      standLiefern(stand({ nutzungsbedingungen: NB_FEHLT }));
      await anhaken('art9-haekchen');

      knopf('Weiter').click();
      fixture.detectChanges();

      const fehler = el().querySelector('[data-testid=nb-fehler]');
      expect(fehler?.getAttribute('role')).toBe('alert');
      expect(haekchen('nb-haekchen').getAttribute('aria-describedby')).toContain('nb-fehler');
      expect(document.activeElement).toBe(haekchen('nb-haekchen'));
      http.expectNone(NB_URL);
      http.expectNone({ method: 'POST', url: URL });

      await anhaken('nb-haekchen');
      expect(el().querySelector('[data-testid=nb-fehler]')).toBeNull();
    });

    it('nur Nutzungsbedingungen: stimmt zu, merkt "ohne Einwilligung" und geht weiter', async () => {
      starten();
      standLiefern(stand({ nutzungsbedingungen: NB_FEHLT }));
      await anhaken('nb-haekchen');

      knopf('Weiter').click();
      const nb = http.expectOne({ method: 'POST', url: NB_URL });
      expect(nb.request.body).toEqual({ stand: '2026-11-19' });
      nb.flush(null, { status: 204, statusText: 'No Content' });

      const ohne = http.expectOne({ method: 'POST', url: `${URL}/ohne` });
      expect(ohne.request.body).toEqual({ wortlaut: WORTLAUT.kennung });
      ohne.flush(null, { status: 204, statusText: 'No Content' });
      http.expectNone({ method: 'POST', url: URL });
      expect(router.navigateByUrl).toHaveBeenCalledWith('/einwerfen');
    });

    it('beide Haekchen: erst die Nutzungsbedingungen, dann die Einwilligung', async () => {
      starten();
      standLiefern(stand({ nutzungsbedingungen: NB_FEHLT }));
      await anhaken('nb-haekchen');
      await anhaken('art9-haekchen');

      knopf('Weiter').click();
      http.expectNone({ method: 'POST', url: URL });
      http.expectOne({ method: 'POST', url: NB_URL }).flush(null, { status: 204, statusText: 'No Content' });
      const einwilligung = http.expectOne({ method: 'POST', url: URL });
      expect(einwilligung.request.body).toEqual({ wortlaut: WORTLAUT.kennung });
      einwilligung.flush(null, { status: 204, statusText: 'No Content' });

      expect(router.navigateByUrl).toHaveBeenCalledWith('/einwerfen');
    });

    it('schon eingewilligt (Bestandskonto): nur das Haekchen der Nutzungsbedingungen', async () => {
      starten();
      standLiefern(
        stand({ eingewilligt: true, wortlaut: WORTLAUT.kennung, eingewilligt_am: '2026-11-05T09:00:00Z', nutzungsbedingungen: NB_FEHLT }),
      );

      expect(el().querySelector('[data-testid=art9-haekchen]')).toBeNull();
      expect(el().textContent).toContain('Deine Einwilligung zur Mitwirkung besteht weiter.');
      await anhaken('nb-haekchen');
      knopf('Weiter').click();
      http.expectOne({ method: 'POST', url: NB_URL }).flush(null, { status: 204, statusText: 'No Content' });

      http.expectNone({ method: 'POST', url: URL });
      expect(router.navigateByUrl).toHaveBeenCalledWith('/einwerfen');
    });

    it('wer beides hat, sieht nichts Neues: den Stand mit dem Datum der Zustimmung', async () => {
      starten();
      standLiefern(
        stand({
          eingewilligt: true,
          wortlaut: WORTLAUT.kennung,
          eingewilligt_am: '2026-11-05T09:00:00Z',
          nutzungsbedingungen: { ...NB_FEHLT, zugestimmt: true, stand: '2026-11-19', zugestimmt_am: '2026-11-20T09:00:00Z' },
        }),
      );

      expect(el().querySelector('[data-testid=nb-haekchen]')).toBeNull();
      expect(el().querySelector('[data-testid=nb-zugestimmt]')!.textContent).toContain('20.11.2026');
      expect(knopf('Einwilligung widerrufen')).toBeTruthy();
    });

    it('Stand der Nutzungsbedingungen gilt nicht mehr (400): laedt neu und sagt es', async () => {
      starten();
      standLiefern(stand({ nutzungsbedingungen: NB_FEHLT }));
      await anhaken('nb-haekchen');

      knopf('Weiter').click();
      http.expectOne({ method: 'POST', url: NB_URL }).flush({}, { status: 400, statusText: 'Bad Request' });
      standLiefern(stand({ nutzungsbedingungen: NB_FEHLT }));

      expect(el().querySelector('[data-testid=wortlaut-geaendert]')).not.toBeNull();
      await fixture.whenStable();
      fixture.detectChanges();
      expect(haekchen('nb-haekchen').checked).toBeFalse();
    });
  });

  describe('Frage', () => {
    it('zeigt den Wortlaut vom Backend am Haekchen, nicht angehakt', () => {
      starten();
      standLiefern(stand());

      const haekchen = el().querySelector('mat-checkbox input[type=checkbox]') as HTMLInputElement;
      expect(el().querySelector('mat-checkbox')?.textContent).toContain(WORTLAUT.text);
      expect(haekchen.checked).toBeFalse();
      expect(knopf('Einwilligen und weiter').disabled).toBeTrue();
    });

    // #620: ein Satz am Haekchen, der ganze Wortlaut aufklappbar darunter, Text unveraendert
    it('zeigt am Haekchen den ersten Satz und den ganzen Wortlaut aufklappbar darunter', () => {
      const lang = {
        kennung: '2026-11-05-b',
        text: 'Ich willige ausdrücklich ein (Art. 9 Abs. 2 lit. a DSGVO). Das betrifft Beiträge. Ich kann widerrufen.',
      };
      starten();
      standLiefern(stand({ aktueller_wortlaut: lang }));

      expect(el().querySelector('mat-checkbox')!.textContent!.trim()).toBe(
        'Ich willige ausdrücklich ein (Art. 9 Abs. 2 lit. a DSGVO).',
      );
      const aufklapp = el().querySelector('details.wortlaut-aufklapp') as HTMLDetailsElement;
      expect(aufklapp.open).toBeFalse();
      expect(aufklapp.querySelector('summary')!.textContent!.trim()).toBe('Ganzen Wortlaut lesen');
      expect(aufklapp.querySelector('.wortlaut-voll')!.textContent!.trim()).toBe(lang.text);
      const eingabe = el().querySelector('mat-checkbox input[type=checkbox]') as HTMLInputElement;
      expect(eingabe.getAttribute('aria-describedby')).toBe('einwilligung-wortlaut-voll');
    });

    // ErwG 42 DSGVO: Verantwortlicher und Datenschutzerklaerung direkt an der Frage
    it('nennt den Verantwortlichen und verlinkt die Datenschutzerklaerung', () => {
      starten();
      standLiefern(stand());

      const fussnote = el().querySelector('.fussnote')!;
      expect(fussnote.textContent).toContain('Verantwortlich ist NETZBEGRÜNUNG');
      expect(fussnote.querySelector('a')!.getAttribute('href')).toBe('/datenschutz');
    });

    it('zeigt einen Wortlaut aus einem Satz ganz am Haekchen, ohne Aufklapper', () => {
      starten();
      standLiefern(stand());

      expect(el().querySelector('details.wortlaut-aufklapp')).toBeNull();
    });

    it('ohne Haekchen geht nichts ans Backend', () => {
      starten();
      standLiefern(stand());

      fixture.componentInstance.einwilligen();

      http.expectNone({ method: 'POST', url: URL });
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it('mit Haekchen schickt die Kennung des gezeigten Wortlauts und fuehrt zurueck', () => {
      starten('/einwerfen?von=fangkorb');
      standLiefern(stand());

      fixture.componentInstance.angehakt = true;
      fixture.detectChanges();
      knopf('Einwilligen und weiter').click();

      const anfrage = http.expectOne({ method: 'POST', url: URL });
      expect(anfrage.request.body).toEqual({ wortlaut: '2026-11-05' });
      anfrage.flush(null, { status: 204, statusText: 'No Content' });
      expect(router.navigateByUrl).toHaveBeenCalledWith('/einwerfen?von=fangkorb');
    });

    it('laedt bei einem veralteten Wortlaut (400) den aktuellen selbst und sagt es darueber', () => {
      starten();
      standLiefern(stand());
      fixture.componentInstance.angehakt = true;
      fixture.detectChanges();

      knopf('Einwilligen und weiter').click();
      http.expectOne({ method: 'POST', url: URL }).flush(null, { status: 400, statusText: 'Bad Request' });
      const neu = { kennung: '2026-11-13', text: 'Ich willige ausdrücklich ein, neu …' };
      standLiefern(stand({ aktueller_wortlaut: neu }));

      expect(el().querySelector('[data-testid="wortlaut-geaendert"]')?.textContent).toContain(
        'Der Text hat sich gerade geändert. Bitte lies ihn und stimm neu zu.',
      );
      expect(el().textContent).toContain(neu.text);
      expect(fixture.componentInstance.angehakt).toBeFalse();
      expect(el().textContent).not.toContain('Noch einmal');
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it('ohne Einwilligung weiter speichert nichts', () => {
      starten('/einwerfen');
      standLiefern(stand());

      knopf('Ohne Einwilligung weiter').click();

      http.expectNone({ method: 'POST', url: URL });
      expect(router.navigateByUrl).toHaveBeenCalledWith('/einwerfen');
    });

    // UX-Review B2: wer bewusst ohne weitergeht, wird nicht bei jedem Start wieder hergefuehrt
    it('ohne Einwilligung weiter merkt sich die Entscheidung mit dem gezeigten Wortlaut', () => {
      starten('/einwerfen');
      standLiefern(stand());

      knopf('Ohne Einwilligung weiter').click();

      // Am Konto, nicht im Browser (Entscheidung Maintainer 13.11.2026)
      const anfrage = http.expectOne({ method: 'POST', url: `${URL}/ohne` });
      expect(anfrage.request.body).toEqual({ wortlaut: WORTLAUT.kennung });
      anfrage.flush(null, { status: 204, statusText: 'No Content' });
      expect(router.navigateByUrl).toHaveBeenCalledWith('/einwerfen');
    });

    it('ohne Einwilligung öffnet sich die Hilfe danach nicht wieder (Parameter hilfe fällt weg)', () => {
      starten('/result?searchQuery=x&hilfe=1');
      standLiefern(stand());

      knopf('Ohne Einwilligung weiter').click();

      expect(router.navigateByUrl).toHaveBeenCalledWith('/result?searchQuery=x');
    });

    it('mit Einwilligung bleibt der Parameter hilfe, die Hilfe öffnet sich danach', () => {
      starten('/search?hilfe=1');
      standLiefern(stand());

      fixture.componentInstance.angehakt = true;
      fixture.detectChanges();
      knopf('Einwilligen und weiter').click();
      http.expectOne({ method: 'POST', url: URL }).flush(null, { status: 204, statusText: 'No Content' });

      expect(router.navigateByUrl).toHaveBeenCalledWith('/search?hilfe=1');
    });

    it('fuehrt nur innerhalb der App zurueck', () => {
      starten('//fremd.example/');
      standLiefern(stand());

      knopf('Ohne Einwilligung weiter').click();

      expect(router.navigateByUrl).toHaveBeenCalledWith('/search');
    });
  });

  describe('Stand und Widerruf', () => {
    it('zeigt Zeitpunkt und Wortlaut der Einwilligung', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));

      expect(el().textContent).toContain('05.11.2026');
      expect(el().querySelector('.wortlaut')?.textContent).toContain(WORTLAUT.text);
      expect(el().querySelector('mat-checkbox')).toBeNull();
    });

    it('zeigt das Datum eines Wortlauts mit Suffix in der Kennung (2026-11-05-b)', () => {
      starten(null);
      const zweiter = { kennung: '2026-11-05-b', text: 'Dazu gehören ein Punktestand, ein Level, Quests und Meilenstein-Abzeichen …' };
      standLiefern(
        stand({
          eingewilligt: true,
          wortlaut: '2026-11-05-b',
          eingewilligt_am: '2026-11-06T09:30:00Z',
          aktueller_wortlaut: zweiter,
        }),
      );

      expect(el().textContent).toContain('Wortlaut vom 05.11.2026');
      expect(el().querySelector('.wortlaut')?.textContent).toContain(zweiter.text);
    });

    it('sagt vor dem Widerruf, was mit Beiträgen, Einwürfen und Sätzen geschieht (Löschauftrag)', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));

      const text = el().textContent!.replace(/\s+/g, ' ');
      expect(text).toContain('Innerhalb von sieben Tagen zeigen deine Beiträge dann „ehemalige Person“');
      expect(text).toContain('deine Einwürfe werden gelöscht');
      expect(text).toContain('Dein Konto bleibt.');
      expect(text).toContain('Was du nach einer neuen Einwilligung beiträgst, bleibt davon unberührt.');
      expect(text).not.toContain('bleibt, bis du es löschst');
    });

    // UX-Review B3: Rueckfrage mit den Folgen, bevor etwas geloescht wird
    it('fragt vor dem Widerruf nach und nennt die Folgen', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));

      knopf('Einwilligung widerrufen').click();

      expect(dialog.open).toHaveBeenCalledTimes(1);
      const daten = dialog.open.calls.mostRecent().args[1]!.data as typeof WIDERRUF_FRAGE;
      expect(daten.ja).toBe('Widerrufen');
      expect(daten.nein).toBe('Abbrechen');
      expect(daten.text).toContain('Bewertungen werden sofort gelöscht');
      expect(daten.text).toContain('sieben Tagen');
      http.expectOne({ method: 'DELETE', url: URL }).flush(null, { status: 204, statusText: 'No Content' });
      standLiefern(stand({ wortlaut: '2026-11-05', widerrufen_am: '2026-11-06T09:30:00Z' }));
    });

    it('oeffnet bei einem Doppelklick nur eine Rueckfrage', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));
      const offen = new Subject<boolean>();
      dialog.open.and.callFake((() => ({ afterClosed: () => offen.asObservable() })) as any);

      knopf('Einwilligung widerrufen').click();
      knopf('Einwilligung widerrufen').click();
      expect(dialog.open).toHaveBeenCalledTimes(1);

      offen.next(false);
      offen.complete();
      knopf('Einwilligung widerrufen').click();
      expect(dialog.open).toHaveBeenCalledTimes(2);
    });

    it('widerruft nach Abbrechen nicht', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));
      rueckfrage = false;

      knopf('Einwilligung widerrufen').click();
      fixture.detectChanges();

      http.expectNone({ method: 'DELETE', url: URL });
      expect(knopf('Einwilligung widerrufen').disabled).toBeFalse();
    });

    it('widerruft nicht, wenn die Rueckfrage ohne Antwort schliesst (Escape)', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));
      rueckfrage = undefined;

      knopf('Einwilligung widerrufen').click();

      http.expectNone({ method: 'DELETE', url: URL });
      expect(dialog.open).toHaveBeenCalledTimes(1);
    });

    it('widerrufen fragt danach erneut, ohne Haekchen', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));

      knopf('Einwilligung widerrufen').click();
      http.expectOne({ method: 'DELETE', url: URL }).flush(null, { status: 204, statusText: 'No Content' });
      standLiefern(stand({ wortlaut: '2026-11-05', widerrufen_am: '2026-11-06T09:30:00Z' }));

      expect(el().textContent).toContain('widerrufen');
      expect(fixture.componentInstance.angehakt).toBeFalse();
      expect(knopf('Einwilligen und weiter').disabled).toBeTrue();
    });

    it('zeigt einen frueheren Widerruf auch nach dem Neuladen', () => {
      starten(null);
      standLiefern(stand({ wortlaut: '2026-11-05', widerrufen_am: '2026-11-06T09:30:00Z' }));

      expect(el().querySelector('.hinweis')?.textContent).toContain('06.11.2026');
      expect(el().querySelector('mat-checkbox')).not.toBeNull();
    });

    it('zeigt beim ersten Mal keinen Hinweis auf einen Widerruf', () => {
      starten(null);
      standLiefern(stand());

      expect(el().querySelector('.hinweis')).toBeNull();
      expect(el().textContent).not.toContain('Frühere Einwilligung widerrufen');
    });

    // Seit 2026-11-13 zaehlen nur GELTENDE_WORTLAUTE; eine fruehere Einwilligung fragt neu
    it('fragt neu, wer einem frueheren Wortlaut zugestimmt hat, und laesst ihn widerrufen', () => {
      starten(null);
      standLiefern(stand({ wortlaut: '2026-11-12', eingewilligt_am: '2026-11-12T09:30:00Z' }));

      expect(el().querySelector('mat-checkbox')).not.toBeNull();
      expect(el().querySelector('.hinweis')?.textContent).toContain('12.11.2026 einem früheren Wortlaut zugestimmt');

      knopf('Frühere Einwilligung widerrufen').click();
      fixture.detectChanges();
      // Waehrend des Widerrufs: weiter die Frage, gesperrt, nicht der Block fuer Eingewilligte
      expect(el().querySelector('mat-checkbox')).not.toBeNull();
      expect(el().textContent).not.toContain('Widerrufst du, kannst du nichts mehr beitragen');
      expect(knopf('Frühere Einwilligung widerrufen').disabled).toBeTrue();
      expect(knopf('Einwilligen und weiter').disabled).toBeTrue();
      http.expectOne({ method: 'DELETE', url: URL }).flush(null, { status: 204, statusText: 'No Content' });
      standLiefern(stand({ wortlaut: '2026-11-12', eingewilligt_am: '2026-11-12T09:30:00Z', widerrufen_am: '2026-11-13T09:30:00Z' }));

      expect(el().querySelector('.hinweis')?.textContent).toContain('13.11.2026 widerrufen');
      expect(el().textContent).not.toContain('Frühere Einwilligung widerrufen');
    });
  });

  it('holt den Stand neu, wenn der Tab wieder sichtbar wird (Widerruf in einem anderen Tab)', () => {
    starten(null);
    standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));

    document.dispatchEvent(new Event('visibilitychange'));
    standLiefern(stand({ wortlaut: '2026-11-05', widerrufen_am: '2026-11-06T09:30:00Z' }));

    expect(el().querySelector('mat-checkbox')).not.toBeNull();
    expect(el().querySelector('.hinweis')?.textContent).toContain('06.11.2026');
  });

  it('laedt beim Zurueckkommen nicht neu, wenn das Haekchen schon gesetzt ist', () => {
    starten(null);
    standLiefern(stand());
    fixture.componentInstance.angehakt = true;

    document.dispatchEvent(new Event('visibilitychange'));

    http.expectNone({ method: 'GET', url: URL });
  });

  it('zeigt einen Fehler, wenn der Stand nicht kommt', () => {
    starten();
    http.expectOne({ method: 'GET', url: URL }).flush(null, { status: 500, statusText: 'Fehler' });
    fixture.detectChanges();

    expect(el().querySelector('[role=alert]')).not.toBeNull();
  });
});
