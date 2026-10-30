/**
 * Specs, die belegen, ob der Browser einen fremden Server anspricht (#447). Ein
 * PerformanceObserver faengt jede Ressource ab, die der Browser laedt. Als "fremder Server"
 * dient der Karma-Server unter dem anderen Hostnamen (localhost <-> 127.0.0.1): anderer
 * Origin, aber erreichbar, sodass eine ausgeloeste Anfrage nachweislich auftaucht.
 */

let zaehler = 0;

/** Eine neue, noch nie angefragte Adresse auf einem fremden, aber erreichbaren Server. */
export function fremdeAdresse(): string {
  const host = location.hostname === '127.0.0.1' ? 'localhost' : '127.0.0.1';
  zaehler += 1;
  return `${location.protocol}//${host}:${location.port}/fremd-447.png?n=${Date.now()}-${zaehler}`;
}

/** Sammelt die Adressen aller Ressourcen, die der Browser ab ``starten()`` laedt. */
export class Anfragen {
  private readonly angefragt: string[] = [];
  private readonly beobachter = new PerformanceObserver((liste) =>
    this.angefragt.push(...liste.getEntries().map((e) => e.name)),
  );

  starten(): void {
    this.beobachter.observe({ type: 'resource' });
  }

  beenden(): void {
    this.beobachter.disconnect();
  }

  /** Gibt dem Browser Zeit fuer Anfragen, die er ausloesen wuerde, und sammelt sie ein. */
  async abwarten(): Promise<string[]> {
    await new Promise((weiter) => setTimeout(weiter, 300));
    this.angefragt.push(...this.beobachter.takeRecords().map((e) => e.name));
    return this.angefragt;
  }
}

/** Wartet, bis das Bild geladen oder gescheitert ist; beides heisst: die Anfrage ist raus. */
export function bildFertig(bild: HTMLImageElement): Promise<void> {
  if (bild.complete && bild.src) return Promise.resolve();
  return new Promise((fertig) => {
    bild.addEventListener('load', () => fertig(), { once: true });
    bild.addEventListener('error', () => fertig(), { once: true });
  });
}
