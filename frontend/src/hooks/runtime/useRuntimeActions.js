import { useState } from "react";
import { toast } from "sonner";
// Phase A.3 Step 4.2A — run-once routed through canonical taRuntime.
// Phase A.3 Step 4.2B — engine start/stop/mode now via taRuntime.
// Phase A.3 Step 4.3 (approve+reject+note) — decisions lifecycle via taRuntime.
// Engine control = orchestrator-level (NOT the same as daemon).
import { taRuntime } from "../../modules/ta/services";

export function useRuntimeActions() {
  const [loading, setLoading] = useState(false);

  const startRuntime = async () => {
    setLoading(true);
    try {
      // Step 4.2B: canonical /api/ta/runtime/start via taRuntime.start().
      // Returns parsed JSON identical to legacy fetch().json() shape.
      const json = await taRuntime.start();
      if (json.ok) {
        toast.success("Runtime started");
        return json;
      } else {
        toast.error("Failed to start runtime");
        return null;
      }
    } catch (e) {
      toast.error(`Error: ${e.message}`);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const stopRuntime = async () => {
    setLoading(true);
    try {
      // Step 4.2B: canonical /api/ta/runtime/stop via taRuntime.stop().
      const json = await taRuntime.stop();
      if (json.ok) {
        toast.success("Runtime stopped");
        return json;
      } else {
        toast.error("Failed to stop runtime");
        return null;
      }
    } catch (e) {
      toast.error(`Error: ${e.message}`);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const runOnce = async () => {
    setLoading(true);
    try {
      // Step 4.2A: canonical /api/ta/runtime/run-once via taRuntime.
      // taRuntime.runOnce() returns already-parsed JSON (same shape as
      // the legacy fetch().json()), so downstream logic is unchanged.
      const json = await taRuntime.runOnce();
      if (json.ok) {
        const summary = json.summary || {};
        toast.success(
          `Cycle complete: ${summary.signals || 0} signals, ${summary.pending_created || 0} pending created`
        );
        return json;
      } else {
        toast.error("Run-once failed");
        return null;
      }
    } catch (e) {
      toast.error(`Error: ${e.message}`);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const setMode = async (mode) => {
    setLoading(true);
    try {
      // Step 4.2B: canonical /api/ta/runtime/mode via taRuntime.setMode().
      // Payload preserved 1-to-1: { mode }. No defaults, no validation.
      const json = await taRuntime.setMode(mode);
      if (json.ok) {
        toast.success(`Mode set to ${mode}`);
        return json;
      } else {
        toast.error("Failed to set mode");
        return null;
      }
    } catch (e) {
      toast.error(`Error: ${e.message}`);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const approveDecision = async (decisionId) => {
    setLoading(true);
    try {
      // Step 4.3 (approve): canonical /api/ta/runtime/decisions/{id}/approve
      // via taRuntime.decisions.approve(). Returns parsed JSON identical to
      // the legacy fetch().json() shape. Non-2xx surfaces as thrown Error
      // (caught below) → identical user-visible toast.error path.
      // Reject/note still on legacy until next sub-steps. DO NOT migrate them.
      const json = await taRuntime.decisions.approve(decisionId);
      if (json.ok) {
        toast.success("Decision approved & executed");
        return json;
      } else {
        toast.error("Failed to approve decision");
        return null;
      }
    } catch (e) {
      toast.error(`Error: ${e.message}`);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const rejectDecision = async (decisionId, reason = null) => {
    setLoading(true);
    try {
      // Step 4.3 (reject): canonical /api/ta/runtime/decisions/{id}/reject
      // via taRuntime.decisions.reject(). Payload preserved byte-identically:
      // legacy sent { reason } where `reason` could be null (caller default).
      // taService's _post serialises {reason: null} → '{"reason":null}' which
      // is bit-equal to the legacy fetch's JSON.stringify({reason}).
      // Note + cockpit still on legacy. DO NOT migrate them here.
      const json = await taRuntime.decisions.reject(decisionId, reason);
      if (json.ok) {
        toast.success("Decision rejected");
        return json;
      } else {
        toast.error("Failed to reject decision");
        return null;
      }
    } catch (e) {
      toast.error(`Error: ${e.message}`);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return {
    loading,
    startRuntime,
    stopRuntime,
    runOnce,
    setMode,
    approveDecision,
    rejectDecision,
  };
}
