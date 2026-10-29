import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { MatDialogRef } from '@angular/material/dialog';

import { HelpDialogComponent } from './help-dialog.component';

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
});
