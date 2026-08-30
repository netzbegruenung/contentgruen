import { TestBed } from '@angular/core/testing';
import { SessionService } from './session.service';

const SESSION_KEY = 'gutgesagt_session_id';
const CREATED_AT_KEY = 'gutgesagt_session_id_created_at';
const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const DAY_MS = 24 * 60 * 60 * 1000;

describe('SessionService', () => {
  let service: SessionService;
  let localStorageSpy: jasmine.SpyObj<Storage>;
  let originalLocalStorage: PropertyDescriptor | undefined;
  let store: Record<string, string>;

  beforeEach(() => {
    // Den echten Descriptor merken: window.localStorage wird hier global
    // ersetzt, und ohne Wiederherstellung sieht jedes danach laufende Spec den
    // Spy statt des echten Speichers -- inklusive der fehlenden Methoden, die
    // der Spy nicht nachbildet.
    originalLocalStorage = Object.getOwnPropertyDescriptor(window, 'localStorage');

    // Der Spy muss nach Schluessel unterscheiden: der Dienst liest Kennung und
    // Zeitstempel getrennt, und ein Spy mit einem einzigen Rueckgabewert lieferte
    // die UUID auch als Zeitstempel aus.
    store = {};
    localStorageSpy = jasmine.createSpyObj('localStorage', ['getItem', 'setItem', 'removeItem']);
    localStorageSpy.getItem.and.callFake((key: string) => store[key] ?? null);
    localStorageSpy.setItem.and.callFake((key: string, value: string) => { store[key] = value; });
    localStorageSpy.removeItem.and.callFake((key: string) => { delete store[key]; });

    Object.defineProperty(window, 'localStorage', {
      value: localStorageSpy,
      writable: true,
      configurable: true
    });

    TestBed.configureTestingModule({});
  });

  afterEach(() => {
    localStorageSpy.getItem.calls.reset();
    localStorageSpy.setItem.calls.reset();
    localStorageSpy.removeItem.calls.reset();

    if (originalLocalStorage) {
      Object.defineProperty(window, 'localStorage', originalLocalStorage);
    }
  });

  /** Bestehende Kennung mit definiertem Alter in den Speicher legen. */
  function seedSession(sessionId: string, ageMs: number | null): void {
    store[SESSION_KEY] = sessionId;
    if (ageMs !== null) {
      store[CREATED_AT_KEY] = String(Date.now() - ageMs);
    }
  }

  describe('Session ID Generation', () => {
    it('should create the service', () => {
      service = TestBed.inject(SessionService);
      expect(service).toBeTruthy();
    });

    it('should generate a new session ID if none exists', () => {
      service = TestBed.inject(SessionService);

      const sessionId = service.getSessionId();

      expect(sessionId).toBeTruthy();
      expect(sessionId).toMatch(UUID_V4);
      expect(localStorageSpy.setItem).toHaveBeenCalledWith(SESSION_KEY, sessionId);
    });

    it('should store a creation timestamp alongside a new session ID', () => {
      const before = Date.now();
      service = TestBed.inject(SessionService);

      service.getSessionId();

      const createdAt = Number(store[CREATED_AT_KEY]);
      expect(createdAt).toBeGreaterThanOrEqual(before);
      expect(createdAt).toBeLessThanOrEqual(Date.now());
    });

    it('should not use Math.random for session IDs', () => {
      // Math.random ist nicht kryptografisch sicher: der Zustand des Generators
      // laesst sich aus wenigen Ausgaben rekonstruieren, kuenftige Werte sind
      // dann vorhersagbar. Fuer eine Kennung, die anonyme Meldungen und
      // Nutzungsereignisse zusammenhaelt, ist das die falsche Eigenschaft.
      //
      // Die Formatpruefungen in den anderen Specs wuerden einen Rueckfall auf
      // Math.random nicht bemerken -- der alte Code erzeugte dieselbe UUID-Form.
      const randomSpy = spyOn(Math, 'random').and.callThrough();
      localStorageSpy.getItem.and.returnValue(null);

      service = TestBed.inject(SessionService);
      service.regenerateSessionId();

      expect(randomSpy).not.toHaveBeenCalled();
    });

    it('should produce distinct session IDs on repeated generation', () => {
      localStorageSpy.getItem.and.returnValue(null);
      service = TestBed.inject(SessionService);

      const ids = new Set<string>();
      for (let i = 0; i < 100; i++) {
        ids.add(service.regenerateSessionId());
      }

      expect(ids.size).toBe(100);
    });

    it('should retrieve existing session ID from localStorage', () => {
      const existingSessionId = '12345678-1234-4234-8234-123456789012';
      seedSession(existingSessionId, DAY_MS);

      service = TestBed.inject(SessionService);
      const sessionId = service.getSessionId();

      expect(sessionId).toBe(existingSessionId);
      expect(localStorageSpy.getItem).toHaveBeenCalledWith(SESSION_KEY);
    });

    it('should return the same session ID on multiple calls', () => {
      service = TestBed.inject(SessionService);

      const sessionId1 = service.getSessionId();
      const sessionId2 = service.getSessionId();

      expect(sessionId1).toBe(sessionId2);
    });
  });

  describe('Session ID Expiry', () => {
    it('should keep a session ID that is younger than 30 days', () => {
      const existingSessionId = '12345678-1234-4234-8234-123456789012';
      seedSession(existingSessionId, 29 * DAY_MS);

      service = TestBed.inject(SessionService);

      expect(service.getSessionId()).toBe(existingSessionId);
    });

    it('should replace a session ID that is older than 30 days', () => {
      const existingSessionId = '12345678-1234-4234-8234-123456789012';
      seedSession(existingSessionId, 31 * DAY_MS);

      service = TestBed.inject(SessionService);
      const sessionId = service.getSessionId();

      expect(sessionId).not.toBe(existingSessionId);
      expect(sessionId).toMatch(UUID_V4);
      expect(store[SESSION_KEY]).toBe(sessionId);
    });

    it('should refresh the creation timestamp when a session ID expires', () => {
      seedSession('12345678-1234-4234-8234-123456789012', 31 * DAY_MS);
      const before = Date.now();

      service = TestBed.inject(SessionService);
      service.getSessionId();

      expect(Number(store[CREATED_AT_KEY])).toBeGreaterThanOrEqual(before);
    });

    it('should treat a session ID without a timestamp as expired', () => {
      const existingSessionId = '12345678-1234-4234-8234-123456789012';
      seedSession(existingSessionId, null);

      service = TestBed.inject(SessionService);
      const sessionId = service.getSessionId();

      expect(sessionId).not.toBe(existingSessionId);
      expect(sessionId).toMatch(UUID_V4);
      expect(store[CREATED_AT_KEY]).toBeTruthy();
    });

    it('should treat an unparseable timestamp as expired', () => {
      const existingSessionId = '12345678-1234-4234-8234-123456789012';
      store[SESSION_KEY] = existingSessionId;
      store[CREATED_AT_KEY] = 'not-a-number';

      service = TestBed.inject(SessionService);

      expect(service.getSessionId()).not.toBe(existingSessionId);
    });

    it('should not re-read a stale session ID after it expires mid-session', () => {
      const existingSessionId = '12345678-1234-4234-8234-123456789012';
      seedSession(existingSessionId, 29 * DAY_MS);

      service = TestBed.inject(SessionService);
      expect(service.getSessionId()).toBe(existingSessionId);

      // Ohne Zwischenspeicher im Dienst schlaegt ein nachtraeglich gealterter
      // Zeitstempel beim naechsten Lesen sofort durch.
      store[CREATED_AT_KEY] = String(Date.now() - 31 * DAY_MS);

      expect(service.getSessionId()).not.toBe(existingSessionId);
    });
  });

  describe('Session ID Regeneration', () => {
    it('should generate a new session ID when regenerateSessionId is called', () => {
      const existingSessionId = '12345678-1234-4234-8234-123456789012';
      seedSession(existingSessionId, DAY_MS);

      service = TestBed.inject(SessionService);
      const oldSessionId = service.getSessionId();
      const newSessionId = service.regenerateSessionId();

      expect(newSessionId).not.toBe(oldSessionId);
      expect(newSessionId).toMatch(UUID_V4);
      expect(localStorageSpy.setItem).toHaveBeenCalledWith(SESSION_KEY, newSessionId);
    });

    it('should refresh the creation timestamp on regeneration', () => {
      seedSession('12345678-1234-4234-8234-123456789012', 20 * DAY_MS);
      const before = Date.now();

      service = TestBed.inject(SessionService);
      service.regenerateSessionId();

      expect(Number(store[CREATED_AT_KEY])).toBeGreaterThanOrEqual(before);
    });

    it('should use the new session ID after regeneration', () => {
      service = TestBed.inject(SessionService);

      const newSessionId = service.regenerateSessionId();
      const currentSessionId = service.getSessionId();

      expect(currentSessionId).toBe(newSessionId);
    });
  });

  describe('Session ID Clearing', () => {
    it('should clear session ID and its timestamp from localStorage', () => {
      seedSession('12345678-1234-4234-8234-123456789012', DAY_MS);

      service = TestBed.inject(SessionService);
      service.clearSessionId();

      expect(localStorageSpy.removeItem).toHaveBeenCalledWith(SESSION_KEY);
      expect(localStorageSpy.removeItem).toHaveBeenCalledWith(CREATED_AT_KEY);
      expect(store[SESSION_KEY]).toBeUndefined();
      expect(store[CREATED_AT_KEY]).toBeUndefined();
    });

    it('should generate a new session ID after clearing', () => {
      seedSession('12345678-1234-4234-8234-123456789012', DAY_MS);
      service = TestBed.inject(SessionService);
      const oldSessionId = service.getSessionId();

      service.clearSessionId();

      const newSessionId = service.getSessionId();

      expect(newSessionId).not.toBe(oldSessionId);
      expect(newSessionId).toMatch(UUID_V4);
    });
  });

  describe('UUID v4 Format', () => {
    it('should generate valid UUID v4 format', () => {
      service = TestBed.inject(SessionService);

      const sessionId = service.getSessionId();

      // UUID format validation
      const parts = sessionId.split('-');
      expect(parts.length).toBe(5);
      expect(parts[0].length).toBe(8);
      expect(parts[1].length).toBe(4);
      expect(parts[2].length).toBe(4);
      expect(parts[2].charAt(0)).toBe('4'); // Version 4
      expect(parts[3].length).toBe(4);
      expect(['8', '9', 'a', 'b']).toContain(parts[3].charAt(0)); // Variant bits
      expect(parts[4].length).toBe(12);
    });
  });
});
