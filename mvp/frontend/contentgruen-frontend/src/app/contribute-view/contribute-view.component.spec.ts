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

    it('zeigt alle vier Typen als Zeilen', () => {
      expect(zeilen().map((zeile) => zeile.querySelector('.typ-titel')!.textContent!.trim()))
        .toEqual(['Einwerfen', 'Kommentar', 'Hintergrundinfo', 'Bild']);
      expect(text()).not.toContain('Zum Fangkorb');
    });

    it('fuehrt mit der Einwerfen-Zeile zum Formular, nicht zur Liste', () => {
      zeilen()[0].click();

      expect(router.navigate).toHaveBeenCalledWith(['/einwerfen']);
    });

    it('oeffnet mit einer Typ-Zeile das Formular des Typs', () => {
      zeilen()[1].click();

      expect(component.showMobileForm).toBe('commentary');
    });
  });
});
