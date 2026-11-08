import { Component } from '@angular/core';
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
      <button class="neu">Neu anlegen</button>
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

  const ANGEMELDET: UserInfo = { isAuthenticated: true, userId: 'u-1', userName: 'Test', claims: null };

  function starten(angemeldet: UserInfo | null = ANGEMELDET): HTMLElement {
    statementService = jasmine.createSpyObj('StatementService', ['aussageVorschlaege']);
    statementService.aussageVorschlaege.and.returnValue(of([AEHNLICH, ZWEITE]));
    nutzer = new BehaviorSubject<UserInfo | null>(angemeldet);
    TestBed.configureTestingModule({
      imports: [GastgeberComponent],
      providers: [
        provideRouter([]),
        { provide: StatementService, useValue: statementService },
        { provide: AuthService, useValue: { userInfo$: nutzer.asObservable() } },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['warn', 'error', 'debug']) },
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
    expect(seite.querySelector('button.neu')?.textContent).toContain('Neu anlegen');
    expect(statementService.aussageVorschlaege).toHaveBeenCalledOnceWith('Wärmepumpen sind zu teuer');
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

  it('fragt fuer Besucher nicht nach (der Endpunkt waere 401 und fuehrte auf /login)', () => {
    const seite = starten({ isAuthenticated: false, userId: null, userName: null, claims: null });

    expect(statementService.aussageVorschlaege).not.toHaveBeenCalled();
    expect(seite.querySelector('.aehnliche')).toBeNull();
    expect(seite.querySelector('button.neu')).withContext('Neu anlegen bleibt').toBeTruthy();
  });

  it('fragt nach dem Anmelden nach und bei neuem Suchtext neu', () => {
    starten(null);
    expect(statementService.aussageVorschlaege).not.toHaveBeenCalled();

    nutzer.next(ANGEMELDET);
    fixture.detectChanges();
    expect(statementService.aussageVorschlaege).toHaveBeenCalledTimes(1);

    fixture.componentInstance.suchtext = 'Tempolimit bringt nichts';
    fixture.detectChanges();
    expect(statementService.aussageVorschlaege).toHaveBeenCalledTimes(2);
    expect(statementService.aussageVorschlaege.calls.mostRecent().args[0]).toBe('Tempolimit bringt nichts');
  });

  it('fragt bei zu kurzem Suchtext nicht nach', () => {
    statementService = jasmine.createSpyObj('StatementService', ['aussageVorschlaege']);
    const seite = starten();
    statementService.aussageVorschlaege.calls.reset();
    fixture.componentInstance.suchtext = ' a ';
    fixture.detectChanges();

    expect(statementService.aussageVorschlaege).not.toHaveBeenCalled();
    expect(seite.querySelector('.aehnliche')).toBeNull();
  });

  it('bleibt ohne Liste nutzbar, wenn die aehnlichen Aussagen nicht ladbar sind', () => {
    TestBed.overrideProvider(StatementService, {
      useValue: { aussageVorschlaege: () => throwError(() => new Error('500')) },
    });
    const seite = starten();

    expect(seite.querySelector('.aehnliche')).toBeNull();
    expect(seite.querySelector('.nicht-dabei-titel')?.textContent).toContain('Nicht dabei?');
    expect(seite.querySelector('button.neu')).toBeTruthy();
  });
});
