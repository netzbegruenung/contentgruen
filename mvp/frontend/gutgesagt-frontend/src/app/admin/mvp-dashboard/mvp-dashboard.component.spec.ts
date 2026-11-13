import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { KENNZAHLEN_NACHLADEN_MS, MvpDashboardComponent } from './mvp-dashboard.component';
import { MetricsService, MVPMetrics } from '../../services/metrics.service';
import { NachladeHinweisComponent } from '../../shared/components/nachlade-hinweis/nachlade-hinweis.component';

const KENNZAHLEN: MVPMetrics = {
  timestamp: '2026-11-13T10:00:00Z',
  period_days: 7,
  daily_active_users: 12,
  searches_per_user: 2.5,
  content_created_this_week: 4,
  usage_counter_total: 100,
  usage_counter_current_week: 10,
  usage_counter_previous_week: 8,
  usage_counter_trend: 'increasing',
  helpful_rate: 80,
  helpful_like_count: 8,
  helpful_dislike_count: 2,
  helpful_total_votes: 10,
};

describe('MvpDashboardComponent', () => {
  let fixture: ComponentFixture<MvpDashboardComponent>;
  let metrics: jasmine.SpyObj<MetricsService>;

  beforeEach(() => {
    metrics = jasmine.createSpyObj('MetricsService', ['getMVPDashboard']);
    metrics.getMVPDashboard.and.returnValue(of(KENNZAHLEN));
    TestBed.configureTestingModule({
      imports: [MvpDashboardComponent, NoopAnimationsModule],
      providers: [{ provide: MetricsService, useValue: metrics }],
    });
    // Die Listen darunter (Bilanz, Feedback …) haben eigene Specs; hier nur die Kennzahlen.
    TestBed.overrideComponent(MvpDashboardComponent, {
      set: {
        imports: [CommonModule, MatCardModule, MatIconModule, MatTooltipModule, NachladeHinweisComponent],
        schemas: [CUSTOM_ELEMENTS_SCHEMA],
      },
    });
  });

  it('macht die Erklaerungen antippbar und beschriftet, statt nur per Hovern', () => {
    fixture = TestBed.createComponent(MvpDashboardComponent);
    fixture.detectChanges();

    const knoepfe = Array.from(fixture.nativeElement.querySelectorAll('button.info-icon')) as HTMLButtonElement[];
    expect(knoepfe.length).toBe(5);
    expect(knoepfe.every((knopf) => knopf.getAttribute('aria-label') === 'So wird gezählt')).toBeTrue();
    expect(knoepfe.every((knopf) => knopf.type === 'button')).toBeTrue();
  });

  it('laedt nach einem Fehler weiter nach, statt fuer immer stehen zu bleiben', fakeAsync(() => {
    spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
    metrics.getMVPDashboard.and.returnValue(throwError(() => new Error('weg')));
    fixture = TestBed.createComponent(MvpDashboardComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Kennzahlen gerade nicht erreichbar, neuer Versuch in Kürze');

    metrics.getMVPDashboard.and.returnValue(of(KENNZAHLEN));
    tick(KENNZAHLEN_NACHLADEN_MS);
    fixture.detectChanges();

    expect(fixture.componentInstance.metrics).toEqual(KENNZAHLEN);
    expect(fixture.nativeElement.textContent).not.toContain('nicht erreichbar');
    fixture.destroy();
  }));

  it('laedt beim Zurueckkehren auf den Reiter sofort nach', () => {
    spyOnProperty(document, 'visibilityState', 'get').and.returnValue('visible');
    fixture = TestBed.createComponent(MvpDashboardComponent);
    fixture.detectChanges();

    document.dispatchEvent(new Event('visibilitychange'));

    expect(metrics.getMVPDashboard).toHaveBeenCalledTimes(2);
    fixture.destroy();
  });
});
