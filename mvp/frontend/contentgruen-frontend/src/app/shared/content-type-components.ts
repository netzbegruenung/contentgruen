import { Type } from '@angular/core';
import { CommentaryResultItemComponent } from '../commentary-result-item/commentary-result-item.component';
import { GenerictextResultItemComponent } from '../generictext-result-item/generictext-result-item.component';
import { PostResultItemComponent } from '../post-result-item/post-result-item.component';
import { ImageResultItemComponent } from '../image-result-item/image-result-item.component';
import { CONTENT_TYPE_REGISTRY, resolveContentType } from './content-type-registry';

/**
 * Die Suchkarte je Registry-Schluessel. Getrennt von content-type-registry.ts, damit
 * wer nur einen Typnamen braucht, nicht alle Karten mitlaedt. Typen ohne Eintrag
 * (Aussage, Herkunft) haben keine Karte.
 */
export const RESULT_COMPONENTS: Readonly<Record<string, Type<any>>> = {
  commentary: CommentaryResultItemComponent,
  generictext: GenerictextResultItemComponent,
  post: PostResultItemComponent,
  image: ImageResultItemComponent,
};

/**
 * Resolve the result-item component for a search-result wrapper, inspecting either an
 * explicit `content_type`/`result_type` field or the presence of a `*_result` payload.
 * Defaults to commentary to preserve prior behaviour for unexpected shapes.
 */
export function resolveResultComponent(result: any): Type<any> {
  const explicit = resolveContentType(result?.content_type ?? result?.result_type);
  if (explicit) {
    // Aussage und Herkunft sind registriert, haben aber keine Karte. Das ist keine
    // Luecke im Wire-up, deshalb faellt ihr Weg auf commentary ohne Warnung.
    return RESULT_COMPONENTS[explicit] ?? RESULT_COMPONENTS['commentary'];
  }
  for (const config of Object.values(CONTENT_TYPE_REGISTRY)) {
    const component = RESULT_COMPONENTS[config.key];
    if (config.resultField && component && result?.[config.resultField]) {
      return component;
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
  return RESULT_COMPONENTS['commentary'];
}
