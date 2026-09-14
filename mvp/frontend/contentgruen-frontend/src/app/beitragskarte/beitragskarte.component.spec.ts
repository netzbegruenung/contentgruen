import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';

import { BeitragskarteComponent } from './beitragskarte.component';
import { KartenAktionenComponent } from './karten-aktionen/karten-aktionen.component';
import { KartenDaten, ausSuchergebnis } from './karten-daten';
import { AuthService } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { VotingService } from '../services/voting.service';

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

    await TestBed.configureTestingModule({
      imports: [BeitragskarteComponent, NoopAnimationsModule],
      providers: [
        { provide: VotingService, useValue: votingService },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: AuthService, useValue: authServiceSpy },
        { provide: Clipboard, useValue: jasmine.createSpyObj('Clipboard', ['copy']) },
        { provide: UsageTrackingService, useValue: jasmine.createSpyObj('UsageTrackingService', ['trackContentUsage']) },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['error', 'debug', 'info', 'warn']) },
        { provide: MatDialog, useValue: jasmine.createSpyObj('MatDialog', ['open']) },
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
      const bild = element<HTMLImageElement>('.karte-bild img');

      expect(bild.getAttribute('src')).toBe('https://example.org/dach.jpg');
      expect(bild.alt).toBe('Solardach');
      expect(getComputedStyle(element('.karte-titel')).webkitLineClamp).toBe('4');
      expect(element('.kopieren-knopf').textContent).toContain('Bildunterschrift kopieren');
    });

    it('zeigt die gekuerzte Kennung, solange es keinen Anzeigenamen gibt', () => {
      const daten = ausSuchergebnis(paket('commentary_result'));
      zeigen(daten);
      expect(element('.karte-meta').textContent).toContain('Von: 0f3c2a9e');

      zeigen({ ...daten, autorName: 'Kim Grün' });
      expect(element('.karte-meta').textContent).toContain('Von: Kim Grün');
    });

    it('zeigt ohne Herkunft einen Hinweis und sonst die Adressen', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')));
      expect(element('.quellen-leer').textContent).toContain('Keine Herkunft hinterlegt');

      zeigen(
        ausSuchergebnis(
          paket('commentary_result', {
            references: [{ reference_id: 'r-1', created: '', reference_text: 'https://example.org/studie' }],
          }),
        ),
      );
      expect(element<HTMLAnchorElement>('.quelle-link').getAttribute('href')).toBe('https://example.org/studie');
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

    it('zaehlt die Nutzung nach dem Kopieren hoch', fakeAsync(() => {
      zeigen(ausSuchergebnis(paket('commentary_result', { usage_count: 2 })));

      element<HTMLButtonElement>('.kopieren-knopf').click();
      fixture.detectChanges();

      expect(element('.badge-nutzung').textContent!.trim()).toBe('3x');
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
    it('zeigt die Aussage zugeklappt und klappt sie im Fluss auf', () => {
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

    it('zeigt ohne Aussage keinen Aufklapper', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', {}, { statement_text: '' })));

      expect(element('.statement')).toBeNull();
    });
  });

  describe('Text', () => {
    it('wechselt zwischen Kurz, Standard und Lang und kopiert die angezeigte Fassung', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { short_text: 'Kurzfassung', long_text: 'Langfassung' })));
      expect(element('.karte-text').textContent!.trim()).toBe('Test text');

      component.textModusSetzen('short');
      fixture.detectChanges();

      expect(element('.karte-text').textContent!.trim()).toBe('Kurzfassung');
      expect(aktionen().kopierText).toBe('Kurzfassung');
    });

    it('beschriftet den Umschalter mit Kurz, Mittel und Lang', () => {
      zeigen(ausSuchergebnis(paket('commentary_result', { short_text: 'Kurzfassung', long_text: 'Langfassung' })));
      const beschriftungen = Array.from(fixture.nativeElement.querySelectorAll('.textlaenge mat-button-toggle')).map(
        (knopf) => (knopf as HTMLElement).textContent!.trim(),
      );

      expect(beschriftungen).toEqual(['Kurz', 'Mittel', 'Lang']);
    });

    it('zeigt ohne Kurz- und Langfassung keinen Umschalter', () => {
      zeigen(ausSuchergebnis(paket('generictext_result')));

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

  describe('Vorschau', () => {
    it('reicht die Vorschau an die Aktionen weiter', () => {
      zeigen(ausSuchergebnis(paket('commentary_result')), { vorschau: true });

      expect(aktionen().vorschau).toBeTrue();
      expect(fixture.debugElement.query(By.directive(KartenAktionenComponent)).nativeElement.classList).toContain(
        'ist-vorschau',
      );
    });
  });
});
