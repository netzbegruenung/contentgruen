import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ContributeViewComponent } from './contribute-view.component';
import { ActivatedRoute, provideRouter, Router } from '@angular/router';
import { of } from 'rxjs';
import { MatDialogModule } from '@angular/material/dialog';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BreakpointService } from '../shared/services/breakpoint.service';

describe('ContributeViewComponent', () => {
  let component: ContributeViewComponent;
  let fixture: ComponentFixture<ContributeViewComponent>;
  let router: Router;

  async function erstellen(mobil: boolean): Promise<void> {
    await TestBed.configureTestingModule({
      imports: [
        ContributeViewComponent,
        MatDialogModule,
        BrowserAnimationsModule
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: BreakpointService, useValue: { isMobile$: of(mobil) } },
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({}),
            queryParams: of({}),
            snapshot: {
              params: {},
              queryParams: {}
            }
          }
        }
      ]
    })
    .compileComponents();

    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(ContributeViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  function text(): string {
    return fixture.nativeElement.textContent;
  }

  describe('Desktop', () => {
    beforeEach(() => erstellen(false));

    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('leitet mit einem Satz ein, darueber der Erstnutzer-Satz', () => {
      expect(fixture.nativeElement.querySelector('.einleitung-satz').textContent.trim())
        .toBe('Wähle, was du beitragen willst:');
      expect(fixture.nativeElement.querySelector('.einleitung .erstnutzer-satz').textContent)
        .toContain('Gut gesagt ist neu.');
    });

    it('beschriftet den Fangkorb-Knopf mit Einwerfen und fuehrt zum Formular', () => {
      const knopf: HTMLButtonElement = fixture.nativeElement.querySelector('.fangkorb-karte button');

      expect(knopf.textContent).toContain('Einwerfen');
      knopf.click();

      expect(router.navigate).toHaveBeenCalledWith(['/einwerfen']);
    });

    it('zeigt keine Typ-Zeilen', () => {
      expect(fixture.nativeElement.querySelector('.typ-zeilen')).toBeNull();
    });
  });

  describe('Mobil', () => {
    beforeEach(() => erstellen(true));

    function zeilen(): HTMLButtonElement[] {
      return Array.from(fixture.nativeElement.querySelectorAll('button.typ-zeile'));
    }

    it('zeigt Einwerfen, Fangkorb und die drei Typen als Zeilen', () => {
      expect(zeilen().map((zeile) => zeile.querySelector('.typ-titel')!.textContent!.trim()))
        .toEqual(['Einwerfen', 'Fangkorb', 'Kommentar', 'Hintergrundinfo', 'Bild']);
      expect(text()).not.toContain('Zum Fangkorb');
    });

    it('gliedert die Kette in Einwerfen, Weiterarbeiten und Verfassen', () => {
      const ueberschriften: HTMLElement[] = Array.from(
        fixture.nativeElement.querySelectorAll('.typ-zwischenueberschrift'),
      );
      const [einwerfen, weiterarbeiten, verfassen] = ueberschriften;

      expect(ueberschriften.map((u) => u.textContent!.trim())).toEqual(['Einwerfen', 'Weiterarbeiten', 'Verfassen']);
      expect(einwerfen.nextElementSibling!.classList).toContain('einwerfen-block');
      expect(weiterarbeiten.nextElementSibling!.classList).toContain('fangkorb-block');
      expect(verfassen.nextElementSibling!.matches('nav.typ-liste')).toBeTrue();
      expect(verfassen.nextElementSibling!.querySelectorAll('button.typ-zeile').length).toBe(3);
      expect(fixture.nativeElement.querySelector('.einleitung-satz')).toBeNull();
    });

    it('fuehrt mit der Fangkorb-Kachel zur Liste', () => {
      (fixture.nativeElement.querySelector('.fangkorb-block') as HTMLButtonElement).click();

      expect(router.navigate).toHaveBeenCalledWith(['/fangkorb']);
    });

    it('fuehrt mit der Einwerfen-Zeile zum Formular, nicht zur Liste', () => {
      zeilen()[0].click();

      expect(router.navigate).toHaveBeenCalledWith(['/einwerfen']);
    });

    it('oeffnet mit einer Typ-Zeile das Formular des Typs', () => {
      zeilen()[2].click();

      expect(component.showMobileForm).toBe('commentary');
    });
  });
});
