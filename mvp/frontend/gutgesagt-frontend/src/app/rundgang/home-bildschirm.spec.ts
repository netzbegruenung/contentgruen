import { GeraetInfo, istIosSafariImBrowser } from './home-bildschirm';

/** Wer den Hinweis „Gut gesagt als App“ bekommt (14.11.2026). */
describe('istIosSafariImBrowser', () => {
  const IPHONE_SAFARI =
    'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1';
  const MAC_SAFARI =
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15';
  const IPHONE_CHROME =
    'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/130.0.6723.90 Mobile/15E148 Safari/604.1';
  const IPHONE_INSTAGRAM =
    'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 357.0.0.25.101';
  const ANDROID_CHROME =
    'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36';
  const WINDOWS_CHROME =
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36';

  const geraet = (userAgent: string, mehr: Partial<GeraetInfo> = {}): GeraetInfo => ({
    userAgent,
    maxTouchPoints: 0,
    alsAppGestartet: false,
    ...mehr,
  });

  it('erkennt Safari auf dem iPhone', () => {
    expect(istIosSafariImBrowser(geraet(IPHONE_SAFARI, { maxTouchPoints: 5, standalone: false }))).toBeTrue();
  });

  it('erkennt das iPad, das sich wie ein Mac meldet, am Touchscreen', () => {
    expect(istIosSafariImBrowser(geraet(MAC_SAFARI, { maxTouchPoints: 5, standalone: false }))).toBeTrue();
  });

  it('lässt den Mac ohne Touchscreen aus', () => {
    expect(istIosSafariImBrowser(geraet(MAC_SAFARI))).toBeFalse();
  });

  it('lässt Android und Desktop aus', () => {
    expect(istIosSafariImBrowser(geraet(ANDROID_CHROME, { maxTouchPoints: 5 }))).toBeFalse();
    expect(istIosSafariImBrowser(geraet(WINDOWS_CHROME))).toBeFalse();
  });

  it('lässt die schon installierte App aus (navigator.standalone)', () => {
    expect(istIosSafariImBrowser(geraet(IPHONE_SAFARI, { maxTouchPoints: 5, standalone: true }))).toBeFalse();
  });

  it('lässt die schon installierte App aus (display-mode: standalone)', () => {
    expect(istIosSafariImBrowser(geraet(IPHONE_SAFARI, { maxTouchPoints: 5, alsAppGestartet: true }))).toBeFalse();
  });

  it('lässt andere Browser und eingebettete Ansichten auf dem iPhone aus: der Hinweis nennt Safari', () => {
    expect(istIosSafariImBrowser(geraet(IPHONE_CHROME, { maxTouchPoints: 5 }))).toBeFalse();
    expect(istIosSafariImBrowser(geraet(IPHONE_INSTAGRAM, { maxTouchPoints: 5 }))).toBeFalse();
  });
});
