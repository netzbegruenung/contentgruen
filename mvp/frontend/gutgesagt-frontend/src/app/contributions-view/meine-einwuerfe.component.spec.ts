import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter, Router } from '@angular/router';
import { MatBottomSheet } from '@angular/material/bottom-sheet';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Clipboard } from '@angular/cdk/clipboard';
import { BehaviorSubject, of, throwError } from 'rxjs';

import { MeineEinwuerfeComponent } from './meine-einwuerfe.component';
import { Einwurf, EinwurfService, EinwurfSeite } from '../services/einwurf.service';
import { EinwurfBeitragSheetComponent } from '../raw-input-list/einwurf-beitrag-sheet.component';
import { AuthService, UserInfo } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';
import { VotingService } from '../services/voting.service';
import { UsageTrackingService } from '../services/usage-tracking.service';

describe('MeineEinwuerfeComponent', () => {
  let fixture: ComponentFixture<MeineEinwuerfeComponent>;
  let einwurfService: jasmine.SpyObj<EinwurfService>;
  let bottomSheet: MatBottomSheet;
  let router: Router;

  function einwurf(felder: Partial<Einwurf> = {}): Einwurf {
    return {
      id: 'e-1',
      content: 'Guter Thread zu Waermepumpen',
      url: 'https://example.org/post/1',
      image_url: null,
      submitted_by: 'ich',
      source_channel: 'web',
      status: 'open',
      created_at: '2026-10-20T12:00:00Z',
      drafts: [],
      links: [],
      ...felder,
    };
  }

  function antwort(einwuerfe: Einwurf[], gesamt = einwuerfe.length): EinwurfSeite {
    return { results_count: einwuerfe.length, results: einwuerfe, total_records_count: gesamt };
  }

  const ausformuliert = einwurf({
    id: 'e-aus',
    status: 'processed',
    drafts: [{ id: 's-1', user_id: 'jemand', sentence: 'Waermepumpe lohnt sich auch im Altbau', updated_at: '2026-10-21T12:00:00Z' }],
    links: [{ content_id: 'c-1', content_type: 'commentary', draft_id: 's-1', processed_by: 'jemand', processed_at: '2026-10-22T12:00:00Z' }],
  });
  const verworfen = einwurf({ id: 'e-weg', status: 'discarded' });
  const offen = einwurf({ id: 'e-offen' });

  function anzeigen(): void {
    fixture = TestBed.createComponent(MeineEinwuerfeComponent);
    fixture.detectChanges();
  }

  function texte(selektor: string): string[] {
    return Array.from(fixture.nativeElement.querySelectorAll(selektor) as NodeListOf<HTMLElement>).map((el) =>
      el.textContent!.trim(),
    );
  }

  beforeEach(async () => {
    einwurfService = jasmine.createSpyObj('EinwurfService', ['eigeneLaden', 'updateStatus']);
    einwurfService.eigeneLaden.and.returnValue(of(antwort([ausformuliert, verworfen, offen])));
    const auth = jasmine.createSpyObj('AuthService', ['getUserInfo', 'getCurrentUserId']);
    auth.getUserInfo.and.returnValue({ isAuthenticated: true, userId: 'ich' } as UserInfo);
    auth.getCurrentUserId.and.returnValue('ich');
    auth.userInfo$ = new BehaviorSubject<UserInfo | null>({ isAuthenticated: true, userId: 'ich' } as UserInfo);

    await TestBed.configureTestingModule({
      imports: [MeineEinwuerfeComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: EinwurfService, useValue: einwurfService },
        { provide: AuthService, useValue: auth },
        { provide: MatSnackBar, useValue: jasmine.createSpyObj('MatSnackBar', ['open']) },
        { provide: Clipboard, useValue: jasmine.createSpyObj('Clipboard', ['copy']) },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['error', 'debug', 'info', 'warn']) },
        { provide: VotingService, useValue: jasmine.createSpyObj('VotingService', ['setLike']) },
        { provide: UsageTrackingService, useValue: jasmine.createSpyObj('UsageTrackingService', ['trackContentUsage']) },
      ],
    }).compileComponents();

    bottomSheet = TestBed.inject(MatBottomSheet);
    spyOn(bottomSheet, 'open');
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
  });

  it('laedt nur die eigenen Einwuerfe, erste Seite', () => {
    anzeigen();

    expect(einwurfService.eigeneLaden).toHaveBeenCalledOnceWith(1, 24);
  });

  it('zeigt jeden eigenen Einwurf mit seiner Stufe', () => {
    anzeigen();

    expect(texte('.einwurf-stufe')).toEqual(['Ausformuliert: Kommentar', 'Verworfen', 'Offen']);
    expect(texte('.einwuerfe-statistik')).toEqual(['3 Einwürfe']);
  });

  it('macht verworfene Einwuerfe erkennbar', () => {
    anzeigen();

    expect(texte('.einwurf-stufe')[1]).toBe('Verworfen');
  });

  it('fuehrt bei einem ausformulierten Einwurf zu seinem Beitrag', () => {
    anzeigen();

    const ansehen = Array.from(fixture.nativeElement.querySelectorAll('.einwurf-primaer') as NodeListOf<HTMLElement>).find(
      (knopf) => knopf.textContent!.includes('Ansehen'),
    )!;
    ansehen.click();

    const [inhalt, konfiguration] = (bottomSheet.open as jasmine.Spy).calls.mostRecent().args;
    expect(inhalt).toBe(EinwurfBeitragSheetComponent);
    expect(konfiguration.data).toEqual({
      beitraege: [{ contentId: 'c-1', typ: 'commentary', satz: 'Waermepumpe lohnt sich auch im Altbau' }],
    });
  });

  it('fuehrt bei einem offenen Einwurf zum Destillieren', () => {
    einwurfService.eigeneLaden.and.returnValue(of(antwort([offen])));
    anzeigen();

    (fixture.nativeElement.querySelector('.einwurf-primaer') as HTMLElement).click();

    expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'e-offen']);
  });

  it('laedt nach dem Verwerfen dieselbe Seite neu', () => {
    einwurfService.updateStatus.and.returnValue(of(einwurf({ id: 'e-offen', status: 'discarded' })));
    anzeigen();
    einwurfService.eigeneLaden.calls.reset();

    fixture.componentInstance.aktionAusfuehren(fixture.componentInstance.karten[2], 'verwerfen');

    expect(einwurfService.updateStatus).toHaveBeenCalledWith('e-offen', 'discarded');
    expect(einwurfService.eigeneLaden).toHaveBeenCalledOnceWith(1, 24);
  });

  it('sagt, wenn noch nichts eingeworfen ist', () => {
    einwurfService.eigeneLaden.and.returnValue(of(antwort([])));
    anzeigen();

    expect(texte('.einwuerfe-leer')).toEqual(['Du hast noch nichts eingeworfen.']);
    expect(texte('.einwuerfe-statistik')).toEqual([]);
  });

  it('sagt, wenn die Liste nicht geladen werden konnte', () => {
    einwurfService.eigeneLaden.and.returnValue(throwError(() => ({ status: 500 })));
    anzeigen();

    expect(texte('.einwuerfe-fehler')).toEqual(['Deine Einwürfe konnten nicht geladen werden. Bitte lade die Seite neu.']);
  });

  it('blaettert erst ab mehr als einer Seite', () => {
    anzeigen();
    expect(fixture.nativeElement.querySelector('mat-paginator')).toBeNull();

    einwurfService.eigeneLaden.and.returnValue(of(antwort([offen], 30)));
    anzeigen();
    expect(fixture.nativeElement.querySelector('mat-paginator')).not.toBeNull();
  });
});
