/** „einmal“ statt „1-mal“, sonst „3-mal“. */
function mal(anzahl: number): string {
  return anzahl === 1 ? 'einmal' : `${anzahl}-mal`;
}

/**
 * Der Wirkungssatz oben in Meine Beitraege (Nutzerfuehrung 13.11.): wie oft die eigenen
 * Beitraege genutzt wurden, und davon in den letzten 7 Tagen. Ohne Zahl fuer die Woche
 * (null: nicht alle Beitraege geladen) oder bei 0 entfaellt der zweite Teil; nichts
 * wird geschaetzt.
 */
export function wirkungssatz(beitraege: number, genutzt: number, dieseWoche: number | null): string {
  const subjekt = beitraege === 1 ? 'Dein Beitrag wurde' : `Deine ${beitraege} Beiträge wurden`;
  if (genutzt <= 0) {
    return `${subjekt} noch nicht genutzt.`;
  }
  let woche = '';
  if (dieseWoche && dieseWoche > 0) {
    if (dieseWoche >= genutzt) {
      woche = genutzt === 1 ? ', diese Woche' : ', alle diese Woche';
    } else {
      woche = `, ${dieseWoche} davon diese Woche`;
    }
  }
  return `${subjekt} ${mal(genutzt)} genutzt${woche}.`;
}
