/**
 * Texte der Seite /einwilligung, wenn sie die Nutzungsbedingungen und die
 * Art.-9-Einwilligung zusammen fragt (Entscheidung Maintainer, 20.11.2026).
 *
 * PLATZHALTER, FREIGABE OFFEN: Vorschläge, bis der Maintainer die Texte freigibt. Den
 * Wortlaut der Einwilligung selbst liefert weiter das Backend (domain/art9_einwilligung.py);
 * hier stehen nur die Sätze um die Häkchen. Das Häkchen der Nutzungsbedingungen heißt nie
 * „Einwilligung“ (es ist ein Vertrag), und es gibt keinen Knopf „Alle annehmen“.
 */
import { DATENSCHUTZ_EINSTELLUNGEN } from '../shared/fangkorb-texte';

export const EINE_SEITE_TEXTE = {
  titel: 'Nutzungsbedingungen und Einwilligung',
  einleitung:
    'Bevor du Gut gesagt mit deinem Konto nutzt, stimm bitte den Nutzungsbedingungen zu. ' +
    'Die Einwilligung darunter ist freiwillig: Ohne sie kannst du suchen und lesen, aber nichts beitragen und nichts bewerten.',
  /** Label am Häkchen der Nutzungsbedingungen; der Link steht darunter, nicht im Label. */
  nbLabel: 'Ich stimme den Nutzungsbedingungen zu.',
  nbLink: 'Nutzungsbedingungen lesen',
  nbPflicht: 'Pflicht, um Gut gesagt mit Konto zu nutzen.',
  nbFehler: 'Bitte stimm den Nutzungsbedingungen zu. Ohne sie kannst du Gut gesagt nicht mit deinem Konto nutzen.',
  /** Direkt unter dem Häkchen der Einwilligung, vor der Abgabe (Art. 7 Abs. 3 S. 3 DSGVO). */
  art9Freiwillig:
    `Freiwillig, nötig zum Mitmachen. Du kannst die Einwilligung jederzeit unter „${DATENSCHUTZ_EINSTELLUNGEN}“ widerrufen.`,
  art9Besteht: 'Deine Einwilligung zur Mitwirkung besteht weiter.',
  weiter: 'Weiter',
} as const;
