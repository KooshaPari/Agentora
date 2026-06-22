/**
 * T66 agent-platform sub-port: DesktopStage.
 *
 * DesktopStage is the *desktop-modal* view of the device-stage contract.
 * It is a structural sub-trait of DeviceStage (T66) — it requires the
 * core DeviceStage surface (listDevices / openSession / closeSession / pointer /
 * key / screenshot / viewport / call) and ADDS desktop-specific semantics.
 *
 * The desktop-specific additions spell out the controls an agent needs to
 * drive a real desktop / laptop OS — the canonical Eidolon eidolon-desktop
 * wrapper (see findings/2026-06-17-agent-platform-domain.md §4 PR 3 and
 * findings/2026-06-17-eidolon-absorption.md Phase 4 note) speaks this
 * vocabulary on top of the device-stage baseline.
 *
 * Per ADR-023 (app-effort governance), the agent-platform interface domain
 * is the single coordination point between the agent runtime and any
 * device modality. Implementations are swappable via the Adapter pattern:
 *
 *   ports/adapters/desktop.ts  — Eidolon-backed implementation
 *                                  (delegates via EidolonStage transport;
 *                                   defaults to NullDesktopTransport when no
 *                                   Eidolon server is reachable)
 *
 * A reference adapter that satisfies the structural shape may also live in
 * other backends (KDesktopVirt Core Graphics shim, PlayCua browser-driver,
 * xdotool/). Domain code depends on this trait, not on the backend.
 */

import type {
  DeviceStage,
  DeviceId,
  SessionId,
  PointerInput,
  KeyInput,
  Viewport,
  ScreenshotResult,
  DeviceSession,
} from "./device_stage";

// ---------------------------------------------------------------------------
// Desktop-specific types
// ---------------------------------------------------------------------------

/**
 * Identifier for a single desktop display (monitor).
 * Branded to prevent accidental string interchange with raw IDs.
 */
export type DisplayId = string & { readonly __brand: "DisplayId" };

/**
 * Description of a single display attached to the desktop session.
 * Returned by getActiveDisplay() so an agent can reason about
 * screen layout (top-left coordinates + dimensions + scale factor)
 * before issuing pointer events.
 */
export interface DisplayInfo {
  readonly id: DisplayId;
  readonly width: number;
  readonly height: number;
  readonly scale: number;
  readonly originX: number;
  readonly originY: number;
  readonly isPrimary: boolean;
}

/**
 * Result of startCaptures() — a handle the agent can pass back to later
 * capture calls to tie frames together into a recording / video.
 */
export interface CaptureSession {
  readonly id: string;
  readonly sessionId: SessionId;
  readonly startedAt: string;
  readonly outputPath: string;
  readonly format: "png" | "jpg" | "mp4" | "h264";
}

/**
 * A semantic mouse button for click / doubleClick / rightClick.
 * The DeviceStage PointerInput already covers raw coords; DesktopStage
 * adds the higher-level vocabulary that an agent typically wants to use.
 */
export type MouseButton = "left" | "right" | "middle";

// ---------------------------------------------------------------------------
// DesktopStage sub-trait
// ---------------------------------------------------------------------------

/**
 * DesktopStage — the desktop modal of DeviceStage.
 *
 * Inherits the full DeviceStage surface (listDevices, openSession,
 * closeSession, pointer, key, screenshot, viewport, call) and adds
 * the desktop-specific semantic operations.
 *
 * Structural typing: anything implementing this interface is automatically
 * a DeviceStage, so consumers that only need the device-stage baseline can
 * accept a DesktopStage interchangeably with any other DeviceStage.
 */
export interface DesktopStage extends DeviceStage {
  // The modality is locked to "desktop" for this adapter — it is the
  // invariant the Eidolon-backed adapter guarantees.
  readonly modality: "desktop";

  /**
   * Begin a desktop capture session. Frame-by-frame screenshots taken
   * via screenshot() while this session is active get associated with
   * the returned CaptureSession (the agent platform may assemble them
   * into a recording).
   */
  startCaptures(sessionId: SessionId, outputPath: string): Promise<CaptureSession>;

  /**
   * Single click at (x, y). Wraps PointerInput kind:"click" with an
   * explicit button so adapters can map accurately to OS events.
   */
  click(sessionId: SessionId, x: number, y: number, button?: MouseButton): Promise<void>;

  /**
   * Double click at (x, y). Used in desktop UIs to trigger selection /
   * word-highlighting / open actions.
   */
  doubleClick(sessionId: SessionId, x: number, y: number, button?: MouseButton): Promise<void>;

  /**
   * Right click (context menu trigger) at (x, y).
   */
  rightClick(sessionId: SessionId, x: number, y: number): Promise<void>;

  /**
   * Press + release a single key (no modifiers). E.g. "Enter", "Escape",
   * the character "a".
   */
  keyTap(sessionId: SessionId, key: string): Promise<void>;

  /**
   * Press a modifier combo. E.g. ("cmd", "c") -> copy on macOS,
   * ("ctrl", "c") on Linux/Windows. The order of modifiers is preserved
   * by the adapter; backend (Eidolon eidolon-desktop) is responsible for
   * the OS-specific keymap.
   */
  keyCombo(sessionId: SessionId, modifiers: readonly string[], key: string): Promise<void>;

  /**
   * Discover the active display for the open session. Returns the primary
   * display by default; some adapters may accept a DisplayId argument
   * (extended surface kept minimal here — agents that need multi-display
   * should go through the call() escape hatch).
   */
  getActiveDisplay(sessionId: SessionId): Promise<DisplayInfo>;
}

/**
 * Type narrowed view of PointerInput that DesktopStage uses for the
 * underlying click / doubleClick / rightClick implementations. Re-exported
 * here so that consumers of DesktopStage don't need to also import from
 * device_stage.ts.
 */
export type { PointerInput, KeyInput, Viewport, ScreenshotResult, DeviceSession, DeviceId, SessionId };
