import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AussagekarteComponent, jeAussage } from './aussagekarte.component';

const LANG = 'Windräder töten die Vögel, ' + 'und überhaupt ist alles viel zu teuer und zu laut und zu hoch, '.repeat(8);

@Component({
  standalone: true,
  imports: [AussagekarteComponent],
  template: `
    <div [style.width.px]="breite">
      <app-aussagekarte [text]="text" titelId="aussage-a-1" [ebene]="ebene" [knopf]="knopf"
                        [gesucht]="gesucht" antwortenPfad="/workflow/add-commentary"
                        [antwortenParams]="{ aussage: 'a-1' }">
        <span class="projiziert">Themen</span>
      </app-aussagekarte>
    </div>
  `,
})
class GastgeberComponent {
  text = 'Wärmepumpen sind zu teuer';
  ebene: 2 | 3 = 2;
  knopf: 'haupt' | 'neben' = 'haupt';
  gesucht = '';
  breite = 260;
}

/** Ein Frame warten, damit ResizeObserver und requestAnimationFrame durchlaufen. */
function frame(): Promise<void> {
  return new Promise((fertig) => requestAnimationFrame(() => setTimeout(fertig, 0)));
}

describe('AussagekarteComponent', () => {
  let fixture: ComponentFixture<GastgeberComponent>;

  function erstellen(werte: Partial<GastgeberComponent> = {}): HTMLElement {
    TestBed.configureTestingModule({ imports: [GastgeberComponent], providers: [provideRouter([])] });
    fixture = TestBed.createComponent(GastgeberComponent);
    Object.assign(fixture.componentInstance, werte);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('zeigt die Aussage als Überschrift im Kopfband, die Karte trägt sie als Namen', () => {
    const el = erstellen();
    const titel = el.querySelector('.aussagekarte-kopf h2.aussagekarte-titel') as HTMLElement;
    expect(titel.textContent?.trim()).toBe('Wärmepumpen sind zu teuer');
    expect(titel.id).toBe('aussage-a-1');
    expect(el.querySelector('article')?.getAttribute('aria-labelledby')).toBe('aussage-a-1');
    expect(el.querySelector('.aussagekarte-art')?.textContent?.trim()).toBe('Unbeantwortete Aussage');
  });

  it('setzt den Titel mit ebene 3 unter eine Abschnittsüberschrift', () => {
    const el = erstellen({ ebene: 3 });
    expect(el.querySelector('h3.aussagekarte-titel')).not.toBeNull();
    expect(el.querySelector('h2')).toBeNull();
  });

  it('führt mit "Antworten" ins Formular und verweist für Screenreader auf die Aussage', () => {
    const knopf = erstellen().querySelector('.aussagekarte-fuss a.antworten') as HTMLAnchorElement;
    expect(knopf.textContent?.trim()).toBe('Antworten');
    expect(knopf.classList).toContain('dark-green-button');
    expect(knopf.getAttribute('href')).toBe('/workflow/add-commentary?aussage=a-1');
    expect(knopf.getAttribute('aria-describedby')).toBe('aussage-a-1');
  });

  it('zeigt "Antworten" als Nebenknopf, wo die Seite schon einen Hauptknopf hat', () => {
    const knopf = erstellen({ knopf: 'neben' }).querySelector('a.antworten') as HTMLAnchorElement;
    expect(knopf.classList).not.toContain('dark-green-button');
    expect(knopf.getAttribute('href')).toBe('/workflow/add-commentary?aussage=a-1');
  });

  it('zeigt die Nachfrage nur, wenn es sie gibt', () => {
    expect(erstellen().querySelector('.gesucht')).toBeNull();
    TestBed.resetTestingModule();
    expect(erstellen({ gesucht: '2 Personen suchten das ohne Treffer' }).querySelector('.gesucht')?.textContent?.trim()).toBe(
      '2 Personen suchten das ohne Treffer',
    );
  });

  it('nimmt Zusätzliches in den Körper der Karte', () => {
    expect(erstellen().querySelector('.aussagekarte-inhalt .projiziert')?.textContent).toBe('Themen');
  });

  it('bietet "Ganz lesen" nur bei gekürzten Aussagen an', () => {
    expect(erstellen().querySelector('.ganz-lesen')).toBeNull();
  });

  it('klappt eine lange Aussage per Knopf auf und wieder zu, mit aria-expanded', () => {
    const el = erstellen({ text: LANG });
    fixture.detectChanges();
    const titel = el.querySelector('.aussagekarte-titel') as HTMLElement;
    const knopf = el.querySelector('button.ganz-lesen') as HTMLButtonElement;
    expect(titel.classList).toContain('aussagekarte-titel--zu');
    expect(knopf.textContent?.trim()).toBe('Ganz lesen');
    expect(knopf.getAttribute('aria-expanded')).toBe('false');
    expect(knopf.getAttribute('aria-controls')).toBe('aussage-a-1');

    knopf.click();
    fixture.detectChanges();
    expect(titel.classList).not.toContain('aussagekarte-titel--zu');
    expect(knopf.getAttribute('aria-expanded')).toBe('true');
    expect(knopf.textContent?.trim()).toBe('Weniger zeigen');

    knopf.click();
    fixture.detectChanges();
    expect(titel.classList).toContain('aussagekarte-titel--zu');
    // Gekürzt wird nur sichtbar: der volle Text steht weiter im Titel
    expect(titel.textContent).toContain('zu hoch, und überhaupt');
  });

  it('nimmt "Ganz lesen" zurück, wenn die Karte breiter wird und nichts mehr fehlt', async () => {
    const el = erstellen({ text: LANG });
    await frame();
    fixture.detectChanges();
    expect(el.querySelector('.ganz-lesen')).not.toBeNull();

    fixture.componentInstance.breite = 4000;
    fixture.detectChanges();
    await frame();
    await frame();
    fixture.detectChanges();
    expect(el.querySelector('.ganz-lesen')).toBeNull();
  });

  it('misst nach dem Zuklappen neu: breiter gewordene Karte ohne "Ganz lesen"', async () => {
    const el = erstellen({ text: LANG });
    await frame();
    fixture.detectChanges();
    (el.querySelector('.ganz-lesen') as HTMLButtonElement).click();
    fixture.detectChanges();
    fixture.componentInstance.breite = 4000;
    fixture.detectChanges();
    await frame();
    (el.querySelector('.ganz-lesen') as HTMLButtonElement).click();
    fixture.detectChanges();
    await frame();
    await frame();
    fixture.detectChanges();
    expect(el.querySelector('.ganz-lesen')).toBeNull();
  });

  it('beschreibt "Ganz lesen" mit der Aussage', () => {
    const el = erstellen({ text: LANG });
    fixture.detectChanges();
    const knopf = el.querySelector('button.ganz-lesen') as HTMLButtonElement;
    expect(knopf.getAttribute('aria-describedby')).toBe('aussage-a-1');
  });

  it('meldet den ResizeObserver beim Zerstören ab', () => {
    const abmelden = spyOn(ResizeObserver.prototype, 'disconnect').and.callThrough();
    erstellen();
    fixture.destroy();
    expect(abmelden).toHaveBeenCalled();
  });
});

describe('jeAussage', () => {
  it('bildet das Ergebnis je statement_id nur einmal', () => {
    const bilden = jasmine.createSpy('bilden').and.callFake((a: { statement_id: string }) => ({ aussage: a.statement_id }));
    const params = jeAussage(bilden);
    const erstes = params({ statement_id: 'a-1' });
    expect(params({ statement_id: 'a-1' })).toBe(erstes);
    expect(params({ statement_id: 'a-2' })).toEqual({ aussage: 'a-2' });
    expect(bilden).toHaveBeenCalledTimes(2);
  });
});
