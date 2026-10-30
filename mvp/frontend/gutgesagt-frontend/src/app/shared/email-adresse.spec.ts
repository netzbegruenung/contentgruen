import { istEmailAdresse } from './email-adresse';

/**
 * Erwartungen aus dem Suchdienst: So entscheidet `EmailStr` (email_validator 2.2.0)
 * an der Melde-Route ueber dieselben Adressen (#438, Review-Befund 19).
 */
describe('istEmailAdresse', () => {
  const angenommen = [
    'anna@example.org',
    'a+b@ex.org',
    'anna@sub.example.com',
    'anna@bücher.de',
    'änna@ex.org',
    'anna@xn--bcher-kva.de',
    'a@ab.xn--p1ai',
    'a@ex.c',
    'a@e-x.org',
    'a@ex.local.org',
    'a@ex.example',
    'x'.repeat(64) + '@ex.org',
  ];

  const abgewiesen = [
    'anna',
    'anna@',
    '@example.org',
    'a b@c.de',
    'anna@localhost',
    'anna@example',
    'anna@x.local',
    'a@ex.test',
    'a@ex.invalid',
    'a@ex.onion',
    'a@ex.home.arpa',
    'a..b@ex.org',
    '.a@ex.org',
    'a@ex..org',
    'a@-ex.org',
    'a@ex_y.org',
    'a@ex.123',
    'a@ex.co1',
    'a@ex.org.',
    'a@1.2.3.4',
    'a@[1.2.3.4]',
    '"a b"@ex.org',
    'x'.repeat(65) + '@ex.org',
    'a@' + 'b'.repeat(64) + '.org',
  ];

  for (const adresse of angenommen) {
    it(`nimmt ${adresse.slice(0, 40)} an`, () => {
      expect(istEmailAdresse(adresse)).toBeTrue();
    });
  }

  for (const adresse of abgewiesen) {
    it(`weist ${adresse.slice(0, 40)} ab`, () => {
      expect(istEmailAdresse(adresse)).toBeFalse();
    });
  }
});
