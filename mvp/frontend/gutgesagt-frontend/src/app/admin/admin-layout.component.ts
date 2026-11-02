import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';

/**
 * Rahmen des Admin-Bereichs: Navigation links, mobil als Zeile ueber dem Inhalt.
 *
 * Keine eigene Leiste und keine Seitenleiste mehr (#512): Den Titel traegt der
 * App-Kopf wie auf jeder Seite, und die fest offene Seitenleiste liess auf dem Handy
 * fuer den Inhalt rund 150 px. Kein eigener Zurueck-Knopf: Der Pfeil im Kopf fuehrt
 * von hier auf die Startseite (data.parent an der Route /admin).
 */
@Component({
  selector: 'app-admin-layout',
  standalone: true,
  imports: [CommonModule, RouterModule, MatIconModule],
  template: `
    <div class="admin-container">
      <nav class="admin-nav" aria-label="Admin-Bereich">
        <a routerLink="/admin/dashboard" routerLinkActive="aktiv">
          <mat-icon aria-hidden="true">dashboard</mat-icon>
          <span>Übersicht</span>
        </a>
        <a routerLink="/admin/moderation" routerLinkActive="aktiv">
          <mat-icon aria-hidden="true">flag</mat-icon>
          <span>Moderation</span>
        </a>
        <a routerLink="/admin/themen" routerLinkActive="aktiv">
          <mat-icon aria-hidden="true">label</mat-icon>
          <span>Themen</span>
        </a>
      </nav>

      <div class="admin-content">
        <router-outlet></router-outlet>
      </div>
    </div>
  `,
  styles: [`
    /* Container-Abfrage: Massgeblich ist die Breite des Rahmens, nicht des Fensters. */
    :host {
      display: block;
      container-type: inline-size;
    }

    .admin-container {
      display: grid;
      grid-template-columns: 220px minmax(0, 1fr);
      gap: var(--spacing-lg);
      padding: var(--spacing-md) var(--spacing-lg) var(--spacing-xl);
    }

    .admin-nav {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-xs);
      align-self: start;
    }

    .admin-nav a {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      min-height: 44px;
      padding: 0 var(--spacing-md);
      border-radius: var(--border-radius-medium);
      color: var(--text-secondary);
      font-weight: 500;
      text-decoration: none;
      white-space: nowrap;
    }

    .admin-nav a:hover {
      background-color: var(--hover-bg);
    }

    /* Gewaehlt wie bei den Ansichts-Umschaltern: Tanne-Hauch, Tanne-Text */
    .admin-nav a.aktiv {
      background-color: var(--auswahl-grund);
      color: var(--primary-dark);
      font-weight: 700;
    }

    .admin-content {
      min-width: 0;
    }

    @container (max-width: 959px) {
      .admin-container {
        grid-template-columns: minmax(0, 1fr);
        gap: var(--spacing-md);
        padding: var(--spacing-sm) var(--spacing-md) var(--spacing-xl);
      }

      .admin-nav {
        flex-direction: row;
        overflow-x: auto;
        border-bottom: 1px solid var(--divider-color);
      }

      .admin-nav a {
        border-radius: var(--border-radius-medium) var(--border-radius-medium) 0 0;
      }

      .admin-nav a.aktiv {
        box-shadow: inset 0 -2px 0 var(--primary-dark);
      }
    }
  `]
})
export class AdminLayoutComponent {}
