import { InjectionToken } from '@angular/core';

/** Was die Erkennung vom Browser braucht; in Tests frei belegbar. */
export interface GeraetInfo {
  userAgent: string;
  maxTouchPoints: number;
  /** Nur Safari auf iOS: true in der vom Home-Bildschirm gestarteten App. */
  standalone?: boolean;
  /** `(display-mode: standalone)` trifft zu: als App gestartet (auch iOS ab 16.4). */
  alsAppGestartet: boolean;
}

/**
 * Andere Browser und eingebettete Ansichten (Instagram, Facebook …) auf iOS: Der Hinweis
 * nennt Safari, und in eingebetteten Ansichten gibt es „Zum Home-Bildschirm“ nicht.
 */
const NICHT_SAFARI = /CriOS|FxiOS|EdgiOS|OPiOS|OPT\/|YaBrowser|DuckDuckGo|GSA\/|FBAN|FBAV|Instagram|Line\/|Twitter|WhatsApp/;

/**
 * Safari auf iPhone oder iPad, nicht schon als App vom Home-Bildschirm gestartet. iPadOS
 * meldet sich in der Grundeinstellung wie ein Mac; ein Mac hat aber keinen Touchscreen.
 */
export function istIosSafariImBrowser(g: GeraetInfo): boolean {
  const ua = g.userAgent;
  const ios = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && g.maxTouchPoints > 1);
  if (!ios || !/Safari\//.test(ua) || NICHT_SAFARI.test(ua)) return false;
  return g.standalone !== true && !g.alsAppGestartet;
}

export function geraetAusBrowser(): GeraetInfo {
  const nav = navigator as Navigator & { standalone?: boolean };
  return {
    userAgent: nav.userAgent ?? '',
    maxTouchPoints: nav.maxTouchPoints ?? 0,
    standalone: nav.standalone,
    alsAppGestartet: typeof matchMedia === 'function' && matchMedia('(display-mode: standalone)').matches,
  };
}

/** Ob der Hinweis „Gut gesagt als App“ auf diesem Gerät passt; in Tests ersetzbar. */
export const HOME_BILDSCHIRM_MOEGLICH = new InjectionToken<() => boolean>('HOME_BILDSCHIRM_MOEGLICH', {
  providedIn: 'root',
  factory: () => () => istIosSafariImBrowser(geraetAusBrowser()),
});
