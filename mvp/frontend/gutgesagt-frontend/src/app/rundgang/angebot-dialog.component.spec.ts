import { TestBed, fakeAsync, flush } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { AngebotWahl, angebotOeffnen } from './angebot-dialog.component';
import { MITMACHEN_ANGEBOT, WILLKOMMEN } from './rundgang-daten';

describe('AngebotDialogComponent', () => {
  let dialog: MatDialog;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideNoopAnimations()] });
    dialog = TestBed.inject(MatDialog);
  });

  afterEach(() => dialog.closeAll());

  const fenster = () => document.querySelector('app-angebot-dialog') as HTMLElement;
  const container = () => document.querySelector('mat-dialog-container') as HTMLElement;
  const knoepfe = () => Array.from(fenster().querySelectorAll('button')) as HTMLButtonElement[];

  it('begrüßt mit Daumen, einem Satz und zwei gleichwertigen Knöpfen', fakeAsync(() => {
    angebotOeffnen(dialog, WILLKOMMEN);
    flush();
    expect(fenster().querySelector('img')!.getAttribute('src')).toBe('marke/daumen.svg');
    expect(fenster().querySelector('h2')!.textContent).toBe(WILLKOMMEN.titel);
    expect(fenster().querySelector('.satz')!.textContent).toBe(WILLKOMMEN.satz);
    expect(knoepfe().map((k) => k.textContent!.trim())).toEqual(['Rundgang starten', 'Später']);
    // gleichwertig: dieselbe Gestaltung, keiner vorbelegt
    expect(knoepfe().map((k) => k.className)).toEqual(['rundgang-knopf umriss', 'rundgang-knopf umriss']);
    expect(knoepfe()).not.toContain(document.activeElement as HTMLButtonElement);
  }));

  it('ist ein modaler Dialog mit Titel und Beschreibung für Screenreader', fakeAsync(() => {
    angebotOeffnen(dialog, MITMACHEN_ANGEBOT);
    flush();
    const c = container();
    expect(c.getAttribute('aria-modal')).toBe('true');
    expect(document.getElementById(c.getAttribute('aria-labelledby')!)!.textContent).toBe(MITMACHEN_ANGEBOT.titel);
    expect(document.getElementById(c.getAttribute('aria-describedby')!)!.textContent).toBe(MITMACHEN_ANGEBOT.satz);
  }));

  it('liefert die Wahl des Knopfs', fakeAsync(() => {
    let wahl: AngebotWahl | undefined;
    angebotOeffnen(dialog, WILLKOMMEN).afterClosed().subscribe((w) => (wahl = w));
    flush();
    knoepfe()[0].click();
    flush();
    expect(wahl).toBe('starten');
  }));

  it('schließt mit Escape ohne Wahl (gilt als „Später“)', fakeAsync(() => {
    let zu = false;
    let wahl: AngebotWahl | undefined = 'starten';
    angebotOeffnen(dialog, WILLKOMMEN)
      .afterClosed()
      .subscribe((w) => {
        zu = true;
        wahl = w;
      });
    flush();
    container().dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', keyCode: 27, bubbles: true }));
    flush();
    expect(zu).toBeTrue();
    expect(wahl).toBeUndefined();
  }));
});
