import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, convertToParamMap, ParamMap, provideRouter, Router } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';

import { AUTOSAVE_VERZOEGERUNG_MS, DestillierenComponent } from './destillieren.component';
import { DestillierUebergabeService } from './destillier-uebergabe.service';
import { RawInput, RawInputService } from '../services/raw-input.service';
import { AuthService } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';

function einwurf(overrides: Partial<RawInput> = {}): RawInput {
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
  let rawInputService: jasmine.SpyObj<RawInputService>;
  let uebergabe: jasmine.SpyObj<DestillierUebergabeService>;
  let router: Router;
  let params: BehaviorSubject<ParamMap>;
  let queryParams: ParamMap;

  async function erstellen(id: string | null, geladen: RawInput = einwurf()) {
    params = new BehaviorSubject(convertToParamMap(id ? { id } : {}));
    rawInputService.getRawInput.and.returnValue(of(geladen));

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
        { provide: RawInputService, useValue: rawInputService },
        { provide: DestillierUebergabeService, useValue: uebergabe },
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
    queryParams = convertToParamMap({});
    rawInputService = jasmine.createSpyObj('RawInputService', [
      'getRawInput',
      'saveDraft',
      'saveDraftKeepalive',
      'updateStatus',
      'naechsterOffenerEinwurf',
    ]);
    rawInputService.saveDraft.and.callFake((id: string, sentence: string) =>
      of({ raw_input_id: id, sentence, updated_at: null }),
    );
    rawInputService.updateStatus.and.returnValue(of(einwurf({ status: 'discarded' })));
    uebergabe = jasmine.createSpyObj('DestillierUebergabeService', ['zumNaechsten']);
  });

  describe('Satz', () => {
    it('laedt den Einwurf und uebernimmt den eigenen Entwurf', async () => {
      await erstellen('id-1', einwurf({ own_draft: 'Mein Satz' }));

      expect(rawInputService.getRawInput).toHaveBeenCalledWith('id-1');
      expect(component.satz.value).toBe('Mein Satz');
      expect(text()).toContain('Was ist der Punkt? Ein Satz.');
      expect(text()).toContain('9 / 120');
      expect(text()).toContain('https://example.org/post');
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
      expect(rawInputService.saveDraft).not.toHaveBeenCalled();

      tick(1);
      expect(rawInputService.saveDraft).toHaveBeenCalledOnceWith('id-1', 'Erster Satz');
      fixture.destroy();
    }));

    it('speichert beim Verlassen des Felds, aber nicht doppelt', async () => {
      await erstellen('id-1');
      component.satz.setValue('Mein Satz', { emitEvent: false });

      component.onBlur();
      component.onBlur();

      expect(rawInputService.saveDraft).toHaveBeenCalledOnceWith('id-1', 'Mein Satz');
    });

    it('sichert beim Wegwechseln der App per keepalive', async () => {
      await erstellen('id-1');
      component.satz.setValue('Mein Satz', { emitEvent: false });
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('hidden');

      document.dispatchEvent(new Event('visibilitychange'));

      expect(rawInputService.saveDraftKeepalive).toHaveBeenCalledOnceWith('id-1', 'Mein Satz');
    });

    it('sichert beim Wegwechseln nichts, was schon gespeichert ist', async () => {
      await erstellen('id-1', einwurf({ own_draft: 'Mein Satz' }));
      spyOnProperty(document, 'visibilityState', 'get').and.returnValue('hidden');

      document.dispatchEvent(new Event('visibilitychange'));

      expect(rawInputService.saveDraftKeepalive).not.toHaveBeenCalled();
    });
  });

  describe('Knoepfe', () => {
    it('zeigt Verwerfen nur beim eigenen Einwurf', async () => {
      await erstellen('id-1', einwurf({ submitted_by: 'bob' }));

      expect(knopf('verwerfen')).toBeNull();
      expect(knopf('spaeter')).toBeTruthy();
    });

    it('verwirft den eigenen Einwurf und oeffnet den naechsten', async () => {
      await erstellen('id-1');

      knopf('verwerfen')!.click();

      expect(rawInputService.updateStatus).toHaveBeenCalledWith('id-1', 'discarded');
      expect(uebergabe.zumNaechsten).toHaveBeenCalledWith('id-1');
    });

    it('speichert bei Spaeter den Satz und oeffnet den naechsten', async () => {
      await erstellen('id-1');
      component.satz.setValue('Noch nicht ganz', { emitEvent: false });

      knopf('spaeter')!.click();

      expect(rawInputService.saveDraft).toHaveBeenCalledWith('id-1', 'Noch nicht ganz');
      expect(uebergabe.zumNaechsten).toHaveBeenCalledWith('id-1');
    });

    it('fuehrt mit Weiter zur Typwahl, Kommentar ist vorausgewaehlt', async () => {
      await erstellen('id-1');
      component.satz.setValue('Waermepumpe lohnt sich auch im Altbau', { emitEvent: false });
      fixture.detectChanges();

      knopf('weiter')!.click();
      fixture.detectChanges();

      expect(rawInputService.saveDraft).toHaveBeenCalledWith(
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
      rawInputService.naechsterOffenerEinwurf.and.returnValue(of(einwurf({ id: 'id-9' })));

      await erstellen(null);

      expect(rawInputService.naechsterOffenerEinwurf).toHaveBeenCalledWith('id-vorher');
      expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'id-9'], {
        replaceUrl: true,
      });
    });

    it('sagt "Alles destilliert", wenn nichts mehr offen ist', async () => {
      rawInputService.naechsterOffenerEinwurf.and.returnValue(of(null));

      await erstellen(null);
      fixture.detectChanges();

      expect(text()).toContain('Alles destilliert');
      const link: HTMLAnchorElement = fixture.nativeElement.querySelector('a[href="/fangkorb"]');
      expect(link).toBeTruthy();
    });
  });
});
