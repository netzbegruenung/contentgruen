import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';

import { AdminLayoutComponent } from './admin-layout.component';

/**
 * Design-Audit A4/B10 (#512): Der Admin-Bereich hatte eine eigene gruene Leiste
 * ueber die volle Breite und eine fest offene Seitenleiste, die auf dem Handy fuer
 * den Inhalt rund 150 px liess. Jetzt steht er im Seitenrahmen wie jede Seite, den
 * Titel traegt der App-Kopf, die Navigation ist mobil eine Zeile ueber dem Inhalt.
 */
describe('AdminLayoutComponent', () => {
  let fixture: ComponentFixture<AdminLayoutComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AdminLayoutComponent],
      providers: [provideRouter([]), provideNoopAnimations()],
    }).compileComponents();
    fixture = TestBed.createComponent(AdminLayoutComponent);
    fixture.detectChanges();
  });

  afterEach(() => fixture.nativeElement.remove());

  function breit(px: number): void {
    const host: HTMLElement = fixture.nativeElement;
    host.style.display = 'block';
    host.style.width = `${px}px`;
    document.body.appendChild(host);
  }

  it('hat keine eigene Leiste mehr, den Titel traegt der App-Kopf', () => {
    expect(fixture.nativeElement.querySelector('mat-toolbar')).toBeNull();
    expect(fixture.nativeElement.querySelector('mat-sidenav')).toBeNull();
  });

  it('fuehrt auf Deutsch zu Uebersicht, Moderation und Themen', () => {
    const links = Array.from(fixture.nativeElement.querySelectorAll('nav.admin-nav a')) as HTMLAnchorElement[];

    expect(links.map((a) => a.querySelector('span')!.textContent!.trim())).toEqual(['Übersicht', 'Moderation', 'Themen']);
    expect(links.map((a) => a.getAttribute('href'))).toEqual(['/admin/dashboard', '/admin/moderation', '/admin/themen']);
  });

  it('laesst dem Inhalt auf dem Handy die volle Breite', () => {
    breit(390);

    const inhalt = (fixture.nativeElement.querySelector('.admin-content') as HTMLElement).getBoundingClientRect();
    // 390 px abzueglich 16 px Seitenrand je Seite
    expect(inhalt.width).toBe(358);
  });
});
