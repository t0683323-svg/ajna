# Ajna

A perception and insight module for Node.js applications.

## Overview

Ajna (Sanskrit: आज्ञा, meaning "perceive" or "command") is a lightweight library for observing, collecting, and analyzing data patterns. It provides a simple API for tracking observations and generating insights from collected data.

## Installation

```bash
npm install ajna
```

## Quick Start

```typescript
import Ajna from 'ajna';

// Create an instance
const ajna = new Ajna();

// Observe values
ajna.observe(42);
ajna.observe(45, { source: 'sensor-1' });
ajna.observe(48);
ajna.observe(51);

// Generate insights
const insights = ajna.perceive();
console.log(insights);
// Output might include trend detection, frequency analysis, etc.

// Reset when done
ajna.reset();
```

## API

### Classes

#### `Ajna`

The main class that combines observation and analysis functionality.

- `observe(value: unknown, metadata?: Record<string, unknown>)`: Record an observation
- `perceive()`: Analyze all observations and return insights
- `reset()`: Clear all observations

#### `Observer`

Low-level class for managing observations.

- `observe(value, metadata?)`: Create a new observation
- `get(id)`: Get an observation by ID
- `getAll()`: Get all observations
- `count()`: Get the number of observations
- `clear()`: Remove all observations

#### `Analyzer`

Class for analyzing observations and detecting patterns.

- `analyze(observations)`: Analyze observations and return insights

### Interfaces

#### `Observation`

```typescript
interface Observation {
  id: string;
  timestamp: Date;
  value: unknown;
  metadata?: Record<string, unknown>;
}
```

#### `InsightResult`

```typescript
interface InsightResult {
  type: string;
  confidence: number;
  description: string;
  relatedObservations: string[];
}
```

## Insight Types

Currently supported insight types:

- **frequency**: Analyzes the rate of observations over time
- **trend**: Detects increasing or decreasing trends in numeric values

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Type check (including tests)
npm run typecheck

# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Lint
npm run lint

# Lint and fix
npm run lint:fix
```

## License

MIT License - see [LICENSE](LICENSE) for details.
