export const APP_CONSTANTS = {
  // Breakpoints (should align with CDK breakpoints)
  BREAKPOINTS: {
    MOBILE: 768,
    TABLET: 1024,
    DESKTOP: 1280
  },

  // Touch target sizes (Material Design guidelines)
  TOUCH_TARGETS: {
    MIN_SIZE: 48, // Minimum touch target size in pixels
    RECOMMENDED_SIZE: 56
  },

  // Z-index values
  Z_INDEX: {
    DROPDOWN: 1000,
    STICKY: 1020,
    FIXED: 1030,
    MODAL_BACKDROP: 1040,
    MODAL: 1050,
    POPOVER: 1060,
    TOOLTIP: 1070,
    MOBILE_MENU: 1080,
    TOAST: 1090
  },

  // Animation durations
  ANIMATION: {
    FAST: '0.2s',
    NORMAL: '0.3s',
    SLOW: '0.5s'
  }
};

export const CONTENT_ICONS = {
  COMMENTARY: '💬',
  GENERIC_TEXT: '📄',
  REFERENCE: '🔗',
  SEARCH: '🔍',
  EDIT: '✏️',
  DELETE: '🗑️',
  SUCCESS: '✅',
  ERROR: '❌',
  WARNING: '⚠️',
  INFO: 'ℹ️'
};

export const PAGE_TITLES = {
  HOME: 'ContentGrün',
  SEARCH_RESULTS: 'Suchergebnisse',
  CONTRIBUTE: 'Beitrag verfassen',
  CONTRIBUTIONS: 'Meine Beiträge',
  RAW_INPUT: 'Schnell einwerfen',
  RAW_INPUT_LIST: 'Fangkorb',
  COMMENTARY: 'Fertiger Kommentar',
  GENERIC_TEXT: 'Hintergrundinfo',
  LOGIN: 'Anmelden',
  HELP: 'Hilfe'
};

export const ROUTES = {
  HOME: '/',
  SEARCH: '/search',
  RESULT: '/result',
  CONTRIBUTE: '/contribute',
  CONTRIBUTIONS: '/contributions',
  RAW_INPUT: '/einwerfen',
  RAW_INPUT_LIST: '/fangkorb',
  LOGIN: '/login',
  HELP: '/help'
};

export const STORAGE_KEYS = {
  USER_INFO: 'userInfo',
  AUTH_TOKEN: 'authToken',
  SEARCH_HISTORY: 'searchHistory',
  PREFERENCES: 'userPreferences'
};
