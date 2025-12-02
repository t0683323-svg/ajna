import { Ajna, Observer, Analyzer, Observation } from './index';

describe('Observer', () => {
  let observer: Observer;

  beforeEach(() => {
    observer = new Observer();
  });

  describe('observe', () => {
    it('should create an observation with correct structure', () => {
      const result = observer.observe('test value');

      expect(result).toHaveProperty('id');
      expect(result).toHaveProperty('timestamp');
      expect(result.value).toBe('test value');
      expect(result.id).toMatch(/^obs_\d+$/);
    });

    it('should include metadata when provided', () => {
      const metadata = { source: 'test', priority: 1 };
      const result = observer.observe('value', metadata);

      expect(result.metadata).toEqual(metadata);
    });

    it('should generate unique IDs for each observation', () => {
      const obs1 = observer.observe('first');
      const obs2 = observer.observe('second');

      expect(obs1.id).not.toBe(obs2.id);
    });
  });

  describe('get', () => {
    it('should retrieve an observation by ID', () => {
      const created = observer.observe('test');
      const retrieved = observer.get(created.id);

      expect(retrieved).toEqual(created);
    });

    it('should return undefined for non-existent ID', () => {
      const result = observer.get('non_existent');

      expect(result).toBeUndefined();
    });
  });

  describe('getAll', () => {
    it('should return all observations', () => {
      observer.observe('first');
      observer.observe('second');
      observer.observe('third');

      const all = observer.getAll();

      expect(all).toHaveLength(3);
    });

    it('should return empty array when no observations', () => {
      expect(observer.getAll()).toEqual([]);
    });
  });

  describe('count', () => {
    it('should return correct count', () => {
      expect(observer.count()).toBe(0);

      observer.observe('one');
      expect(observer.count()).toBe(1);

      observer.observe('two');
      expect(observer.count()).toBe(2);
    });
  });

  describe('clear', () => {
    it('should remove all observations', () => {
      observer.observe('test');
      observer.observe('test2');

      observer.clear();

      expect(observer.count()).toBe(0);
      expect(observer.getAll()).toEqual([]);
    });

    it('should reset ID counter', () => {
      observer.observe('test');
      observer.clear();
      const newObs = observer.observe('new');

      expect(newObs.id).toBe('obs_1');
    });
  });
});

describe('Analyzer', () => {
  let analyzer: Analyzer;

  beforeEach(() => {
    analyzer = new Analyzer();
  });

  describe('analyze', () => {
    it('should return empty array for no observations', () => {
      const result = analyzer.analyze([]);

      expect(result).toEqual([]);
    });

    it('should detect frequency pattern when time span exists', () => {
      const now = new Date();
      const observations: Observation[] = [
        { id: 'obs_1', timestamp: new Date(now.getTime() - 1000), value: 1 },
        { id: 'obs_2', timestamp: new Date(now.getTime() - 500), value: 2 },
        { id: 'obs_3', timestamp: now, value: 3 },
      ];

      const result = analyzer.analyze(observations);
      const frequencyInsight = result.find((i) => i.type === 'frequency');

      expect(frequencyInsight).toBeDefined();
      expect(frequencyInsight?.confidence).toBeGreaterThan(0);
      expect(frequencyInsight?.relatedObservations).toEqual(['obs_1', 'obs_2', 'obs_3']);
    });

    it('should detect increasing trend', () => {
      const now = new Date();
      const observations: Observation[] = [
        { id: 'obs_1', timestamp: new Date(now.getTime() - 400), value: 1 },
        { id: 'obs_2', timestamp: new Date(now.getTime() - 300), value: 2 },
        { id: 'obs_3', timestamp: new Date(now.getTime() - 200), value: 3 },
        { id: 'obs_4', timestamp: new Date(now.getTime() - 100), value: 4 },
        { id: 'obs_5', timestamp: now, value: 5 },
      ];

      const result = analyzer.analyze(observations);
      const trendInsight = result.find((i) => i.type === 'trend');

      expect(trendInsight).toBeDefined();
      expect(trendInsight?.description).toContain('increasing');
      expect(trendInsight?.confidence).toBeGreaterThan(0.7);
    });

    it('should detect decreasing trend', () => {
      const now = new Date();
      const observations: Observation[] = [
        { id: 'obs_1', timestamp: new Date(now.getTime() - 400), value: 5 },
        { id: 'obs_2', timestamp: new Date(now.getTime() - 300), value: 4 },
        { id: 'obs_3', timestamp: new Date(now.getTime() - 200), value: 3 },
        { id: 'obs_4', timestamp: new Date(now.getTime() - 100), value: 2 },
        { id: 'obs_5', timestamp: now, value: 1 },
      ];

      const result = analyzer.analyze(observations);
      const trendInsight = result.find((i) => i.type === 'trend');

      expect(trendInsight).toBeDefined();
      expect(trendInsight?.description).toContain('decreasing');
    });

    it('should not detect trend for non-numeric values', () => {
      const now = new Date();
      const observations: Observation[] = [
        { id: 'obs_1', timestamp: new Date(now.getTime() - 100), value: 'a' },
        { id: 'obs_2', timestamp: now, value: 'b' },
      ];

      const result = analyzer.analyze(observations);
      const trendInsight = result.find((i) => i.type === 'trend');

      expect(trendInsight).toBeUndefined();
    });
  });
});

describe('Ajna', () => {
  let ajna: Ajna;

  beforeEach(() => {
    ajna = new Ajna();
  });

  describe('constructor', () => {
    it('should initialize with observer and analyzer', () => {
      expect(ajna.observer).toBeInstanceOf(Observer);
      expect(ajna.analyzer).toBeInstanceOf(Analyzer);
    });
  });

  describe('observe', () => {
    it('should delegate to observer', () => {
      const observation = ajna.observe('test value');

      expect(observation.value).toBe('test value');
      expect(ajna.observer.count()).toBe(1);
    });
  });

  describe('perceive', () => {
    it('should analyze all observations', () => {
      // Add observations with time delay simulation
      const now = Date.now();
      jest.useFakeTimers();
      jest.setSystemTime(now);
      ajna.observe(1);

      jest.setSystemTime(now + 500);
      ajna.observe(2);

      jest.setSystemTime(now + 1000);
      ajna.observe(3);

      const insights = ajna.perceive();

      expect(insights).toBeInstanceOf(Array);
      jest.useRealTimers();
    });

    it('should return empty array when no observations', () => {
      const insights = ajna.perceive();

      expect(insights).toEqual([]);
    });
  });

  describe('reset', () => {
    it('should clear all observations', () => {
      ajna.observe('test1');
      ajna.observe('test2');

      ajna.reset();

      expect(ajna.observer.count()).toBe(0);
    });
  });
});

describe('Integration', () => {
  it('should work as a complete perception system', () => {
    const ajna = new Ajna();

    // Simulate collecting observations over time
    const now = Date.now();
    jest.useFakeTimers();

    for (let i = 0; i < 10; i++) {
      jest.setSystemTime(now + i * 100);
      ajna.observe(i * 2, { iteration: i });
    }

    const insights = ajna.perceive();

    expect(insights.length).toBeGreaterThan(0);
    expect(ajna.observer.count()).toBe(10);

    // Reset and verify clean state
    ajna.reset();
    expect(ajna.observer.count()).toBe(0);
    expect(ajna.perceive()).toEqual([]);

    jest.useRealTimers();
  });
});
