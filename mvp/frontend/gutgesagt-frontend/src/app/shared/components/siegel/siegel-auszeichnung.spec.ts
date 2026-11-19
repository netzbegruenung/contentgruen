import { GLANZ_AB, hatGlanz } from './siegel-auszeichnung';

describe('Glanz am Siegel (#351)', () => {
  it('Glanz ab der Schwelle der Nutzung', () => {
    expect(hatGlanz(GLANZ_AB - 1)).toBeFalse();
    expect(hatGlanz(GLANZ_AB)).toBeTrue();
    expect(hatGlanz(null)).toBeFalse();
  });
});
