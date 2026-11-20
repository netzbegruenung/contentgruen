import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ContributeViewComponent } from './contribute-view.component';
import { ActivatedRoute, ParamMap, convertToParamMap, provideRouter, Router } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { MatDialogModule } from '@angular/material/dialog';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { RUNDGAENGE } from '../rundgang/rundgang-daten';

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

    // Sebastian 20.11.: oben die Kette in drei Schritten, darunter die vier Typen
    it('zeigt zuerst die drei Schritte der Kette, dann die vier Typen', () => {
      expect(zeilen().map((zeile) => zeile.querySelector('.typ-titel')!.textContent!.trim()))
        .toEqual(['Schnell einwerfen', 'Einwürfe destillieren', 'Sätze ausformulieren', 'Kommentar', 'Hintergrundinfo', 'Bild', 'Post']);
    });

    it('ordnet die Schritte als Liste, mit Pfeilen nur zwischen den Kacheln und ohne Pfeile auf ihnen', () => {
      const liste: HTMLElement = fixture.nativeElement.querySelector('.ketten-abschnitt ol.ketten-liste');
      const schritte = Array.from(liste.children) as HTMLElement[];
      expect(schritte.map((li) => li.tagName)).toEqual(['LI', 'LI', 'LI']);
      const bloecke = ['einwerfen-block', 'destillieren-block', 'ausformulieren-block'];
      expect(schritte.map((li) => bloecke.find((k) => li.querySelector('button.typ-zeile')!.classList.contains(k))))
        .toEqual(bloecke);
      // Der Pfeil steht vor dem zweiten und dritten Schritt, dekorativ
      expect(schritte.map((li) => li.querySelectorAll('.ketten-pfeil').length)).toEqual([0, 1, 1]);
      for (const pfeil of Array.from(liste.querySelectorAll('.ketten-pfeil'))) {
        expect(pfeil.getAttribute('aria-hidden')).toBe('true');
        expect(pfeil.closest('button')).toBeNull();
      }
      expect(fixture.nativeElement.querySelector('.typ-zeile mat-icon, .typ-pfeil')).toBeNull();
    });

    it('stellt den Erstnutzer-Satz als eigenen Block unter beide Abschnitte', () => {
      const satz: HTMLElement = fixture.nativeElement.querySelector('.erstnutzer-satz');
      expect(satz.textContent!.trim()).toBe(
        'Gut gesagt ist neu. Alles, was du hier einträgst, prägt mit, was hier Standard wird. Also: kein Quatsch.',
      );
      expect(satz.closest('section')).toBeNull();
      expect(satz.previousElementSibling!.matches('section.verfassen-abschnitt')).toBeTrue();
    });

    it('setzt Meine Beitraege als eigenen Knopf unter den Satz, nicht als Kachel', () => {
      const knopf: HTMLButtonElement = fixture.nativeElement.querySelector('.meine-beitraege-knopf');
      expect(knopf.textContent).toContain('Meine Beiträge');
      // Dieselbe Optik wie "Fangkorb ansehen" auf der Einwerfen-Seite (Sebastian 20.11.)
      expect(knopf.classList).toContain('nebenweg-knopf');
      expect(knopf.parentElement!.classList).toContain('nebenweg-zeile');
      expect(knopf.classList.contains('typ-zeile')).toBeFalse();
      expect(knopf.closest('section')).toBeNull();
      expect(knopf.parentElement!.previousElementSibling!.matches('.erstnutzer-satz')).toBeTrue();

      knopf.click();
      expect(router.navigate).toHaveBeenCalledWith(['/contributions']);
    });

    it('traegt jedes Ziel des Rundgangs Selbst beitragen, das auf dieser Seite spielt', () => {
      const ziele = RUNDGAENGE['mitmachen'].schritte.filter((s) => s.seite?.pfad === '/contribute').map((s) => s.ziel);
      expect(ziele.length).toBe(4);
      for (const ziel of ziele) {
        expect(fixture.nativeElement.querySelector(ziel)).withContext(ziel).not.toBeNull();
      }
    });

    it('nutzt einen Kartenstil fuer alle Zeilen', () => {
      expect(fixture.nativeElement.querySelector('.rahmen-kachel')).toBeNull();
    });

    it('bettet kein Formular und kein Akkordeon ein', () => {
      const seite: HTMLElement = fixture.nativeElement;
      expect(seite.querySelector('mat-expansion-panel')).toBeNull();
      expect(seite.querySelector('app-add-commentary-workflow, app-add-generictext-workflow, app-add-image-workflow'))
        .toBeNull();
    });

    it('gliedert die Seite in Kette und Verfassen mit Abschnittsueberschriften', () => {
      const ueberschriften: HTMLElement[] = Array.from(
        fixture.nativeElement.querySelectorAll('.typ-zwischenueberschrift'),
      );
      const [kette, verfassen] = ueberschriften;

      expect(ueberschriften.map((u) => u.textContent!.trim())).toEqual(['Einwerfen und weiterarbeiten', 'Direkt verfassen']);
      expect(ueberschriften.every((u) => u.tagName === 'H2')).toBeTrue();
      expect(kette.nextElementSibling!.querySelectorAll('button.typ-zeile').length).toBe(3);
      expect(verfassen.nextElementSibling!.matches('nav.typ-liste')).toBeTrue();
      expect(verfassen.nextElementSibling!.querySelectorAll('button.typ-zeile').length).toBe(4);
    });

    it('fuehrt Einwerfen zum Formular, Destillieren und Ausformulieren in ihre Arbeitsliste im Fangkorb', () => {
      const [einwerfen, destillieren, ausformulieren] = zeilen();
      einwerfen.click();
      expect(router.navigate).toHaveBeenCalledWith(['/einwerfen']);

      destillieren.click();
      expect(router.navigate).toHaveBeenCalledWith(['/fangkorb'], { queryParams: { tab: 'destillieren' } });

      ausformulieren.click();
      expect(router.navigate).toHaveBeenCalledWith(['/fangkorb'], { queryParams: { tab: 'ausformulieren' } });
    });

    it('oeffnet mit einer Typ-Zeile die Formularseite des Typs', () => {
      const [, , , kommentar, hintergrund, bild, post] = zeilen();

      kommentar.click();
      expect(router.navigate).toHaveBeenCalledWith(['/workflow/add-commentary']);
      hintergrund.click();
      expect(router.navigate).toHaveBeenCalledWith(['/workflow/add-generictext']);
      bild.click();
      expect(router.navigate).toHaveBeenCalledWith(['/workflow/add-image']);
      post.click();
      expect(router.navigate).toHaveBeenCalledWith(['/workflow/add-post']);
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
