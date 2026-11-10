import { GLANZ_AB, KRONE_AB, hatGlanz, hatKrone } from './siegel-auszeichnung';

describe('Glanz und Krone am Siegel (#351)', () => {
  it('Glanz ab der Schwelle der Nutzung', () => {
    expect(hatGlanz(GLANZ_AB - 1)).toBeFalse();
    expect(hatGlanz(GLANZ_AB)).toBeTrue();
    expect(hatGlanz(null)).toBeFalse();
  });

  it('Krone erst ab der Schwelle der Meilensteine, ohne Abzeichen nie', () => {
    expect(hatKrone(KRONE_AB - 1)).toBeFalse();
    expect(hatKrone(KRONE_AB)).toBeTrue();
    expect(hatKrone(null)).toBeFalse();
    expect(hatKrone(undefined)).toBeFalse();
  });
});
