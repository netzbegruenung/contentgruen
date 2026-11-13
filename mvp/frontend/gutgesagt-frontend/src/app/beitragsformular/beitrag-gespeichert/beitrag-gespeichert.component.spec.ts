import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { Observable, of, throwError } from 'rxjs';

import { Clipboard } from '@angular/cdk/clipboard';
import { MatSnackBar } from '@angular/material/snack-bar';

import { BeitragGespeichertComponent, EINWURF_NICHT_MIT_NEUEM_VERKNUEPFT, beitragLink } from './beitrag-gespeichert.component';
import { GespeichertZustand, gespeichertEltern } from './gespeichert-adresse';
import { CommentaryService } from '../../services/commentary.service';
import { GenericTextService } from '../../services/generic-text.service';
import { PostService } from '../../services/post.service';
import { ImageService } from '../../services/image.service';
import { LoggingService } from '../../services/logging.service';
import { NavigationService } from '../../services/navigation.service';
import { Einwurf, EinwurfService } from '../../services/einwurf.service';
import { FILTER_SCHLUESSEL, filterLaden } from '../../fangkorb/fangkorb-filter';
import { DestillierUebergabeService } from '../../destillieren/destillier-uebergabe.service';
import { BeitragskarteComponent } from '../../beitragskarte/beitragskarte.component';
import { BeitragskarteStubComponent } from '../../beitragskarte/beitragskarte.stub';

