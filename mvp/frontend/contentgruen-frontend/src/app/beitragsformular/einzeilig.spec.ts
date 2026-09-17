import { einzeilig } from './einzeilig';

describe('einzeilig', () => {
  it('macht aus Umbruechen ein Leerzeichen und schneidet Raender ab', () => {
    expect(einzeilig('  Wärmepumpen\n  lohnen sich\r\nim Altbau ')).toBe('Wärmepumpen lohnen sich im Altbau');
  });

  it('laesst einen Satz ohne Umbruch unveraendert und kommt mit leer zurecht', () => {
    expect(einzeilig('Ein Satz.')).toBe('Ein Satz.');
    expect(einzeilig(null)).toBe('');
  });
});
