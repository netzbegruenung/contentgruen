/**
 * Single source of truth for a content type's identity and name (Seam 3 of
 * CONTENT_MODEL.md). Search-results, recent-content and contribution surfaces read
 * from here, so registering a new type wires it through the UI in one place instead
 * of a forest of per-type `*ngIf` references.
 *
 * Note on the discriminator string: the frontend has historically used the
 * underscore-free form ("generictext") in result wrappers (`generictext_result`,
 * `result_type: 'generictext'`), while the backend `ContentType` enum is
 * "generic_text". `resolveContentType()` normalises both to a single registry key.
 *
 * Das Label ist die einzige Quelle fuer den deutschen Typnamen im UI; gelesen wird
 * es ueber typLabel(). Aussage und Herkunft haben nur ein Label und keine Suchkarte.
 *
 * Die Suchkarten selbst stehen in content-type-components.ts. Diese Datei importiert
 * bewusst keine Komponenten: die App-Shell liest Typnamen (PAGE_TITLES), und ein
 * Komponenten-Import hier zoege alle Karten ins initiale Bundle.
 */
export interface ContentTypeConfig {
  /** Canonical registry key (frontend form). */
  key: string;
  icon: string;
  /** Deutscher Typname im UI, Einzahl. */
  label: string;
  /** Name of the nested result field on a search-result wrapper; nur bei Typen mit Suchkarte. */
  resultField?: string;
}

export const CONTENT_TYPE_REGISTRY: Record<string, ContentTypeConfig> = {
  commentary: {
    key: 'commentary',
    icon: 'forum',
    label: 'Kommentar',
    resultField: 'commentary_result',
  },
  generictext: {
    key: 'generictext',
    icon: 'description',
    label: 'Hintergrundinfo',
    resultField: 'generictext_result',
  },
  post: {
    key: 'post',
    icon: 'campaign',
    label: 'Post',
    resultField: 'post_result',
  },
  image: {
    key: 'image',
    icon: 'image',
    label: 'Bild',
    resultField: 'image_result',
  },
  statement: {
    key: 'statement',
    icon: 'format_quote',
    label: 'Aussage',
  },
  reference: {
    key: 'reference',
    icon: 'link',
    label: 'Herkunft',
  },
};

/** Normalise any backend/frontend content-type spelling to a registry key. */
export function resolveContentType(contentType: string | undefined | null): string | undefined {
  if (!contentType) return undefined;
  const normalised = contentType.replace(/_/g, '');
  return CONTENT_TYPE_REGISTRY[normalised] ? normalised : undefined;
}

/**
 * Der deutsche Name eines Inhaltstyps, in beiden Schreibweisen (generic_text und
 * generictext). Ein unbekannter Typ kommt unveraendert zurueck, damit er sichtbar
 * bleibt statt als leere Zelle zu verschwinden.
 */
export function typLabel(contentType: string | undefined | null): string {
  const key = resolveContentType(contentType);
  return key ? CONTENT_TYPE_REGISTRY[key].label : (contentType ?? '');
}
