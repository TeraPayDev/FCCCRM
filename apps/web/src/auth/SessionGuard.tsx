import { useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import {
  SESSION_IDLE_TIMEOUT_MS,
  isSessionTimedOut,
  loadTokens,
  signalSessionExpired,
  touchSession,
} from "./session";

const CHECK_INTERVAL_MS = 15_000;
const TOUCH_THROTTLE_MS = 60_000;

export function SessionGuard() {
  const navigate = useNavigate();

  useEffect(() => {
    if (!loadTokens()) {
      navigate("/login?reason=expired", { replace: true });
      return;
    }

    let lastTouch = 0;
    const recordActivity = () => {
      const now = Date.now();
      if (now - lastTouch >= TOUCH_THROTTLE_MS) {
        touchSession();
        lastTouch = now;
      }
    };
    const expire = () => {
      signalSessionExpired();
      navigate("/login?reason=expired", { replace: true });
    };
    const check = () => {
      if (isSessionTimedOut()) expire();
    };
    const handleExpired = () => navigate("/login?reason=expired", { replace: true });

    window.addEventListener("pointerdown", recordActivity, { passive: true });
    window.addEventListener("keydown", recordActivity);
    window.addEventListener("touchstart", recordActivity, { passive: true });
    window.addEventListener("cram:session-expired", handleExpired);
    const timer = window.setInterval(check, Math.min(CHECK_INTERVAL_MS, SESSION_IDLE_TIMEOUT_MS));

    return () => {
      window.clearInterval(timer);
      window.removeEventListener("pointerdown", recordActivity);
      window.removeEventListener("keydown", recordActivity);
      window.removeEventListener("touchstart", recordActivity);
      window.removeEventListener("cram:session-expired", handleExpired);
    };
  }, [navigate]);

  return <Outlet />;
}
