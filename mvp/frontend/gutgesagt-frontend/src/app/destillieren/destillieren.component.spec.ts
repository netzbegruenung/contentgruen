import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, convertToParamMap, ParamMap, provideRouter, Router } from '@angular/router';
import { BehaviorSubject, of, Subject, throwError } from 'rxjs';

import { AUTOSAVE_VERZOEGERUNG_MS, DestillierenComponent, TYPEN } from './destillieren.component';
import { BeitragAnsehenService } from '../beitragsformular/beitrag-ansehen.service';
import { DestillierUebergabeService } from './destillier-uebergabe.service';
import { SatzResponse, Einwurf, EinwurfService } from '../services/einwurf.service';
import { AuthService, UserInfo } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';
import { FILTER_SCHLUESSEL, filterLaden } from '../raw-input-list/fangkorb-filter';
import { NavigationService } from '../services/navigation.service';

function einwurf(overrides: Partial<Einwurf> = {}): Einwurf {
  return {
    id: 'id-1',
    content: 'Guter Thread',
    url: 'https://example.org/post',
    image_url: null,
    submitted_by: 'alice',
    source_channel: 'share',
    status: 'open',
    created_at: '2026-09-13T12:00:00Z',
    own_draft: null,
    ...overrides,
  };
}

describe('DestillierenComponent', () => {
  let fixture: ComponentFixture<DestillierenComponent>;
  let component: DestillierenComponent;
  let einwurfService: jasmine.SpyObj<EinwurfService>;
  let uebergabe: jasmine.SpyObj<DestillierUebergabeService>;
  let nutzer: UserInfo;
  let navigation: jasmine.SpyObj<NavigationService>;
  let beitragAnsehen: jasmine.SpyObj<BeitragAnsehenService>;
  let router: Router;
  let params: BehaviorSubject<ParamMap>;
  let queryParams: ParamMap;

  async function erstellen(id: string | null, geladen: Einwurf = einwurf()) {
    params = new BehaviorSubject(convertToParamMap(id ? { id } : {}));
    beitragAnsehen = jasmine.createSpyObj('BeitragAnsehenService', ['oeffnen', 'kannAnsehen']);
    beitragAnsehen.kannAnsehen.and.returnValue(true);
    navigation = jasmine.createSpyObj('NavigationService', [
      'goBack',
      'registerBeforeBack',
      'unregisterBeforeBack',
    ]);
    einwurfService.einwurfLaden.and.returnValue(of(geladen));

    await TestBed.configureTestingModule({
      imports: [DestillierenComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: params.asObservable(),
            get snapshot() {
              return { queryParamMap: queryParams };
            },
          },
        },
        { provide: EinwurfService, useValue: einwurfService },
        { provide: DestillierUebergabeService, useValue: uebergabe },
        { provide: NavigationService, useValue: navigation },
        { provide: BeitragAnsehenService, useValue: beitragAnsehen },
        {
          provide: AuthService,
          useValue: {
            getCurrentUserId: () => nutzer.userId,
            getUserInfo: () => nutzer,
            userInfo$: of(nutzer),
            fetchUserInfo: () => of(nutzer),
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
    fixture = TestBed.createComponent(DestillierenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  function text(): string {
    return fixture.nativeElement.textContent;
  }

  function knopf(klasse: string): HTMLButtonElement | null {
    return fixture.nativeElement.querySelector(`button.${klasse}`);
  }

  beforeEach(() => {
    // Tab und Chip liegen im sessionStorage - sonst traegt ein Test den Stand des
    // vorigen weiter.
    sessionStorage.removeItem(FILTER_SCHLUESSEL);
    nutzer = { isAuthenticated: true, userId: 'alice', userName: null, claims: null };
    queryParams = convertToParamMap({});
    einwurfService = jasmine.createSpyObj('EinwurfService', [
      'einwurfLaden',
      'satzSpeichern',
      'satzSpeichernKeepalive',
      'updateStatus',
      'naechsterOffenerEinwurf',
      'zurueckstellen',
      'rundeBeginnen',
    ]);
    einwurfService.satzSpeichern.and.callFake((id: string, sentence: string) =>
      of({ raw_input_id: id, sentence, updated_at: null }),
    );
    einwurfService.updateStatus.and.returnValue(of(einwurf({ status: 'discarded' })));
    uebergabe = jasmine.createSpyObj('DestillierUebergabeService', ['zumNaechsten']);
  });

  afterEach(() => sessionStorage.removeItem(FILTER_SCHLUESSEL));

  describe('Satz', () => {
    it('laedt den Einwurf und uebernimmt den eigenen Satz', async () => {
      await erstellen('id-1', einwurf({ own_draft: 'Mein Satz' }));

      expect(einwurfService.einwurfLaden).toHaveBeenCalledWith('id-1');
      expect(component.satz.value).toBe('Mein Satz');
      expect(text()).toContain('Was ist der Punkt? Ein Satz.');
      expect(text()).toContain('9 / 120');
      // Die Adresse steht im Kopfband, dort gekuerzt ohne Schema.
      expect(text()).toContain('example.org/post');
    });

    it('sperrt Weiter ohne Satz und gibt es mit Satz frei', async () => {
      await erstellen('id-1');

      expect(knopf('weiter')!.disabled).toBeTrue();

      component.satz.setValue('Waermepumpe lohnt sich auch im Altbau');
      fixture.detectChanges();
      expect(knopf('weiter')!.disabled).toBeFalse();
    });

    it('sperrt Weiter ueber 120 Zeichen', async () => {
      await erstellen('id-1');

      component.satz.setValue('a'.repeat(121));
      fixture.detectChanges();

      expect(component.kannWeiter).toBeFalse();
      const feld: HTMLTextAreaElement = fixture.nativeElement.querySelector('textarea#satz');
      expect(feld.getAttribute('maxlength')).toBe('120');
    });

    it('speichert verzoegert beim Tippen', fakeAsync(() => {
      erstellen('id-1');
      tick();

      component.satz.setValue('Erster Satz');
      tick(AUTOSAVE_VERZOEGERUNG_MS - 1);
      expect(einwurfService.satzSpeichern).not.toHaveBeenCalled();

      tick(1);
      expect(einwurfService.satzSpeichern).toHaveBeenCalledOnceWith('id-1', 'Erster Satz');
      fixture.destroy();
    }));

    it('speichert beim Verlassen des Felds, aber nicht doppelt', async () => {
      await erstellen('id-1');
      component.satz.setValue('Mein Satz', { emitEvent: false });

      component.onBlur();
      component.onBlur();

      expect(einwurfService.satzSpeichern).toHaveBeenCalledOnceWith('id-1', 'Mein Satz');
    });

    it('sichert beim Wegwechseln der App per keepalive', async () => {
      await erstellen('id-1');
      component.satz.setValue('Mein Satz', { emitEvent: false });
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('hidden');

      document.dispatchEvent(new Event('visibilitychange'));

      expect(einwurfService.satzSpeichernKeepalive).toHaveBeenCalledOnceWith('id-1', 'Mein Satz');
    });

    it('sichert beim Wegwechseln nichts, was schon gespeichert ist', async () => {
      await erstellen('id-1', einwurf({ own_draft: 'Mein Satz' }));
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('hidden');

      document.dispatchEvent(new Event('visibilitychange'));

      expect(einwurfService.satzSpeichernKeepalive).not.toHaveBeenCalled();
    });
  });

  describe('Knoepfe', () => {
    it('zeigt Verwerfen nur beim eigenen Einwurf', async () => {
      await erstellen('id-1', einwurf({ submitted_by: 'bob' }));

      expect(knopf('verwerfen')).toBeNull();
      expect(knopf('spaeter')!.textContent!.trim()).toBe('Später');
    });

    it('zeigt Admins Verwerfen auch beim fremden Einwurf', async () => {
      nutzer = { ...nutzer, userId: 'admin', isAdmin: true };
      await erstellen('id-1', einwurf({ submitted_by: 'bob' }));

      knopf('verwerfen')!.click();

      expect(einwurfService.updateStatus).toHaveBeenCalledWith('id-1', 'discarded');
      expect(uebergabe.zumNaechsten).toHaveBeenCalledWith('id-1', 'destillieren');
    });

    it('zeigt Verwerfen bei Ausformuliertem und Verworfenem niemandem', async () => {
      nutzer = { ...nutzer, isAdmin: true };
      await erstellen('id-1', einwurf({ status: 'processed' }));
      expect(knopf('verwerfen')).toBeNull();

      TestBed.resetTestingModule();
      await erstellen('id-1', einwurf({ status: 'discarded' }));
      expect(knopf('verwerfen')).toBeNull();
    });

    it('zeigt Mitwirkenden ohne Adminrechte bei fremdem Einwurf kein Verwerfen', async () => {
      nutzer = { ...nutzer, isAdmin: false };
      await erstellen('id-1', einwurf({ submitted_by: 'bob', status: 'in_progress' }));

      expect(knopf('verwerfen')).toBeNull();
    });

    it('verwirft den eigenen Einwurf und oeffnet den naechsten', async () => {
      await erstellen('id-1');

      knopf('verwerfen')!.click();

      expect(einwurfService.updateStatus).toHaveBeenCalledWith('id-1', 'discarded');
      // Verworfenes ohne Satz liegt unter "Destillieren" hinter einem Chip - und der
      // wird eingeschaltet, sonst waere der Einwurf nach dem Verwerfen scheinbar
      // spurlos weg.
      expect(uebergabe.zumNaechsten).toHaveBeenCalledWith('id-1', 'destillieren');
      expect(filterLaden().verworfenSichtbar).toBeTrue();
    });

    it('nennt nach dem Verwerfen mit gespeichertem Satz den Tab "Ausformulieren"', async () => {
      await erstellen('id-1', einwurf({ status: 'in_progress', own_draft: 'Waermepumpe lohnt sich' }));

      knopf('verwerfen')!.click();

      expect(uebergabe.zumNaechsten).toHaveBeenCalledWith('id-1', 'ausformulieren');
      expect(filterLaden().verworfenSichtbar).toBeTrue();
    });

    it('nennt bei einer Ablehnung, wer verwerfen darf', async () => {
      await erstellen('id-1');
      einwurfService.updateStatus.and.returnValue(throwError(() => ({ status: 403 })));

      knopf('verwerfen')!.click();

      expect(component.fehler).toBe('Verwerfen können nur der Einwerfer und Admins.');
      expect(component.arbeitet).toBeFalse();
      expect(uebergabe.zumNaechsten).not.toHaveBeenCalled();
    });

    it('speichert bei Spaeter den Satz und oeffnet den naechsten', async () => {
      await erstellen('id-1');
      component.satz.setValue('Noch nicht ganz', { emitEvent: false });

      knopf('spaeter')!.click();

      expect(einwurfService.satzSpeichern).toHaveBeenCalledWith('id-1', 'Noch nicht ganz');
      // Zurueckgestellt heisst: Satz steht, Beitrag fehlt - Tab "Ausformulieren".
      expect(uebergabe.zumNaechsten).toHaveBeenCalledWith('id-1', 'ausformulieren');
      expect(einwurfService.zurueckstellen).toHaveBeenCalledWith('id-1');
    });

    it('stellt bei Spaeter ohne Satz zurueck und nennt den Tab "Destillieren"', async () => {
      await erstellen('id-1');

      knopf('spaeter')!.click();

      expect(einwurfService.satzSpeichern).not.toHaveBeenCalled();
      expect(einwurfService.zurueckstellen).toHaveBeenCalledWith('id-1');
      expect(uebergabe.zumNaechsten).toHaveBeenCalledWith('id-1', 'destillieren');
    });

    it('nennt bei Spaeter ohne eigenen, aber mit fremdem Satz den Tab "Ausformulieren"', async () => {
      await erstellen(
        'id-1',
        einwurf({
          status: 'in_progress',
          drafts: [{ id: 's-1', user_id: 'bob', sentence: 'Satz von Bob', updated_at: '2026-09-13T12:00:00Z' }],
        }),
      );

      knopf('spaeter')!.click();

      expect(uebergabe.zumNaechsten).toHaveBeenCalledWith('id-1', 'ausformulieren');
    });

    it('stellt bei gescheitertem Speichern nichts zurueck', async () => {
      await erstellen('id-1');
      einwurfService.satzSpeichern.and.returnValue(throwError(() => ({ status: 500 })));
      component.satz.setValue('Noch nicht ganz', { emitEvent: false });

      knopf('spaeter')!.click();

      expect(einwurfService.zurueckstellen).not.toHaveBeenCalled();
      expect(uebergabe.zumNaechsten).not.toHaveBeenCalled();
    });

    it('fuehrt mit Weiter zur Typwahl, Kommentar ist vorausgewaehlt', async () => {
      await erstellen('id-1');
      component.satz.setValue('Waermepumpe lohnt sich auch im Altbau', { emitEvent: false });
      fixture.detectChanges();

      knopf('weiter')!.click();
      fixture.detectChanges();

      expect(einwurfService.satzSpeichern).toHaveBeenCalledWith(
        'id-1',
        'Waermepumpe lohnt sich auch im Altbau',
      );
      expect(component.schritt).toBe('typwahl');
      expect(component.typ).toBe('commentary');
      expect(text()).toContain('Kommentar');
      expect(text()).toContain('Hintergrundinfo');
      expect(text()).not.toContain('Bild');
    });

    it('oeffnet das Formular nur mit der ID in der Adresse', async () => {
      await erstellen('id-1');
      component.schritt = 'typwahl';

      component.formularOeffnen();
      expect(router.navigate).toHaveBeenCalledWith(['/workflow/add-commentary'], {
        queryParams: { rohinput: 'id-1' },
      });

      component.typ = 'generictext';
      component.formularOeffnen();
      expect(router.navigate).toHaveBeenCalledWith(['/workflow/add-generictext'], {
        queryParams: { rohinput: 'id-1' },
      });
    });
  });

  describe('Warteschlange', () => {
    it('oeffnet ohne ID den naechsten offenen Einwurf', async () => {
      queryParams = convertToParamMap({ nach: 'id-vorher' });
      einwurfService.naechsterOffenerEinwurf.and.returnValue(of(einwurf({ id: 'id-9' })));

      await erstellen(null);

      expect(einwurfService.naechsterOffenerEinwurf).toHaveBeenCalledWith('id-vorher');
      expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'id-9'], {
        replaceUrl: true,
      });
      // Mitten im Ablauf bleibt Zurueckgestelltes zurueckgestellt.
      expect(einwurfService.rundeBeginnen).not.toHaveBeenCalled();
    });

    it('beginnt ohne "nach" eine neue Runde, bevor es sucht', async () => {
      einwurfService.naechsterOffenerEinwurf.and.returnValue(of(einwurf({ id: 'id-9' })));

      await erstellen(null);

      expect(einwurfService.rundeBeginnen).toHaveBeenCalledBefore(einwurfService.naechsterOffenerEinwurf);
    });

    it('beginnt am Ende des Ablaufs eine neue Runde', async () => {
      queryParams = convertToParamMap({ nach: 'id-vorher', tab: 'destillieren' });
      einwurfService.naechsterOffenerEinwurf.and.returnValue(of(null));

      await erstellen(null);

      expect(einwurfService.rundeBeginnen).toHaveBeenCalled();
      expect(filterLaden().tab).toBe('destillieren');
      expect(router.navigate).toHaveBeenCalledWith(['/fangkorb'], { replaceUrl: true });
    });

    it('sagt "Alles destilliert", wenn nichts mehr offen ist', async () => {
      einwurfService.naechsterOffenerEinwurf.and.returnValue(of(null));

      await erstellen(null);
      fixture.detectChanges();

      expect(text()).toContain('Alles destilliert');
      const link: HTMLAnchorElement = fixture.nativeElement.querySelector('a[href="/fangkorb"]');
      expect(link).toBeTruthy();
    });

    it('springt aus dem Ablauf in den Tab der Handlung, ohne Halt in der History', async () => {
      queryParams = convertToParamMap({ nach: 'id-vorher', tab: 'ausformulieren' });
      einwurfService.naechsterOffenerEinwurf.and.returnValue(of(null));

      await erstellen(null);

      expect(filterLaden().tab).toBe('ausformulieren');
      // replaceUrl: Sonst bliebe /destillieren?nach=... in der History stehen, und
      // das System-Zurueck liefe von hier wieder in dieselbe Weiterleitung.
      expect(router.navigate).toHaveBeenCalledWith(['/fangkorb'], { replaceUrl: true });
    });

    it('nimmt ohne Tab-Angabe den Tab "Ausformulieren"', async () => {
      queryParams = convertToParamMap({ nach: 'id-vorher' });
      einwurfService.naechsterOffenerEinwurf.and.returnValue(of(null));

      await erstellen(null);

      expect(filterLaden().tab).toBe('ausformulieren');
    });

    it('oeffnet mit ?schritt=typwahl die Typwahl, wenn ein eigener Satz dasteht', async () => {
      queryParams = convertToParamMap({ schritt: 'typwahl' });

      await erstellen('id-1', einwurf({ own_draft: 'Waermepumpe lohnt sich auch im Altbau' }));

      expect(component.schritt).toBe('typwahl');
      expect(text()).toContain('Waermepumpe lohnt sich auch im Altbau');
    });

    const ausformuliert = () =>
      einwurf({
        own_draft: 'Waermepumpe lohnt sich',
        status: 'processed',
        links: [{ content_id: 'k-1', content_type: 'commentary', draft_id: null, processed_by: 'alice', processed_at: '' }],
      } as any);

    it('zeigt bei einem ausformulierten Einwurf die Typwahl mit Hinweis statt umzuleiten (Rueckweg von der Ergebnisseite)', async () => {
      queryParams = convertToParamMap({ schritt: 'typwahl' });

      await erstellen('id-1', ausformuliert());

      expect(router.navigate).not.toHaveBeenCalledWith(['/fangkorb'], jasmine.anything());
      expect(component.schritt).toBe('typwahl');
      const hinweis: HTMLElement = fixture.nativeElement.querySelector('.schon-verknuepft');
      expect(hinweis.textContent).toContain('Zu diesem Einwurf gibt es schon einen Beitrag');
      expect(fixture.nativeElement.querySelector('.typen')).toBeTruthy();

      (hinweis.querySelector('.beitrag-ansehen') as HTMLButtonElement).click();
      expect(beitragAnsehen.oeffnen).toHaveBeenCalledOnceWith('k-1', 'commentary');
    });

    it('zeigt ohne verknuepften Beitrag keinen Hinweis', async () => {
      queryParams = convertToParamMap({ schritt: 'typwahl' });

      await erstellen('id-1', einwurf({ own_draft: 'Waermepumpe lohnt sich' }));

      expect(fixture.nativeElement.querySelector('.schon-verknuepft')).toBeNull();
    });

    it('laesst einen ausformulierten Einwurf ohne ?schritt beim Satz (Weiter destillieren)', async () => {
      await erstellen('id-1', ausformuliert());

      expect(router.navigate).not.toHaveBeenCalledWith(['/fangkorb'], jasmine.anything());
      expect(component.schritt).toBe('satz');
    });

    it('zeigt in der Typwahl den Einwurf als Kopfband statt rohem Link und Text', async () => {
      queryParams = convertToParamMap({ schritt: 'typwahl' });

      await erstellen('id-1', einwurf({ own_draft: 'Waermepumpe lohnt sich auch im Altbau' }));

      const seite: HTMLElement = fixture.nativeElement;
      expect(seite.querySelector('.einwurf-link')).toBeNull();
      expect(seite.querySelector('.satz-vorschau')).toBeNull();
      expect(seite.querySelector('.einwurf-kopf .einwurf-band')).toBeTruthy();
      expect(seite.querySelector('.einwurf-kopf .einwurf-titel')!.textContent).toContain('Guter Thread');
      expect(seite.querySelector('.einwurf-kopf .einwurf-kopfsatz')!.textContent).toContain('Waermepumpe lohnt sich auch im Altbau');
      // Mit Satz ist der Einwurf auszuformulieren - auch wenn er vor dem Speichern geladen wurde.
      expect(seite.querySelector('.einwurf-kopf .karte')!.classList).toContain('stufe-destilliert');
    });

    it('beschreibt die Typen mit den Saetzen aus der Registry', () => {
      expect(TYPEN.map((t) => t.erlaeuterung)).toEqual([
        'Eine Antwort, die du direkt posten kannst.',
        'Fakten und Zahlen, die eine Antwort stützen.',
      ]);
    });

    it('bleibt mit ?schritt=typwahl ohne eigenen Satz beim Satzfeld', async () => {
      queryParams = convertToParamMap({ schritt: 'typwahl' });

      await erstellen('id-1', einwurf({ own_draft: null }));

      expect(component.schritt).toBe('satz');
      expect(text()).toContain('Was ist der Punkt? Ein Satz.');
    });
  });
  describe('Saetze anderer', () => {
    const saetze = [
      { id: 's-1', user_id: 'bob-1234-5678-9abc', user_name: 'Bob K.', sentence: 'Satz von Bob', updated_at: '2026-09-13T12:00:00Z' },
      { id: 's-2', user_id: 'alice', user_name: 'Alice M.', sentence: 'Mein Satz', updated_at: '2026-09-13T12:05:00Z' },
    ];

    it('zeigt vorhandene Saetze anderer oberhalb des eigenen Felds, nicht editierbar', async () => {
      await erstellen(
        'id-1',
        einwurf({ status: 'in_progress', own_draft: 'Mein Satz', drafts: saetze }),
      );
      const fremde: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll('.fremder-satz'));
      const feld: HTMLTextAreaElement = fixture.nativeElement.querySelector('textarea#satz');

      expect(fremde.length).toBe(1);
      expect(fremde[0].textContent).toContain('Satz von Bob');
      expect(fremde[0].querySelector('.person')!.textContent!.trim()).toBe('Bob K.');
      expect(fremde[0].textContent).not.toContain('bob-1234');
      expect(fremde[0].querySelector('.person')!.hasAttribute('title')).toBeFalse();
      expect(fixture.nativeElement.querySelector('.fremde-saetze textarea, .fremde-saetze input')).toBeNull();
      expect(fremde[0].compareDocumentPosition(feld) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(component.satz.value).toBe('Mein Satz');
    });

    it('nennt einen Satz ohne Anzeigenamen "Mitglied"', async () => {
      const ohneName = { ...saetze[0], user_name: null };
      await erstellen('id-1', einwurf({ status: 'in_progress', drafts: [ohneName] }));

      const person = fixture.nativeElement.querySelector('.fremder-satz .person');
      expect(person.textContent.trim()).toBe('Mitglied');
    });

    it('zeigt keinen Kasten, wenn nur der eigene Satz existiert', async () => {
      await erstellen('id-1', einwurf({ status: 'in_progress', drafts: [saetze[1]] }));

      expect(fixture.nativeElement.querySelector('.fremde-saetze')).toBeNull();
    });
  });

  describe('Nachlese', () => {
    /** Was die Ansicht beim Dienst angemeldet hat, damit der Pfeil im Kopf es abwartet. */
    function angemeldeterHook(): () => Promise<void> {
      return navigation.registerBeforeBack.calls.mostRecent().args[0] as () => Promise<void>;
    }

    /** Denselben Hook ausfuehren - so, wie der Dienst es beim Pfeil tut. */
    function hookAusfuehren(): Promise<void> {
      return angemeldeterHook()();
    }

    it('hat keinen eigenen Pfeil mehr, sondern meldet das Speichern beim Dienst an', async () => {
      await erstellen('id-1');

      expect(fixture.nativeElement.querySelector('button.zurueck-pfeil')).toBeNull();
      expect(text()).not.toContain('Zurück zum Fangkorb');
      expect(navigation.registerBeforeBack).toHaveBeenCalledTimes(1);
    });

    it('meldet den Dienst beim Verlassen wieder ab', async () => {
      await erstellen('id-1');
      const angemeldet = angemeldeterHook();

      fixture.destroy();

      expect(navigation.unregisterBeforeBack).toHaveBeenCalledWith(angemeldet);
    });

    it('ist erst fertig, wenn der Satz gespeichert ist', async () => {
      await erstellen('id-1');
      const antwort = new Subject<SatzResponse>();
      einwurfService.satzSpeichern.and.returnValue(antwort);
      component.satz.setValue('Frisch getippt', { emitEvent: false });

      let fertig = false;
      const lauf = hookAusfuehren().then(() => (fertig = true));

      expect(einwurfService.satzSpeichern).toHaveBeenCalledOnceWith('id-1', 'Frisch getippt');
      await Promise.resolve();
      expect(fertig).toBeFalse();

      antwort.next({ raw_input_id: 'id-1', sentence: 'Frisch getippt', updated_at: null });
      antwort.complete();
      await lauf;

      expect(fertig).toBeTrue();
    });

    it('scheitert bei einem zu langen Satz und nennt die Laenge als Grund', async () => {
      await erstellen('id-1');
      component.satz.setValue('a'.repeat(121), { emitEvent: false });

      await expectAsync(hookAusfuehren()).toBeRejected();
      fixture.detectChanges();

      // Nicht speicherbar heisst: nicht verlassen. Frueher lief das still als
      // "nichts zu tun" durch, und der Satz war nach dem Pfeil weg.
      expect(einwurfService.satzSpeichern).not.toHaveBeenCalled();
      expect(text()).toContain('Der Satz ist zu lang');
      expect(navigation.goBack).not.toHaveBeenCalled();
    });

    it('scheitert und bleibt stehen, wenn das Speichern nicht klappt', async () => {
      await erstellen('id-1');
      einwurfService.satzSpeichern.and.returnValue(throwError(() => new Error('offline')));
      component.satz.setValue('Frisch getippt', { emitEvent: false });

      await expectAsync(hookAusfuehren()).toBeRejected();
      fixture.detectChanges();

      expect(text()).toContain('Der Satz konnte nicht gespeichert werden');
    });

    it('fuehrt aus der Typwahl mit dem Zurueck-Knopf zurueck zum Satz', async () => {
      await erstellen('id-1');
      component.schritt = 'typwahl';
      fixture.detectChanges();

      fixture.nativeElement.querySelector('button.zurueck').click();
      fixture.detectChanges();

      expect(component.schritt).toBe('satz');
      expect(navigation.goBack).not.toHaveBeenCalled();
    });

    it('erlaeutert in der Typwahl beide Typen und faerbt den gewaehlten', async () => {
      await erstellen('id-1');
      component.schritt = 'typwahl';
      fixture.detectChanges();

      expect(text()).toContain('Eine Antwort, die du direkt posten kannst.');
      expect(text()).toContain('Fakten und Zahlen, die eine Antwort stützen.');
      const gewaehlt: HTMLElement = fixture.nativeElement.querySelector('.typ.gewaehlt');
      expect(gewaehlt.classList).toContain('typ-commentary');
    });
  });
});
