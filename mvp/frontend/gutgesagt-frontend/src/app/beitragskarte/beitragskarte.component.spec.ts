import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { BehaviorSubject, of, throwError } from 'rxjs';

import { BeitragskarteComponent } from './beitragskarte.component';
import { KartenAktionenComponent } from './karten-aktionen/karten-aktionen.component';
import { KartenDaten, KartenVariante, ausAussage, ausBeitrag, ausEinwurf, ausSuchergebnis } from './karten-daten';
import { AuthService, UserInfo } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { VotingService } from '../services/voting.service';
import { Einwurf } from '../services/einwurf.service';
import { ContentResult } from '../services/dtos/contributionDtos';
import { Anfragen, bildFertig, fremdeAdresse } from '../testing/anfragen';
import { provideRouter } from '@angular/router';

/**
 * Portiert aus den Specs der vier alten Karten (commentary-, generictext- und
 * post-result-item). Die Badge-Tests stammen aus commentary-result-item, das
 * Rendern und Abstimmen eines Posts aus post-result-item.voting.
 */
describe('BeitragskarteComponent', () => {
  const POST_ID = '123e4567-e89b-12d3-a456-426614174999';

  let fixture: ComponentFixture<BeitragskarteComponent>;
  let component: BeitragskarteComponent;
  let votingService: jasmine.SpyObj<VotingService>;
  let userInfo$: BehaviorSubject<UserInfo | null>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  function inhalt(felder: Record<string, unknown> = {}): any {
    return {
      id: 'test-id',
      text: 'Test text',
      content_type: 'commentary',
      created: new Date().toISOString(),
      last_modified: new Date().toISOString(),
      original_author: '0f3c2a9e-1111-2222-3333-444455556666',
      last_modified_by: 'Test Author',
      title: 'Test Title',
      references: [],
      usage_count: 0,
      ...felder,
    };
  }

  function paket(feld: string, felder: Record<string, unknown> = {}, rest: Record<string, unknown> = {}): any {
    return {
      score: 0.95,
      statement_text: 'Test statement',
      statement_similarity_score: 0.9,
      reply_relevance: 0.85,
      [feld]: inhalt(felder),
      ...rest,
    };
  }

  function postPaket(rest: Record<string, unknown> = {}): any {
    return paket(
      'post_result',
      {
        id: POST_ID,
        text: 'Erneuerbare Energien konsequent ausbauen',
        content_type: 'post',
        title: 'Klimapost',
        platform: 'mastodon',
        author: '@gruen',
        url: 'https://social.example/posts/1',
        engagement: 42,
      },
      { user_vote: null, ...rest },
    );
  }

  function zeigen(daten: KartenDaten, eingaben: Record<string, unknown> = {}): void {
    fixture = TestBed.createComponent(BeitragskarteComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('daten', daten);
    for (const [name, wert] of Object.entries(eingaben)) {
      fixture.componentRef.setInput(name, wert);
    }
    fixture.detectChanges();
  }

  function aktionen(): KartenAktionenComponent {
    return fixture.debugElement.query(By.directive(KartenAktionenComponent)).componentInstance;
  }

  function element<T extends HTMLElement = HTMLElement>(selektor: string): T {
    return fixture.nativeElement.querySelector(selektor);
  }

  beforeEach(async () => {
    votingService = jasmine.createSpyObj('VotingService', ['setLike', 'removeLike', 'setDislike', 'removeDislike']);
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
    const authServiceSpy = jasmine.createSpyObj('AuthService', ['getUserInfo', 'login']);
    authServiceSpy.getUserInfo.and.returnValue({ isAuthenticated: true, userId: 'test-user' });
    // Die Karte abonniert den Strom, um nach einer spaeten Antwort neu zu zeichnen.
    userInfo$ = new BehaviorSubject<UserInfo | null>({ isAuthenticated: true, userId: 'test-user' } as UserInfo);
    authServiceSpy.userInfo$ = userInfo$;

    await TestBed.configureTestingModule({
      imports: [BeitragskarteComponent, NoopAnimationsModule],
      providers: [
        { provide: VotingService, useValue: votingService },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: AuthService, useValue: authServiceSpy },
        { provide: Clipboard, useValue: jasmine.createSpyObj('Clipboard', ['copy']) },
        { provide: UsageTrackingService, useValue: jasmine.createSpyObj('UsageTrackingService', { trackContentUsage: undefined, gepostetBekannt: false }) },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['error', 'debug', 'info', 'warn']) },
        { provide: MatDialog, useValue: jasmine.createSpyObj('MatDialog', ['open']) },
        provideRouter([]),
      ],
    }).compileComponents();
  });

  describe('Rendern', () => {
    it('should create', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')));
      expect(component).toBeTruthy();
    });

    it('erstellt eine Hintergrundinfo-Karte', () => {
      zeigen(ausSuchergebnis(paket('generictext_result', { content_type: 'generictext' })));

      expect(component).toBeTruthy();
      expect(element('.karte').classList).toContain('typ-generictext');
      expect(element('.karte').classList).toContain('karte--voll');
    });

    it('should render the post title, body and platform/author', () => {
      zeigen(ausSuchergebnis(postPaket()));
      const text: string = fixture.nativeElement.textContent;

      expect(text).toContain('Klimapost');
      expect(text).toContain('Erneuerbare Energien konsequent ausbauen');
      expect(text).toContain('@gruen');
      expect(text).toContain('mastodon');
    });

    it('should expose the post_result as the shared content', () => {
      zeigen(ausSuchergebnis(postPaket()));

      expect(aktionen().inhaltId).toBe(POST_ID);
      expect(aktionen().typ).toBe('post');
    });

    it('zeigt Interaktionen nur bei Posts', () => {
      zeigen(ausSuchergebnis(paket('generictext_result')));
      expect(element('.post-engagement')).toBeNull();

      zeigen(ausSuchergebnis(postPaket()));
      expect(element('.post-engagement').textContent).toContain('42');
    });

    it('should render two vote buttons', () => {
      zeigen(ausSuchergebnis(postPaket()));

      expect(fixture.nativeElement.querySelectorAll('.stimme-knopf').length).toBe(2);
    });

    it('zeigt Typname und Symbol aus der Registry im Kopf', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')));
      const icon = element('.karte-icon');

      expect(icon.textContent!.trim()).toBe('💬');
      expect(icon.getAttribute('aria-label')).toBe('Kommentar');
    });

    it('zeigt ein Bild mit Beschreibung und kuerzt den Titel auf vier Zeilen', () => {
      zeigen(
        ausSuchergebnis(paket('image_result', { content_type: 'image', image_url: 'https://example.org/dach.jpg', text: 'Solardach' })),
      );
      expect(element('.karte-bild img')).toBeNull();
      element<HTMLButtonElement>('.karte-bild button.bild-laden').click();
      fixture.detectChanges();
      const bild = element<HTMLImageElement>('.karte-bild img');

      expect(bild.getAttribute('src')).toBe('https://example.org/dach.jpg');
      expect(bild.alt).toBe('Solardach');
      expect(getComputedStyle(element('.karte-titel')).webkitLineClamp).toBe('4');
      expect(element('.kopieren-knopf').textContent).toContain('Bildunterschrift kopieren');
    });

    it('nimmt in der Vorschau keinen Platzhalter als Alternativtext (#619)', () => {
      zeigen(
        ausSuchergebnis(
          paket('image_result', { content_type: 'image', image_url: '/assets/dach.jpg', text: 'Bildunterschrift eingeben...' }),
        ),
        { vorschau: true },
      );

      // Eigenes Bild: laedt ohne Klick; neben dem Formular ist es Schmuck, die Angaben stehen daneben.
      expect(element<HTMLImageElement>('.karte-bild img').alt).toBe('');
    });

    it('zeigt den Anzeigenamen und ohne Namen "Mitglied" - nie die Kennung', () => {
      const daten = ausSuchergebnis(paket('commentary_result'));
      zeigen(daten);
      expect(element('.karte-meta').textContent).toContain('Von: Mitglied');
      expect(element('.karte-meta').textContent).not.toContain('0f3c2a9e');

      zeigen({ ...daten, autorName: 'Kim G.' });
      expect(element('.karte-meta').textContent).toContain('Von: Kim G.');
    });

    it('nennt den eigenen Beitrag "Du", nicht die eigene Kennung', () => {
      const daten = ausSuchergebnis(paket('commentary_result'));
      zeigen({ ...daten, autor: 'test-user', eigen: true, autorName: 'Kim Grün' });

      expect(element('.karte-meta').textContent).toContain('Von: Du');
      expect(element('.karte-meta').textContent).not.toContain('Kim Grün');
    });

    it('vergleicht keine Kennungen: ohne Kennzeichen des Servers nicht der eigene (#385)', () => {
      const daten = ausSuchergebnis(paket('commentary_result'));
      zeigen({ ...daten, autor: 'test-user', eigen: null, autorName: 'Kim Grün' });

      expect(component.istEigen).toBeFalse();
      expect(element('.karte-meta').textContent).toContain('Von: Kim Grün');
    });

    it('erkennt den eigenen Beitrag am Kennzeichen des Servers, ohne Kennung (#333)', fakeAsync(() => {
      const daten = ausSuchergebnis(
        paket('commentary_result', { original_author: undefined, ist_eigener_beitrag: true, usage_count: 2 }),
      );
      zeigen({ ...daten, autorName: 'Kim Grün' });

      expect(element('.karte-meta').textContent).toContain('Von: Du');

      element<HTMLButtonElement>('.kopieren-knopf').click();
      fixture.detectChanges();
      expect(element('.karte-nutzung').textContent!.trim()).toBe('2× genutzt');
      tick(600);
    }));

    it('zeigt "Von: Mitglied" auch ohne Kennung und ohne Namen (#333)', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { original_author: undefined, ist_eigener_beitrag: false })));

      expect(element('.karte-meta').textContent).toContain('Von: Mitglied');
    });

    it('holt "Von: Du" nach, wenn die Anmeldung erst nach dem Zeichnen ankommt', () => {
      // Die Karte steht oft vor der Antwort von /api/user-info.
      const auth = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
      auth.getUserInfo.and.returnValue(null);
      userInfo$.next(null);
      const daten = ausSuchergebnis(paket('commentary_result'));
      zeigen({ ...daten, autor: 'test-user', eigen: true });
      expect(element('.karte-meta').textContent).not.toContain('Von:');

      auth.getUserInfo.and.returnValue({ isAuthenticated: true, userId: 'test-user' } as UserInfo);
      userInfo$.next({ isAuthenticated: true, userId: 'test-user' } as UserInfo);
      fixture.detectChanges();

      expect(element('.karte-meta').textContent).toContain('Von: Du');
      // Dass die Karte den Strom ueberhaupt abonniert, haelt dieser Test fest:
      // Ohne das Abonnement bliebe die Karte unter OnPush stehen, bis sie aus
      // einem anderen Grund neu gezeichnet wird.
      expect(userInfo$.observed).withContext('Karte abonniert userInfo$').toBeTrue();

      // Und sie haengt sich beim Zerstoeren wieder aus (takeUntilDestroyed).
      fixture.destroy();
      expect(userInfo$.observed).withContext('nach fixture.destroy()').toBeFalse();
    });

    it('laesst ohne Anmeldung die Autorzeile weg und zeigt nur das Alter', () => {
      const auth = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
      auth.getUserInfo.and.returnValue(null);
      zeigen(ausSuchergebnis(paket('commentary_result')));

      expect(element('.karte-meta').textContent).not.toContain('Von:');
      expect(element('.karte-meta')).toBeTruthy();
    });

    it('zeigt das Meilenstein-Abzeichen am Namen, wenn der Server es liefert (#351)', () => {
      const daten = ausSuchergebnis(paket('commentary_result', { autor_name: 'Kim G.', autor_abzeichen: 3 }));
      zeigen(daten);

      const abzeichen = element('.autor-abzeichen');
      expect(abzeichen.textContent).toContain('3');
      expect(abzeichen.getAttribute('title')).toBe('3 Meilensteine erreicht');
      expect(element('.karte-meta').textContent).toContain('Von: Kim G.');
    });

    it('zeigt ohne Abzeichen vom Server keins (#351)', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { autor_name: 'Kim G.' })));

      expect(fixture.nativeElement.querySelector('.autor-abzeichen')).toBeNull();
    });

    it('zeigt ohne Anmeldung kein Abzeichen, auch wenn eins mitkaeme (#351)', () => {
      const auth = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
      auth.getUserInfo.and.returnValue(null);
      zeigen(ausSuchergebnis(paket('commentary_result', { autor_name: 'Kim G.', autor_abzeichen: 3 })));

      expect(fixture.nativeElement.querySelector('.autor-abzeichen')).toBeNull();
    });

    it('zeigt ohne Herkunft keine Zeile und sonst die Adressen (#599)', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')));
      expect(element('.karte-quellen')).toBeNull();
      expect(fixture.nativeElement.textContent).not.toContain('Keine Herkunft');

      zeigen(
        ausSuchergebnis(
          paket('commentary_result', {
            references: [{ reference_id: 'r-1', created: '', reference_text: 'https://example.org/studie' }],
          }),
        ),
      );
      expect(element<HTMLAnchorElement>('.quelle-link').getAttribute('href')).toBe('https://example.org/studie');
    });

    it('zeigt die Herkunft als Domain, die volle Adresse im Tooltip (#640, R47)', () => {
      const url = 'https://www.lfu.bayern.de/natur/vogelschutzwarte/vogelschlag/index.htm';
      zeigen(
        ausSuchergebnis(
          paket('commentary_result', {
            references: [{ reference_id: 'r-1', created: '', reference_text: url }],
          }),
        ),
      );

      const link = element<HTMLAnchorElement>('.quelle-link');
      expect(link.textContent!.trim()).toBe('lfu.bayern.de');
      expect(link.getAttribute('href')).toBe(url);
      expect(element('.quelle').textContent).toContain('Herkunft:');
      expect(component.quellenTooltip(component.daten.quellen[0])).toContain(url);
      expect(fixture.nativeElement.textContent).not.toContain('vogelschlag');
    });
  });

  describe('Titel als Link (#640, R48)', () => {
    function titelLink(): HTMLAnchorElement | null {
      return element<HTMLAnchorElement>('.karte-titel a.titel-link');
    }

    it('verlinkt den Titel auf die Beitragsseite', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')));

      expect(titelLink()!.getAttribute('href')).toBe('/beitrag/test-id');
      expect(titelLink()!.textContent!.trim()).toBe('Test Title');
    });

    it('verlinkt nicht auf der Beitragsseite selbst und nicht in der Vorschau', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')), { ansichtVerlinkt: false });
      expect(titelLink()).toBeNull();
      expect(element('.karte-titel').textContent!.trim()).toBe('Test Title');

      zeigen(ausSuchergebnis(paket('commentary_result')), { vorschau: true });
      expect(titelLink()).toBeNull();
    });

    it('verlinkt kompakte Karten nicht, die sind als Ganzes antippbar', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')), { variante: 'kompakt' });

      expect(element('a.titel-link')).toBeNull();
    });
  });

  describe('Lücke in der Vorlage (#640, R38)', () => {
    const MIT_LUECKE = 'Vögel und Klima. [Hier ein eigenes Erlebnis: Windpark in deiner Gegend] Deshalb ja.';

    it('hebt den Platzhalter als Feld hervor', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { text: MIT_LUECKE })));

      const luecken = fixture.nativeElement.querySelectorAll('.karte-text mark.vorlagen-luecke');
      expect(luecken.length).toBe(1);
      expect(luecken[0].textContent).toContain('[Hier ein eigenes Erlebnis: Windpark in deiner Gegend]');
      expect(element('.karte-text').textContent).toContain('Vögel und Klima. ');
      expect(element('.karte-text').textContent).toContain(' Deshalb ja.');
    });

    it('kopiert den Text unveraendert und erinnert an die Luecke', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { text: MIT_LUECKE })));

      element<HTMLButtonElement>('.kopieren-knopf').click();

      expect(TestBed.inject(Clipboard).copy).toHaveBeenCalledWith(MIT_LUECKE);
      expect(snackBar.open.calls.mostRecent().args[0]).toBe('Kopiert – füll noch den Platzhalter in [ ] aus.');
    });

    it('markiert ohne Platzhalter nichts', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { text: 'Siehe [1] und [sic].' })));

      expect(element('.vorlagen-luecke')).toBeNull();
      expect(element('.karte-text').textContent).toBe('Siehe [1] und [sic].');
    });
  });

  describe('Kopieren mit Herkunft (#641)', () => {
    const MIT_HERKUNFT = { references: [{ reference_id: 'r-1', created: '', reference_text: 'https://example.org/studie' }] };

    it('hat ohne Herkunft nur den Knopf, keine zweite Variante', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')));

      expect(aktionen().kopierText).toBe('Test text');
      expect(aktionen().zweiteKopie).toBeNull();
      expect(aktionen().kopierHinweis).toBe('Kopiert den Text');
    });

    it('kopiert am Kommentar den Text der angezeigten Fassung, mit Herkunft steht im Menue', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { short_text: 'Kurzfassung', ...MIT_HERKUNFT })));
      component.fassungWaehlen('kurz');
      fixture.detectChanges();

      expect(aktionen().kopierText).toBe('Kurzfassung');
      expect(aktionen().zweiteKopie).toEqual({
        text: 'Kurzfassung\n\nHerkunft: https://example.org/studie',
        wort: 'Mit Herkunft kopieren',
      });
      expect(aktionen().kopierHinweis).toBe('Kopiert den Text');
    });

    it('kopiert an der Hintergrundinfo Text samt Herkunft, nur Text steht im Menue', () => {
      zeigen(ausSuchergebnis(paket('generictext_result', { content_type: 'generictext', ...MIT_HERKUNFT })));

      expect(aktionen().kopierText).toBe('Test text\n\nHerkunft: https://example.org/studie');
      expect(aktionen().zweiteKopie).toEqual({ text: 'Test text', wort: 'Nur Text kopieren' });
      expect(aktionen().kopierHinweis).toBe('Kopiert Text und Herkunft');
    });

    it('kopiert an der Hintergrundinfo ohne Herkunft nur den Text', () => {
      zeigen(ausSuchergebnis(paket('generictext_result', { content_type: 'generictext' })));

      expect(aktionen().kopierText).toBe('Test text');
      expect(aktionen().zweiteKopie).toBeNull();
    });

    it('bietet am Post den Link als zweite Variante an', () => {
      zeigen(ausSuchergebnis(postPaket()));

      expect(aktionen().kopierText).toBe('Erneuerbare Energien konsequent ausbauen');
      expect(aktionen().zweiteKopie).toEqual({
        text: 'Erneuerbare Energien konsequent ausbauen\n\nHerkunft: https://social.example/posts/1',
        wort: 'Mit Herkunft kopieren',
      });
    });

    it('sagt am Bild, dass der Knopf die Bildunterschrift kopiert', () => {
      zeigen(ausSuchergebnis(paket('image_result', { content_type: 'image', image_url: 'https://example.org/dach.jpg', text: 'Solardach' })));

      expect(aktionen().kopierHinweis).toBe('Kopiert die Bildunterschrift');
      expect(aktionen().zweiteKopie).toBeNull();
    });

    it('zaehlt auch die zweite Variante als Nutzung an der Karte', fakeAsync(() => {
      zeigen(ausSuchergebnis(paket('commentary_result', { usage_count: 2, ...MIT_HERKUNFT })));

      aktionen().zweiteKopieren();
      fixture.detectChanges();

      expect(element('.karte-nutzung').textContent!.trim()).toBe('3× genutzt');
      tick(600);
    }));
  });

  describe('Zweck und Stil (#357)', () => {
    it('zeigt den Stil und markiert Beitraege fuer die eigenen Leute', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { zweck: 'eigene_leute', style: 'persoenlich' })));

      expect(element('.karte-eigene-leute')?.textContent).toContain('Für die eigenen Leute');
      expect(element('.karte-stil')?.textContent).toContain('persönlich');
    });

    it('markiert Kommentare fuer die Kommentarspalte nicht und zeigt ohne Stil keinen', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { zweck: 'kommentarspalte' })));

      expect(element('.karte-eigene-leute')).toBeNull();
      expect(element('.karte-stil')).toBeNull();
      expect(element('.karte-angaben')).toBeNull();
    });

    it('zeigt den Stil auch bei einem Kommentar fuer die Kommentarspalte', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { style: 'brueckenbauend' })));

      expect(element('.karte-eigene-leute')).toBeNull();
      expect(element('.karte-stil')?.textContent).toContain('brückenbauend');
    });

    it('zeigt den Stil als Chip, der beim Antippen erklaert, was er bewirkt (#641)', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { style: 'brueckenbauend' })));
      const chip = element<HTMLButtonElement>('button.karte-stil');

      expect(chip.getAttribute('aria-label')).toBe('Stil: brückenbauend, Erklärung öffnen');
      expect(getComputedStyle(chip).fontStyle).toBe('normal');
      chip.click();
      fixture.detectChanges();

      expect(document.querySelector('.stil-erklaerung')?.textContent!.trim()).toBe('brückenbauend: holt Unentschiedene ab');
    });

    it('zeigt Markierung und Stil auch in der kompakten Karte (Meine Beitraege)', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { zweck: 'eigene_leute', style: 'humorvoll' })), {
        variante: 'kompakt',
      });

      expect(element('.album-inhalt .karte-eigene-leute')?.textContent).toContain('Für die eigenen Leute');
      expect(element('.album-inhalt .karte-stil')?.textContent).toContain('humorvoll');
      // Die kompakte Karte ist als Ganzes antippbar: dort kein eigener Knopf, die Erklaerung als title
      expect(element('.album-inhalt button.karte-stil')).toBeNull();
      expect(element('.album-inhalt .karte-stil').getAttribute('title')).toBe('humorvoll: nimmt mit einem Augenzwinkern die Schärfe raus');
    });

    describe('Markierung fuer die eigenen Leute (Variante D, Tanne)', () => {
      const TANNE = 'rgb(0, 84, 55)'; // var(--primary-dark), #005437
      const WEISS = 'rgb(255, 255, 255)';

      function eigeneLeute(variante: KartenVariante = 'voll'): void {
        zeigen(ausSuchergebnis(paket('commentary_result', { zweck: 'eigene_leute' })), { variante });
      }

      it('setzt das Etikett weiss auf Tanne', () => {
        eigeneLeute();
        const etikett = getComputedStyle(element('.karte-eigene-leute'));
        const icon = getComputedStyle(element('.karte-eigene-leute .angabe-icon'));

        expect(etikett.backgroundColor).toBe(TANNE);
        expect(etikett.color).toBe(WEISS);
        expect(icon.color).toBe(WEISS);
        expect(etikett.fontWeight).toBe('600');
        expect(etikett.paddingLeft).toBe('8px');
        expect(etikett.paddingTop).toBe('1px');
        expect(etikett.borderTopLeftRadius).toBe('16px'); // var(--border-radius-large)
      });

      it('gibt der ganzen Karte links einen Rand in Tanne', () => {
        eigeneLeute();
        const karte = getComputedStyle(element('.karte'));

        expect(element('.karte').classList).toContain('karte--eigene-leute');
        expect(karte.borderLeftWidth).toBe('6px');
        expect(karte.borderLeftStyle).toBe('solid');
        expect(karte.borderLeftColor).toBe(TANNE);
      });

      it('auch die kompakte Karte bekommt den Rand', () => {
        eigeneLeute('kompakt');

        expect(element('.karte').classList).toContain('karte--eigene-leute');
      });

      it('weist ueber dem Kopieren-Knopf darauf hin', () => {
        eigeneLeute();
        const hinweis = element('.karte-fuss .eigene-leute-hinweis');

        expect(hinweis?.textContent?.trim()).toBe('Für die eigenen Leute – nicht für Kommentarspalten');
        expect(hinweis.nextElementSibling?.tagName.toLowerCase()).toBe('app-karten-aktionen');
        const stil = getComputedStyle(hinweis);
        expect(stil.fontSize).toBe('12px');
        expect(stil.textAlign).toBe('center');
        expect(stil.color).toBe(TANNE);
      });

      it('laesst Kommentare fuer die Kommentarspalte ohne Rand und ohne Hinweis', () => {
        zeigen(ausSuchergebnis(paket('commentary_result', { zweck: 'kommentarspalte', style: 'sachlich' })));

        expect(element('.karte').classList).not.toContain('karte--eigene-leute');
        expect(getComputedStyle(element('.karte')).borderLeftWidth).toBe('0px');
        expect(element('.eigene-leute-hinweis')).toBeNull();
      });
    });
  });

  describe('Fassungen (#355)', () => {
    function nutzungsMelder(): jasmine.SpyObj<UsageTrackingService> {
      return TestBed.inject(UsageTrackingService) as jasmine.SpyObj<UsageTrackingService>;
    }

    it('meldet beim Kopieren die angezeigte Fassung', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { short_text: 'Kurzfassung', long_text: 'Langfassung' })));

      component.fassungWaehlen('mittel');
      fixture.detectChanges();
      aktionen().kopieren();
      component.fassungWaehlen('kurz');
      fixture.detectChanges();
      aktionen().kopieren();
      component.fassungWaehlen('lang');
      fixture.detectChanges();
      aktionen().kopieren();

      expect(nutzungsMelder().trackContentUsage.calls.allArgs()).toEqual([
        ['test-id', 'mittel'],
        ['test-id', 'kurz'],
        ['test-id', 'lang'],
      ]);
    });

    it('meldet am Kommentar ohne weitere Fassungen Mittel', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')));

      aktionen().kopieren();

      expect(nutzungsMelder().trackContentUsage).toHaveBeenCalledWith('test-id', 'mittel');
    });

    it('meldet bei anderen Beitragstypen keine Fassung', () => {
      zeigen(ausSuchergebnis(paket('generictext_result')));

      aktionen().kopieren();

      expect(nutzungsMelder().trackContentUsage.calls.mostRecent().args).toEqual(['test-id', undefined]);
    });

    function meinBeitrag(): ContentResult {
      return {
        id: 'b-1',
        created: new Date().toISOString(),
        text: 'Mittelfassung',
        content_type: 'commentary',
        score: 0,
        title: 'Wärmepumpe lohnt sich auch im Altbau',
        short_text: 'Kurzfassung',
        usage_count: 9,
        nutzung_letzte_7_tage: 3,
        nutzung_je_fassung: {
          kurz: { nutzung: 3, letzte_7_tage: 1 },
          mittel: { nutzung: 4, letzte_7_tage: 0 },
        },
      };
    }

    function zeilen(auswahl: string): string[] {
      return Array.from(fixture.nativeElement.querySelectorAll('.nutzung-je-fassung li')).map((li) =>
        Array.from((li as HTMLElement).querySelectorAll(auswahl))
          .map((teil) => teil.textContent!.trim())
          .join(' '),
      );
    }

    it('zeigt in Meine Beitraege Nutzung und Zuwachs je Fassung', () => {
      zeigen(ausBeitrag(meinBeitrag()));

      // 9 insgesamt, 7 davon mit Fassung: 2 stammen aus der Zeit vor der Zaehlung je Fassung.
      // Vom Zuwachs 3 entfaellt 1 auf Kurz, der Rest von 2 auf "ohne Fassung".
      expect(zeilen('[aria-hidden="true"]')).toEqual(['Kurz 3× +1', 'Mittel 4×', 'ohne Fassung 2× +2']);
    });

    it('liest die Nutzung je Fassung in Worten vor', () => {
      zeigen(ausBeitrag(meinBeitrag()));

      expect(zeilen('.cdk-visually-hidden')).toEqual([
        'Kurz: 3-mal genutzt, 1 davon in den letzten 7 Tagen',
        'Mittel: 4-mal genutzt',
        'ohne Fassung: 2-mal genutzt, 2 davon in den letzten 7 Tagen',
      ]);
    });

    it('zeigt ausserhalb von Meine Beitraege keine Nutzung je Fassung', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { short_text: 'Kurzfassung' })));

      expect(element('.nutzung-je-fassung')).toBeNull();
    });
  });

  describe('Mobile Badge Display', () => {
    it('should show new badge for content created within 24 hours', () => {
      const vor12Stunden = new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString();
      zeigen(ausSuchergebnis(paket('commentary_result', { created: vor12Stunden })));

      expect(component.istNeu).toBeTrue();
      expect(element('.badge-neu')).toBeTruthy();
    });

    it('should not show new badge for content older than 24 hours', () => {
      const vor48Stunden = new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString();
      zeigen(ausSuchergebnis(paket('commentary_result', { created: vor48Stunden })));

      expect(component.istNeu).toBeFalse();
      expect(element('.badge-neu')).toBeNull();
    });

    it('should show trending badge for content with 5 or more uses', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { usage_count: 5 })));

      expect(component.istBeliebt).toBeTrue();
      expect(element('.badge-beliebt')).toBeTruthy();
    });

    it('should not show trending badge for content with less than 5 uses', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { usage_count: 3 })));

      expect(component.istBeliebt).toBeFalse();
      expect(element('.badge-beliebt')).toBeNull();
    });

    it('zeigt Nutzung und Kopieren lesbar gross statt 11/12 px (Nutzerfuehrung 13.11.)', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { usage_count: 2 })));

      expect(parseFloat(getComputedStyle(element('.karte-nutzung')).fontSize)).toBeGreaterThanOrEqual(14);
      expect(parseFloat(getComputedStyle(element('.kopieren-knopf')).fontSize)).toBeGreaterThanOrEqual(15);
    });

    it('zaehlt die Nutzung nach dem Kopieren hoch', fakeAsync(() => {
      zeigen(ausSuchergebnis(paket('commentary_result', { usage_count: 2 })));

      element<HTMLButtonElement>('.kopieren-knopf').click();
      fixture.detectChanges();

      expect(element('.karte-nutzung').textContent!.trim()).toBe('3× genutzt');
      tick(600);
    }));

    it('zaehlt die eigene Kopie auch dann nicht hoch, wenn die Anmeldung spaeter ankommt', fakeAsync(() => {
      const auth = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
      auth.getUserInfo.and.returnValue(null);
      userInfo$.next(null);
      const daten = ausSuchergebnis(paket('commentary_result', { usage_count: 2 }));
      zeigen({ ...daten, autor: 'test-user', eigen: true });

      auth.getUserInfo.and.returnValue({ isAuthenticated: true, userId: 'test-user' } as UserInfo);
      userInfo$.next({ isAuthenticated: true, userId: 'test-user' } as UserInfo);
      fixture.detectChanges();

      element<HTMLButtonElement>('.kopieren-knopf').click();
      fixture.detectChanges();

      expect(element('.karte-nutzung').textContent!.trim()).toBe('2× genutzt');
      tick(600);
    }));

    it('zaehlt die eigene Kopie nicht hoch', fakeAsync(() => {
      const daten = ausSuchergebnis(paket('commentary_result', { usage_count: 2 }));
      zeigen({ ...daten, autor: 'test-user', eigen: true });

      element<HTMLButtonElement>('.kopieren-knopf').click();
      fixture.detectChanges();

      expect(element('.karte-nutzung').textContent!.trim()).toBe('2× genutzt');
      tick(600);
    }));
  });

  describe('Voting', () => {
    beforeEach(() => zeigen(ausSuchergebnis(postPaket())));

    it('should initialize with no votes', () => {
      expect(aktionen().isLiked).toBeFalse();
      expect(aktionen().isDisliked).toBeFalse();
    });

    it('should set like when not voted', fakeAsync(() => {
      votingService.setLike.and.returnValue(of({} as any));

      aktionen().toggleLike();
      tick(50);

      expect(votingService.setLike).toHaveBeenCalledWith(POST_ID);
      expect(aktionen().isLiked).toBeTrue();
      expect(aktionen().isDisliked).toBeFalse();
    }));

    it('should remove like when already liked', fakeAsync(() => {
      aktionen().isLiked = true;
      votingService.removeLike.and.returnValue(of({} as any));

      aktionen().toggleLike();
      tick(50);

      expect(votingService.removeLike).toHaveBeenCalledWith(POST_ID);
      expect(aktionen().isLiked).toBeFalse();
    }));

    it('should set dislike when not voted', fakeAsync(() => {
      votingService.setDislike.and.returnValue(of({} as any));

      aktionen().toggleDislike();
      tick(50);

      expect(votingService.setDislike).toHaveBeenCalledWith(POST_ID);
      expect(aktionen().isDisliked).toBeTrue();
      expect(aktionen().isLiked).toBeFalse();
    }));

    it('should roll back and notify on vote error', fakeAsync(() => {
      votingService.setLike.and.returnValue(throwError(() => ({ status: 500 })));

      aktionen().toggleLike();
      expect(aktionen().isLiked).toBeTrue();
      tick(50);

      expect(snackBar.open).toHaveBeenCalledWith('Fehler beim Abstimmen', 'Schließen', { duration: 3000 });
      expect(aktionen().isLiked).toBeFalse();
    }));

    it('should apply active-button class when liked', () => {
      zeigen(ausSuchergebnis(postPaket({ user_vote: 'like' })));

      const knoepfe = fixture.nativeElement.querySelectorAll('.stimme-knopf');
      expect(knoepfe[0].classList.contains('active-button')).toBeTrue();
    });
  });

  describe('Statement', () => {
    function alsAdmin(): void {
      const auth = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
      auth.getUserInfo.and.returnValue({ isAuthenticated: true, userId: 'test-user', isAdmin: true } as UserInfo);
    }

    it('zeigt Nutzer:innen die Aussage ganz, ohne Aufklapper und ohne Prozentwerte (#640, R39)', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', {}, { statement_similarity_score: 1.13 })));

      const zeile = element('.statement-zeile');
      expect(zeile.classList).toContain('statement-zeile--fest');
      expect(zeile.getAttribute('role')).toBeNull();
      expect(zeile.getAttribute('aria-expanded')).toBeNull();
      expect(element('.statement-pfeil')).toBeNull();
      expect(element('.statement-vorschau').textContent).toContain('Test statement');
      expect(getComputedStyle(element('.statement-vorschau')).whiteSpace).toBe('normal');

      zeile.click();
      fixture.detectChanges();
      expect(element('.statement-details')).toBeNull();
      expect(fixture.nativeElement.textContent).not.toContain('%');
    });

    it('zeigt die Aussage ohne Anmeldung ebenso ohne Werte', () => {
      const auth = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
      auth.getUserInfo.and.returnValue(null);
      zeigen(ausSuchergebnis(paket('commentary_result')));

      expect(element('.statement-zeile--fest')).not.toBeNull();
      expect(fixture.nativeElement.textContent).not.toContain('Suchübereinstimmung');
    });

    it('zeigt Admins die Aussage zugeklappt und klappt sie mit den Werten im Fluss auf', () => {
      alsAdmin();
      zeigen(ausSuchergebnis(paket('commentary_result')));
      expect(element('.statement-vorschau').textContent).toContain('Test statement');
      expect(element('.statement-details')).toBeNull();

      element('.statement-zeile').click();
      fixture.detectChanges();

      const details = element('.statement-details');
      expect(getComputedStyle(details).position).toBe('static');
      expect(details.textContent).toContain('Suchübereinstimmung: 90%');
      expect(details.textContent).toContain('Antwortqualität: 85%');
      expect(element('.statement-zeile').getAttribute('aria-expanded')).toBe('true');
    });

    it('zeigt die Aussage als Kontextzeile vor Titel und Text (#599)', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')));
      const statement = element('.statement');
      const kopf = element('.karte-kopf');
      expect(statement.compareDocumentPosition(kopf) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it('zeigt "0× genutzt" nicht, erst ab 1 (#640, R44)', fakeAsync(() => {
      zeigen(ausSuchergebnis(paket('commentary_result', { usage_count: 0 })));
      expect(element('.karte-nutzung')).toBeNull();
      expect(fixture.nativeElement.textContent).not.toContain('genutzt');

      element<HTMLButtonElement>('.kopieren-knopf').click();
      fixture.detectChanges();
      expect(element('.karte-nutzung').textContent!.trim()).toBe('1× genutzt');
      tick(600);
    }));

    it('zeigt die Nutzung beschriftet in der Meta-Zeile statt als Kreis im Kopf (#599)', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { usage_count: 1 })));
      expect(element('.karte-kopf .badge-nutzung')).toBeNull();
      expect(element('.karte-meta').textContent).toContain('1× genutzt');
    });

    it('zeigt ohne Aussage keinen Aufklapper', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', {}, { statement_text: '' })));

      expect(element('.statement')).toBeNull();
    });
  });

  describe('Text', () => {
    it('wechselt zwischen Kurz, Standard und Lang und kopiert die angezeigte Fassung', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { short_text: 'Kurzfassung', long_text: 'Langfassung' })));
      expect(element('.karte-text').textContent!.trim()).toBe('Kurzfassung');

      component.fassungWaehlen('lang');
      fixture.detectChanges();

      expect(element('.karte-text').textContent!.trim()).toBe('Langfassung');
      expect(aktionen().kopierText).toBe('Langfassung');
    });

    it('beschriftet die Reiter mit Fassung und Zeichenzahl (#641)', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { short_text: 'Kurzfassung', long_text: 'Langfassung' })));
      const knoepfe = Array.from(fixture.nativeElement.querySelectorAll('.textlaenge mat-button-toggle')) as HTMLElement[];

      expect(knoepfe.map((knopf) => knopf.textContent!.replace(/\s+/g, ' ').trim())).toEqual([
        'Kurz · 11',
        'Mittel · 9',
        'Lang · 11',
      ]);
      expect(knoepfe[0].querySelector('button')!.getAttribute('aria-label')).toBe('Kurz, 11 Zeichen');
    });

    it('zeigt nur die vorhandenen Fassungen als Reiter', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { long_text: 'Langfassung' })));
      const beschriftungen = Array.from(fixture.nativeElement.querySelectorAll('.textlaenge mat-button-toggle')).map(
        (knopf) => (knopf as HTMLElement).textContent!.replace(/\s+/g, ' ').trim(),
      );

      expect(beschriftungen).toEqual(['Mittel · 9', 'Lang · 11']);
    });

    it('waehlt die kuerzeste Fassung vor, die auf X passt (#641)', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { short_text: 'Kurzfassung', long_text: 'Langfassung' })));
      expect(component.angezeigteFassung).toBe('kurz');
      expect(element('.textlaenge .mat-button-toggle-checked').textContent).toContain('Kurz');

      zeigen(ausSuchergebnis(paket('commentary_result', { text: 'M'.repeat(200), long_text: 'L'.repeat(900) })));
      expect(component.angezeigteFassung).toBe('mittel');

      zeigen(ausSuchergebnis(paket('commentary_result', { text: 'M'.repeat(400), long_text: 'L'.repeat(900) })));
      expect(component.angezeigteFassung).toBe('mittel');
    });

    it('bleibt in der Formular-Vorschau beim Tippen bei der gewaehlten Fassung', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { short_text: 'Kurzfassung' })), { vorschau: true });
      expect(component.angezeigteFassung).toBe('mittel');

      component.fassungWaehlen('kurz');
      fixture.componentRef.setInput('daten', ausSuchergebnis(paket('commentary_result', { short_text: 'Kurzfassung', text: 'Neuer Text' })));
      fixture.detectChanges();
      expect(component.angezeigteFassung).toBe('kurz');

      component.fassungWaehlen('mittel');
      fixture.componentRef.setInput('daten', ausSuchergebnis(paket('commentary_result', { short_text: 'Kurzfassung', text: 'Neuer Text 2' })));
      fixture.detectChanges();
      expect(component.angezeigteFassung).toBe('mittel');
    });

    it('behaelt die Reiter beim Wechsel der Fassung, damit der Fokus bleibt', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { short_text: 'Kurzfassung', long_text: 'Langfassung' })));
      const vorher = element('.textlaenge mat-button-toggle');

      component.fassungWaehlen('lang');
      fixture.detectChanges();

      expect(element('.textlaenge mat-button-toggle')).toBe(vorher);
    });

    it('setzt die Marke "passt auf X/Bluesky" nur, wenn die angezeigte Fassung passt', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { text: 'M'.repeat(400), short_text: 'Kurzfassung' })));
      expect(element('.fassung-marke')?.textContent).toContain('passt auf X/Bluesky');

      component.fassungWaehlen('mittel');
      fixture.detectChanges();
      expect(element('.fassung-marke')).toBeNull();
    });

    it('zeichnet die gewaehlte Fassung wie die Tabs: Tanne-Text auf Tanne-Hauch (#512)', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { short_text: 'Kurzfassung', long_text: 'Langfassung' })));
      const gewaehlt = element('.textlaenge .mat-button-toggle-checked');

      expect(getComputedStyle(gewaehlt).color).toBe('rgb(0, 84, 55)');
      expect(getComputedStyle(gewaehlt).backgroundColor).toBe('rgba(0, 84, 55, 0.07)');
    });

    it('zeigt ohne Kurz- und Langfassung keinen Umschalter', () => {
      zeigen(ausSuchergebnis(paket('generictext_result')));

      expect(element('.textlaenge')).toBeNull();
    });

    it('zeigt bei leerer oder nur aus Leerzeichen bestehender Fassung keinen Umschalter', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { short_text: '', long_text: '   ' })));

      expect(element('.textlaenge')).toBeNull();
    });

    it('kuerzt langen Text und klappt ihn mit "mehr" auf', () => {
      zeigen(ausSuchergebnis(paket('generictext_result', { text: 'Sehr langer Text. '.repeat(200) })));

      component.pruefeKuerzung();
      fixture.detectChanges();
      const knopf = element<HTMLButtonElement>('.mehr-knopf');
      expect(knopf.textContent!.trim()).toBe('mehr');

      knopf.click();
      fixture.detectChanges();

      expect(element('.karte-text').classList).toContain('aufgeklappt');
      expect(element('.mehr-knopf').textContent!.trim()).toBe('weniger');
    });

    it('zeigt bei kurzem Text keinen "mehr"-Knopf', () => {
      zeigen(ausSuchergebnis(paket('generictext_result')));

      component.pruefeKuerzung();
      fixture.detectChanges();

      expect(element('.mehr-knopf')).toBeNull();
    });
  });

  describe('Varianten (#356)', () => {
    it('zeigt "N Varianten" als Link auf ihre Liste', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { varianten: 3 })));

      const link = element<HTMLAnchorElement>('.karte-varianten');
      expect(link.textContent!.trim()).toContain('3 Varianten');
      expect(link.getAttribute('href')).toBe('/varianten/test-id');
    });

    it('sagt "1 Variante" in der Einzahl', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { varianten: 1 })));

      expect(element('.karte-varianten').textContent!.trim()).toContain('1 Variante');
    });

    it('zeigt nichts ohne Varianten und nichts in der Vorschau', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')));
      expect(element('.karte-varianten')).toBeNull();

      zeigen(ausSuchergebnis(paket('commentary_result', { varianten: 2 })), { vorschau: true });
      expect(element('.karte-varianten')).toBeNull();
    });
  });

  describe('Vorschau', () => {
    it('laesst ohne Datum das "·" in der Meta-Zeile weg', () => {
      zeigen({ ...ausSuchergebnis(paket('commentary_result')), erstellt: '', autorName: 'Du' }, { vorschau: true });

      expect(element('.karte-meta').textContent!.trim()).toBe('Von: Du');
    });

    it('reicht die Vorschau an die Aktionen weiter', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')), { vorschau: true });

      expect(aktionen().vorschau).toBeTrue();
      expect(fixture.debugElement.query(By.directive(KartenAktionenComponent)).nativeElement.classList).toContain(
        'ist-vorschau',
      );
    });

    // Design-Audit A2 (#512): Die feste Breite von 450 px liess die Vorschau aus dem
    // Formularrahmen ragen; als Vorschau fuellt die Karte ihre Spalte, hoechstens 450 px.
    it('fuellt als Vorschau ihre Spalte statt fester 450 px', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')), { vorschau: true });
      const spalte = document.createElement('div');
      spalte.style.width = '400px';
      spalte.appendChild(fixture.nativeElement);
      document.body.appendChild(spalte);

      expect(element('.karte').classList).toContain('karte--vorschau');
      expect(element('.karte').getBoundingClientRect().width).toBe(400);
      spalte.style.width = '600px';
      expect(element('.karte').getBoundingClientRect().width).toBe(450);
      spalte.remove();
    });
  });
  describe('Kompakt', () => {
    it('zeigt als Album Symbol im Kopf, Titel und Anriss auf zwei Zeilen, Datum und Nutzung im Fuss', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { usage_count: 7, created: '2026-09-13T12:00:00' })), {
        variante: 'kompakt',
      });
      const karte = element('.karte');

      expect(karte.classList).toContain('karte--kompakt');
      expect(karte.classList).toContain('typ-commentary');
      expect(element('.karte-kopf .karte-icon').textContent!.trim()).toBe('💬');
      expect(element('.karte-kopf .karte-titel')).toBeNull();
      expect(element('.karte-kopf .karte-badges')).toBeNull();
      expect(element('.album-inhalt .karte-titel').textContent).toContain('Test Title');
      expect(getComputedStyle(element('.karte-titel')).webkitLineClamp).toBe('2');
      expect(getComputedStyle(element('.karte-titel')).fontSize).toBe('15px');
      expect(element('.album-anriss').textContent).toContain('Test text');
      expect(getComputedStyle(element('.album-anriss')).webkitLineClamp).toBe('2');
      expect(getComputedStyle(element('.album-anriss')).fontSize).toBe('13px');
      expect(element('.album-fuss .karte-datum').textContent!.trim()).toBe('13.09.2026');
      expect(element('.album-fuss .badge-nutzung').textContent!.trim()).toBe('7× genutzt');
      expect(getComputedStyle(element('.album-fuss .badge-nutzung')).fontSize).toBe('15px');
      expect(element('.badge-nutzung').classList).not.toContain('ungenutzt');
      expect(element('.statement')).toBeNull();
      expect(element('.karte-text')).toBeNull();
      expect(element('.karte-meta')).toBeNull();
      expect(element('app-karten-aktionen')).toBeNull();
    });

    it('zeigt ein Bild im Kopfband erst auf Klick, das Symbol darauf, mit dem Titel als alt (#447)', () => {
      const daten = ausSuchergebnis(
        paket('image_result', { content_type: 'image', title: 'Solardach der Schule', image_url: 'https://example.org/dach.jpg' }),
      );

      zeigen(daten, { variante: 'kompakt' });
      const angetippt = jasmine.createSpy('angetippt');
      component.angetippt.subscribe(angetippt);

      expect(element('.karte-kopf').classList).toContain('karte-kopf--bild');
      expect(element('.karte-kopf img')).toBeNull();
      const knopf = element<HTMLButtonElement>('.karte-kopf .kopf-bild button.bild-laden');
      expect(knopf.getAttribute('aria-label')).toBe('Bild laden: Solardach der Schule');
      expect(knopf.querySelector('.bild-laden-symbol')).toBeNull();

      knopf.click();
      fixture.detectChanges();
      const bild = element<HTMLImageElement>('.karte-kopf .kopf-bild img');

      expect(angetippt).not.toHaveBeenCalled();
      expect(bild.getAttribute('src')).toBe('https://example.org/dach.jpg');
      expect(bild.alt).toBe('Solardach der Schule');
      expect(getComputedStyle(bild).objectFit).toBe('cover');
      expect(element('.karte-kopf .karte-icon').textContent!.trim()).toBe('🖼️');
    });

    it('laedt kein fremdes Bild, bevor jemand "Bild laden" waehlt, auch nicht im Kopfband (#447)', () => {
      const daten = ausSuchergebnis(
        paket('image_result', { content_type: 'image', title: 'Dach', image_url: 'https://example.org/dach.jpg' }),
      );

      zeigen(daten);
      expect(fixture.nativeElement.querySelectorAll('img').length).toBe(0);
      expect(element('.karte-bild button.bild-laden').textContent).toContain('Bild laden');

      zeigen(daten, { variante: 'kompakt' });
      expect(fixture.nativeElement.querySelectorAll('img').length).toBe(0);
    });

    it('stellt in voller und kompakter Karte ohne Klick keine Anfrage an den fremden Server (#447)', async () => {
      const anfragen = new Anfragen();
      anfragen.starten();
      try {
        const voll = fremdeAdresse();
        const kompakt = fremdeAdresse();
        zeigen(ausSuchergebnis(paket('image_result', { content_type: 'image', title: 'Dach', image_url: voll })));
        zeigen(ausSuchergebnis(paket('image_result', { content_type: 'image', title: 'Dach', image_url: kompakt })), {
          variante: 'kompakt',
        });

        const angefragt = await anfragen.abwarten();
        expect(angefragt).not.toContain(voll);
        expect(angefragt).not.toContain(kompakt);

        element<HTMLButtonElement>('.karte-kopf button.bild-laden').click();
        fixture.detectChanges();
        await bildFertig(element<HTMLImageElement>('.karte-kopf img'));
        expect(await anfragen.abwarten()).toContain(kompakt);
      } finally {
        anfragen.beenden();
      }
    });

    it('laesst das Kopfband ohne Bild wie bisher und aendert die volle Karte nicht', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')), { variante: 'kompakt' });
      expect(element('.kopf-bild')).toBeNull();
      expect(element('.karte-kopf').classList).not.toContain('karte-kopf--bild');

      zeigen(ausSuchergebnis(paket('image_result', { content_type: 'image', image_url: 'https://example.org/dach.jpg' })));
      expect(element('.kopf-bild')).toBeNull();
      expect(element('.karte-bild app-fremdes-bild')).not.toBeNull();
    });

    it('zeigt ohne oder mit unbekannter Nutzung dezent "Noch nicht genutzt"', () => {
      const daten = ausSuchergebnis(paket('commentary_result', { usage_count: 0 }));

      zeigen(daten, { variante: 'kompakt' });
      expect(element('.badge-nutzung').textContent!.trim()).toBe('Noch nicht genutzt');
      expect(element('.badge-nutzung').classList).toContain('ungenutzt');

      zeigen({ ...daten, nutzung: null }, { variante: 'kompakt' });
      expect(element('.badge-nutzung').textContent!.trim()).toBe('Noch nicht genutzt');
      expect(element('.badge-nutzung').classList).toContain('ungenutzt');
    });

    it('zeigt im Fuss den Zuwachs der letzten 7 Tage ausgeschrieben unter der Nutzung', () => {
      const daten = { ...ausSuchergebnis(paket('commentary_result', { usage_count: 7 })), nutzungLetzte7Tage: 2 };

      zeigen(daten, { variante: 'kompakt' });
      const zuwachs = element('.album-fuss .nutzung-zuwachs');

      expect(zuwachs.textContent!.trim()).toBe('+2 diese Woche');
      expect(getComputedStyle(zuwachs).fontSize).toBe('13px');
      expect(element('.album-fuss .badge-nutzung').textContent!.trim()).toBe('7× genutzt');
    });

    it('zeigt ohne Zuwachs keinen Zuwachs', () => {
      const daten = ausSuchergebnis(paket('commentary_result', { usage_count: 7 }));

      zeigen({ ...daten, nutzungLetzte7Tage: 0 }, { variante: 'kompakt' });
      expect(element('.nutzung-zuwachs')).toBeNull();

      zeigen(daten, { variante: 'kompakt' });
      expect(element('.nutzung-zuwachs')).toBeNull();
    });

    it('meldet kompakt den Tipp, voll nicht', () => {
      const daten = ausSuchergebnis(paket('commentary_result'));
      zeigen(daten, { variante: 'kompakt' });
      const kompakt = jasmine.createSpy('kompakt');
      component.angetippt.subscribe(kompakt);

      element('.karte').click();

      expect(kompakt).toHaveBeenCalledOnceWith(daten);
      expect(element('.karte').getAttribute('role')).toBe('link');
      expect(element('.karte').getAttribute('tabindex')).toBe('0');

      zeigen(daten);
      const voll = jasmine.createSpy('voll');
      component.angetippt.subscribe(voll);

      element('.karte').click();

      expect(voll).not.toHaveBeenCalled();
      expect(element('.karte').getAttribute('role')).toBeNull();
    });
  });

  describe('Kopf', () => {
    it('zeigt aus einem Einwurf das Sandband mit Link und dem einen Satz, ohne Saetze, Aktionen und Meta', () => {
      const daten: KartenDaten = {
        id: 'e-1',
        typ: null,
        titel: 'Gute Antwort in den Kommentaren',
        text: null,
        erstellt: new Date().toISOString(),
        autor: 'jemand',
        autorName: null,
        nutzung: null,
        quellen: [],
        einwurfAngaben: {
          einwurfId: 'e-1',
          stufe: 'destilliert',
          herkunft: 'Instagram',
          link: 'https://www.instagram.com/reel/ABC/',
          linkText: 'instagram.com/reel/ABC',
          saetze: [{ id: 's-1', text: 'Erster Satz', beitraege: 0 } as any, { id: 's-2', text: 'Zweiter', beitraege: 1 } as any],
          beitraege: [],
          beitragZustand: null,
          verwerfbar: true,
          kopfSatz: 'Wärmepumpen lohnen sich im Altbau',
        },
      };

      zeigen(daten, { variante: 'kopf' });

      expect(element('.karte').classList).toContain('stufe-destilliert');
      expect(element('.einwurf-band .einwurf-titel').textContent).toContain('Gute Antwort in den Kommentaren');
      expect(element('.einwurf-herkunft').textContent).toContain('Instagram');
      expect(element('.einwurf-kopfsatz').textContent).toContain('Wärmepumpen lohnen sich im Altbau');
      expect(element('.einwurf-saetze')).toBeNull();
      expect(element('.einwurf-aktion')).toBeNull();
      expect(element('.einwurf-menue')).toBeNull();
      expect(element('.einwurf-meta')).toBeNull();
    });

    it('zeigt nur das Band mit Symbol und Titel der Aussage', () => {
      zeigen(ausAussage('a-1', 'Die Grünen wollen uns das Autofahren verbieten'), { variante: 'kopf' });

      expect(element('.karte').classList).toContain('karte--kopf');
      expect(element('.karte').classList).toContain('typ-statement');
      expect(element('.karte-icon').textContent!.trim()).toBe('🗨️');
      expect(element('.karte-titel').textContent!.trim()).toBe('Die Grünen wollen uns das Autofahren verbieten');
      expect(element('.karte-badges')).toBeNull();
      expect(element('.karte-inhalt')).toBeNull();
      expect(element('app-karten-aktionen')).toBeNull();
      expect(element('.album-fuss')).toBeNull();
      expect(element('.karte').getAttribute('role')).toBeNull();
    });
  });

  describe('Verwerfen', () => {
    function einwurfKarte(felder: Partial<Einwurf> = {}): KartenDaten {
      return ausEinwurf({
        id: 'e-1',
        content: 'Hinweis',
        url: null,
        image_url: null,
        submitted_by: 'bob',
        source_channel: 'web',
        status: 'open',
        created_at: '2026-09-13T12:00:00Z',
        drafts: [],
        links: [],
        ...felder,
      });
    }

    function alsNutzer(nutzer: Partial<UserInfo>): void {
      const auth = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
      auth.getUserInfo.and.returnValue({ isAuthenticated: true, userId: 'test-user', ...nutzer } as UserInfo);
    }

    it('erlaubt Admins das Verwerfen fremder und einwerferloser Einwuerfe', () => {
      alsNutzer({ isAdmin: true });

      zeigen(einwurfKarte(), { variante: 'einwurf' });
      expect(component.darfVerwerfen).toBeTrue();

      zeigen(einwurfKarte({ submitted_by: null }), { variante: 'einwurf' });
      expect(component.darfVerwerfen).toBeTrue();
    });

    it('erlaubt Mitwirkenden ohne Adminrechte nur eigene Einwuerfe', () => {
      alsNutzer({ isAdmin: false });

      zeigen(einwurfKarte(), { variante: 'einwurf' });
      expect(component.darfVerwerfen).toBeFalse();

      zeigen(einwurfKarte({ submitted_by: 'test-user', ist_eigener_einwurf: true }), { variante: 'einwurf' });
      expect(component.darfVerwerfen).toBeTrue();
    });

    it('nennt im Band die Stufe des Einwurfs, wie das Glossar sie nennt', () => {
      zeigen(einwurfKarte(), { variante: 'einwurf' });
      expect(component.stufenName).toBe('Offen');
      expect(element('.karte').classList).toContain('stufe-offen');

      zeigen(
        einwurfKarte({ status: 'in_progress', drafts: [{ id: 's-1', sentence: 'Ein Satz' } as any] }),
        { variante: 'einwurf' },
      );
      expect(component.stufenName).toBe('Destilliert');

      zeigen(einwurfKarte({ status: 'discarded' }), { variante: 'einwurf' });
      expect(component.stufenName).toBe('Verworfen');

      zeigen(
        einwurfKarte({ status: 'processed', links: [{ content_id: 'c-1', content_type: null, draft_id: null } as any] }),
        { variante: 'einwurf' },
      );
      expect(component.stufenName).toBe('Ausformuliert');

      zeigen(
        einwurfKarte({ status: 'processed', links: [{ content_id: 'c-1', content_type: 'commentary', draft_id: null } as any] }),
        { variante: 'einwurf' },
      );
      expect(component.stufenName).toBe('Ausformuliert: Kommentar');
      expect(element('.karte-icon').getAttribute('aria-label')).toBe('Ausformuliert: Kommentar');
    });

    it('schreibt die Stufe in die Meta-Zeile, wenn die Seite das will (Meine Einwuerfe)', () => {
      zeigen(
        einwurfKarte({
          submitted_by: 'test-user',
          status: 'processed',
          links: [{ content_id: 'c-1', content_type: 'commentary', draft_id: null } as any],
        }),
        { variante: 'einwurf', stufeZeigen: true },
      );

      expect(element('.einwurf-stufe').textContent!.trim()).toBe('Ausformuliert: Kommentar');
      // Alle Einwuerfe dort sind die eigenen - "Von: Du" saehe auf jeder Karte gleich aus.
      expect(element('.einwurf-einwerfer')).toBeNull();
    });

    it('nennt einen verworfenen Einwurf mit stufeZeigen nur einmal verworfen', () => {
      zeigen(einwurfKarte({ status: 'discarded' }), { variante: 'einwurf', stufeZeigen: true });

      expect(element('.einwurf-stufe').textContent!.trim()).toBe('Verworfen');
      expect(element('.einwurf-verworfen')).toBeNull();
    });

    it('nennt ohne stufeZeigen den Einwerfer und keine Stufe in der Meta-Zeile', () => {
      zeigen(einwurfKarte(), { variante: 'einwurf' });

      expect(element('.einwurf-einwerfer').textContent).toContain('Von:');
      expect(element('.einwurf-stufe')).toBeNull();
    });

    it('erlaubt auch Admins kein Verwerfen von Ausformuliertem', () => {
      alsNutzer({ isAdmin: true });

      zeigen(einwurfKarte({ status: 'processed' }), { variante: 'einwurf' });

      expect(component.darfVerwerfen).toBeFalse();
    });
  });
  describe('Einwurf quer (Fangkorb am Desktop)', () => {
    function einwurfKarte(): KartenDaten {
      return ausEinwurf({
        id: 'e-quer',
        content: 'Hinweis',
        url: 'https://www.instagram.com/reel/ABC/',
        image_url: null,
        submitted_by: 'bob',
        source_channel: 'web',
        status: 'open',
        created_at: '2026-09-13T12:00:00Z',
        drafts: [],
        links: [],
      });
    }

    it('steht ohne quer wie bisher: Griff ueber der Meta-Zeile', () => {
      zeigen(einwurfKarte(), { variante: 'einwurf' });
      fixture.nativeElement.style.display = 'block';
      fixture.nativeElement.style.width = '700px';

      expect(element('.karte').classList).not.toContain('karte--quer');
      const griff = element('.einwurf-primaer').getBoundingClientRect();
      const meta = element('.einwurf-meta').getBoundingClientRect();
      expect(meta.top).toBeGreaterThanOrEqual(griff.bottom);
    });

    it('stellt quer Meta links und Griff mit Menue rechts in eine Zeile', () => {
      zeigen(einwurfKarte(), { variante: 'einwurf', quer: true });
      fixture.nativeElement.style.display = 'block';
      fixture.nativeElement.style.width = '700px';

      expect(element('.karte').classList).toContain('karte--quer');
      const griff = element('.einwurf-primaer').getBoundingClientRect();
      const meta = element('.einwurf-meta').getBoundingClientRect();
      expect(meta.right).toBeLessThanOrEqual(griff.left);
      expect(meta.top).toBeLessThan(griff.bottom);
      expect(meta.bottom).toBeGreaterThan(griff.top);
      // Tab-Reihenfolge wie hochkant: erst der Griff, die Meta-Zeile hat keinen Tab-Stopp
      expect(element('.einwurf-fuss').firstElementChild!.classList).toContain('einwurf-aktion');
    });

    it('wirkt im Kopf nicht', () => {
      zeigen(einwurfKarte(), { variante: 'kopf', quer: true });

      expect(element('.karte').classList).not.toContain('karte--quer');
      expect(element('.einwurf-fuss')).toBeNull();
    });
  });
});
