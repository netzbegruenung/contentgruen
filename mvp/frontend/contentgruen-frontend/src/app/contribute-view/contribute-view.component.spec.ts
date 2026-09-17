import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ContributeViewComponent } from './contribute-view.component';
import { ActivatedRoute, ParamMap, convertToParamMap, provideRouter, Router } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { MatDialogModule } from '@angular/material/dialog';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('ContributeViewComponent', () => {
  let fixture: ComponentFixture<ContributeViewComponent>;
  let router: Router;

  let adresse: BehaviorSubject<ParamMap>;

  async function erstellen(queryParams: Record<string, string> = {}): Promise<void> {
    adresse = new BehaviorSubject(convertToParamMap(queryParams));
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
        {
          provide: ActivatedRoute,
          useValue: { queryParamMap: adresse.asObservable() }
        }
      ]
    })
    .compileComponents();

    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(ContributeViewComponent);
    fixture.detectChanges();
  }

  function zeilen(): HTMLButtonElement[] {
    return Array.from(fixture.nativeElement.querySelectorAll('button.typ-zeile'));
  }

  // Desktop und Handy zeigen dieselbe Seite; ein Breakpoint wird nicht mehr gelesen.
  describe('Kette', () => {
    beforeEach(() => erstellen());

    it('zeigt Einwerfen, Fangkorb und die drei Typen als Zeilen', () => {
      expect(zeilen().map((zeile) => zeile.querySelector('.typ-titel')!.textContent!.trim()))
        .toEqual(['Einwerfen', 'Fangkorb', 'Meine Beiträge', 'Kommentar', 'Hintergrundinfo', 'Bild']);
      expect(fixture.nativeElement.querySelector('.einleitung .erstnutzer-satz').textContent)
        .toContain('Gut gesagt ist neu.');
    });

    it('bettet kein Formular und kein Akkordeon ein', () => {
      const seite: HTMLElement = fixture.nativeElement;
      expect(seite.querySelector('mat-expansion-panel')).toBeNull();
      expect(seite.querySelector('app-add-commentary-workflow, app-add-generictext-workflow, app-add-image-workflow'))
        .toBeNull();
    });

    it('gliedert die Kette in Einwerfen, Weiterarbeiten und Verfassen', () => {
      const ueberschriften: HTMLElement[] = Array.from(
        fixture.nativeElement.querySelectorAll('.typ-zwischenueberschrift'),
      );
      const [einwerfen, weiterarbeiten, verfassen] = ueberschriften;

      expect(ueberschriften.map((u) => u.textContent!.trim())).toEqual(['Einwerfen', 'Weiterarbeiten', 'Verfassen']);
      expect(einwerfen.nextElementSibling!.classList).toContain('einwerfen-block');
      expect(weiterarbeiten.nextElementSibling!.classList).toContain('fangkorb-block');
      expect(weiterarbeiten.nextElementSibling!.nextElementSibling!.classList).toContain('beitraege-block');
      expect(verfassen.nextElementSibling!.matches('nav.typ-liste')).toBeTrue();
      expect(verfassen.nextElementSibling!.querySelectorAll('button.typ-zeile').length).toBe(3);
    });

    it('fuehrt mit der Einwerfen-Zeile zum Formular, mit der Fangkorb-Zeile zur Liste', () => {
      zeilen()[0].click();
      expect(router.navigate).toHaveBeenCalledWith(['/einwerfen']);

      zeilen()[1].click();
      expect(router.navigate).toHaveBeenCalledWith(['/fangkorb']);

      zeilen()[2].click();
      expect(router.navigate).toHaveBeenCalledWith(['/contributions']);
    });

    it('oeffnet mit einer Typ-Zeile die Formularseite des Typs', () => {
      const [, , , kommentar, hintergrund, bild] = zeilen();

      kommentar.click();
      expect(router.navigate).toHaveBeenCalledWith(['/workflow/add-commentary']);
      hintergrund.click();
      expect(router.navigate).toHaveBeenCalledWith(['/workflow/add-generictext']);
      bild.click();
      expect(router.navigate).toHaveBeenCalledWith(['/workflow/add-image']);
    });

    it('leitet ohne alte Parameter nirgendwohin weiter', () => {
      expect(router.navigate).not.toHaveBeenCalled();
    });
  });

  describe('Weiterleitung alter Adressen', () => {
    it('fuehrt ?form= ins Formular und nimmt searchQuery mit', async () => {
      await erstellen({ form: 'commentary', searchQuery: 'Waermepumpen sind zu teuer' });

      expect(router.navigate).toHaveBeenCalledOnceWith(['/workflow/add-commentary'], {
        queryParams: { searchQuery: 'Waermepumpen sind zu teuer' },
        replaceUrl: true,
      });
    });

    it('fuehrt ?panel= ins Formular', async () => {
      await erstellen({ panel: 'generictext' });

      expect(router.navigate).toHaveBeenCalledOnceWith(['/workflow/add-generictext'], {
        queryParams: {},
        replaceUrl: true,
      });
    });

    it('fuehrt auch das Bild weiter', async () => {
      await erstellen({ form: 'image' });

      expect(router.navigate).toHaveBeenCalledOnceWith(['/workflow/add-image'], {
        queryParams: {},
        replaceUrl: true,
      });
    });

    it('leitet auch weiter, wenn der Parameter erst bei offener Seite kommt', async () => {
      await erstellen();
      expect(router.navigate).not.toHaveBeenCalled();

      adresse.next(convertToParamMap({ form: 'generictext', searchQuery: 'spaeter' }));

      expect(router.navigate).toHaveBeenCalledOnceWith(['/workflow/add-generictext'], {
        queryParams: { searchQuery: 'spaeter' },
        replaceUrl: true,
      });
    });

    it('bleibt bei einem unbekannten Typ auf der Uebersicht', async () => {
      await erstellen({ form: 'reference', panel: 'toString' });

      expect(router.navigate).not.toHaveBeenCalled();
    });
  });
});
