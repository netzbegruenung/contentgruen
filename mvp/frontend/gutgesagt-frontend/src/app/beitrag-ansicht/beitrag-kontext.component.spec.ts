import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { environment } from '../../environments/environment';
import { ANTWORT_AUF, BeitragKontextComponent, WEITERE_ANTWORTEN } from './beitrag-kontext.component';
import { AussageKurz, WeitereAntwort } from '../services/content.service';

describe('BeitragKontextComponent (#603)', () => {
  let fixture: ComponentFixture<BeitragKontextComponent>;

  const aussage: AussageKurz = { id: 'a-1', text: 'Wärmepumpen funktionieren nur im Neubau!' };
  const weitere: WeitereAntwort[] = [
    { id: 'b-2', content_type: 'commentary', titel: 'Viele ältere Häuser lassen sich gut heizen' },
    { id: 'b-3', content_type: 'generic_text', titel: 'Feldtest: Jahresarbeitszahl 3,3' },
  ];

  async function zeigen(a: AussageKurz | null, w: WeitereAntwort[] = []): Promise<HTMLElement> {
    await TestBed.configureTestingModule({
      imports: [BeitragKontextComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    fixture = TestBed.createComponent(BeitragKontextComponent);
    fixture.componentRef.setInput('aussage', a);
    fixture.componentRef.setInput('weitere', w);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('zeigt ohne Aussage nichts', async () => {
    const element = await zeigen(null, weitere);
    expect(element.querySelector('.beitrag-kontext')).toBeNull();
  });

  it('verlinkt die Aussage auf die Suche nach ihrem Text', async () => {
    const element = await zeigen(aussage);
    expect(element.textContent).toContain(ANTWORT_AUF);
    const link = element.querySelector('a.aussage-link') as HTMLAnchorElement;
    expect(link.textContent?.trim()).toBe(aussage.text);
    const ziel = new URL(link.getAttribute('href')!, 'https://gutgesagt.example');
    expect(ziel.pathname).toBe('/result');
    expect(ziel.searchParams.get('searchQuery')).toBe(aussage.text);
  });

  it('listet weitere Antworten als Links auf ihre Adresse, mit Typ', async () => {
    const element = await zeigen(aussage, weitere);
    expect(element.querySelector('h2.weitere-titel')?.textContent).toContain(WEITERE_ANTWORTEN);
    const links = Array.from(element.querySelectorAll('a.weitere-link')) as HTMLAnchorElement[];
    expect(links.map((l) => l.getAttribute('href'))).toEqual(['/beitrag/b-2', '/beitrag/b-3']);
    expect(links[0].textContent).toContain('Viele ältere Häuser lassen sich gut heizen');
    expect(links[0].textContent).toContain('Kommentar');
    expect(links[1].textContent).toContain('Hintergrundinfo');
  });

  it('zeigt die Themen der Aussage', async () => {
    const element = await zeigen({ ...aussage, themen: [{ schluessel: 'energie-heizen', name: 'Energie und Heizen' }] });
    TestBed.inject(HttpTestingController)
      .match(`${environment.baseUrl}/api/v1/statement/themen`)
      .forEach((r) => r.flush({ themen: [] }));
    fixture.detectChanges();

    const marken = Array.from(element.querySelectorAll('app-aussage-themen .thema-marke')).map((m) => m.textContent?.trim());
    expect(marken).toEqual(['Energie und Heizen']);
  });

  it('bietet ohne bekannte Themen (null oder aelterer Dienst) kein Zuordnen an', async () => {
    const element = await zeigen({ ...aussage, themen: null });
    expect(element.querySelector('app-aussage-themen')).toBeNull();
    fixture.componentRef.setInput('aussage', aussage);
    fixture.detectChanges();
    expect(element.querySelector('app-aussage-themen')).toBeNull();
  });

  it('behaelt geaenderte Themen, solange die Aussage dieselbe bleibt', async () => {
    await zeigen({ ...aussage, themen: [] });
    const vorher = fixture.componentInstance.mitThemen!;
    vorher.themen = [{ schluessel: 'wohnen', name: 'Wohnen' }];

    fixture.componentRef.setInput('weitere', weitere);
    fixture.detectChanges();
    expect(fixture.componentInstance.mitThemen).toBe(vorher);

    fixture.componentRef.setInput('aussage', { id: 'a-2', text: 'Andere Aussage', themen: [] });
    fixture.detectChanges();
    expect(fixture.componentInstance.mitThemen).toEqual({ statement_id: 'a-2', themen: [] });
  });

  it('laesst die Ueberschrift ohne weitere Antworten weg', async () => {
    const element = await zeigen(aussage, []);
    expect(element.querySelector('.antwort-auf')).not.toBeNull();
    expect(element.querySelector('h2.weitere-titel')).toBeNull();
  });
});
