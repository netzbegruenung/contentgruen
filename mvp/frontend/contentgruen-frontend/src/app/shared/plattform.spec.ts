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

  it('erkennt Threads unter beiden Domains', () => {
    expect(plattformAusUrl('https://www.threads.net/@a/post/1')).toBe('threads');
    expect(plattformAusUrl('https://www.threads.com/@a/post/1')).toBe('threads');
  });

  it('erkennt X, auch unter dem alten Namen Twitter', () => {
    expect(plattformAusUrl('https://x.com/a/status/1')).toBe('x');
    expect(plattformAusUrl('https://twitter.com/a/status/1')).toBe('x');
    expect(plattformAusUrl('https://mobile.twitter.com/a/status/1')).toBe('x');
  });

  it('erkennt Bluesky', () => {
    expect(plattformAusUrl('https://bsky.app/profile/a.bsky.social/post/1')).toBe('bluesky');
  });

  it('laesst Mastodon und kurze Lookalikes beim Web', () => {
    expect(plattformAusUrl('https://mastodon.social/@a/1')).toBe('web');
    expect(plattformAusUrl('https://box.com/s/1')).toBe('web');
    expect(plattformAusUrl('https://x.com.example.org/a')).toBe('web');
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
    expect(plattformName('threads')).toBe('Threads');
    expect(plattformName('x')).toBe('X');
    expect(plattformName('bluesky')).toBe('Bluesky');
    expect(plattformName('web')).toBe('Web');
  });
});
