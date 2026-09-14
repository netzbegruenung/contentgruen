import { RESULT_COMPONENTS, resolveResultComponent } from './content-type-components';
import { CONTENT_TYPE_REGISTRY } from './content-type-registry';
import { CommentaryResultItemComponent } from '../commentary-result-item/commentary-result-item.component';
import { GenerictextResultItemComponent } from '../generictext-result-item/generictext-result-item.component';

describe('content-type-components', () => {
  it('hat fuer jeden Registry-Typ mit Ergebnisfeld eine Karte', () => {
    for (const config of Object.values(CONTENT_TYPE_REGISTRY)) {
      if (config.resultField) {
        expect(RESULT_COMPONENTS[config.key]).withContext(config.key).toBeDefined();
      }
    }
  });

  describe('resolveResultComponent', () => {
    it('liefert die Karte ueber content_type und ueber das Ergebnisfeld', () => {
      expect(resolveResultComponent({ content_type: 'generic_text' })).toBe(
        GenerictextResultItemComponent,
      );
      expect(resolveResultComponent({ commentary_result: {} })).toBe(CommentaryResultItemComponent);
    });

    it('faellt fuer Aussage und Herkunft ohne Warnung auf commentary zurueck', () => {
      spyOn(console, 'warn');
      expect(resolveResultComponent({ content_type: 'statement' })).toBe(CommentaryResultItemComponent);
      expect(resolveResultComponent({ result_type: 'reference' })).toBe(CommentaryResultItemComponent);
      expect(console.warn).not.toHaveBeenCalled();
    });

    it('warnt weiterhin bei einer unbekannten Form', () => {
      spyOn(console, 'warn');
      expect(resolveResultComponent({ irgendwas: true })).toBe(CommentaryResultItemComponent);
      expect(console.warn).toHaveBeenCalled();
    });
  });
});
