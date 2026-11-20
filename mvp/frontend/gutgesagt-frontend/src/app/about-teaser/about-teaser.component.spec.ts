import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { AboutTeaserComponent } from './about-teaser.component';

describe('AboutTeaserComponent', () => {
  it('fasst die Über-Seite ohne Widerlegen-Rahmen zusammen und verlinkt sie', async () => {
    await TestBed.configureTestingModule({
      imports: [AboutTeaserComponent],
      providers: [provideRouter([])],
    }).compileComponents();
    const fixture = TestBed.createComponent(AboutTeaserComponent);
    fixture.detectChanges();
    const teaser: HTMLElement = fixture.nativeElement;

    // Designrunde 17.11.: erst die Erklaerung, dann der Knopf, darunter das Zitat mit Bild
    expect(teaser.querySelector('.teaser-text')!.textContent).toContain('sammelt deshalb gute Antworten');
    expect(teaser.querySelector('a')!.getAttribute('href')).toBe('/about');
    expect(teaser.querySelector('.cta-container')!.nextElementSibling!.classList).toContain('zitat');
    expect(teaser.querySelector('.zitat blockquote')!.textContent).toContain('Antworten, die Unentschiedene mitnehmen');
    expect(teaser.querySelector('.zitat img')!.getAttribute('src')).toBe('/profilbild-2026-11.jpg');
  });
});
