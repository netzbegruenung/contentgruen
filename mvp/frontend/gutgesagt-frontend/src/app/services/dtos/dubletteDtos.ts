/** In der Antwort auf das Anlegen: der vorhandene Beitrag, dessen Dublette der neue waere. */
export interface VorhandenDto {
  /** Titel des vorhandenen, soweit das Backend ihn nennt. */
  titel?: string | null;
  /** Von derselben Person. */
  eigen?: boolean;
}
