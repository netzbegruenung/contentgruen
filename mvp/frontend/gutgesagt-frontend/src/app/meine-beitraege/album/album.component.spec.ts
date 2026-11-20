import { ChangeDetectorRef } from '@angular/core';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { BreakpointObserver } from '@angular/cdk/layout';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { provideRouter } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';

import { AlbumComponent, SUCHE_WARTEN_MS } from './album.component';
import { AlbumEintrag, KARTEN_JE_ABSCHNITT, albumEintrag } from './album';
import { ContentResult } from '../../services/dtos/contributionDtos';
import { Thema } from '../../services/dtos/themenDtos';
import { Meilenstein, UsageTrackingService } from '../../services/usage-tracking.service';
import { AuthService } from '../../auth/auth.service';
import { LoggingService } from '../../services/logging.service';
import { VotingService } from '../../services/voting.service';

const THEMEN: Thema[] = [
  { schluessel: 'klima', name: 'Klima', motiv: 'themen/klima.svg' },
  { schluessel: 'wohnen', name: 'Wohnen', motiv: 'themen/wohnen.svg' },
  { schluessel: 'europa', name: 'Europa', motiv: 'themen/europa.svg' },
];

function beitrag(i: number, felder: Partial<ContentResult> & { themen?: Thema[] } = {}): ContentResult {
  const { themen, ...rest } = felder;
  return {
    id: `b${i}`,
    created: `2026-11-01T10:${String(i % 60).padStart(2, '0')}:00`,
    text: `Text ${i}`,
    content_type: 'commentary',
    title: `Behauptung Nummer ${i}`,
    usage_count: 0,
    score: 0,
    aussage: { id: `a${i}`, text: `Aussage ${i}`, themen: themen ?? [THEMEN[i % THEMEN.length]] },
    ...rest,
  };
}

function viele(n: number, felder: (i: number) => Partial<ContentResult> & { themen?: Thema[] } = () => ({})): AlbumEintrag[] {
  return Array.from({ length: n }, (_, i) => albumEintrag(beitrag(i, felder(i))));
}

const MEILENSTEIN: Meilenstein = {
  kennung: 'genutzt-1',
  name: 'Erstmals genutzt',
  untertitel: 'Ausgeflogen',
  beschreibung: '',
  bild: 'meilensteine/vogel.svg',
  bildnachweis: '',
  art: 'wirkung',
  schwelle: 10,
  stand: 6,
  erreicht: false,
};

