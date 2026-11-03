/**
 * Status einer Meldung (Glossar „Meldung“: offen, bearbeitet oder abgewiesen), wie die
 * Moderation sie zeigt. Die Werte sind die aus `content_reports.status`.
 */
const MELDUNGSSTATUS: Record<string, string> = {
  pending: 'Offen',
  reviewed: 'Bearbeitet',
  dismissed: 'Abgewiesen',
};

export function meldungsstatusLabel(status: string): string {
  return MELDUNGSSTATUS[status] ?? status;
}