describe('BeitragGespeichertComponent', () => {
  let fixture: ComponentFixture<BeitragGespeichertComponent>;
  let commentaryService: jasmine.SpyObj<CommentaryService>;
  let postService: jasmine.SpyObj<PostService>;
  let imageService: jasmine.SpyObj<ImageService>;
  let uebergabe: jasmine.SpyObj<DestillierUebergabeService>;
  let navigation: jasmine.SpyObj<NavigationService>;
  let einwurfService: jasmine.SpyObj<EinwurfService>;
  /** Was das Nachladen des Einwurfs liefert; Standard: der eigene. */
  let geladenerEinwurf: Observable<Einwurf>;

  beforeEach(() => {
    geladenerEinwurf = of({ id: 'e-1', ist_eigener_einwurf: true } as Einwurf);
  });

  async function oeffnen(
    adresse: Record<string, string> = {},
    zustand: GespeichertZustand | undefined = undefined,
    laden = true,
    typ = 'commentary',
  ): Promise<void> {
    commentaryService = jasmine.createSpyObj('CommentaryService', ['getCommentaryById']);
    commentaryService.getCommentaryById.and.returnValue(
      laden
        ? of({ id: 'k-1', title: 'Wärmepumpe lohnt sich', text: 'Text', content_type: 'commentary', references: [] } as any)
        : throwError(() => new Error('404')),
    );
    postService = jasmine.createSpyObj('PostService', ['getPostById']);
    imageService = jasmine.createSpyObj('ImageService', ['getImageById']);
    imageService.getImageById.and.returnValue(
      of({ id: 'k-1', title: 'Solardach auf der Grundschule', text: 'Unterschrift', content_type: 'image', image_url: '/assets/dach.jpg' } as any),
    );
    postService.getPostById.and.returnValue(
      of({ id: 'k-1', title: 'Ein Reel zur Wärmepumpe', text: 'Text', content_type: 'post', platform: 'Instagram', author: '@konto' } as any),
    );
    uebergabe = jasmine.createSpyObj('DestillierUebergabeService', ['zumNaechsten']);
    navigation = jasmine.createSpyObj('NavigationService', ['navigateToResult', 'navigateToMeineEinwuerfe']);
    einwurfService = jasmine.createSpyObj('EinwurfService', ['einwurfLaden']);
    einwurfService.einwurfLaden.and.callFake(() => geladenerEinwurf);

    await TestBed.configureTestingModule({
      imports: [BeitragGespeichertComponent],
      providers: [
        provideRouter([]),
        { provide: CommentaryService, useValue: commentaryService },
        { provide: GenericTextService, useValue: jasmine.createSpyObj('GenericTextService', ['getGenericTextById']) },
        { provide: PostService, useValue: postService },
        { provide: ImageService, useValue: imageService },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['warn']) },
        { provide: DestillierUebergabeService, useValue: uebergabe },
        { provide: NavigationService, useValue: navigation },
        { provide: EinwurfService, useValue: einwurfService },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { data: { typ }, queryParamMap: convertToParamMap(adresse) },
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

  it('zeigt den gespeicherten Post und bietet noch einen an', async () => {
    await oeffnen({}, undefined, true, 'post');
    const navigieren = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);

    expect(postService.getPostById).toHaveBeenCalledOnceWith('k-1');
    expect(commentaryService.getCommentaryById).not.toHaveBeenCalled();
    expect(seite().textContent).toContain('Dein Post ist gespeichert.');
    expect(seite().querySelector('.gespeichert-karte')!.textContent).toContain('Ein Reel zur Wärmepumpe');
    expect(knoepfe()).toEqual(['Noch einen Post', 'Link kopieren', 'Meine Beiträge']);
    (seite().querySelector('.noch-einer') as HTMLButtonElement).click();
    expect(navigieren).toHaveBeenCalledOnceWith(['/workflow/add-post']);
  });

  it('zeigt das gespeicherte Bild und bietet noch eins an (#619)', async () => {
    await oeffnen({}, { aussage: { id: 'a-1', text: 'Solar lohnt sich nicht' }, verknuepft: true }, true, 'image');
    const navigieren = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);

    expect(imageService.getImageById).toHaveBeenCalledOnceWith('k-1');
    expect(seite().textContent).toContain('Dein Bild ist gespeichert.');
    expect(seite().querySelector('.gespeichert-karte')!.textContent).toContain('Solardach auf der Grundschule');
    expect(seite().textContent).toContain('Solar lohnt sich nicht');
    expect(knoepfe()).toEqual(['Noch ein Bild', 'Zur Aussage', 'Link kopieren', 'Meine Beiträge']);
    (seite().querySelector('.noch-einer') as HTMLButtonElement).click();
    expect(navigieren).toHaveBeenCalledOnceWith(['/workflow/add-image']);
  });

  describe('Knoepfe je Herkunft', () => {
    it('frei: noch einer und Meine Beitraege', async () => {
      await oeffnen();
      const navigieren = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);

      expect(knoepfe()).toEqual(['Noch einen Kommentar', 'Link kopieren', 'Meine Beiträge']);
      (seite().querySelector('.noch-einer') as HTMLButtonElement).click();
      expect(navigieren).toHaveBeenCalledOnceWith(['/workflow/add-commentary']);
      expect(seite().querySelector('a.meine-beitraege')!.getAttribute('href')).toBe('/contributions');
    });

    it('Fangkorb, eigener Einwurf: naechster Einwurf und zu meinen Einwuerfen', async () => {
      await oeffnen({ einwurf: 'e-1' }, { einwurfVerknuepft: true });
      const navigieren = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);

      expect(einwurfService.einwurfLaden).toHaveBeenCalledOnceWith('e-1');
      expect(knoepfe()).toEqual(['Nächster Einwurf', 'Zu meinen Einwürfen', 'Link kopieren', 'Meine Beiträge']);

      (seite().querySelector('.naechster-einwurf') as HTMLButtonElement).click();
      expect(uebergabe.zumNaechsten).toHaveBeenCalledOnceWith('e-1', 'ausformulieren');

      // Ausformuliertes liegt in keinem Tab, sondern unter "Meine Einwuerfe" (#508, F1).
      (seite().querySelector('.zu-meinen-einwuerfen') as HTMLButtonElement).click();
      expect(navigation.navigateToMeineEinwuerfe).toHaveBeenCalledOnceWith();
      expect(navigieren).not.toHaveBeenCalled();
    });

    // F1 in #511: Fremde Einwuerfe stehen nicht unter "Meine Einwuerfe".
    for (const [fall, laden] of [
      ['fremder Einwurf', () => of({ id: 'e-1', ist_eigener_einwurf: false } as Einwurf)],
      ['Einwurf nicht ladbar', () => throwError(() => ({ status: 500 }))],
    ] as const) {
      it(`Fangkorb, ${fall}: zum Fangkorb nach Ausformulieren`, async () => {
        geladenerEinwurf = laden();
        await oeffnen({ einwurf: 'e-1' }, { einwurfVerknuepft: true });
        const navigieren = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);

        expect(knoepfe()).toEqual(['Nächster Einwurf', 'Zum Fangkorb', 'Link kopieren', 'Meine Beiträge']);
        (seite().querySelector('.zum-fangkorb') as HTMLButtonElement).click();

        expect(navigieren).toHaveBeenCalledOnceWith(['/fangkorb']);
        expect(navigation.navigateToMeineEinwuerfe).not.toHaveBeenCalled();
        expect(filterLaden().tab).toBe('ausformulieren');
        sessionStorage.removeItem(FILTER_SCHLUESSEL);
      });
    }

    it('Fangkorb: nicht verknuepft fuehrt nach Ausformulieren und sagt es', async () => {
      await oeffnen({ einwurf: 'e-1' }, { einwurfVerknuepft: false });

      expect(seite().querySelector('.verknuepfen-fehlgeschlagen')!.textContent).toContain(EINWURF_NICHT_MIT_NEUEM_VERKNUEPFT);
      (seite().querySelector('.naechster-einwurf') as HTMLButtonElement).click();
      expect(uebergabe.zumNaechsten).toHaveBeenCalledOnceWith('e-1', 'ausformulieren');
    });

    it('Fangkorb: nicht verknuepft fuehrt "Zum Fangkorb" nach Ausformulieren, wo der Einwurf noch liegt', async () => {
      await oeffnen({ einwurf: 'e-1' }, { einwurfVerknuepft: false });
      const navigieren = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);

      (seite().querySelector('.zum-fangkorb') as HTMLButtonElement).click();

      expect(navigieren).toHaveBeenCalledOnceWith(['/fangkorb']);
      expect(navigation.navigateToMeineEinwuerfe).not.toHaveBeenCalled();
      expect(einwurfService.einwurfLaden).not.toHaveBeenCalled();
      expect(filterLaden().tab).toBe('ausformulieren');
      sessionStorage.removeItem(FILTER_SCHLUESSEL);
    });

    it('Suche: zurueck zur Suche mit der urspruenglichen Anfrage', async () => {
      await oeffnen({ von: 'suche', suche: 'Wärmepumpen zu teuer' });

      expect(knoepfe()).toEqual(['Zurück zur Suche', 'Link kopieren', 'Meine Beiträge']);
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

  describe('Lücke zu (Nutzerfuehrung 13.11.)', () => {
    const aussage = { aussage: { id: 'a-1', text: 'Windkraft tötet Vögel' }, verknuepft: true };

    it('sagt nach "Hier fehlt eine Antwort" Lücke zu, mit der Nachfrage, und bietet die nächste an', async () => {
      await oeffnen({ von: 'hier-fehlt-eine-antwort', gesucht: '2' }, aussage);
      const navigieren = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);

      expect(seite().querySelector('.luecke-zu-titel')!.textContent!.trim()).toBe('Lücke zu.');
      expect(seite().querySelector('.luecke-zu')!.textContent!.replace(/\s+/g, ' ').trim()).toBe(
        'Lücke zu. 2 Personen haben danach gesucht, ab jetzt finden sie was.',
      );
      expect(seite().textContent).not.toContain('Dein Kommentar ist gespeichert.');
      expect(knoepfe()[0]).toBe('Nächste Lücke');
      expect(knoepfe()).not.toContain('Noch einen Kommentar');
      (seite().querySelector('.naechste-luecke') as HTMLButtonElement).click();
      expect(navigieren).toHaveBeenCalledOnceWith(['/hier-fehlt-eine-antwort']);
    });

    it('spricht bei einer Person im Singular und ohne Zahl allgemein', async () => {
      await oeffnen({ von: 'hier-fehlt-eine-antwort', gesucht: '1' }, aussage);
      expect(seite().querySelector('.luecke-zu')!.textContent).toContain('Eine Person hat danach gesucht, ab jetzt findet sie was.');

      TestBed.resetTestingModule();
      await oeffnen({ von: 'hier-fehlt-eine-antwort' }, aussage);
      expect(seite().querySelector('.luecke-zu')!.textContent).toContain('Wer danach sucht, findet ab jetzt deine Antwort.');
    });

    it('bleibt beim allgemeinen Satz, wenn die Verknüpfung scheiterte oder es nicht von dort kam', async () => {
      await oeffnen({ von: 'hier-fehlt-eine-antwort', gesucht: '3' }, { ...aussage, verknuepft: false });
      expect(seite().querySelector('.luecke-zu')).toBeNull();
      expect(knoepfe()).toContain('Noch einen Kommentar');

      TestBed.resetTestingModule();
      await oeffnen({ gesucht: '3' }, aussage);
      expect(seite().querySelector('.luecke-zu')).toBeNull();
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

    it('sagt, wenn die gewaehlten Themen nicht galten (#455)', async () => {
      const hinweis = 'Diese Aussage gibt es schon. Themen: Klima.';
      await oeffnen({}, { aussage: { id: 'a-1', text: 'Wärmepumpen sind zu teuer' }, verknuepft: true, themenHinweis: hinweis });

      expect(seite().querySelector('.themen-hinweis')!.textContent!.trim()).toBe(hinweis);
    });

    it('zeigt ohne Themenhinweis keinen', async () => {
      await oeffnen({}, { aussage: { id: 'a-1', text: 'Wärmepumpen sind zu teuer' }, verknuepft: true });

      expect(seite().querySelector('.themen-hinweis')).toBeNull();
    });

    it('markiert eine eben neu angelegte Aussage mit "neu" (#617)', async () => {
      await oeffnen({}, { aussage: { id: 'a-1', text: 'Wärmepumpen sind zu teuer' }, verknuepft: true, aussageNeu: true });

      expect(seite().querySelector('.gespeichert-label .neu-marke')!.textContent).toBe('neu');
    });

    it('markiert eine vorhandene Aussage nicht als neu', async () => {
      await oeffnen({}, { aussage: { id: 'a-1', text: 'Wärmepumpen sind zu teuer' }, verknuepft: true });

      expect(seite().querySelector('.neu-marke')).toBeNull();
    });

    it('fuehrt "Zur Aussage" in die Suche nach ihr (#617)', async () => {
      await oeffnen({}, { aussage: { id: 'a-1', text: 'Wärmepumpen sind zu teuer' }, verknuepft: true });

      expect(knoepfe()).toEqual(['Noch einen Kommentar', 'Zur Aussage', 'Link kopieren', 'Meine Beiträge']);
      (seite().querySelector('.zur-aussage') as HTMLButtonElement).click();
      expect(navigation.navigateToResult).toHaveBeenCalledOnceWith('Wärmepumpen sind zu teuer');
    });

    it('laesst "Zur Aussage" weg, wenn "Zurueck zur Suche" dorthin fuehrt', async () => {
      await oeffnen(
        { von: 'suche', suche: 'Wärmepumpen sind zu teuer' },
        { aussage: { id: 'a-1', text: 'Wärmepumpen sind zu teuer' }, verknuepft: true },
      );

      expect(seite().querySelector('.zur-aussage')).toBeNull();
      expect(seite().querySelector('.zur-suche')).toBeTruthy();
    });

    it('bietet "Zur Aussage" nicht an, wenn nicht verknuepft', async () => {
      await oeffnen({}, { aussage: { id: '', text: 'Wärmepumpen sind zu teuer' }, verknuepft: false });

      expect(seite().querySelector('.zur-aussage')).toBeNull();
    });

    it('kommt nach dem Neuladen ohne State ohne Antwort-auf aus', async () => {
      await oeffnen({ einwurf: 'e-1' });

      expect(seite().querySelector('.gespeichert-aussage')).toBeNull();
      expect(seite().querySelector('.gespeichert-warnung')).toBeNull();
      expect(seite().textContent).toContain('Dein Kommentar ist gespeichert.');
    });
  });

  describe('Link kopieren (#617)', () => {
    it('kopiert die eigene Adresse des Beitrags und sagt es', async () => {
      await oeffnen();
      const kopieren = spyOn(fixture.debugElement.injector.get(Clipboard), 'copy').and.returnValue(true);
      const snack = spyOn(fixture.debugElement.injector.get(MatSnackBar), 'open');

      (seite().querySelector('.link-kopieren') as HTMLButtonElement).click();

      expect(kopieren).toHaveBeenCalledOnceWith(`${window.location.origin}/beitrag/k-1`);
      expect(snack.calls.mostRecent().args[0]).toBe('Link kopiert.');
    });

    it('sagt, wenn das Kopieren nicht klappt', async () => {
      await oeffnen();
      spyOn(fixture.debugElement.injector.get(Clipboard), 'copy').and.returnValue(false);
      const snack = spyOn(fixture.debugElement.injector.get(MatSnackBar), 'open');

      (seite().querySelector('.link-kopieren') as HTMLButtonElement).click();

      expect(snack.calls.mostRecent().args[0]).toBe('Kopieren hat nicht geklappt.');
    });

    it('baut die Adresse mit kodierter ID', () => {
      expect(beitragLink('a b', 'https://example.org')).toBe('https://example.org/beitrag/a%20b');
    });

    it('fehlt, solange der Beitrag nicht ladbar ist', async () => {
      await oeffnen({}, undefined, false);
      expect(seite().querySelector('.link-kopieren')).toBeNull();
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

    expect(gespeichertEltern(snapshot({ einwurf: 'e-1' }))).toBe('/fangkorb');
    expect(gespeichertEltern(snapshot({ von: 'suche', suche: 'a b' }))).toBe('/result?searchQuery=a%20b');
    expect(gespeichertEltern(snapshot({ von: 'suche' }))).toBe('/search');
    expect(gespeichertEltern(snapshot({}))).toBe('/contribute');
  });

  it('gibt der Karte die Herkunft mit Link, wie getById sie liefert (Persona-Test Gerd)', async () => {
    await oeffnen();
    commentaryService.getCommentaryById.and.returnValue(
      of({
        id: 'k-1',
        title: 'Wärmepumpe lohnt sich',
        text: 'Text',
        content_type: 'commentary',
        references: [{ reference_id: '6f1c2d3e-0000-4000-8000-000000000001', created: '', reference_text: 'https://example.org/studie' }],
      } as any),
    );
    fixture.componentInstance.ngOnInit();

    expect(fixture.componentInstance.karte!.quellen).toEqual([
      { id: '6f1c2d3e-0000-4000-8000-000000000001', url: 'https://example.org/studie', beschreibung: undefined },
    ]);
  });
});
