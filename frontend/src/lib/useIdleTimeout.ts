/**
 * Idle-timeout auto-logout, mounted once in PortalShell so it covers all
 * three portals. After WARN_AFTER_MS without user activity a warning modal
 * offers "Stay signed in"; at LOGOUT_AFTER_MS the shared signOut() runs
 * (which also revokes the token server-side). The 24h absolute session
 * lifetime is separate and untouched.
 *
 * Elapsed time is computed from a timestamp, not counted in ticks, so a
 * throttled background tab or a laptop waking from sleep evaluates the true
 * idle gap immediately. The timestamp lives in localStorage so activity in
 * any portal tab keeps every tab alive, and removing the auth token in one
 * tab (sign-out) bounces the others to /login via the storage event.
 */

import { useEffect, useRef, useState } from "react";
import { signOut } from "./authStore";

const WARN_AFTER_MS = 18 * 60 * 1000;
const LOGOUT_AFTER_MS = 20 * 60 * 1000;
const ACTIVITY_KEY = "last_activity";
const TOKEN_KEY = "auth_token";

export interface IdleState {
  warning: boolean;
  secondsLeft: number;
  staySignedIn: () => void;
}

export function useIdleTimeout(): IdleState {
  const [warning, setWarning] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const warningRef = useRef(false);
  const signingOutRef = useRef(false);

  useEffect(() => {
    // QA override so the timer logic can be exercised in seconds instead of
    // waiting 20 real minutes: localStorage.idle_ms_override = "warn,logout"
    // (e.g. "8000,15000"). Client-side only — real session security is the
    // 24h token + server-side token_version check, so this grants nothing.
    let warnMs = WARN_AFTER_MS;
    let logoutMs = LOGOUT_AFTER_MS;
    const override = localStorage.getItem("idle_ms_override");
    if (override) {
      const [w, l] = override.split(",").map(Number);
      if (w > 0 && l > w) {
        warnMs = w;
        logoutMs = l;
      }
    }

    const touch = () => localStorage.setItem(ACTIVITY_KEY, String(Date.now()));
    touch(); // page load counts as activity

    let lastMove = 0;
    const onActivity = () => {
      // Once the warning is showing, passive events must not dismiss it —
      // only the explicit "Stay signed in" button resets the clock, so a
      // bumped mouse can't silently defeat the timeout.
      if (warningRef.current) return;
      touch();
    };
    const onMouseMove = () => {
      const now = Date.now();
      if (now - lastMove < 1000) return;
      lastMove = now;
      onActivity();
    };

    const listeners: [string, EventListener][] = [
      ["mousedown", onActivity],
      ["keydown", onActivity],
      ["touchstart", onActivity],
      ["wheel", onActivity],
      ["scroll", onActivity],
      ["mousemove", onMouseMove],
    ];
    for (const [name, fn] of listeners) {
      // capture:true so scrolls inside nested containers register too
      window.addEventListener(name, fn, { passive: true, capture: true });
    }

    // Signed out in another tab (token removed) → leave immediately.
    const onStorage = (event: StorageEvent) => {
      if (event.key === TOKEN_KEY && event.newValue === null) {
        window.location.replace("/login");
      }
    };
    window.addEventListener("storage", onStorage);

    const tick = window.setInterval(() => {
      const last = Number(localStorage.getItem(ACTIVITY_KEY)) || Date.now();
      const elapsed = Date.now() - last;

      if (elapsed >= logoutMs) {
        if (!signingOutRef.current) {
          signingOutRef.current = true;
          void signOut();
        }
        return;
      }
      if (elapsed >= warnMs) {
        warningRef.current = true;
        setWarning(true);
        setSecondsLeft(Math.max(1, Math.ceil((logoutMs - elapsed) / 1000)));
      } else if (warningRef.current) {
        // The shared clock was reset (Stay signed in, or another tab).
        warningRef.current = false;
        setWarning(false);
      }
    }, 1000);

    return () => {
      window.clearInterval(tick);
      for (const [name, fn] of listeners) {
        window.removeEventListener(name, fn, { capture: true });
      }
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const staySignedIn = () => {
    localStorage.setItem(ACTIVITY_KEY, String(Date.now()));
    warningRef.current = false;
    setWarning(false);
  };

  return { warning, secondsLeft, staySignedIn };
}
