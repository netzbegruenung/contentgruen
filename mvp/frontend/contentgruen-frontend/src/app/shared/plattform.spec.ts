import { plattformAusUrl, plattformName } from './plattform';

describe('plattformAusUrl', () => {
  it('erkennt Instagram, auch mit www', () => {
    expect(plattformAusUrl('https://www.instagram.com/reel/ABC/')).toBe('instagram');
    expect(plattformAusUrl('https://instagram.com/p/XYZ')).toBe('instagram');
  });

  it('erkennt YouTube unter beiden Domains und mobil', () => {
    expect(plattformAusUrl('https://www.youtube.com/watch?v=1')).toBe('youtube');
    expect(plattformAusUrl('https://youtu.be/1')).toBe('youtube');
    expect(plattformAusUrl('https://m.youtube.com/shorts/1')).toBe('youtube');
  });

  it('erkennt TikTok, auch Kurzlinks', () => {
    expect(plattformAusUrl('https://www.tiktok.com/@a/video/1')).toBe('tiktok');
    expect(plattformAusUrl('https://vm.tiktok.com/ZM123/')).toBe('tiktok');
  });

  it('ordnet alles andere dem Web zu', () => {
    expect(plattformAusUrl('https://www.tagesschau.de/inland/x-100.html')).toBe('web');
  });

  it('laesst sich von aehnlich klingenden Domains nicht taeuschen', () => {
    expect(plattformAusUrl('https://notinstagram.com/p/1')).toBe('web');
    expect(plattformAusUrl('https://instagram.com.example.org/p/1')).toBe('web');
  });

  it('zaehlt eine unlesbare Adresse als Web', () => {
    expect(plattformAusUrl('kein richtiger link')).toBe('web');
  });

  it('hat ohne Link keine Plattform', () => {
    expect(plattformAusUrl(null)).toBeNull();
    expect(plattformAusUrl(undefined)).toBeNull();
    expect(plattformAusUrl('   ')).toBeNull();
  });
});

describe('plattformName', () => {
  it('schreibt die Plattformen so, wie sie sich selbst schreiben', () => {
    expect(plattformName('instagram')).toBe('Instagram');
    expect(plattformName('youtube')).toBe('YouTube');
    expect(plattformName('tiktok')).toBe('TikTok');
    expect(plattformName('web')).toBe('Web');
  });
});
