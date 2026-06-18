/**
 * T22.x: Lightweight OTLP telemetry wrapper for agent-platform.
 *
 * Optional — no hard dependency on @opentelemetry/api.
 * Gracefully degrades to no-op when the OTel SDK is not installed.
 *
 * Usage:
 *   import { tracer } from "./telemetry";
 *   const span = tracer.startSpan("device-stage.listDevices", { attributes: { "device.modality": "mobile" } });
 *   // ... do work ...
 *   span.end();
 */

export interface TelemetrySpan {
  end(): void;
  recordError(error: Error): void;
  setAttribute(key: string, value: string | number | boolean): void;
  setAttributes(attrs: Record<string, string | number | boolean>): void;
}

export interface TelemetryTracer {
  startSpan(
    name: string,
    options?: { attributes?: Record<string, string | number | boolean> },
  ): TelemetrySpan;
}

/**
 * No-op span — used when @opentelemetry/api is not available.
 */
class NoopSpan implements TelemetrySpan {
  end(): void {}
  recordError(_error: Error): void {}
  setAttribute(_key: string, _value: string | number | boolean): void {}
  setAttributes(_attrs: Record<string, string | number | boolean>): void {}
}

/**
 * No-op tracer — used when @opentelemetry/api is not available.
 */
class NoopTracer implements TelemetryTracer {
  startSpan(
    _name: string,
    _options?: { attributes?: Record<string, string | number | boolean> },
  ): TelemetrySpan {
    return new NoopSpan();
  }
}

/**
 * Real OTel tracer — wraps @opentelemetry/api when available.
 */
class OtelTracer implements TelemetryTracer {
  private readonly tracer: import("@opentelemetry/api").Tracer;

  constructor(tracer: import("@opentelemetry/api").Tracer) {
    this.tracer = tracer;
  }

  startSpan(
    name: string,
    options?: { attributes?: Record<string, string | number | boolean> },
  ): TelemetrySpan {
    const span = this.tracer.startSpan(name, { attributes: options?.attributes });
    return {
      end(): void {
        span.end();
      },
      recordError(error: Error): void {
        span.recordException(error);
        span.setStatus({ code: 2 /* ERROR */, message: error.message });
      },
      setAttribute(key: string, value: string | number | boolean): void {
        span.setAttribute(key, value);
      },
      setAttributes(attrs: Record<string, string | number | boolean>): void {
        span.setAttributes(attrs);
      },
    };
  }
}

let _tracer: TelemetryTracer | null = null;

/**
 * Returns the singleton tracer. Attempts to load @opentelemetry/api at
 * runtime; falls back to NoopTracer if the import fails.
 */
export function getTracer(): TelemetryTracer {
  if (_tracer) return _tracer;

  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const otel = require("@opentelemetry/api");
    _tracer = new OtelTracer(otel.trace.getTracer("agent-platform", "0.1.0"));
  } catch {
    _tracer = new NoopTracer();
  }

  return _tracer;
}

/**
 * Reset the tracer singleton (for testing).
 */
export function resetTracer(): void {
  _tracer = null;
}
