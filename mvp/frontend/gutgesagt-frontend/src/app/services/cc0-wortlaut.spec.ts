import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { CommentaryService } from './commentary.service';
import { GenericTextService } from './generic-text.service';
import { ImageService } from './image.service';
import { PostService } from './post.service';
import { LoggingService } from './logging.service';
import { CONSENT_HINWEIS } from '../shared/consent-hinweis';

/**
 * Jeder Beitrag geht mit der Kennung des CC0-Hinweises raus, den das Formular zeigt
 * (#431); der Dienst speichert sie am Beitrag.
 */
describe('Kennung des CC0-Hinweises beim Speichern eines Beitrags', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: LoggingService,
          useValue: jasmine.createSpyObj('LoggingService', ['debug', 'error', 'warn', 'info']),
        },
      ],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function body(pfad: string): Record<string, unknown> {
    const anfrage = http.expectOne((req) => req.url.endsWith(pfad));
    anfrage.flush({ id: 'neu' });
    return anfrage.request.body;
  }

  it('Kommentar', () => {
    TestBed.inject(CommentaryService)
      .addCommentary({ commentary: { title: 't', text: 'x' }, references: [] } as never)
      .subscribe();

    expect(body('/addCommentary')['cc0_wortlaut']).toBe(CONSENT_HINWEIS.kennung);
  });

  it('Hintergrundinfo', () => {
    TestBed.inject(GenericTextService)
      .addGenericText({ generictext: { title: 't', text: 'x' }, references: [] } as never)
      .subscribe();

    expect(body('/addGenericText')['cc0_wortlaut']).toBe(CONSENT_HINWEIS.kennung);
  });

  it('Bild', () => {
    TestBed.inject(ImageService)
      .addImage({ image: { title: 't', image_url: 'https://example.org/a.jpg', text: 'x' } } as never)
      .subscribe();

    expect(body('/addImage')['cc0_wortlaut']).toBe(CONSENT_HINWEIS.kennung);
  });

  it('Post', () => {
    TestBed.inject(PostService)
      .addPost({ post: { title: 't', text: 'x', platform: 'Instagram', author: 'a', url: 'https://example.org' } })
      .subscribe();

    expect(body('/addPost')['cc0_wortlaut']).toBe(CONSENT_HINWEIS.kennung);
  });
});
