import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Clipboard } from '@angular/cdk/clipboard';
import { MAT_BOTTOM_SHEET_DATA, MatBottomSheetRef } from '@angular/material/bottom-sheet';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';

import { BeitragSheetComponent, WISCH_SCHWELLE } from './beitrag-sheet.component';
import { KartenDaten } from './karten-daten';
import { AuthService } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { VotingService } from '../services/voting.service';

describe('BeitragSheetComponent', () => {
  let fixture: ComponentFixture<BeitragSheetComponent>;
  let sheet: jasmine.SpyObj<MatBottomSheetRef<BeitragSheetComponent>>;

  const daten: KartenDaten = {
    id: 'b-1',
    typ: 'commentary',
    titel: 'Wärmepumpen rechnen sich im Altbau',
    text: 'Mit Förderung liegt die Wärmepumpe nach zehn Jahren vorn.',
    erstellt: '2026-09-12T10:00:00',
    autor: 'user-001',
    autorName: null,
    nutzung: 3,
    quellen: [{ id: 'r-1', url: 'https://example.org/studie', beschreibung: 'Studie' }],
  };

  beforeEach(() => {
    sheet = jasmine.createSpyObj('MatBottomSheetRef', ['dismiss']);
    const auth = jasmine.createSpyObj('AuthService', ['getUserInfo', 'login']);
    auth.getUserInfo.and.returnValue({ isAuthenticated: true, userId: 'user-001' });

    TestBed.configureTestingModule({
      imports: [BeitragSheetComponent, NoopAnimationsModule],
      providers: [
        { provide: MAT_BOTTOM_SHEET_DATA, useValue: daten },
        { provide: MatBottomSheetRef, useValue: sheet },
        { provide: VotingService, useValue: jasmine.createSpyObj('VotingService', ['setLike']) },
        { provide: MatSnackBar, useValue: jasmine.createSpyObj('MatSnackBar', ['open']) },
        { provide: AuthService, useValue: auth },
        { provide: Clipboard, useValue: jasmine.createSpyObj('Clipboard', ['copy']) },
        { provide: UsageTrackingService, useValue: jasmine.createSpyObj('UsageTrackingService', ['trackContentUsage']) },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['error', 'debug', 'info', 'warn']) },
        { provide: MatDialog, useValue: jasmine.createSpyObj('MatDialog', ['open']) },
      ],
    });
    fixture = TestBed.createComponent(BeitragSheetComponent);
    fixture.detectChanges();
  });

  function wischen(vonY: number, nachY: number): void {
    const host: HTMLElement = fixture.nativeElement;
    const beruehrung = (y: number) => new Touch({ identifier: 1, target: host, clientY: y });
    host.dispatchEvent(new TouchEvent('touchstart', { touches: [beruehrung(vonY)], bubbles: true }));
    host.dispatchEvent(new TouchEvent('touchend', { changedTouches: [beruehrung(nachY)], bubbles: true }));
  }

  it('zeigt den Beitrag als volle Karte mit Kopieren, Menue und Herkunft, ohne Abstimmen', () => {
    const karte: HTMLElement = fixture.nativeElement.querySelector('app-beitragskarte article');

    expect(karte.classList).toContain('karte--voll');
    expect(karte.querySelector('app-karten-aktionen')).not.toBeNull();
    expect(karte.querySelectorAll('.stimme-knopf').length).toBe(0);
    expect(karte.querySelector('.kopieren-knopf')).not.toBeNull();
    expect(karte.querySelector('.menue-knopf')).not.toBeNull();
    expect(karte.querySelector('.quelle-link')!.getAttribute('href')).toBe('https://example.org/studie');
    expect(karte.getAttribute('role')).toBeNull();
  });

  it('schliesst beim Wisch nach unten, nicht bei einem kurzen', () => {
    wischen(100, 100 + WISCH_SCHWELLE - 10);
    expect(sheet.dismiss).not.toHaveBeenCalled();

    wischen(100, 100 + WISCH_SCHWELLE + 20);
    expect(sheet.dismiss).toHaveBeenCalledTimes(1);
  });
});
