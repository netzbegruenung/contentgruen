import { ChangeDetectorRef, Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';

import { NichtDabeiComponent } from './nicht-dabei.component';
import { AuthService, UserInfo } from '../auth/auth.service';
import { StatementService } from '../services/statement.service';
import { LoggingService } from '../services/logging.service';
import { StatementSearchResult } from '../services/dtos/statementDtos';

/** Wie die Ergebnisseite: Suchtext, bekannte Aussagen und der Knopf als Inhalt. */
@Component({
  standalone: true,
  imports: [NichtDabeiComponent],
  template: `
    <app-nicht-dabei [suchtext]="suchtext" [bekannteAussagen]="bekannt">
      <button class="neu">Selbst beantworten</button>
    </app-nicht-dabei>
  `,
})
class GastgeberComponent {
  suchtext = 'Wärmepumpen sind zu teuer';
  bekannt: string[] = [];
}

describe('NichtDabeiComponent', () => {
  const AEHNLICH: StatementSearchResult = { id: 'a-1', text: 'Wärmepumpen lohnen sich nicht', replysuggestions_count: 2, score: 0.9 };
  const ZWEITE: StatementSearchResult = { id: 'a-2', text: 'Heizen mit Strom ist teuer', replysuggestions_count: 1, score: 0.89 };

  let fixture: ComponentFixture<GastgeberComponent>;
  let statementService: jasmine.SpyObj<StatementService>;
  let nutzer: BehaviorSubject<UserInfo | null>;
  let logger: jasmine.SpyObj<LoggingService>;

  const ANGEMELDET: UserInfo = { isAuthenticated: true, userId: 'u-1', userName: 'Test', claims: null };

  function starten(angemeldet: UserInfo | null = ANGEMELDET): HTMLElement {
    statementService = jasmine.createSpyObj('StatementService', ['aehnlicheAussagen']);
    statementService.aehnlicheAussagen.and.returnValue(of([AEHNLICH, ZWEITE]));
    nutzer = new BehaviorSubject<UserInfo | null>(angemeldet);
    logger = jasmine.createSpyObj('LoggingService', ['warn', 'error', 'debug']);
    TestBed.configureTestingModule({
      imports: [GastgeberComponent],
      providers: [
        provideRouter([]),
        { provide: StatementService, useValue: statementService },
        { provide: AuthService, useValue: { userInfo$: nutzer.asObservable() } },
        { provide: LoggingService, useValue: logger },
      ],
    });
    fixture = TestBed.createComponent(GastgeberComponent);
    fixture.detectChanges();
    return fixture.nativeElement;
  }

  function aehnliche(seite: HTMLElement): string[] {
    return Array.from(seite.querySelectorAll('.aehnliche-aussage .aussage-text')).map((e) => (e.textContent ?? '').trim());
  }

  it('zeigt "Nicht dabei?", aehnliche Aussagen mit "passt vielleicht" und den Knopf', () => {
    const seite = starten();

    expect(seite.querySelector('.nicht-dabei-titel')?.textContent).toContain('Nicht dabei?');
    expect(seite.querySelector('.aehnliche-titel')?.textContent).toContain('Ähnliche Aussagen');
    expect(aehnliche(seite)).toEqual(['Wärmepumpen lohnen sich nicht', 'Heizen mit Strom ist teuer']);
    expect(seite.querySelectorAll('.passt-vielleicht').length).toBe(2);
    expect(seite.querySelector('button.neu')?.textContent).toContain('Selbst beantworten');
    expect(statementService.aehnlicheAussagen).toHaveBeenCalledOnceWith('Wärmepumpen sind zu teuer');
  });

  it('verlinkt jede aehnliche Aussage auf die Suche nach ihr', () => {
    const seite = starten();
    const link = seite.querySelector<HTMLAnchorElement>('.aehnliche-aussage')!;
    expect(link.getAttribute('href')).toBe('/result?searchQuery=W%C3%A4rmepumpen%20lohnen%20sich%20nicht');
  });

  it('laesst Aussagen weg, die schon als Treffer dastehen', () => {
    const seite = starten();
    fixture.componentInstance.bekannt = ['a-1'];
    fixture.detectChanges();
    expect(aehnliche(seite)).toEqual(['Heizen mit Strom ist teuer']);
  });

  it('fragt auch fuer Besucher nach (oeffentlicher Endpunkt, #642)', () => {
    const seite = starten({ isAuthenticated: false, userId: null, userName: null, claims: null });

    expect(statementService.aehnlicheAussagen).toHaveBeenCalledOnceWith('Wärmepumpen sind zu teuer');
    expect(aehnliche(seite)).toEqual(['Wärmepumpen lohnen sich nicht', 'Heizen mit Strom ist teuer']);
  });

  it('fragt bei neuem Suchtext neu, nicht beim Anmelden', () => {
    starten(null);
    expect(statementService.aehnlicheAussagen).toHaveBeenCalledTimes(1);

    nutzer.next(ANGEMELDET);
    fixture.detectChanges();
    expect(statementService.aehnlicheAussagen).toHaveBeenCalledTimes(1);

    fixture.componentInstance.suchtext = 'Tempolimit bringt nichts';
    fixture.detectChanges();
    expect(statementService.aehnlicheAussagen).toHaveBeenCalledTimes(2);
    expect(statementService.aehnlicheAussagen.calls.mostRecent().args[0]).toBe('Tempolimit bringt nichts');
  });

  it('meldet die Zahl der aehnlichen Aussagen ohne die bekannten', () => {
    starten();
    const komponente = fixture.debugElement.children[0].componentInstance as NichtDabeiComponent;
    const gemeldet: number[] = [];
    komponente.aehnlicheAnzahl.subscribe((n) => gemeldet.push(n));
    fixture.componentInstance.bekannt = ['a-1'];
    fixture.detectChanges();
    expect(gemeldet).toEqual([1]);
  });

  it('fragt bei zu kurzem Suchtext nicht nach', () => {
    const seite = starten();
    statementService.aehnlicheAussagen.calls.reset();
    fixture.componentInstance.suchtext = ' a ';
    fixture.detectChanges();

    expect(statementService.aehnlicheAussagen).not.toHaveBeenCalled();
    expect(seite.querySelector('.aehnliche')).toBeNull();
  });

  it('bleibt ohne Liste nutzbar, wenn die aehnlichen Aussagen nicht ladbar sind', () => {
    TestBed.overrideProvider(StatementService, {
      useValue: { aehnlicheAussagen: () => throwError(() => new Error('500')) },
    });
    const seite = starten();

    expect(seite.querySelector('.aehnliche')).toBeNull();
    expect(seite.querySelector('.nicht-dabei-titel')?.textContent).toContain('Nicht dabei?');
    expect(seite.querySelector('button.neu')).toBeTruthy();
    expect(logger.warn).toHaveBeenCalled();
  });

  it('zeigt ohne Treffer den Titel nur ueber einer Liste', () => {
    TestBed.overrideProvider(StatementService, { useValue: { aehnlicheAussagen: () => of([]) } });
    const seite = starten();
    const komponente = fixture.debugElement.children[0].componentInstance as NichtDabeiComponent;
    komponente.ohneTreffer = true;
    fixture.debugElement.children[0].injector.get(ChangeDetectorRef).markForCheck();
    fixture.detectChanges();

    expect(seite.querySelector('.nicht-dabei-titel')).toBeNull();
    expect(seite.querySelector('section')?.getAttribute('aria-labelledby')).toBeNull();
    expect(seite.querySelector('button.neu')).toBeTruthy();
  });

  function ohneTreffer(): void {
    const komponente = fixture.debugElement.children[0].componentInstance as NichtDabeiComponent;
    komponente.ohneTreffer = true;
    fixture.debugElement.children[0].injector.get(ChangeDetectorRef).markForCheck();
    fixture.detectChanges();
  }

  it('nennt ohne Treffer die Zahl der Antworten an der aehnlichen Aussage (#617)', () => {
    const seite = starten();
    expect(seite.querySelector('.antworten-zahl')).withContext('mit Treffern nicht').toBeNull();
    ohneTreffer();
    const zahlen = Array.from(seite.querySelectorAll('.antworten-zahl')).map((e) => (e.textContent ?? '').trim());
    expect(zahlen).toEqual(['2 Antworten', '1 Antwort']);
  });

  it('zeigt ohne Antworten keine Zahl', () => {
    TestBed.overrideProvider(StatementService, {
      useValue: { aehnlicheAussagen: () => of([{ ...AEHNLICH, replysuggestions_count: 0 }]) },
    });
    const seite = starten();
    ohneTreffer();
    expect(seite.querySelector('.antworten-zahl')).toBeNull();
    expect(seite.querySelector('.passt-vielleicht')).toBeTruthy();
  });

  it('bietet ohne Treffer "Selbst beantworten" zuerst fuer die aehnliche Aussage an (#617)', () => {
    const MIT_ID = { ...AEHNLICH, id: '11111111-2222-4333-8444-555555555555' };
    TestBed.overrideProvider(StatementService, { useValue: { aehnlicheAussagen: () => of([MIT_ID]) } });
    const seite = starten();
    expect(seite.querySelector('.aehnliche .selbst-beantworten')).withContext('mit Treffern nicht').toBeNull();
    ohneTreffer();

    const link = seite.querySelector<HTMLAnchorElement>('.aehnliche .selbst-beantworten')!;
    expect(link.textContent).toContain('Selbst beantworten');
    expect(link.getAttribute('href')).toBe('/workflow/add-commentary?aussage=11111111-2222-4333-8444-555555555555');
    expect(link.getAttribute('aria-label')).toBe('Selbst beantworten: Wärmepumpen lohnen sich nicht');
    // Vor dem Knopf fuer die eigene Formulierung
    const alle = Array.from(seite.querySelectorAll('.selbst-beantworten, button.neu'));
    expect(alle[0]).toBe(link);
  });

  it('fragt ohne Treffer "Meintest du …?" statt "Nicht dabei?" (#617)', () => {
    const seite = starten();
    const komponente = fixture.debugElement.children[0].componentInstance as NichtDabeiComponent;
    komponente.ohneTreffer = true;
    fixture.debugElement.children[0].injector.get(ChangeDetectorRef).markForCheck();
    fixture.detectChanges();

    expect(seite.querySelector('.nicht-dabei-titel')?.textContent).toContain('Meintest du …?');
  });

  it('vergibt je Instanz eigene IDs', () => {
    const seite = starten();
    const titel = seite.querySelector('.nicht-dabei-titel')!;
    expect(titel.id).toMatch(/^nicht-dabei-titel-\d+$/);
    expect(seite.querySelector('section')?.getAttribute('aria-labelledby')).toBe(titel.id);
  });
});
