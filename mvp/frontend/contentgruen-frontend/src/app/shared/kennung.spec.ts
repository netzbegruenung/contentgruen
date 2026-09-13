import { kurzeKennung } from './kennung';

describe('kurzeKennung', () => {
  it('kuerzt eine UUID auf ihren Anfang', () => {
    expect(kurzeKennung('0f3c2a9e-1111-2222-3333-444455556666')).toBe('0f3c2a9e');
  });

  it('laesst kurze Kennungen stehen', () => {
    expect(kurzeKennung('testuser')).toBe('testuser');
  });

  it('benennt eine fehlende Kennung', () => {
    expect(kurzeKennung(null)).toBe('ohne Kennung');
    expect(kurzeKennung('')).toBe('ohne Kennung');
  });
});
