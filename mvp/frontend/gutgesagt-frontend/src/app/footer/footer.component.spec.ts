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
    const satz = Array.from(fixture.nativeElement.querySelectorAll('.footer > span') as NodeListOf<HTMLElement>)
      .map((span) => span.textContent!.replace(/\s+/g, ' ').trim())
      .find((text) => text.startsWith('Ein Projekt'));

    expect(satz).toBe('Ein Projekt von Netzbegrünung e.V., entwickelt von Sebastian Banach');
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
});
