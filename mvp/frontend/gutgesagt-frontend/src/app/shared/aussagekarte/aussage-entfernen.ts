import { BestaetigungsDialogDaten } from '../components/bestaetigungs-dialog/bestaetigungs-dialog.component';

/**
 * Die Rueckfrage vor "Aussage entfernen" (nur Admins), auf der Aussagekarte und in der
 * Moderation: endgueltig, ohne Papierkorb. Was mit weggeht, steht in
 * moderation_service.delete_content (Verweise, Stimmen, Varianten; offene Meldungen
 * gelten danach als bearbeitet).
 */
export function entfernenFrage(text: string): BestaetigungsDialogDaten {
  return {
    titel: 'Aussage endgültig entfernen?',
    text:
      `„${text}“ wird endgültig entfernt, mit ihren Stimmen und Verweisen. ` +
      'Das lässt sich nicht rückgängig machen. Offene Meldungen zu ihr gelten danach als bearbeitet.',
    ja: 'Endgültig entfernen',
    nein: 'Abbrechen',
  };
}

export const AUSSAGE_NICHT_ENTFERNT = 'Die Aussage konnte nicht entfernt werden. Bitte versuche es erneut.';
