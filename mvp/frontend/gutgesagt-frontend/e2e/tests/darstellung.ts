import { Page } from '@playwright/test';

/** Hilfen fuer die Darstellungs-Specs (11, 12): Kontrast nach WCAG 2.1. */

/** Kontrast zweier CSS-Farben `rgb(...)` nach WCAG 2.1. */
export function kontrast(vorne: string, hinten: string): number {
  const leuchtdichte = (farbe: string): number => {
    const [r, g, b] = farbe.match(/[\d.]+/g)!.slice(0, 3).map((wert) => {
      const kanal = Number(wert) / 255;
      return kanal <= 0.03928 ? kanal / 12.92 : ((kanal + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const [hell, dunkel] = [leuchtdichte(vorne), leuchtdichte(hinten)].sort((a, b) => b - a);
  return (hell + 0.05) / (dunkel + 0.05);
}

/**
 * Schriftfarbe und die erste deckende Hintergrundfarbe darunter (Element oder Vorfahr).
 * Nur fuer deckende Hintergruende und sRGB-Ausgabe (`rgb(...)`) gedacht: Halbtransparente
 * Flaechen, Verlaeufe, Bilder und andere Farbraeume misst sie nicht richtig.
 */
export async function farben(page: Page, selektor: string): Promise<{ vorne: string; hinten: string }> {
  return page.locator(selektor).first().evaluate((element) => {
    let ebene: Element | null = element;
    let hinten = 'rgb(255, 255, 255)';
    while (ebene) {
      const farbe = getComputedStyle(ebene).backgroundColor;
      if (farbe && farbe !== 'transparent' && !farbe.startsWith('rgba(0, 0, 0, 0)')) {
        hinten = farbe;
        break;
      }
      ebene = ebene.parentElement;
    }
    return { vorne: getComputedStyle(element).color, hinten };
  });
}
