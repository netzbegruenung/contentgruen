import { Component } from '@angular/core';
import { Routes } from '@angular/router';

/** Platzhalter fuer jede Route: Geprueft wird die Navigation, nicht die Ansicht. */
@Component({ standalone: true, template: '' })
export class LeerComponent {}

/**
 * Die echte Routentabelle der App, nur ohne Waechter und ohne nachgeladene
 * Komponenten.
 *
 * So laesst sich ``data.parent`` im Test gegen die Tabelle pruefen, die auch in
 * Produktion gilt - ohne Anmeldung, HTTP und Lazy Loading. Kindrouten behalten
 * ihre Verschachtelung, damit das Erben des Elternziels mitgeprueft wird.
 */
export function ohneWaechter(eintraege: Routes): Routes {
  return eintraege.map((eintrag) => {
    const { canActivate, loadComponent, children, ...rest } = eintrag;
    const kopie: Routes[number] = { ...rest };
    if (!kopie.redirectTo) {
      kopie.component = LeerComponent;
    }
    if (children) {
      kopie.children = ohneWaechter(children);
      delete kopie.component;
    }
    return kopie;
  });
}
