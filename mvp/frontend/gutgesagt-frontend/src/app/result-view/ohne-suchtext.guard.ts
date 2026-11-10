import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { ROUTES } from '../shared/constants/app.constants';
import { SUCHTEXT_PARAM } from '../shared/formular-adresse';

/**
 * /result ohne Suchtext zeigte nur Suchfeld und Fusszeile, ohne jeden Hinweis
 * (#642, R50). Solche Aufrufe gehen auf den Start: Dort stehen Suchfeld,
 * Startbeispiel und die neuesten Inhalte.
 */
export const ohneSuchtextZumStart: CanActivateFn = (route) =>
  route.queryParamMap.get(SUCHTEXT_PARAM)?.trim() ? true : inject(Router).createUrlTree([ROUTES.SEARCH]);
