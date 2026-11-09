import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AussageKurz, WeitereAntwort } from '../services/content.service';
import { typEmoji, typLabel } from '../shared/content-type-registry';
import { ROUTES } from '../shared/constants/app.constants';

export const ANTWORT_AUF = 'Antwort auf:';
export const WEITERE_ANTWORTEN = 'Weitere Antworten zu dieser Aussage';

/**
 * Unter der Karte auf /beitrag/:id (#603): die Aussage, auf die der Beitrag antwortet,
 * als Link zur Suche, und weitere Antworten zu ihr als Links auf ihre eigene Adresse.
 * Ohne Aussage zeigt die Komponente nichts. Die Daten liefert /beitrag/{id} mit.
 */
@Component({
  selector: 'app-beitrag-kontext',
  standalone: true,
  imports: [CommonModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section *ngIf="aussage" class="beitrag-kontext" aria-label="Aussage und weitere Antworten">
      <p class="antwort-auf">
        <span class="beschriftung">{{ antwortAuf }}</span>
        <a class="aussage-link" [routerLink]="ergebnisse" [queryParams]="{ searchQuery: aussage.text }">{{
          aussage.text
        }}</a>
      </p>
      <ng-container *ngIf="weitere.length">
        <h2 class="weitere-titel">{{ weitereAntworten }}</h2>
        <ul class="weitere">
          <li *ngFor="let antwort of weitere; trackBy: nachId">
            <a class="weitere-link" [routerLink]="[beitragPfad, antwort.id]">
              <span class="typ" aria-hidden="true">{{ emoji(antwort.content_type) }}</span>
              <span class="titel">{{ antwort.titel }}</span>
              <span class="typ-name">{{ label(antwort.content_type) }}</span>
            </a>
          </li>
        </ul>
      </ng-container>
    </section>
  `,
  styles: [
    `
      .beitrag-kontext {
        display: flex;
        flex-direction: column;
        gap: 8px;
        width: 100%;
      }

      .antwort-auf {
        margin: 0;
        line-height: 1.4;
      }

      .beschriftung {
        color: var(--text-secondary);
        margin-right: 4px;
      }

      .aussage-link {
        font-weight: 600;
      }

      .weitere-titel {
        margin: 8px 0 0;
        font-family: inherit;
        font-style: normal;
        font-size: 1rem;
        font-weight: 600;
        letter-spacing: normal;
      }

      .weitere {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .weitere-link {
        display: flex;
        align-items: baseline;
        gap: 8px;
        min-height: 44px;
        padding: 8px 4px;
        box-sizing: border-box;
        text-decoration: none;
        color: inherit;
        border-bottom: 1px solid var(--border-color, rgba(0, 0, 0, 0.12));
      }

      .weitere-link:hover .titel,
      .weitere-link:focus-visible .titel {
        text-decoration: underline;
      }

      .titel {
        flex: 1;
        min-width: 0;
      }

      .typ-name {
        color: var(--text-secondary);
        font-size: 0.85rem;
        white-space: nowrap;
      }
    `,
  ],
})
export class BeitragKontextComponent {
  @Input() aussage: AussageKurz | null = null;
  @Input() weitere: WeitereAntwort[] = [];

  readonly antwortAuf = ANTWORT_AUF;
  readonly weitereAntworten = WEITERE_ANTWORTEN;
  readonly ergebnisse = ROUTES.RESULT;
  readonly beitragPfad = ROUTES.BEITRAG;

  emoji(typ: string): string {
    return typEmoji(typ);
  }

  label(typ: string): string {
    return typLabel(typ);
  }

  nachId(_: number, antwort: WeitereAntwort): string {
    return antwort.id;
  }
}
