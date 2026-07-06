import { Type } from '@angular/core';
import { CommentaryResultItemComponent } from '../commentary-result-item/commentary-result-item.component';
import { GenerictextResultItemComponent } from '../generictext-result-item/generictext-result-item.component';
import { PostResultItemComponent } from '../post-result-item/post-result-item.component';
import { ImageResultItemComponent } from '../image-result-item/image-result-item.component';

/**
 * Single source of truth mapping a content type to its presentation (Seam 3 of
 * CONTENT_MODEL.md). Search-results, recent-content and contribution surfaces read
 * from here, so registering a new type wires it through the UI in one place instead
 * of a forest of per-type `*ngIf`/`Type<any>` references.
 *
 * Note on the discriminator string: the frontend has historically used the
 * underscore-free form ("generictext") in result wrappers (`generictext_result`,
 * `result_type: 'generictext'`), while the backend `ContentType` enum is
 * "generic_text". `resolveContentType()` normalises both to a single registry key.
 */
export interface ContentTypeConfig {
  /** Canonical registry key (frontend form). */
  key: string;
  icon: string;
  label: string;
  resultComponent: Type<any>;
  /** Name of the nested result field on a search-result wrapper. */
  resultField: string;
}

export const CONTENT_TYPE_REGISTRY: Record<string, ContentTypeConfig> = {
  commentary: {
    key: 'commentary',
    icon: 'forum',
    label: 'Kommentar',
    resultComponent: CommentaryResultItemComponent,
    resultField: 'commentary_result',
  },
  generictext: {
    key: 'generictext',
    icon: 'description',
    label: 'Textbaustein',
    resultComponent: GenerictextResultItemComponent,
    resultField: 'generictext_result',
  },
  post: {
    key: 'post',
    icon: 'campaign',
    label: 'Beitrag',
    resultComponent: PostResultItemComponent,
    resultField: 'post_result',
  },
  image: {
    key: 'image',
    icon: 'image',
    label: 'Bild',
    resultComponent: ImageResultItemComponent,
    resultField: 'image_result',
  },
};

/** Normalise any backend/frontend content-type spelling to a registry key. */
export function resolveContentType(contentType: string | undefined | null): string | undefined {
  if (!contentType) return undefined;
  const normalised = contentType.replace(/_/g, '');
  return CONTENT_TYPE_REGISTRY[normalised] ? normalised : undefined;
}

/**
 * Resolve the result-item component for a search-result wrapper, inspecting either an
 * explicit `content_type`/`result_type` field or the presence of a `*_result` payload.
 * Defaults to commentary to preserve prior behaviour for unexpected shapes.
 */
export function resolveResultComponent(result: any): Type<any> {
  const explicit = resolveContentType(result?.content_type ?? result?.result_type);
  if (explicit) {
    return CONTENT_TYPE_REGISTRY[explicit].resultComponent;
  }
  for (const config of Object.values(CONTENT_TYPE_REGISTRY)) {
    if (result?.[config.resultField]) {
      return config.resultComponent;
    }
  }
  // No explicit discriminator and no known `*_result` payload matched. We still render
  // as commentary to preserve prior behaviour, but warn: for a newly added type this
  // usually means a registry/wire-up gap (missing entry or mismatched resultField)
  // rather than genuine commentary, and a silent fallback would otherwise mask it.
  console.warn(
    '[content-type-registry] resolveResultComponent: unrecognised result shape, ' +
      'falling back to commentary. Check that the content type is registered and its ' +
      'resultField matches the wire payload.',
    result,
  );
  return CONTENT_TYPE_REGISTRY['commentary'].resultComponent;
}
