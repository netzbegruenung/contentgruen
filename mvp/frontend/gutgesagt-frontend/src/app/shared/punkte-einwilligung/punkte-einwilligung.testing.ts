import { Provider } from '@angular/core';
import { of } from 'rxjs';

import { PunkteEinwilligungService } from './punkte-einwilligung.service';

/** Für Specs, die das Häkchen nur mitrendern: Punkte aus, keine Anfrage ans Backend. */
export const PUNKTE_EINWILLIGUNG_AUS: Provider = {
  provide: PunkteEinwilligungService,
  useValue: { stand$: of(null), laden: () => of(null), setzen: () => of(false) },
};
