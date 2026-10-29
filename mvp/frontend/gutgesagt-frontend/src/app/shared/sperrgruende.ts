/**
 * Sperrgruende (Glossar „Sperrgrund“, #448): eine Liste fuer den Sperrdialog der
 * Moderation und die Sperrnachricht in „Meine Beiträge“. Sie folgt Abschnitt 6 der
 * Nutzungsbedingungen. Die Werte sind dieselben wie in `domain/models/sperrgrund.py`
 * im Suchdienst; gespeicherte Sperren tragen sie, deshalb nie umbenennen.
 */
export type SperrgrundWert =
  | 'rechtswidrig'
  | 'rechte_dritter'
  | 'personendaten_dritter'
  | 'unterstellung'
  | 'ohne_bezug'
  | 'anderer_verstoss';

export interface Sperrgrund {
  value: SperrgrundWert;
  label: string;
}

export const SPERRGRUENDE: readonly Sperrgrund[] = [
  { value: 'rechtswidrig', label: 'Rechtswidriger Inhalt' },
  { value: 'rechte_dritter', label: 'Verletzt Rechte Dritter' },
  { value: 'personendaten_dritter', label: 'Personenbezogene Daten Dritter' },
  { value: 'unterstellung', label: 'Unterstellung über Motive oder pauschale Zuschreibung an Gruppen' },
  { value: 'ohne_bezug', label: 'Werbung oder ohne Bezug zum Zweck der Plattform' },
  { value: 'anderer_verstoss', label: 'Anderer Verstoß gegen die Nutzungsbedingungen' },
];

/** Die Beschriftung eines Sperrgrunds; ein unbekannter Wert bleibt, wie er ist. */
export function sperrgrundLabel(value: string): string {
  return SPERRGRUENDE.find((grund) => grund.value === value)?.label ?? value;
}
