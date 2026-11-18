/** Ein `beforeinstallprompt`, wie Chrome es schickt, mit vorgegebener Antwort im Dialog. */
export function installierenEreignis(antwort: 'accepted' | 'dismissed'): Event & { prompt: jasmine.Spy } {
  const e = new Event('beforeinstallprompt', { cancelable: true }) as Event & { prompt: jasmine.Spy };
  e.prompt = jasmine.createSpy('prompt').and.resolveTo(undefined);
  Object.defineProperty(e, 'userChoice', { value: Promise.resolve({ outcome: antwort }) });
  return e;
}
