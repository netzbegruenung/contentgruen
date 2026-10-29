import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef } from '@angular/material/dialog';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ProfilbildDialogComponent } from './profilbild-dialog.component';
import { INITIALEN, PROFILBILD_SCHLUESSEL, ProfilbildService } from '../../services/profilbild.service';

describe('ProfilbildDialogComponent', () => {
  let fixture: ComponentFixture<ProfilbildDialogComponent>;
  let service: ProfilbildService;
  let dialogRef: jasmine.SpyObj<MatDialogRef<ProfilbildDialogComponent>>;

  function element(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  function optionen(): HTMLInputElement[] {
    return Array.from(element().querySelectorAll('input[type="radio"]'));
  }

  function knopf(text: string): HTMLButtonElement | undefined {
    return Array.from(element().querySelectorAll('button')).find((b) => b.textContent?.includes(text));
  }

  function starten(): void {
    fixture = TestBed.createComponent(ProfilbildDialogComponent);
    fixture.detectChanges();
  }

  beforeEach(async () => {
    localStorage.removeItem(PROFILBILD_SCHLUESSEL);
    dialogRef = jasmine.createSpyObj('MatDialogRef', ['close']);
    await TestBed.configureTestingModule({
      imports: [ProfilbildDialogComponent],
      providers: [provideNoopAnimations(), { provide: MatDialogRef, useValue: dialogRef }],
    }).compileComponents();
    service = TestBed.inject(ProfilbildService);
    service.setzePerson({ isAuthenticated: true, userId: 'user-001', userName: 'Test User', claims: {} });
  });

  afterEach(() => localStorage.removeItem(PROFILBILD_SCHLUESSEL));

  it('zeigt alle Bilder als Optionen einer Gruppe, jedes mit Alternativtext', () => {
    starten();

    const gruppe = element().querySelector('[role="radiogroup"]');
    expect(gruppe?.getAttribute('aria-label')).toBe('Profilbild');
    expect(optionen().length).toBe(service.auswahl().length);
    for (const bild of Array.from(element().querySelectorAll('.profilbild-option img'))) {
      expect(bild.getAttribute('alt')?.length).toBeGreaterThan(3);
      expect(bild.getAttribute('loading')).toBe('lazy');
    }
  });

  it('teilt nicht nach Geschlecht ein und beschriftet nicht danach', () => {
    starten();

    const text = element().textContent ?? '';
    const alts = Array.from(element().querySelectorAll('img')).map((b) => b.getAttribute('alt') ?? '');
    for (const t of [text, ...alts]) {
      expect(t).not.toMatch(/female|male|weiblich|männlich|Frauen|Männer/i);
    }
    expect(element().querySelectorAll('[role="radiogroup"]').length).toBe(1);
  });

  it('markiert das angezeigte Bild als ausgewaehlt', () => {
    starten();

    const gewaehlt = optionen().filter((o) => o.checked);
    expect(gewaehlt.length).toBe(1);
    expect(service.auswahl().find((o) => o.id === gewaehlt[0].value)?.url).toBe(service.bild());
  });

  it('speichert erst beim Uebernehmen, nicht schon beim Anklicken', () => {
    starten();
    optionen()[0].click();
    fixture.detectChanges();

    expect(localStorage.getItem(PROFILBILD_SCHLUESSEL)).toBeNull();

    knopf('Übernehmen')!.click();

    expect(localStorage.getItem(PROFILBILD_SCHLUESSEL)).toBe(INITIALEN);
    expect(service.gewaehlt()).toBe(INITIALEN);
    expect(dialogRef.close).toHaveBeenCalled();
  });

  it('Abbrechen laesst alles, wie es war', () => {
    starten();
    optionen()[0].click();
    knopf('Abbrechen')!.click();

    expect(service.gewaehlt()).toBeNull();
    expect(localStorage.getItem(PROFILBILD_SCHLUESSEL)).toBeNull();
    expect(dialogRef.close).toHaveBeenCalled();
  });

  it('bietet Zuruecksetzen nur an, wenn es eine eigene Wahl gibt, und loescht sie', () => {
    starten();
    expect(knopf('Zurücksetzen')).toBeUndefined();

    service.waehlen(INITIALEN);
    fixture.destroy();
    starten();
    knopf('Zurücksetzen')!.click();

    expect(service.gewaehlt()).toBeNull();
    expect(localStorage.getItem(PROFILBILD_SCHLUESSEL)).toBeNull();
    expect(dialogRef.close).toHaveBeenCalled();
  });

  it('ist mit der Tastatur bedienbar: echte Radioknoepfe mit gemeinsamem Namen', () => {
    starten();

    const namen = new Set(optionen().map((o) => o.name));
    expect(namen.size).toBe(1);
    optionen()[2].dispatchEvent(new Event('change'));
    optionen()[2].checked = true;
    optionen()[2].dispatchEvent(new Event('change'));
    fixture.detectChanges();
    knopf('Übernehmen')!.click();

    expect(service.gewaehlt()).toBe(service.auswahl()[2].id);
  });
});
