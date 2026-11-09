import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
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
      providers: [provideRouter([])],
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

  it('laesst die Ueberschrift ohne weitere Antworten weg', async () => {
    const element = await zeigen(aussage, []);
    expect(element.querySelector('.antwort-auf')).not.toBeNull();
    expect(element.querySelector('h2.weitere-titel')).toBeNull();
  });
});
