import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, Observable, of, throwError } from 'rxjs';

import { Clipboard } from '@angular/cdk/clipboard';
import { MatSnackBar } from '@angular/material/snack-bar';
import {
  BeitragAnsichtComponent,
  LINK_KOPIERT,
  LINK_NICHT_KOPIERT,
  beitragsLink,
} from './beitrag-ansicht.component';
import { BeitragAnsicht, ContentService } from '../services/content.service';
import { LoggingService } from '../services/logging.service';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { BeitragskarteStubComponent } from '../beitragskarte/beitragskarte.stub';

describe('BeitragAnsichtComponent', () => {
  let fixture: ComponentFixture<BeitragAnsichtComponent>;
  let contentService: jasmine.SpyObj<ContentService>;
  let params: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let clipboard: jasmine.SpyObj<Clipboard>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  function beitrag(felder: Partial<BeitragAnsicht> = {}): BeitragAnsicht {
    return {
      id: 'b-1',
      content_type: 'commentary',
      title: 'Wärmepumpe lohnt sich auch im Altbau',
      text: 'Text',
      created: '2026-11-01T12:00:00Z',
      references: [],
      ...felder,
    } as BeitragAnsicht;
  }

  async function oeffnen(antwort: Observable<BeitragAnsicht>, id = 'b-1'): Promise<void> {
    contentService = jasmine.createSpyObj('ContentService', ['beitragLaden']);
    contentService.beitragLaden.and.returnValue(antwort);
    params = new BehaviorSubject(convertToParamMap({ id }));
    clipboard = jasmine.createSpyObj('Clipboard', ['copy']);
    clipboard.copy.and.returnValue(true);
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);

    await TestBed.configureTestingModule({
      imports: [BeitragAnsichtComponent],
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { paramMap: params.asObservable() } },
        { provide: ContentService, useValue: contentService },
        { provide: Clipboard, useValue: clipboard },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['warn', 'error']) },
      ],
    })
      .overrideComponent(BeitragAnsichtComponent, {
        remove: { imports: [BeitragskarteComponent] },
        add: { imports: [BeitragskarteStubComponent] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(BeitragAnsichtComponent);
    fixture.detectChanges();
  }

  function karte(): BeitragskarteStubComponent | null {
    const element = fixture.debugElement.query((d) => d.componentInstance instanceof BeitragskarteStubComponent);
    return element?.componentInstance ?? null;
  }

  function text(): string {
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }

  function fehler(status: number): Observable<never> {
    return throwError(() => new HttpErrorResponse({ status }));
  }

  describe('Laden', () => {
    it('laedt den Beitrag zur ID aus der Adresse', async () => {
      await oeffnen(of(beitrag()), 'b-7');

      expect(contentService.beitragLaden).toHaveBeenCalledWith('b-7');
    });

    it('zeigt ihn als volle Karte mit Abstimmen, ohne Link auf sich selbst', async () => {
      await oeffnen(of(beitrag()));

      expect(karte()?.daten?.titel).toBe('Wärmepumpe lohnt sich auch im Altbau');
      expect(karte()?.variante).toBe('voll');
      expect(karte()?.abstimmenSichtbar).toBeTrue();
      expect(karte()?.ansichtVerlinkt).toBeFalse();
    });

    it('zeigt die eigene Stimme an der Karte', async () => {
      await oeffnen(of(beitrag({ user_vote: 'like' })));

      expect(karte()?.daten?.stimme).toBe('like');
    });

    it('zeigt jeden Beitragstyp, auch ein Bild', async () => {
      await oeffnen(of(beitrag({ content_type: 'image', image_url: 'https://example.org/b.jpg' })));

      expect(karte()?.daten?.typ).toBe('image');
      expect(karte()?.daten?.bildUrl).toBe('https://example.org/b.jpg');
    });

    it('laedt neu, wenn sich die ID in der Adresse aendert', async () => {
      await oeffnen(of(beitrag()));

      params.next(convertToParamMap({ id: 'b-2' }));

      expect(contentService.beitragLaden).toHaveBeenCalledWith('b-2');
    });
  });

  describe('Nicht da', () => {
    it('sagt bei 404, dass es den Beitrag nicht gibt, und zeigt keine Karte', async () => {
      await oeffnen(fehler(404));
      fixture.detectChanges();

      expect(karte()).toBeNull();
      expect(text()).toContain('Dieser Beitrag ist nicht verfügbar.');
    });

    it('unterscheidet eine Stoerung von einem fehlenden Beitrag', async () => {
      await oeffnen(fehler(500));
      fixture.detectChanges();

      expect(karte()).toBeNull();
      expect(text()).toContain('Der Beitrag lässt sich gerade nicht anzeigen.');
    });

    it('fuehrt ohne Beitrag zur Suche', async () => {
      await oeffnen(fehler(404));
      fixture.detectChanges();

      const link: HTMLAnchorElement = fixture.nativeElement.querySelector('a.zur-suche');
      expect(link.getAttribute('href')).toBe('/search');
    });
  });

  describe('Link kopieren (#603)', () => {
    function knopf(): HTMLButtonElement | null {
      return fixture.nativeElement.querySelector('button.link-kopieren');
    }

    it('baut die Adresse aus Origin und ID', () => {
      expect(beitragsLink('b-1', 'https://gutgesagt.example')).toBe('https://gutgesagt.example/beitrag/b-1');
    });

    it('kopiert die Adresse des Beitrags und sagt es', async () => {
      await oeffnen(of(beitrag()), 'b-7');
      knopf()!.click();
      expect(clipboard.copy).toHaveBeenCalledWith(beitragsLink('b-7'));
      expect(snackBar.open).toHaveBeenCalledWith(LINK_KOPIERT, undefined, jasmine.anything());
    });

    it('sagt, wenn das Kopieren nicht geklappt hat', async () => {
      await oeffnen(of(beitrag()));
      clipboard.copy.and.returnValue(false);
      knopf()!.click();
      expect(snackBar.open).toHaveBeenCalledWith(LINK_NICHT_KOPIERT, undefined, jasmine.anything());
    });

    it('kopiert nach einem Wechsel die neue Adresse', async () => {
      await oeffnen(of(beitrag()), 'b-1');
      params.next(convertToParamMap({ id: 'b-2' }));
      fixture.detectChanges();
      knopf()!.click();
      expect(clipboard.copy).toHaveBeenCalledWith(beitragsLink('b-2'));
    });

    it('fehlt ohne Beitrag', async () => {
      await oeffnen(fehler(404));
      fixture.detectChanges();
      expect(knopf()).toBeNull();
    });
  });

  describe('Aussage und weitere Antworten (#603)', () => {
    function kontext(): HTMLElement | null {
      return fixture.nativeElement.querySelector('app-beitrag-kontext');
    }

    it('gibt Aussage und weitere Antworten aus der Antwort weiter', async () => {
      const aussage = { id: 'a-1', text: 'Wärmepumpen funktionieren nur im Neubau!' };
      const weitere = [{ id: 'b-2', content_type: 'commentary', titel: 'Altbau geht' }];
      await oeffnen(of(beitrag({ aussage, weitere_antworten: weitere })));
      expect(fixture.componentInstance.kontext).toEqual({ aussage, weitere });
      expect(kontext()?.textContent).toContain('Wärmepumpen funktionieren nur im Neubau!');
      expect(kontext()?.textContent).toContain('Altbau geht');
    });

    it('kommt ohne die Felder aus (aelteres Backend)', async () => {
      await oeffnen(of(beitrag()));
      expect(fixture.componentInstance.kontext).toEqual({ aussage: null, weitere: [] });
    });

    it('fehlt ohne Beitrag', async () => {
      await oeffnen(fehler(404));
      fixture.detectChanges();
      expect(kontext()).toBeNull();
    });
  });
});
