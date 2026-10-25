import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ResultCarouselComponent } from './result-carousel.component';
import { BeitragskarteStubComponent } from '../beitragskarte/beitragskarte.stub';
import { KartenDaten } from '../beitragskarte/karten-daten';

describe('ResultCarouselComponent', () => {
  let fixture: ComponentFixture<ResultCarouselComponent>;

  function karte(id: string): KartenDaten {
    return {
      id,
      typ: 'commentary',
      titel: `Titel ${id}`,
      text: 'Text',
      erstellt: '2026-09-13T12:00:00Z',
      autor: null,
      autorName: null,
      nutzung: 0,
      quellen: [],
    };
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ResultCarouselComponent],
    })
      .overrideComponent(ResultCarouselComponent, {
        set: { imports: [CommonModule, MatIconModule, MatTooltipModule, BeitragskarteStubComponent] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(ResultCarouselComponent);
    fixture.componentRef.setInput('daten', [karte('a'), karte('b'), karte('c')]);
    fixture.detectChanges();
  });

  it('rendert je Karte eine Beitragskarte mit ihren Daten', () => {
    const karten: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll('.result-item-wrapper app-beitragskarte'));

    expect(karten.length).toBe(3);
    expect(karten[1].textContent).toContain('Titel b');
  });

  it('hat keinen mobilen Zweig und keine feste Hoehe mehr', () => {
    const reihe: HTMLElement = fixture.nativeElement.querySelector('.result-container');

    expect(fixture.nativeElement.querySelector('.mobile-scroll-container')).toBeNull();
    expect(fixture.nativeElement.querySelector('.dot')).toBeNull();
    expect(getComputedStyle(reihe).minHeight).toBe('0px');
    expect(getComputedStyle(reihe).alignItems).toBe('stretch');
  });

  it('beschriftet die Pfeile auf Deutsch und sperrt links am Anfang', () => {
    const links: HTMLButtonElement = fixture.nativeElement.querySelector('.scroll-button.left');
    const rechts: HTMLButtonElement = fixture.nativeElement.querySelector('.scroll-button.right');

    expect(links.disabled).toBeTrue();
    expect(links.getAttribute('aria-label')).toBe('Vorherige Karte');
    expect(rechts.getAttribute('aria-label')).toBe('Nächste Karte');
  });
});
