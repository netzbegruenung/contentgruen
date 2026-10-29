import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Observable, of } from 'rxjs';
import { OftGenutztComponent } from './oft-genutzt.component';
import { OftGenutztAntwort, UsageTrackingService } from '../services/usage-tracking.service';
import { KartenlisteComponent } from '../beitragskarte/kartenliste.component';
import { ResultCarouselComponent } from '../result-carousel/result-carousel.component';
import { BeitragskarteStubComponent } from '../beitragskarte/beitragskarte.stub';

describe('OftGenutztComponent', () => {
  let fixture: ComponentFixture<OftGenutztComponent>;
  let usage: jasmine.SpyObj<UsageTrackingService>;
  let mobil: boolean;

  function beitraege(): any[] {
    return [
      { id: 'k-1', result_type: 'commentary', title: 'Wärmepumpe lohnt sich auch im Altbau', usage_count: 9, recent_uses: 6 },
      { id: 'h-1', result_type: 'generic_text', title: 'Windkraft kostet weniger als Kohle', usage_count: 4, recent_uses: 3 },
      { id: 'p-1', result_type: 'post', title: 'Tempolimit', url: 'https://social.example/p/1', usage_count: 2, recent_uses: 2 },
    ];
  }

  function erstellen(antwort: Observable<OftGenutztAntwort>): void {
    usage.getOftGenutzt.and.returnValue(antwort);
    fixture = TestBed.createComponent(OftGenutztComponent);
    fixture.detectChanges();
  }

  function alle(selektor: string): Element[] {
    return Array.from(fixture.nativeElement.querySelectorAll(selektor));
  }

  beforeEach(async () => {
    mobil = false;
    usage = jasmine.createSpyObj('UsageTrackingService', ['getOftGenutzt']);

    await TestBed.configureTestingModule({
      imports: [OftGenutztComponent],
      providers: [
        { provide: UsageTrackingService, useValue: usage },
        { provide: BreakpointObserver, useValue: { observe: () => of({ matches: mobil, breakpoints: {} }) } },
      ],
    })
      .overrideComponent(KartenlisteComponent, { set: { imports: [CommonModule, BeitragskarteStubComponent] } })
      .overrideComponent(ResultCarouselComponent, {
        set: { imports: [CommonModule, MatIconModule, MatTooltipModule, BeitragskarteStubComponent] },
      })
      .compileComponents();
  });

  it('zeigt bei genug Nutzung den Bereich mit Ueberschrift und je einer Karte', () => {
    erstellen(of({ results: beitraege() }));

    const bereich: HTMLElement = fixture.nativeElement.querySelector('section.oft-genutzt');
    expect(bereich).toBeTruthy();
    expect(bereich.querySelector('h2')!.textContent!.trim()).toBe('Diese Woche oft genutzt');
    expect(alle('app-beitragskarte').length).toBe(3);
  });

  it('baut die Karten in der Reihenfolge der Nutzung, fuer jeden Beitragstyp', () => {
    erstellen(of({ results: beitraege() }));

    expect(fixture.componentInstance.karten.map((karte) => [karte.id, karte.typ, karte.titel])).toEqual([
      ['k-1', 'commentary', 'Wärmepumpe lohnt sich auch im Altbau'],
      ['h-1', 'generictext', 'Windkraft kostet weniger als Kohle'],
      ['p-1', 'post', 'Tempolimit'],
    ]);
  });

  it('zeigt bei zu wenig Nutzung keinen Bereich, auch keinen Leer-Hinweis', () => {
    erstellen(of({ results: [] }));

    expect(fixture.nativeElement.querySelector('section')).toBeNull();
    expect(fixture.nativeElement.textContent.trim()).toBe('');
  });

  it('zeigt mobil eine Liste statt des Karussells', () => {
    mobil = true;
    erstellen(of({ results: beitraege() }));

    expect(alle('app-kartenliste').length).toBe(1);
    expect(alle('app-result-carousel').length).toBe(0);
  });
});
