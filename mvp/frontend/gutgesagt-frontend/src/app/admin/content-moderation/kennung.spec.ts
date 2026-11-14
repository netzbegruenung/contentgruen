import { kurzeKennung } from './kennung';

describe('kurzeKennung', () => {
  it('macht aus einer langen Kennung „Person“ und acht Zeichen eines Hashs', () => {
    const kurz = kurzeKennung('f3a9c1d2-7b4e-4c55-9a10-2e8d6b0c7f11');

    expect(kurz).toMatch(/^Person [0-9a-f]{8}$/);
    expect(kurzeKennung('f3a9c1d2-7b4e-4c55-9a10-2e8d6b0c7f11')).toBe(kurz);
  });

  it('unterscheidet Kennungen mit gleichem Anfang', () => {
    expect(kurzeKennung('f3a9c1d2-7b4e-4c55-9a10-2e8d6b0c7f11')).not.toBe(kurzeKennung('f3a9c1d2-7b4e-4c55-9a10-2e8d6b0c7f12'));
  });

  it('lässt kurze Kennungen, wie sie sind, und gibt ohne Kennung nichts', () => {
    expect(kurzeKennung('user-001')).toBe('user-001');
    expect(kurzeKennung(null)).toBe('');
  });
});
