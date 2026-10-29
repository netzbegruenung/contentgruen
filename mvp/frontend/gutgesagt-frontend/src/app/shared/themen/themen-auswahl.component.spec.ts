import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ThemenAuswahlComponent } from './themen-auswahl.component';
import { Thema } from '../../services/dtos/themenDtos';

const THEMEN: Thema[] = [
  { schluessel: 'klima', name: 'Klima' },
  { schluessel: 'verkehr', name: 'Verkehr' },
  { schluessel: 'europa', name: 'Europa' },
];

describe('ThemenAuswahlComponent', () => {
  let fixture: ComponentFixture<ThemenAuswahlComponent>;
  let gemeldet: string[][];

  function setzen(gewaehlt: string[]): void {
    fixture.componentRef.setInput('gewaehlt', gewaehlt);
    fixture.detectChanges();
  }

  function knopf(name: string): HTMLButtonElement {
    const knoepfe = Array.from(fixture.nativeElement.querySelectorAll('button')) as HTMLButtonElement[];
    return knoepfe.find((k) => k.textContent?.trim() === name)!;
  }

  beforeEach(() => {
    fixture = TestBed.createComponent(ThemenAuswahlComponent);
    fixture.componentRef.setInput('themen', THEMEN);
    gemeldet = [];
    fixture.componentInstance.gewaehltChange.subscribe((g) => gemeldet.push(g));
    setzen([]);
  });

  it('waehlt ein Thema per Klick', () => {
    knopf('Verkehr').click();

    expect(gemeldet).toEqual([['verkehr']]);
  });

  it('zeigt gewaehlte Themen als gedrueckt und waehlt sie per Klick ab', () => {
    setzen(['klima']);

    expect(knopf('Klima').getAttribute('aria-pressed')).toBe('true');
    expect(knopf('Verkehr').getAttribute('aria-pressed')).toBe('false');
    knopf('Klima').click();
    expect(gemeldet).toEqual([[]]);
  });

  it('laesst hoechstens zwei Themen zu', () => {
    setzen(['klima', 'verkehr']);

    expect(knopf('Europa').disabled).toBeTrue();
    expect(knopf('Klima').disabled).toBeFalse();
    knopf('Europa').click();
    expect(gemeldet).toEqual([]);
  });
});
