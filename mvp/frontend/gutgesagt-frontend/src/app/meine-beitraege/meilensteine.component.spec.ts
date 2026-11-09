import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { MeilensteineComponent } from './meilensteine.component';
import { Meilenstein, UsageTrackingService } from '../services/usage-tracking.service';

describe('MeilensteineComponent (#351)', () => {
  let fixture: ComponentFixture<MeilensteineComponent>;

  function meilenstein(felder: Partial<Meilenstein>): Meilenstein {
    return { kennung: 'nutzung-1', name: 'Erste Nutzung durch andere', art: 'wirkung', schwelle: 1, stand: 0, erreicht: false, ...felder };
  }

  function erstellen(meilensteine: Meilenstein[]): HTMLElement {
    TestBed.configureTestingModule({
      imports: [MeilensteineComponent],
      providers: [{ provide: UsageTrackingService, useValue: { getEigeneMeilensteine: () => of(meilensteine) } }],
    });
    fixture = TestBed.createComponent(MeilensteineComponent);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('zeigt nichts ohne Meilensteine (Punkte aus, Startkonto, keine Einwilligung)', () => {
    const element = erstellen([]);

    expect(element.querySelector('.meilensteine')).toBeNull();
  });

  it('zeigt erreichte als Abzeichen und offene mit Stand', () => {
    const element = erstellen([
      meilenstein({ stand: 3, erreicht: true }),
      meilenstein({ kennung: 'nutzung-10', name: '10 Nutzungen', schwelle: 10, stand: 3 }),
    ]);

    const eintraege = Array.from(element.querySelectorAll('.meilenstein'));
    expect(eintraege.length).toBe(2);
    expect(eintraege[0].classList).toContain('erreicht');
    expect(eintraege[0].textContent).toContain('Erste Nutzung durch andere');
    expect(eintraege[0].querySelector('.meilenstein-stand')).toBeNull();
    expect(eintraege[1].classList).not.toContain('erreicht');
    expect(eintraege[1].querySelector('.meilenstein-stand')?.textContent).toContain('3/10');
    expect(element.querySelector('h2')?.textContent).toContain('1 von 2');
  });

  it('sagt, dass nur die Person selbst sie sieht', () => {
    const element = erstellen([meilenstein({})]);

    expect(element.textContent).toContain('Nur du siehst deine Meilensteine.');
  });

  it('nennt den Zustand auch Screenreadern', () => {
    const element = erstellen([meilenstein({ erreicht: true, stand: 1 }), meilenstein({ kennung: 'x', schwelle: 10, stand: 2 })]);

    const versteckt = Array.from(element.querySelectorAll('.visually-hidden')).map((e) => e.textContent?.trim());
    expect(versteckt).toEqual([', erreicht', ', noch nicht erreicht:']);
  });
});