describe('AlbumComponent', () => {
  let fixture: ComponentFixture<AlbumComponent>;
  let mobil: BehaviorSubject<{ matches: boolean; breakpoints: Record<string, boolean> }>;

  beforeEach(() => {
    mobil = new BehaviorSubject<{ matches: boolean; breakpoints: Record<string, boolean> }>({ matches: false, breakpoints: {} });
    const auth = jasmine.createSpyObj('AuthService', ['getUserInfo', 'login']);
    auth.getUserInfo.and.returnValue({ isAuthenticated: true, userId: 'user-001' });
    auth.userInfo$ = of({ isAuthenticated: true, userId: 'user-001' });
    TestBed.configureTestingModule({
      imports: [AlbumComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: BreakpointObserver, useValue: { observe: () => mobil } },
        { provide: AuthService, useValue: auth },
        { provide: VotingService, useValue: jasmine.createSpyObj('VotingService', ['setLike']) },
        { provide: MatSnackBar, useValue: jasmine.createSpyObj('MatSnackBar', ['open']) },
        { provide: Clipboard, useValue: jasmine.createSpyObj('Clipboard', ['copy']) },
        { provide: UsageTrackingService, useValue: jasmine.createSpyObj('UsageTrackingService', { trackContentUsage: undefined, gepostetBekannt: false }) },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['error', 'debug', 'info', 'warn']) },
        { provide: MatDialog, useValue: jasmine.createSpyObj('MatDialog', ['open']) },
      ],
    });
  });

  function erstellen(eintraege: AlbumEintrag[], meilenstein: Meilenstein | null = null): void {
    fixture = TestBed.createComponent(AlbumComponent);
    fixture.componentRef.setInput('eintraege', eintraege);
    fixture.componentRef.setInput('naechsterMeilenstein', meilenstein);
    fixture.detectChanges();
  }

  const el = (): HTMLElement => fixture.nativeElement;
  const alle = (selektor: string): HTMLElement[] => Array.from(el().querySelectorAll(selektor));
  const text = (selektor: string): string => el().querySelector(selektor)!.textContent!.replace(/\s+/g, ' ').trim();
  const karten = (): HTMLElement[] => alle('app-beitragskarte article');

  describe('Deckel', () => {
    it('zeigt Beitraege, Nutzung mit Zuwachs und Themen, dazu den Wirkungssatz', () => {
      erstellen(viele(4, (i) => ({ usage_count: i, nutzung_letzte_7_tage: i ? 1 : 0 })), MEILENSTEIN);

      expect(alle('.zahl .zahl-wert').map((z) => z.textContent!.trim())).toEqual(['4', '6×', '3']);
      expect(text('[data-testid="zahl-genutzt"]')).toContain('+3 diese Woche');
      expect(text('.wirkung')).toBe('Deine 4 Beiträge wurden 6-mal genutzt, 3 davon diese Woche.');
      expect(el().querySelector('.deckel--meilenstein-gross')).toBeNull();
    });

    it('zeigt bei 0 Nutzungen statt „0× genutzt“ den naechsten Meilenstein gross mit Balken', () => {
      erstellen(viele(4), MEILENSTEIN);

      expect(el().querySelector('[data-testid="zahl-genutzt"]')).toBeNull();
      expect(el().querySelector('.deckel--meilenstein-gross')).not.toBeNull();
      expect(text('.naechster-name')).toBe('Erstmals genutzt');
      expect(text('.naechster-stand')).toBe('6 von 10 · noch 4');
      const balken = el().querySelector('[role="progressbar"]')!;
      expect(balken.getAttribute('aria-valuenow')).toBe('6');
      expect(balken.getAttribute('aria-valuemax')).toBe('10');
      expect(text('[data-testid="nutzung-leer"]')).toContain('Genutzt heißt');
    });

    it('zeigt ohne Meilensteine (keine Einwilligung) auch bei 0 die Zahl', () => {
      erstellen(viele(4), null);

      expect(text('[data-testid="zahl-genutzt"]')).toContain('0×');
      expect(el().querySelector('[data-testid="naechster-meilenstein"]')).toBeNull();
    });
  });

  describe('Suche', () => {
    it('gibt es bis 6 Beitraege nicht, ab 7 mit der Zahl im Namen', () => {
      erstellen(viele(6));
      expect(el().querySelector('[role="search"]')).toBeNull();

      erstellen(viele(7));
      expect(el().querySelector('[role="search"]')).not.toBeNull();
      expect(text('.feld--suche .feld-name')).toBe('In deinen 7 Beiträgen suchen');
      expect(text('[data-testid="treffer"]')).toBe('7 Beiträge · nach Thema, meistgenutzte zuerst');
    });

    it('filtert beim Tippen nach kurzer Pause und nennt die Treffer', fakeAsync(() => {
      erstellen(viele(10));
      const feld = el().querySelector('input[type="search"]') as HTMLInputElement;

      feld.value = 'nummer 3';
      feld.dispatchEvent(new Event('input'));
      tick(SUCHE_WARTEN_MS);
      fixture.detectChanges();

      expect(text('[data-testid="treffer"]')).toBe('1 von 10 Beiträgen');
      expect(karten().length).toBe(1);
    }));

    it('sagt, wenn nichts passt, und setzt auf Wunsch alles zurueck', fakeAsync(() => {
      erstellen(viele(10));
      const feld = el().querySelector('input[type="search"]') as HTMLInputElement;
      feld.value = 'gibtesnicht';
      feld.dispatchEvent(new Event('input'));
      tick(SUCHE_WARTEN_MS);
      fixture.detectChanges();

      expect(text('[data-testid="nichts-gefunden"]')).toContain('Nichts gefunden zu „gibtesnicht“.');
      (el().querySelector('.nichts .knopf-umriss') as HTMLButtonElement).click();
      fixture.detectChanges();

      expect(el().querySelector('[data-testid="nichts-gefunden"]')).toBeNull();
      expect(text('[data-testid="treffer"]')).toBe('10 Beiträge · nach Thema, meistgenutzte zuerst');
    }));

    it('filtert mit „genutzt“ und oeffnet dann alle Abschnitte mit Treffern', () => {
      erstellen(viele(12, (i) => ({ usage_count: i % 4 === 0 ? 2 : 0 })));
      const genutzt = alle('.filter-zeile .chip')[0] as HTMLButtonElement;

      genutzt.click();
      fixture.detectChanges();

      expect(genutzt.getAttribute('aria-pressed')).toBe('true');
      expect(text('[data-testid="treffer"]')).toBe('3 von 12 Beiträgen');
      expect(alle('.abschnitt-knopf').every((k) => k.getAttribute('aria-expanded') === 'true')).toBeTrue();
    });

    it('klappt am Handy Thema, Stil und genutzt in „Filter“ ein, sobald die Leiste klebt', () => {
      mobil.next({ matches: true, breakpoints: {} });
      erstellen(viele(10));
      const komponente = fixture.componentInstance;

      expect(el().querySelector('.filter-knopf')).toBeNull();
      komponente.klebt = true;
      fixture.debugElement.injector.get(ChangeDetectorRef).markForCheck();
      fixture.detectChanges();

      const knopf = el().querySelector('.filter-knopf') as HTMLButtonElement;
      expect((el().querySelector('#album-filter') as HTMLElement).hidden).toBeTrue();
      expect(el().querySelector('input[type="search"]')).not.toBeNull();
      knopf.click();
      fixture.detectChanges();
      expect(knopf.getAttribute('aria-expanded')).toBe('true');
      expect((el().querySelector('#album-filter') as HTMLElement).hidden).toBeFalse();
    });
  });

  describe('Abschnitte', () => {
    it('stehen bis 3 Beitraege nicht da, die Karten dann untereinander', () => {
      erstellen(viele(3));

      expect(alle('.abschnitt').length).toBe(0);
      expect(karten().length).toBe(3);
    });

    it('zeigen je Thema Motiv und Fortschritt; nur der erste ist offen', () => {
      erstellen(viele(9, (i) => ({ usage_count: i === 0 ? 5 : 0 })));

      const koepfe = alle('.abschnitt-knopf');
      expect(koepfe.map((k) => k.querySelector('.abschnitt-name')!.textContent!.trim())).toEqual(['Klima', 'Wohnen', 'Europa']);
      expect(koepfe.map((k) => k.getAttribute('aria-expanded'))).toEqual(['true', 'false', 'false']);
      expect(koepfe[0].querySelector('.abschnitt-stand')!.textContent!.trim()).toBe('1 von 3 genutzt');
      // Motiv rein dekorativ: der Name steht daneben
      const motiv = koepfe[2].querySelector('.abschnitt-motiv') as HTMLElement;
      expect(motiv.getAttribute('aria-hidden')).toBe('true');
      expect(motiv.querySelector('img')!.getAttribute('src')).toBe('themen/europa.svg');
      expect(motiv.querySelector('img')!.getAttribute('alt')).toBe('');
      expect(karten().length).toBe(3);
    });

    it('zeichnen bei 300 Beitraegen anfangs hoechstens sechs Karten', () => {
      erstellen(viele(300));

      expect(karten().length).toBe(KARTEN_JE_ABSCHNITT);
      expect(text('.mehr-zeigen')).toBe('Alle 100 zu Klima zeigen');
    });

    it('klappen auf und zu und zeigen auf Wunsch alle Karten, der Fokus geht auf die erste neue', () => {
      erstellen(viele(30));
      const zweiter = alle('.abschnitt-knopf')[1] as HTMLButtonElement;

      zweiter.click();
      fixture.detectChanges();
      expect(zweiter.getAttribute('aria-expanded')).toBe('true');
      expect(karten().length).toBe(2 * KARTEN_JE_ABSCHNITT);

      (el().querySelector('.mehr-zeigen button') as HTMLButtonElement).click();
      fixture.detectChanges();
      expect(karten().length).toBe(10 + KARTEN_JE_ABSCHNITT);
      expect(document.activeElement?.classList).toContain('platz');

      zweiter.click();
      fixture.detectChanges();
      expect(zweiter.getAttribute('aria-expanded')).toBe('false');
    });

    it('stellt Beitraege ohne Thema in einen eigenen Abschnitt am Ende', () => {
      erstellen([...viele(4), albumEintrag(beitrag(99, { aussage: null }))]);

      const namen = alle('.abschnitt-name').map((n) => n.textContent!.trim());
      expect(namen[namen.length - 1]).toBe('Ohne Thema');
    });
  });

  describe('Karten', () => {
    it('tragen bei Nutzung die gruene Lasche, fuer Screenreader verborgen', () => {
      erstellen(viele(4, (i) => ({ usage_count: i === 0 ? 7 : 0 })));

      const laschen = alle('.lasche');
      expect(laschen.length).toBe(1);
      expect(laschen[0].textContent!.trim()).toBe('🌱 7× genutzt');
      expect(laschen[0].getAttribute('aria-hidden')).toBe('true');
    });

    it('zeigen Ändern, Teilen als Hauptknopf und ⋮, ohne Abstimmen', () => {
      erstellen(viele(4));
      const karte = karten()[0];

      expect(karte.querySelector('.aendern-knopf')).not.toBeNull();
      expect(karte.querySelector('.teilen-haupt')!.textContent).toContain('Teilen');
      expect(karte.querySelector('.menue-knopf')).not.toBeNull();
      expect(karte.querySelector('.stimme-knopf')).toBeNull();
      expect(karte.textContent).toContain('Antwort auf:');
    });

    it('melden Ändern und Löschen an die Seite', () => {
      erstellen(viele(4));
      const geaendert = jasmine.createSpy('aendern');
      fixture.componentInstance.aendern.subscribe(geaendert);

      (karten()[0].querySelector('.aendern-knopf') as HTMLButtonElement).click();

      expect(geaendert).toHaveBeenCalledWith(jasmine.objectContaining({ id: 'b3' }));
    });
  });
});
