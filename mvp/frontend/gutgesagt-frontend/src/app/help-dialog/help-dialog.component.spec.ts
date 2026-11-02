import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';

import { HelpDialogComponent, hilfeOeffnen } from './help-dialog.component';

describe('HelpDialogComponent', () => {
  let component: HelpDialogComponent;
  let fixture: ComponentFixture<HelpDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HelpDialogComponent, HttpClientTestingModule],
      providers: [
        {
          provide: MatDialogRef,
          useValue: {
            close: jasmine.createSpy('close')
          }
        }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(HelpDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // Design-Audit A7 und Hilfe-Umbau (#512): mobil oeffnete die Hilfe ans Ende
  // gescrollt (Fokus auf dem ersten Link). Jetzt eine Seitenleiste rechts, volle
  // Hoehe, auf dem Handy Vollbild, Fokus auf dem Dialog selbst.
  describe('als Seitenleiste', () => {
    it('oeffnet rechts, volle Hoehe, 560 px breit, auf dem Handy ganze Breite, oben', () => {
      const dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);

      hilfeOeffnen(dialog);

      expect(dialog.open).toHaveBeenCalledWith(
        HelpDialogComponent,
        jasmine.objectContaining({
          autoFocus: 'dialog',
          position: { top: '0', right: '0' },
          width: '560px',
          maxWidth: '100vw',
          height: '100%',
          maxHeight: '100%',
          panelClass: 'hilfe-seitenleiste',
        }),
      );
    });

    it('hat einen festen Kopf mit Titel und Schliessen, nur der Inhalt scrollt', () => {
      const kopf: HTMLElement = fixture.nativeElement.querySelector('.hilfe-kopf');

      expect(kopf.querySelector('h2')!.textContent!.trim()).toBe('Hilfe zur Nutzung');
      expect(kopf.querySelector('button[mat-dialog-close]')!.textContent!.trim()).toBe('Schließen');
      expect(fixture.nativeElement.querySelector('mat-dialog-actions')).toBeNull();
      const inhalt = fixture.nativeElement.querySelector('mat-dialog-content') as HTMLElement;
      expect(getComputedStyle(inhalt).maxHeight).toBe('none');
      expect(getComputedStyle(inhalt).overflowY).toBe('auto');
    });
  });

  it('nennt die sechs Schreibregeln', () => {
    const regeln = fixture.nativeElement.querySelectorAll('.schreibregeln li');

    expect(regeln.length).toBe(6);
    expect(regeln[0].textContent).toContain('Unentschiedenen');
    expect(regeln[4].textContent).toContain('Erfinde nichts');
  });

  it('sagt, dass nicht jede Aussage eine Antwort braucht', () => {
    expect(fixture.nativeElement.querySelector('.nicht-jede-aussage').textContent).toContain(
      'Nicht jede Aussage braucht eine Antwort',
    );
  });

  it('nennt erfundene Erlebnisse oder Zahlen als Grund zu melden', () => {
    expect(fixture.nativeElement.querySelector('.erfundenes-melden').textContent).toContain(
      'Erfundene Erlebnisse oder Zahlen',
    );
  });

  it('verweist auf den Meldegrund „Erfunden oder sachlich falsch“', () => {
    expect(fixture.nativeElement.querySelector('.erfundenes-melden').textContent).toContain(
      '„Erfunden oder sachlich falsch“',
    );
  });
});
