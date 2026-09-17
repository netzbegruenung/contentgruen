import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { BeitragGespeichertComponent, NICHT_MARKIERT } from './beitrag-gespeichert.component';
import { GespeichertZustand, gespeichertEltern } from './gespeichert-adresse';
import { CommentaryService } from '../../services/commentary.service';
import { GenericTextService } from '../../services/generic-text.service';
import { LoggingService } from '../../services/logging.service';
import { NavigationService } from '../../services/navigation.service';
import { DestillierUebergabeService } from '../../destillieren/destillier-uebergabe.service';
import { BeitragskarteComponent } from '../../beitragskarte/beitragskarte.component';
import { BeitragskarteStubComponent } from '../../beitragskarte/beitragskarte.stub';
import { FILTER_SCHLUESSEL } from '../../raw-input-list/fangkorb-filter';

describe('BeitragGespeichertComponent', () => {
  let fixture: ComponentFixture<BeitragGespeichertComponent>;
  let commentaryService: jasmine.SpyObj<CommentaryService>;
  let uebergabe: jasmine.SpyObj<DestillierUebergabeService>;
  let navigation: jasmine.SpyObj<NavigationService>;

  async function oeffnen(
    adresse: Record<string, string> = {},
    zustand: GespeichertZustand | undefined = undefined,
    laden = true,
  ): Promise<void> {
    commentaryService = jasmine.createSpyObj('CommentaryService', ['getCommentaryById']);
    commentaryService.getCommentaryById.and.returnValue(
      laden
        ? of({ id: 'k-1', title: 'Wärmepumpe lohnt sich', text: 'Text', content_type: 'commentary', references: [] } as any)
        : throwError(() => new Error('404')),
    );
    uebergabe = jasmine.createSpyObj('DestillierUebergabeService', ['zumNaechsten']);
    navigation = jasmine.createSpyObj('NavigationService', ['navigateToResult']);

    await TestBed.configureTestingModule({
      imports: [BeitragGespeichertComponent],
      providers: [
        provideRouter([]),
        { provide: CommentaryService, useValue: commentaryService },
        { provide: GenericTextService, useValue: jasmine.createSpyObj('GenericTextService', ['getGenericTextById']) },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['warn']) },
        { provide: DestillierUebergabeService, useValue: uebergabe },
        { provide: NavigationService, useValue: navigation },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { data: { typ: 'commentary' }, queryParamMap: convertToParamMap(adresse) },
            paramMap: of(convertToParamMap({ id: 'k-1' })),
          },
        },
      ],
    })
      .overrideComponent(BeitragGespeichertComponent, {
        remove: { imports: [BeitragskarteComponent] },
        add: { imports: [BeitragskarteStubComponent] },
      })
      .compileComponents();

    // Router-State wie nach router.navigate(..., { state }); ohne ihn wie nach dem Neuladen.
    spyOn(TestBed.inject(Router), 'getCurrentNavigation').and.returnValue(
      zustand ? ({ extras: { state: zustand } } as any) : null,
    );
    fixture = TestBed.createComponent(BeitragGespeichertComponent);
    fixture.detectChanges();
  }

  function seite(): HTMLElement {
    return fixture.nativeElement;
  }

  function knoepfe(): string[] {
    return Array.from(seite().querySelectorAll('.gespeichert-knoepfe > *')).map((k) => k.textContent!.trim());
  }

  it('zeigt den gespeicherten Kommentar', async () => {
    await oeffnen();

    expect(commentaryService.getCommentaryById).toHaveBeenCalledOnceWith('k-1');
    expect(seite().textContent).toContain('Dein Kommentar ist gespeichert.');
    expect(seite().querySelector('.gespeichert-karte')!.textContent).toContain('Wärmepumpe lohnt sich');
  });

  describe('Knoepfe je Herkunft', () => {
    it('frei: noch einer und Meine Beitraege', async () => {
      await oeffnen();
      const navigieren = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);

      expect(knoepfe()).toEqual(['Noch einen Kommentar', 'Meine Beiträge']);
      (seite().querySelector('.noch-einer') as HTMLButtonElement).click();
      expect(navigieren).toHaveBeenCalledOnceWith(['/workflow/add-commentary']);
      expect(seite().querySelector('a.meine-beitraege')!.getAttribute('href')).toBe('/contributions');
    });

    it('Fangkorb: naechster Einwurf und zum Fangkorb', async () => {
      await oeffnen({ rohinput: 'e-1' }, { markiert: true });
      const navigieren = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);

      expect(knoepfe()).toEqual(['Nächster Einwurf', 'Zum Fangkorb', 'Meine Beiträge']);

      (seite().querySelector('.naechster-einwurf') as HTMLButtonElement).click();
      expect(uebergabe.zumNaechsten).toHaveBeenCalledOnceWith('e-1', 'erledigt');

      (seite().querySelector('.zum-fangkorb') as HTMLButtonElement).click();
      expect(navigieren).toHaveBeenCalledOnceWith(['/fangkorb']);
      expect(sessionStorage.getItem(FILTER_SCHLUESSEL) ?? '').toContain('erledigt');
    });

    it('Fangkorb: nicht markiert fuehrt nach Ausformulieren und sagt es', async () => {
      await oeffnen({ rohinput: 'e-1' }, { markiert: false });

      expect(seite().querySelector('.markieren-fehlgeschlagen')!.textContent).toContain(NICHT_MARKIERT);
      (seite().querySelector('.naechster-einwurf') as HTMLButtonElement).click();
      expect(uebergabe.zumNaechsten).toHaveBeenCalledOnceWith('e-1', 'ausformulieren');
    });

    it('Suche: zurueck zur Suche mit der urspruenglichen Anfrage', async () => {
      await oeffnen({ von: 'suche', suche: 'Wärmepumpen zu teuer' });

      expect(knoepfe()).toEqual(['Zurück zur Suche', 'Meine Beiträge']);
      (seite().querySelector('.zur-suche') as HTMLButtonElement).click();
      expect(navigation.navigateToResult).toHaveBeenCalledOnceWith('Wärmepumpen zu teuer');
    });

    it('Suche ohne bekannte Anfrage: zur Startseite der Suche', async () => {
      await oeffnen({ von: 'suche' });
      const navigieren = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);

      (seite().querySelector('.zur-suche') as HTMLButtonElement).click();
      expect(navigieren).toHaveBeenCalledOnceWith(['/search']);
    });
  });

  describe('Antwort auf', () => {
    it('zeigt die Aussage aus dem Router-State als Kopf-Karte', async () => {
      await oeffnen({}, { aussage: { id: 'a-1', text: 'Wärmepumpen sind zu teuer' }, verknuepft: true });

      expect(seite().querySelector('.gespeichert-aussage')!.textContent).toContain('Wärmepumpen sind zu teuer');
      expect(seite().querySelector('.verknuepfung-fehlgeschlagen')).toBeNull();
    });

    it('zeigt bei verknuepft:false keine Karte, nennt die Aussage aber im Hinweis', async () => {
      await oeffnen({}, { aussage: { id: '', text: 'Wärmepumpen sind zu teuer' }, verknuepft: false });

      expect(seite().querySelector('.gespeichert-aussage')).toBeNull();
      expect(seite().querySelector('.verknuepfung-fehlgeschlagen')!.textContent!.trim()).toBe(
        'Dein Beitrag ist gespeichert, konnte aber nicht mit „Wärmepumpen sind zu teuer“ verknüpft werden.',
      );
    });

    it('nennt ohne bekannten Aussagetext den allgemeinen Hinweis', async () => {
      await oeffnen({}, { verknuepft: false });

      expect(seite().querySelector('.verknuepfung-fehlgeschlagen')!.textContent).toContain('nicht mit der Aussage verknüpft');
    });

    it('kommt nach dem Neuladen ohne State ohne Antwort-auf aus', async () => {
      await oeffnen({ rohinput: 'e-1' });

      expect(seite().querySelector('.gespeichert-aussage')).toBeNull();
      expect(seite().querySelector('.gespeichert-warnung')).toBeNull();
      expect(seite().textContent).toContain('Dein Kommentar ist gespeichert.');
    });
  });

  it('bleibt bei der Meldung, wenn der Beitrag nicht ladbar ist', async () => {
    await oeffnen({}, undefined, false);
    fixture.detectChanges();

    expect(seite().textContent).toContain('Dein Kommentar ist gespeichert.');
    expect(seite().querySelector('.gespeichert-karte')).toBeNull();
    expect(seite().querySelector('.gespeichert-hinweis')!.textContent).toContain('Meine Beiträge');
  });

  it('fuehrt mit dem Pfeil dorthin, woher das Formular kam', () => {
    const snapshot = (params: Record<string, string>) => ({ queryParamMap: convertToParamMap(params) }) as any;

    expect(gespeichertEltern(snapshot({ rohinput: 'e-1' }))).toBe('/fangkorb');
    expect(gespeichertEltern(snapshot({ von: 'suche', suche: 'a b' }))).toBe('/result?searchQuery=a%20b');
    expect(gespeichertEltern(snapshot({ von: 'suche' }))).toBe('/search');
    expect(gespeichertEltern(snapshot({}))).toBe('/contribute');
  });
});
