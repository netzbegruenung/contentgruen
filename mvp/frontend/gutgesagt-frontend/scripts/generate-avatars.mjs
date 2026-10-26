/**
 * Erzeugt die Avatarbilder unter public/avatars/.
 *
 * Warum ein Skript und nicht die API: bis hierher luden beide Avatar-Komponenten
 * ihre Bilder zur Laufzeit von api.dicebear.com. Damit ging bei jedem
 * Seitenaufruf die IP-Adresse der Besucherin an einen Drittanbieter -- auch ohne
 * Anmeldung. Die Seeds sind aber fest verdrahtete Konstanten, es sind genau 16
 * Bilder, und sie aendern sich nie. Also einmal erzeugen, ins Repo legen,
 * ausliefern wie die Schriften unter public/fonts/.
 *
 * Die DiceBear-Pakete sind devDependencies mit *exakter* Version: ein
 * Minor-Sprung kann das Aussehen aendern, und die Bilder sollen genau die
 * bleiben, die vorher von der API kamen. Geprueft wurde das durch
 * Byte-Vergleich gegen api.dicebear.com/7.x -- 15 von 15 identisch.
 *
 * Der 16. Avatar (anon-question) kommt nicht von DiceBear. Die alte URL
 *   .../7.x/initials/svg?seed=question&chars=%3F&backgroundColor=e0e0e0
 * lieferte HTTP 400 ("querystring/chars must be integer"), im Browser stand dort
 * also ein kaputtes Bild. Gemeint war ein Fragezeichen; das steht hier als
 * schlichtes SVG im selben Format wie die uebrigen (100x100, gleicher
 * Hintergrund, gleiche Schrift).
 *
 * Aufruf (nur noetig, wenn sich ein Avatar aendern soll):
 *   node scripts/generate-avatars.mjs
 */
import { createAvatar } from '@dicebear/core';
import * as avataaars from '@dicebear/avataaars';
import * as shapes from '@dicebear/shapes';
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const outDir = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'avatars');

/** Die zwoelf waehlbaren Profilbilder angemeldeter Nutzender. */
const profile = [
  ['female1', 'b6e3f4', 'smile'],
  ['female2', 'ffd5dc', 'smile'],
  ['female3', 'c0aede', 'twinkle'],
  ['female4', 'ffdfbf', 'smile'],
  ['female5', 'd1f4e0', 'twinkle'],
  ['female6', 'ffc0cb', 'smile'],
  ['male1', 'aec6cf', 'smile'],
  ['male2', 'ffb6c1', 'twinkle'],
  ['male3', 'ffd700', 'smile'],
  ['male4', '98fb98', 'smile'],
  ['male5', 'dda0dd', 'twinkle'],
  ['male6', 'f0e68c', 'smile'],
];

/** Die Anonym-Avatare der Ergebnisansicht. */
const anonymous = [
  ['anon-female', 'e0e0e0', 'smile'],
  ['anon-male', 'e0e0e0', 'smile'],
];

/**
 * Der Fragezeichen-Avatar. Kein DiceBear-Werk, deshalb ohne dessen
 * Metadatenblock. Positionierung wie bei DiceBears "initials": y auf 50% und
 * ein fester dy, statt dominant-baseline -- das rendert ueber Browser hinweg
 * gleich.
 */
const questionMark =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100" role="img" aria-label="Nicht angemeldet">' +
  '<rect width="100" height="100" x="0" y="0" fill="#e0e0e0" />' +
  '<text x="50%" y="50%" font-family="Arial, Helvetica, sans-serif" font-size="50" font-weight="400" ' +
  'fill="#ffffff" text-anchor="middle" dy="17.800">?</text>' +
  '</svg>\n';

function write(name, svg) {
  writeFileSync(join(outDir, `${name}.svg`), svg.endsWith('\n') ? svg : `${svg}\n`);
  return name;
}

mkdirSync(outDir, { recursive: true });

const written = [];

for (const [seed, backgroundColor, mouth] of [...profile, ...anonymous]) {
  written.push(
    write(
      seed,
      createAvatar(avataaars, {
        seed,
        backgroundColor: [backgroundColor],
        mouth: [mouth],
        eyes: ['happy'],
      }).toString(),
    ),
  );
}

written.push(
  write('anon-shapes', createAvatar(shapes, { seed: 'anon', backgroundColor: ['e0e0e0'] }).toString()),
);
written.push(write('anon-question', questionMark));

console.log(`${written.length} Avatare geschrieben nach public/avatars/:`);
console.log(written.join(', '));
