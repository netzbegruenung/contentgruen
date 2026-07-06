import { ContentStatus } from './content-status-enum';

export const ContentStatusIcons: Record<ContentStatus, string> = {
  [ContentStatus.DRAFT]: '📝',
  [ContentStatus.FLAGGED]: '🚩',
  [ContentStatus.PENDING_REVIEW]: '⏳',
  [ContentStatus.APPROVED]: '✅',
  [ContentStatus.REJECTED]: '❌',
  [ContentStatus.BLOCKED]: '🚫',
  [ContentStatus.RELEASED_INTERNAL]: '🌻',
  [ContentStatus.PUBLISHED_EXTERNAL]: '🌍',
  [ContentStatus.ARCHIVED]: '📦',
  [ContentStatus.DUPLICATE]: '🔄',
};


export const ContentStatusStrings: Record<ContentStatus, string> = {
  [ContentStatus.DRAFT]: 'Entwurf',
  [ContentStatus.FLAGGED]: 'Markiert',
  [ContentStatus.PENDING_REVIEW]: 'Wartet auf Freigabe',
  [ContentStatus.APPROVED]: 'Genehmigt',
  [ContentStatus.REJECTED]: 'Abgelehnt',
  [ContentStatus.BLOCKED]: 'Gesperrt',
  [ContentStatus.RELEASED_INTERNAL]: 'Intern veröffentlicht',
  [ContentStatus.PUBLISHED_EXTERNAL]: 'Extern veröffentlicht',
  [ContentStatus.ARCHIVED]: 'Archiviert',
  [ContentStatus.DUPLICATE]: 'Duplikat',
};
