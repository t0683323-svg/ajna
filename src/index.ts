/**
 * Ajna - A perception and insight module
 *
 * Provides utilities for observing, analyzing, and responding to data patterns.
 */

export interface Observation {
  /** Unique identifier for this observation */
  id: string;
  /** Timestamp when the observation was made */
  timestamp: Date;
  /** The observed data value */
  value: unknown;
  /** Optional metadata about the observation */
  metadata?: Record<string, unknown>;
}

export interface InsightResult {
  /** The type of insight detected */
  type: string;
  /** Confidence level from 0 to 1 */
  confidence: number;
  /** Human-readable description of the insight */
  description: string;
  /** Related observations that contributed to this insight */
  relatedObservations: string[];
}

/**
 * Observer class for collecting and managing observations
 */
export class Observer {
  private observations: Map<string, Observation> = new Map();
  private idCounter = 0;

  /**
   * Create a new observation
   * @param value - The value to observe
   * @param metadata - Optional metadata to attach
   * @returns The created observation
   */
  observe(value: unknown, metadata?: Record<string, unknown>): Observation {
    const id = `obs_${++this.idCounter}`;
    const observation: Observation = {
      id,
      timestamp: new Date(),
      value,
      metadata,
    };

    this.observations.set(id, observation);
    return observation;
  }

  /**
   * Get an observation by ID
   * @param id - The observation ID
   * @returns The observation or undefined if not found
   */
  get(id: string): Observation | undefined {
    return this.observations.get(id);
  }

  /**
   * Get all observations
   * @returns Array of all observations
   */
  getAll(): Observation[] {
    return Array.from(this.observations.values());
  }

  /**
   * Get the count of observations
   * @returns Number of observations
   */
  count(): number {
    return this.observations.size;
  }

  /**
   * Clear all observations
   */
  clear(): void {
    this.observations.clear();
    this.idCounter = 0;
  }
}

/**
 * Analyzer class for generating insights from observations
 */
export class Analyzer {
  /**
   * Analyze observations to detect patterns
   * @param observations - Array of observations to analyze
   * @returns Array of detected insights
   */
  analyze(observations: Observation[]): InsightResult[] {
    const insights: InsightResult[] = [];

    if (observations.length === 0) {
      return insights;
    }

    // Pattern: Frequency analysis
    const frequencyInsight = this.analyzeFrequency(observations);
    if (frequencyInsight) {
      insights.push(frequencyInsight);
    }

    // Pattern: Trend detection (for numeric values)
    const numericObs = observations.filter(
      (obs) => typeof obs.value === "number"
    );
    if (numericObs.length >= 2) {
      const trendInsight = this.analyzeTrend(numericObs);
      if (trendInsight) {
        insights.push(trendInsight);
      }
    }

    return insights;
  }

  private analyzeFrequency(observations: Observation[]): InsightResult | null {
    const timeSpan =
      observations.length > 1
        ? observations[observations.length - 1].timestamp.getTime() -
          observations[0].timestamp.getTime()
        : 0;

    if (timeSpan > 0) {
      const frequency = observations.length / (timeSpan / 1000);
      return {
        type: "frequency",
        confidence: Math.min(0.9, observations.length / 10),
        description: `Observed ${observations.length} events over ${(timeSpan / 1000).toFixed(2)}s (${frequency.toFixed(2)}/s)`,
        relatedObservations: observations.map((o) => o.id),
      };
    }

    return null;
  }

  private analyzeTrend(observations: Observation[]): InsightResult | null {
    const values = observations.map((o) => o.value as number);
    let increasing = 0;
    let decreasing = 0;

    for (let i = 1; i < values.length; i++) {
      if (values[i] > values[i - 1]) {
        increasing++;
      } else if (values[i] < values[i - 1]) {
        decreasing++;
      }
    }

    const totalChanges = values.length - 1;
    if (totalChanges === 0) return null;

    if (increasing / totalChanges > 0.7) {
      return {
        type: "trend",
        confidence: increasing / totalChanges,
        description: `Detected increasing trend (${((increasing / totalChanges) * 100).toFixed(0)}% increases)`,
        relatedObservations: observations.map((o) => o.id),
      };
    } else if (decreasing / totalChanges > 0.7) {
      return {
        type: "trend",
        confidence: decreasing / totalChanges,
        description: `Detected decreasing trend (${((decreasing / totalChanges) * 100).toFixed(0)}% decreases)`,
        relatedObservations: observations.map((o) => o.id),
      };
    }

    return null;
  }
}

/**
 * Main Ajna class combining observation and analysis
 */
export class Ajna {
  public readonly observer: Observer;
  public readonly analyzer: Analyzer;

  constructor() {
    this.observer = new Observer();
    this.analyzer = new Analyzer();
  }

  /**
   * Observe a value and optionally analyze all observations
   * @param value - The value to observe
   * @param metadata - Optional metadata
   * @returns The created observation
   */
  observe(value: unknown, metadata?: Record<string, unknown>): Observation {
    return this.observer.observe(value, metadata);
  }

  /**
   * Generate insights from all collected observations
   * @returns Array of insights
   */
  perceive(): InsightResult[] {
    return this.analyzer.analyze(this.observer.getAll());
  }

  /**
   * Clear all observations
   */
  reset(): void {
    this.observer.clear();
  }
}

// Default export
export default Ajna;
