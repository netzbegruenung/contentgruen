import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';

import { Meilenstein, UsageTrackingService } from '../services/usage-tracking.service';
import { ROUTES } from '../shared/constants/app.constants';

/** Welche erreichten Meilensteine der Browser schon gezeigt hat (Kennungen, JSON). */
export const MEILENSTEINE_GESEHEN_SCHLUESSEL = 'gutgesagt-meilensteine-gesehen';

/** So lange steht der Hinweis, wenn niemand ihn wegtippt; wie die Rückmeldung (#349). */
const ANZEIGEDAUER_MS = 8000;

/**
 * Die gesehenen Kennungen, oder null ohne Speicher (privates Fenster, gesperrt).
 * Ohne Speicher gibt es keinen Hinweis: Er käme sonst nach jedem Einwurf wieder.
 */
export function gesehenLesen(): Set<string> | null {
  try {
    const roh = localStorage.getItem(MEILENSTEINE_GESEHEN_SCHLUESSEL);
    const liste: unknown = roh ? JSON.parse(roh) : [];
    return new Set(Array.isArray(liste) ? liste.filter((k): k is string => typeof k === 'string') : []);
  } catch {
    return null;
  }
}

/** Die erreichten Meilensteine als gesehen merken; ohne Speicher passiert nichts. */
export function gesehenMerken(meilensteine: Meilenstein[]): void {
  const gesehen = gesehenLesen();
  if (!gesehen) {
    return;
  }
  meilensteine.filter((m) => m.erreicht).forEach((m) => gesehen.add(m.kennung));
  try {
    localStorage.setItem(MEILENSTEINE_GESEHEN_SCHLUESSEL, JSON.stringify([...gesehen]));
  } catch {
    // Ohne Speicher kein Merker; der Hinweis bleibt dann ganz aus (gesehenLesen).
  }
}

/**
 * Ein kurzer Hinweis direkt nach dem eigenen Tun (Einwerfen, Ausformulieren, einen
 * Kommentar speichern), wenn dabei ein Meilenstein neu erreicht wurde (#351).
 *
 * Was schon gezeigt wurde, merkt sich nur der Browser, wie beim Rundgang (#389):
 * kein Server-Eintrag, keine Mail, kein Push. Kein Countdown, keine Serie, keine
 * Erinnerung; wer „Meine Beiträge“ öffnet, hat alles gesehen. Ohne eingeschaltete
 * Punkte liefert der Server keine Meilensteine, dann passiert hier nichts.
 */
@Injectable({ providedIn: 'root' })
export class MeilensteinHinweisService {
  constructor(
    private usageTrackingService: UsageTrackingService,
    private snackBar: MatSnackBar,
    private router: Router,
  ) {}

  /** Nach einer gespeicherten Handlung aufrufen; Fehler bleiben still. */
  pruefen(): void {
    if (!gesehenLesen()) {
      return;
    }
    this.usageTrackingService.getEigeneMeilensteine().subscribe((meilensteine) => {
      const gesehen = gesehenLesen();
      if (!gesehen) {
        return;
      }
      const neu = meilensteine.filter((m) => m.erreicht && !gesehen.has(m.kennung));
      if (!neu.length) {
        return;
      }
      gesehenMerken(meilensteine);
      const text =
        neu.length === 1 ? `Meilenstein erreicht: ${neu[0].name}` : `${neu.length} Meilensteine erreicht`;
      this.snackBar
        .open(text, 'Ansehen', { duration: ANZEIGEDAUER_MS })
        .onAction()
        .subscribe(() => this.router.navigateByUrl(ROUTES.MEINE_BEITRAEGE));
    });
  }
}
