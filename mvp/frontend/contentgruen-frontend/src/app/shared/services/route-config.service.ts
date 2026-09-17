import { Injectable } from '@angular/core';
import { CONTENT_ICONS, PAGE_TITLES, ROUTES } from '../constants/app.constants';
import { FORMULAR_PFAD, GESPEICHERT_SEGMENT } from '../formular-adresse';
import { typLabel } from '../content-type-registry';

export interface RouteConfig {
  pageTitle: string;
  /** Kuerzerer Titel fuer den mobilen Kopf, wo neben Pfeil und Knoepfen wenig Platz ist. */
  mobilePageTitle?: string;
  showBackButton: boolean;
  showContributeButton: boolean;
  showContributionsButton: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class RouteConfigService {

  getRouteConfig(url: string): RouteConfig {
    // Parse route and query params
    const urlParts = url.split('?');
    const route = urlParts[0];
    const queryParams = new URLSearchParams(urlParts[1] || '');

    // Default configuration
    const defaultConfig: RouteConfig = {
      pageTitle: PAGE_TITLES.HOME,
      showBackButton: true,
      showContributeButton: true,
      showContributionsButton: false
    };

    // Route-specific configurations
    switch (route) {
      case ROUTES.HOME:
      case ROUTES.SEARCH:
        return {
          pageTitle: PAGE_TITLES.HOME,
          showBackButton: false,
          showContributeButton: true,
          showContributionsButton: false
        };

      case ROUTES.RESULT:
        return {
          pageTitle: PAGE_TITLES.SEARCH_RESULTS,
          showBackButton: true,
          showContributeButton: true,
          showContributionsButton: false
        };

      case ROUTES.CONTRIBUTE:
        return this.getContributeConfig(queryParams);

      // Die Formulare sind eigene Seiten; der Pfeil fuehrt ueber data.parent
      // auf die Beitragen-Seite oder zurueck zum Einwurf.
      case FORMULAR_PFAD.commentary:
        return this.getFormularConfig(PAGE_TITLES.COMMENTARY_FORM, typLabel('commentary'));
      case FORMULAR_PFAD.generictext:
        return this.getFormularConfig(PAGE_TITLES.GENERIC_TEXT_FORM, typLabel('generic_text'));
      case FORMULAR_PFAD.image:
        return this.getFormularConfig(PAGE_TITLES.IMAGE_FORM, typLabel('image'));

      case ROUTES.CONTRIBUTIONS:
        return {
          pageTitle: PAGE_TITLES.CONTRIBUTIONS,
          showBackButton: true,
          showContributeButton: true,
          showContributionsButton: false
        };

      case ROUTES.RAW_INPUT:
        return {
          pageTitle: PAGE_TITLES.RAW_INPUT,
          showBackButton: true,
          showContributeButton: false,
          showContributionsButton: false
        };

      case ROUTES.RAW_INPUT_LIST:
        return {
          pageTitle: PAGE_TITLES.RAW_INPUT_LIST,
          showBackButton: true,
          showContributeButton: true,
          showContributionsButton: false
        };

      case ROUTES.SHARE_TARGET:
        return {
          pageTitle: PAGE_TITLES.SHARE_TARGET,
          showBackButton: true,
          showContributeButton: false,
          showContributionsButton: false
        };

      case ROUTES.LOGIN:
      case '/login':
      case '/login-selector':
        return {
          pageTitle: PAGE_TITLES.LOGIN,
          showBackButton: true,
          showContributeButton: false,
          showContributionsButton: false
        };

      case '/login/managed':
        return {
          pageTitle: 'Gut gesagt – Login',
          showBackButton: true,
          showContributeButton: false,
          showContributionsButton: false
        };

      default:
        return this.getDynamicRouteConfig(route, queryParams, defaultConfig);
    }
  }

  // Mobil nur der Typname: "Kommentar verfassen" passt bei 360 px nicht neben
  // Pfeil, Avatar und Menue.
  private getFormularConfig(pageTitle: string, mobilePageTitle: string): RouteConfig {
    return {
      pageTitle,
      mobilePageTitle,
      showBackButton: true,
      showContributeButton: false,
      showContributionsButton: true
    };
  }

  private getContributeConfig(queryParams: URLSearchParams): RouteConfig {
    // Die Uebersicht; die Formulare haben eigene Titel (getFormularConfig).
    return {
      pageTitle: PAGE_TITLES.CONTRIBUTE,
      showBackButton: true,
      showContributeButton: false,
      showContributionsButton: true
    };
  }

  private getDynamicRouteConfig(
    route: string,
    queryParams: URLSearchParams,
    defaultConfig: RouteConfig
  ): RouteConfig {
    // Ergebnisseite nach dem Speichern: <Formularpfad>/gespeichert/<id>
    if (route.startsWith(`${FORMULAR_PFAD.commentary}/${GESPEICHERT_SEGMENT}/`)) {
      return this.getFormularConfig(PAGE_TITLES.GESPEICHERT, PAGE_TITLES.GESPEICHERT);
    }

    // /destillieren und /destillieren/:id
    // Der Pfeil steht im Kopf wie ueberall und fuehrt in den Fangkorb (data.parent).
    // Dass vorher der Satz gespeichert wird, meldet die Ansicht ueber
    // NavigationService.registerBeforeBack an. Aus der Typwahl zurueck zum Satz
    // fuehrt der Knopf im Ablauf, nicht der Pfeil - der Schritt ist kein
    // Unter-Screen.
    //
    // Im Schritt Typwahl heisst die Seite "Ausformulieren": Destilliert ist da
    // schon, hier entsteht der Beitrag. Der Schritt steht in der Adresse
    // (?schritt=typwahl), damit der Titel ihm folgen kann.
    if (route === ROUTES.DESTILLIEREN || route.startsWith(`${ROUTES.DESTILLIEREN}/`)) {
      return {
        pageTitle:
          queryParams.get('schritt') === 'typwahl'
            ? PAGE_TITLES.AUSFORMULIEREN
            : PAGE_TITLES.DESTILLIEREN,
        showBackButton: true,
        showContributeButton: false,
        showContributionsButton: false
      };
    }

    if (route.startsWith('/commentary/')) {
      return {
        ...defaultConfig,
        pageTitle: PAGE_TITLES.COMMENTARY
      };
    } else if (route.startsWith('/generictext/')) {
      return {
        ...defaultConfig,
        pageTitle: PAGE_TITLES.GENERIC_TEXT
      };
    }

    return defaultConfig;
  }
}
