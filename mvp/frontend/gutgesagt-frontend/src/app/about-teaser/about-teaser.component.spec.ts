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

    expect(teaser.querySelector('.teaser-text')!.textContent).toContain('Antworten, die Unentschiedene mitnehmen');
    expect(teaser.querySelector('a')!.getAttribute('href')).toBe('/about');
  });
});
