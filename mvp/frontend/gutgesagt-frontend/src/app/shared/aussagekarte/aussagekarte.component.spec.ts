import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AussagekarteComponent } from './aussagekarte.component';

@Component({
  standalone: true,
  imports: [AussagekarteComponent],
  template: `
    <app-aussagekarte text="Wärmepumpen sind zu teuer" titelId="aussage-a-1" titelKlasse="aussage-text"
                      [gesucht]="gesucht" antwortenPfad="/workflow/add-commentary"
                      [antwortenParams]="{ aussage: 'a-1' }">
      <span class="projiziert">Themen</span>
    </app-aussagekarte>
  `,
})
class GastgeberComponent {
  gesucht = '';
}

describe('AussagekarteComponent', () => {
  function erstellen(gesucht = '') {
    TestBed.configureTestingModule({ imports: [GastgeberComponent], providers: [provideRouter([])] });
    const fixture = TestBed.createComponent(GastgeberComponent);
    fixture.componentInstance.gesucht = gesucht;
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('zeigt die Aussage als Titel im Kopfband, mit Id und Seitenklasse', () => {
    const el = erstellen();
    const titel = el.querySelector('.aussagekarte-kopf .aussagekarte-titel') as HTMLElement;
    expect(titel.textContent?.trim()).toBe('Wärmepumpen sind zu teuer');
    expect(titel.id).toBe('aussage-a-1');
    expect(titel.classList).toContain('aussage-text');
  });

  it('führt mit "Antworten" ins Formular und verweist für Screenreader auf die Aussage', () => {
    const knopf = erstellen().querySelector('.aussagekarte-fuss a.antworten') as HTMLAnchorElement;
    expect(knopf.textContent?.trim()).toBe('Antworten');
    expect(knopf.getAttribute('href')).toBe('/workflow/add-commentary?aussage=a-1');
    expect(knopf.getAttribute('aria-describedby')).toBe('aussage-a-1');
  });

  it('zeigt die Nachfrage nur, wenn es sie gibt', () => {
    expect(erstellen().querySelector('.gesucht')).toBeNull();
    TestBed.resetTestingModule();
    expect(erstellen('2 Personen suchten das ohne Treffer').querySelector('.gesucht')?.textContent?.trim()).toBe(
      '2 Personen suchten das ohne Treffer',
    );
  });

  it('nimmt Zusätzliches in den Körper der Karte', () => {
    expect(erstellen().querySelector('.aussagekarte-inhalt .projiziert')?.textContent).toBe('Themen');
  });
});
