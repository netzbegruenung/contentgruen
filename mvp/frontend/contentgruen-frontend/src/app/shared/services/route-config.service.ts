import { Injectable } from '@angular/core';
import { CONTENT_ICONS, PAGE_TITLES, ROUTES } from '../constants/app.constants';

export interface RouteConfig {
  pageTitle: string;
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
        return this.getDynamicRouteConfig(route, defaultConfig);
    }
  }

  private getContributeConfig(queryParams: URLSearchParams): RouteConfig {
    // Always use generic "Beitrag verfassen" title for mobile compatibility
    // Content type will be shown as a badge within the page content
    return {
      pageTitle: PAGE_TITLES.CONTRIBUTE,
      showBackButton: true,
      showContributeButton: false,
      showContributionsButton: true
    };
  }

  private getDynamicRouteConfig(route: string, defaultConfig: RouteConfig): RouteConfig {
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
