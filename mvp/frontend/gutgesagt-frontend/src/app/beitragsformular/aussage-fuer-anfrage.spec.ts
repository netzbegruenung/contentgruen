import { aussageFuerAnfrage } from './aussage-fuer-anfrage';

describe('aussageFuerAnfrage', () => {
  it('schickt zur ID den Text mit, damit eine verborgene Suchanfrage nicht ins Leere führt (Vormoderation)', () => {
    expect(aussageFuerAnfrage({ id: 'a-1', text: 'Windräder machen krank' }, [])).toEqual({
      statement_id: 'a-1',
      statement_text: 'Windräder machen krank',
    });
  });

  it('lässt einen zu kurzen Text neben der ID weg, das Backend nähme ihn nicht an', () => {
    expect(aussageFuerAnfrage({ id: 'a-1', text: 'Kurz' }, [])).toEqual({ statement_id: 'a-1' });
  });

  it('nimmt Themen nur zu einer Aussage per Text', () => {
    expect(aussageFuerAnfrage({ id: 'a-1', text: 'Windräder machen krank' }, ['energie'])).toEqual({
      statement_id: 'a-1',
      statement_text: 'Windräder machen krank',
    });
    expect(aussageFuerAnfrage({ id: '', text: 'Windräder machen krank' }, ['energie'])).toEqual({
      statement_text: 'Windräder machen krank',
      themen: ['energie'],
    });
  });

  it('ohne ID und Text: nichts', () => {
    expect(aussageFuerAnfrage({ id: '', text: '' }, [])).toEqual({});
  });
});
