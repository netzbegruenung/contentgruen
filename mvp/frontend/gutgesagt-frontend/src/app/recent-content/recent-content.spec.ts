import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { of } from 'rxjs';
import { RecentContentComponent, TEASER_ANZAHL } from './recent-content.component';
import { ContentService } from '../services/content.service';
import { LoggingService } from '../services/logging.service';
import { KartenlisteComponent } from '../beitragskarte/kartenliste.component';
import { ResultCarouselComponent } from '../result-carousel/result-carousel.component';
import { BeitragskarteStubComponent } from '../beitragskarte/beitragskarte.stub';

describe('RecentContentComponent', () => {
  let component: RecentContentComponent;
  let fixture: ComponentFixture<RecentContentComponent>;
  let contentService: jasmine.SpyObj<ContentService>;
  let mobil: boolean;

  function eintraege(anzahl: number): any[] {
    return Array.from({ length: anzahl }, (_, i) => ({
      id: `c-${i}`,
      result_type: i % 2 ? 'generictext' : 'commentary',
      content_type: i % 2 ? 'generic_text' : 'commentary',
      title: `Titel ${i}`,
      text: 'Text',
      created: '2026-09-13T12:00:00Z',
      references: [],
      usage_count: 0,
    }));
  }

  function erstellen(results: any[] = []): void {
    contentService.getRecentContent.and.returnValue(of({ results, results_count: results.length }));
    fixture = TestBed.createComponent(RecentContentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  function alle(selektor: string): Element[] {
    return Array.from(fixture.nativeElement.querySelectorAll(selektor));
  }

  beforeEach(async () => {
    mobil = false;
    contentService = jasmine.createSpyObj('ContentService', ['getRecentContent']);
    const loggingServiceSpy = jasmine.createSpyObj('LoggingService', ['info', 'error', 'debug', 'warn']);

    await TestBed.configureTestingModule({
      imports: [RecentContentComponent, HttpClientTestingModule],
      providers: [
        { provide: ContentService, useValue: contentService },
        { provide: LoggingService, useValue: loggingServiceSpy },
        { provide: BreakpointObserver, useValue: { observe: () => of({ matches: mobil, breakpoints: {} }) } },
      ]
    })
      .overrideComponent(KartenlisteComponent, { set: { imports: [CommonModule, BeitragskarteStubComponent] } })
      .overrideComponent(ResultCarouselComponent, {
        set: { imports: [CommonModule, MatIconModule, MatTooltipModule, BeitragskarteStubComponent] },
      })
      .compileComponents();
  });

  it('should create', () => {
    erstellen();
    expect(component).toBeTruthy();
  });

  it('laedt fuer den Teaser fuenf Beitraege', () => {
    erstellen();

    expect(TEASER_ANZAHL).toBe(5);
    expect(contentService.getRecentContent).toHaveBeenCalledWith(TEASER_ANZAHL);
  });

  it('baut aus Kommentar und Hintergrundinfo je eine Karte', () => {
    erstellen(eintraege(2));

    expect(component.karten.map((karte) => [karte.id, karte.typ])).toEqual([
      ['c-0', 'commentary'],
      ['c-1', 'generictext'],
    ]);
  });

  it('zeigt mobil eine Liste statt des Karussells', () => {
    mobil = true;
    erstellen(eintraege(3));

    expect(alle('app-kartenliste').length).toBe(1);
    expect(alle('app-result-carousel').length).toBe(0);
    expect(alle('app-beitragskarte').length).toBe(3);
  });

  it('zeigt ab 600 px das Karussell', () => {
    erstellen(eintraege(3));

    expect(alle('app-result-carousel').length).toBe(1);
    expect(alle('app-kartenliste').length).toBe(0);
    expect(alle('app-beitragskarte').length).toBe(3);
  });
});
