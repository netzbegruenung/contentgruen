import { kurzeKennung } from './kennung';

describe('kurzeKennung', () => {
  it('kürzt eine UUID auf „Person“ und vier Zeichen', () => {
    expect(kurzeKennung('f3a9c1d2-7b4e-4c55-9a10-2e8d6b0c7f11')).toBe('Person f3a9');
  });

  it('kürzt lange andere Kennungen ebenso, kurze bleiben', () => {
    expect(kurzeKennung('keycloak|0123456789abcdef')).toBe('Person keyc');
    expect(kurzeKennung('user-001')).toBe('user-001');
  });

  it('gibt ohne Kennung nichts', () => {
    expect(kurzeKennung(null)).toBe('');
  });
});
