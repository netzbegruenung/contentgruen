import { DebugElement } from '@angular/core';

import { SprachhinweisComponent } from './sprachhinweis.component';

/**
 * Prueft den Sprachhinweis eines Beitragsformulars (#405): bekommt Titel und Text des
 * Beitrags und steht direkt ueber dem CC0-Hinweis. Ein zweiter Sprachhinweis fuer die
 * Aussage in "Antwort auf" zaehlt nicht mit.
 */
export function erwarteSprachhinweisZumBeitrag(wurzel: DebugElement, titel: string, text: string): void {
  const sprachhinweis = wurzel
    .queryAll((el) => el.componentInstance instanceof SprachhinweisComponent)
    .find((el) => (el.componentInstance as SprachhinweisComponent).gegenstand === 'beitrag');
  expect(sprachhinweis).withContext('Sprachhinweis zum Beitrag').toBeTruthy();
  const instanz = sprachhinweis!.componentInstance as SprachhinweisComponent;
  expect([instanz.titel, instanz.text]).toEqual([titel, text]);
  expect((sprachhinweis!.nativeElement as HTMLElement).nextElementSibling!.hasAttribute('appCc0Hinweis'))
    .withContext('direkt ueber dem CC0-Hinweis')
    .toBeTrue();
}
