import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ProfilbildDialogComponent, profilbildDialogOeffnen } from './profilbild-dialog.component';
import { PROFILBILD_SCHLUESSEL, ProfilbildService } from '../../services/profilbild.service';

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
    expect(optionen().length).toBe(service.auswahl.length);
    for (const bild of Array.from(element().querySelectorAll('.profilbild-option img'))) {
      expect(bild.getAttribute('alt')?.length).toBeGreaterThan(3);
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
    expect(service.auswahl.find((o) => o.id === gewaehlt[0].value)?.url).toBe(service.bild());
  });

  it('speichert erst beim Uebernehmen, nicht schon beim Anklicken', () => {
    starten();
    optionen()[0].click();
    fixture.detectChanges();

    expect(localStorage.getItem(PROFILBILD_SCHLUESSEL)).toBeNull();

    knopf('Übernehmen')!.click();

    expect(localStorage.getItem(PROFILBILD_SCHLUESSEL)).toBe(service.auswahl[0].id);
    expect(service.gewaehlt()).toBe(service.auswahl[0].id);
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

    service.waehlen(service.auswahl[0].id);
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

    expect(service.gewaehlt()).toBe(service.auswahl[2].id);
  });
});

describe('ProfilbildDialogComponent beim Oeffnen (Abnahme PR 458)', () => {
  let dialog: MatDialog;
  let service: ProfilbildService;

  beforeEach(async () => {
    localStorage.removeItem(PROFILBILD_SCHLUESSEL);
    await TestBed.configureTestingModule({ providers: [provideNoopAnimations()] }).compileComponents();
    dialog = TestBed.inject(MatDialog);
    service = TestBed.inject(ProfilbildService);
    service.setzePerson({ isAuthenticated: true, userId: 'user-001', userName: 'Test User', claims: {} });
    // Weit unten im Raster vorgewaehlt: frueher sprang der Dialog dorthin.
    service.waehlen(service.auswahl[service.auswahl.length - 1].id);
  });

  afterEach(() => {
    dialog.closeAll();
    localStorage.removeItem(PROFILBILD_SCHLUESSEL);
  });

  it('beginnt oben mit Ueberschrift und den ersten Menschen, ohne zum gewaehlten Bild zu scrollen', async () => {
    // Hoehe wie bei 390 px Breite: das Raster passt nicht ganz hinein.
    const ref = profilbildDialogOeffnen(dialog, { height: '600px', maxHeight: '600px' });
    await new Promise((fertig) => setTimeout(fertig, 50));

    const inhalt = document.querySelector('.mat-mdc-dialog-content') as HTMLElement;
    expect(inhalt.scrollHeight).toBeGreaterThan(inhalt.clientHeight);
    expect(inhalt.scrollTop).toBe(0);

    const fokus = document.activeElement as HTMLElement;
    expect(fokus.closest('.profilbild-option')).toBeNull();
    const ganzOben = inhalt.getBoundingClientRect().top;
    const erstes = document.querySelector('.profilbild-option') as HTMLElement;
    expect(erstes.getBoundingClientRect().top - ganzOben).toBeLessThan(150);
    ref.close();
  });

  it('fuehrt mit Tab zum gewaehlten Bild, auch wenn es weit unten steht', async () => {
    profilbildDialogOeffnen(dialog, { height: '600px', maxHeight: '600px' });
    await new Promise((fertig) => setTimeout(fertig, 50));

    const radios = Array.from(document.querySelectorAll('.profilbild-radio')) as HTMLInputElement[];
    const gewaehlt = radios.find((r) => r.checked)!;
    expect(gewaehlt).toBe(radios[radios.length - 1]);
    // Unter den Radioknoepfen einer Gruppe ist nur der gewaehlte per Tab erreichbar.
    expect(radios.filter((r) => r.checked).length).toBe(1);
  });
});
