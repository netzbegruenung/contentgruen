import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FooterComponent, buildKennung } from './footer.component';
import { MatDialogModule } from '@angular/material/dialog';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';
import paket from '../../../package.json';

describe('FooterComponent', () => {
  let component: FooterComponent;
  let fixture: ComponentFixture<FooterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        FooterComponent,
        MatDialogModule
      ],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({}),
            queryParams: of({}),
            snapshot: { params: {}, queryParams: {} }
          }
        }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(FooterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('nennt Anbieter vor Entwickler, wie das Menue', () => {
    const satz = Array.from(fixture.nativeElement.querySelectorAll('.footer .traeger') as NodeListOf<HTMLElement>)
      .map((span) => span.textContent!.replace(/\s+/g, ' ').trim())
      .find((text) => text.startsWith('Ein Projekt'));

    expect(satz).toBe('Ein Projekt von Netzbegrünung e.V., entwickelt von Sebastian Banach');
  });

  // Design-Audit C2 (#512): Ein "|" hing am Zeilenende, "Nutzungsbedingungen" stand
  // allein in der zweiten Zeile. Jetzt Links oben, Traegerzeile darunter, ohne Striche.
  it('ordnet die Links vor der Traegerzeile, ohne Trennstriche', () => {
    const footer: HTMLElement = fixture.nativeElement.querySelector('.footer');
    const links = Array.from(footer.querySelectorAll('.footer-links > a, .footer-links > button')) as HTMLElement[];

    expect(footer.textContent).not.toContain('|');
    expect(links.map((l) => l.textContent!.trim())).toEqual([
      'Hilfe',
      'Über Gut gesagt',
      'Impressum',
      'Datenschutz',
      'Nutzungsbedingungen',
    ]);
    expect(footer.lastElementChild!.classList).toContain('traeger');
  });

  it('oeffnet die Hilfe ueber einen echten Knopf', () => {
    const hilfe = fixture.nativeElement.querySelector('.help-button') as HTMLElement;
    const oeffnen = spyOn(component, 'openHelpDialog');

    expect(hilfe.tagName).toBe('BUTTON');
    hilfe.click();
    expect(oeffnen).toHaveBeenCalled();
  });

  it('zeigt Version aus package.json und Commit', () => {
    const kennung: HTMLElement = fixture.nativeElement.querySelector('.build-kennung');

    expect(kennung.textContent!.trim()).toMatch(new RegExp(`^v${paket.version.replace(/\./g, '\\.')} · \\S+$`));
  });
});

describe('buildKennung', () => {
  it('kuerzt den Commit auf sieben Zeichen', () => {
    expect(buildKennung('1.1.0', '3523b55f0e1d2c3b4a5968778695a4b3c2d1e0f9')).toBe('v1.1.0 · 3523b55');
  });

  it('sagt dev ohne Commit oder mit unersetztem Platzhalter', () => {
    expect(buildKennung('1.1.0', undefined)).toBe('v1.1.0 · dev');
    expect(buildKennung('1.1.0', '')).toBe('v1.1.0 · dev');
    expect(buildKennung('1.1.0', '${GIT_SHA}')).toBe('v1.1.0 · dev');
  });

  // #327: Beim Release-Build kommt die Version aus dem Git-Tag, package.json muss nicht mit.
  it('nimmt die Version aus dem Git-Tag, wenn der Build sie mitgibt', () => {
    expect(buildKennung('0.8.0', '3523b55f0e1d', 'v0.9.0')).toBe('v0.9.0 · 3523b55');
    expect(buildKennung('0.8.0', '3523b55f0e1d', '0.9.0')).toBe('v0.9.0 · 3523b55');
  });

  // Entscheidung @BanSe 03.11. (#542): Builds auf main zeigen "main" statt einer Version.
  it('zeigt main ohne v fuer Builds auf main', () => {
    expect(buildKennung('0.8.0', '3523b55f0e1d', 'main')).toBe('main · 3523b55');
  });

  it('nimmt package.json ohne Tag-Version oder mit unersetztem Platzhalter', () => {
    expect(buildKennung('0.8.0', '3523b55', undefined)).toBe('v0.8.0 · 3523b55');
    expect(buildKennung('0.8.0', '3523b55', '')).toBe('v0.8.0 · 3523b55');
    expect(buildKennung('0.8.0', '3523b55', '${APP_VERSION}')).toBe('v0.8.0 · 3523b55');
  });
});
