import { TestBed } from '@angular/core/testing';
import { SessionService } from './session.service';

describe('SessionService', () => {
  let service: SessionService;
  let localStorageSpy: jasmine.SpyObj<Storage>;

  beforeEach(() => {
    // Create a spy for localStorage
    localStorageSpy = jasmine.createSpyObj('localStorage', ['getItem', 'setItem', 'removeItem']);
    Object.defineProperty(window, 'localStorage', {
      value: localStorageSpy,
      writable: true
    });

    TestBed.configureTestingModule({});
  });

  afterEach(() => {
    localStorageSpy.getItem.calls.reset();
    localStorageSpy.setItem.calls.reset();
    localStorageSpy.removeItem.calls.reset();
  });

  describe('Session ID Generation', () => {
    it('should create the service', () => {
      localStorageSpy.getItem.and.returnValue(null);
      service = TestBed.inject(SessionService);
      expect(service).toBeTruthy();
    });

    it('should generate a new session ID if none exists', () => {
      localStorageSpy.getItem.and.returnValue(null);
      service = TestBed.inject(SessionService);

      const sessionId = service.getSessionId();

      expect(sessionId).toBeTruthy();
      expect(sessionId).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
      expect(localStorageSpy.setItem).toHaveBeenCalledWith('contentgruen_session_id', sessionId);
    });

    it('should retrieve existing session ID from localStorage', () => {
      const existingSessionId = '12345678-1234-4234-8234-123456789012';
      localStorageSpy.getItem.and.returnValue(existingSessionId);

      service = TestBed.inject(SessionService);
      const sessionId = service.getSessionId();

      expect(sessionId).toBe(existingSessionId);
      expect(localStorageSpy.getItem).toHaveBeenCalledWith('contentgruen_session_id');
    });

    it('should return the same session ID on multiple calls', () => {
      localStorageSpy.getItem.and.returnValue(null);
      service = TestBed.inject(SessionService);

      const sessionId1 = service.getSessionId();
      const sessionId2 = service.getSessionId();

      expect(sessionId1).toBe(sessionId2);
    });
  });

  describe('Session ID Regeneration', () => {
    it('should generate a new session ID when regenerateSessionId is called', () => {
      const existingSessionId = '12345678-1234-4234-8234-123456789012';
      localStorageSpy.getItem.and.returnValue(existingSessionId);

      service = TestBed.inject(SessionService);
      const oldSessionId = service.getSessionId();
      const newSessionId = service.regenerateSessionId();

      expect(newSessionId).not.toBe(oldSessionId);
      expect(newSessionId).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
      expect(localStorageSpy.setItem).toHaveBeenCalledWith('contentgruen_session_id', newSessionId);
    });

    it('should use the new session ID after regeneration', () => {
      localStorageSpy.getItem.and.returnValue(null);
      service = TestBed.inject(SessionService);

      const newSessionId = service.regenerateSessionId();
      const currentSessionId = service.getSessionId();

      expect(currentSessionId).toBe(newSessionId);
    });
  });

  describe('Session ID Clearing', () => {
    it('should clear session ID from localStorage', () => {
      const existingSessionId = '12345678-1234-4234-8234-123456789012';
      localStorageSpy.getItem.and.returnValue(existingSessionId);

      service = TestBed.inject(SessionService);
      service.clearSessionId();

      expect(localStorageSpy.removeItem).toHaveBeenCalledWith('contentgruen_session_id');
    });

    it('should generate a new session ID after clearing', () => {
      localStorageSpy.getItem.and.returnValue('12345678-1234-4234-8234-123456789012');
      service = TestBed.inject(SessionService);
      const oldSessionId = service.getSessionId();

      service.clearSessionId();
      localStorageSpy.getItem.and.returnValue(null); // Simulate cleared localStorage

      const newSessionId = service.getSessionId();

      expect(newSessionId).not.toBe(oldSessionId);
      expect(newSessionId).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
    });
  });

  describe('UUID v4 Format', () => {
    it('should generate valid UUID v4 format', () => {
      localStorageSpy.getItem.and.returnValue(null);
      service = TestBed.inject(SessionService);

      const sessionId = service.getSessionId();

      // UUID v4 format validation
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
