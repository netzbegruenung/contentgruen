import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'relativeTime',
  standalone: true,
  pure: false // Make it impure so it updates regularly
})
export class RelativeTimePipe implements PipeTransform {
  transform(value: string | Date | null | undefined): string {
    if (!value) {
      return '';
    }

    const date = typeof value === 'string' ? new Date(value) : value;
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    // For content less than 25 hours old, show detailed time
    if (diffHours < 25 && diffHours > 0) {
      const remainingMinutes = diffMinutes % 60;
      if (diffHours === 1) {
        if (remainingMinutes === 0) {
          return 'vor 1 Stunde';
        } else if (remainingMinutes === 1) {
          return 'vor 1 Stunde, 1 Minute';
        } else {
          return `vor 1 Stunde, ${remainingMinutes} Minuten`;
        }
      } else {
        if (remainingMinutes === 0) {
          return `vor ${diffHours} Stunden`;
        } else if (remainingMinutes === 1) {
          return `vor ${diffHours} Stunden, 1 Minute`;
        } else {
          return `vor ${diffHours} Stunden, ${remainingMinutes} Minuten`;
        }
      }
    }

    // Less than 1 minute
    if (diffSeconds < 60) {
      return 'vor wenigen Sekunden';
    }

    // 1-59 minutes
    if (diffMinutes < 60) {
      if (diffMinutes === 1) {
        return 'vor 1 Minute';
      }
      return `vor ${diffMinutes} Minuten`;
    }

    // 1-24 hours (simplified display for 25+ hours)
    if (diffHours < 24) {
      if (diffHours === 1) {
        return 'vor 1 Stunde';
      }
      return `vor ${diffHours} Stunden`;
    }

    // 1-5 days
    if (diffDays <= 5) {
      if (diffDays === 1) {
        return 'vor 1 Tag';
      }
      return `vor ${diffDays} Tagen`;
    }

    // More than 5 days - use standard date format
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    return `${day}.${month}.${year}`;
  }

  // Helper method to check if content is new (less than 24 hours old)
  isNew(value: string | Date | null | undefined): boolean {
    if (!value) {
      return false;
    }

    const date = typeof value === 'string' ? new Date(value) : value;
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = diffMs / (1000 * 60 * 60);

    return diffHours < 24;
  }

  // Helper method to check if content is trending
  isTrending(usageCount: number | undefined, created: string | Date | null | undefined): boolean {
    if (!usageCount) {
      return false;
    }

    // Simple rule: 10+ total uses makes it trending
    // Could be enhanced with recent usage tracking from backend
    return usageCount >= 10;
  }
}
