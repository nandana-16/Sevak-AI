import { useEffect, useState, useCallback } from "react";
import { getAuth, clearAuth, syncBatch } from "./api";
import { getQueuedVisits, removeQueuedVisit } from "./offline";
import Login from "./components/Login";
import PatientList from "./components/PatientList";
import RecordVisit from "./components/RecordVisit";
import VisitResult from "./components/VisitResult";
import TaskList from "./components/TaskList";
import OfflineBanner from "./components/OfflineBanner";

export default function App() {
  const [auth, setAuthState] = useState(getAuth());
  const [screen, setScreen] = useState("patients"); // patients | record | result | tasks
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [pendingCount, setPendingCount] = useState(0);
  const [toast, setToast] = useState("");

  const refreshPendingCount = useCallback(async () => {
    const queued = await getQueuedVisits();
    setPendingCount(queued.length);
  }, []);

  const syncNow = useCallback(async () => {
    if (!auth) return;
    const queued = await getQueuedVisits();
    if (queued.length === 0) return;
    try {
      const result = await syncBatch(auth.worker_id, queued.map((q) => ({
        record_type: q.record_type, record_json: q.record_json,
      })));
      for (const q of queued) await removeQueuedVisit(q.localId);
      setToast(`Synced ${result.synced} visit(s)${result.failed ? `, ${result.failed} failed` : ""}.`);
      await refreshPendingCount();
    } catch {
      // stay queued, will retry next time we're online
    }
  }, [auth, refreshPendingCount]);

  useEffect(() => {
    refreshPendingCount();
    function onOnline() {
      setIsOnline(true);
      syncNow();
    }
    function onOffline() {
      setIsOnline(false);
    }
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, [syncNow, refreshPendingCount]);

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(""), 4000);
      return () => clearTimeout(t);
    }
  }, [toast]);

  if (!auth) {
    return <Login onLoggedIn={setAuthState} />;
  }

  function handleLogout() {
    clearAuth();
    setAuthState(null);
  }

  return (
    <div className="app-shell">
      <OfflineBanner isOnline={isOnline} pendingCount={pendingCount} onSyncNow={syncNow} />
      {toast && <div className="toast">{toast}</div>}

      {screen === "patients" && (
        <PatientList
          auth={auth}
          onSelectPatient={(p) => { setSelectedPatient(p); setScreen("record"); }}
          onOpenTasks={() => setScreen("tasks")}
        />
      )}

      {screen === "record" && selectedPatient && (
        <RecordVisit
          auth={auth}
          patient={selectedPatient}
          isOnline={isOnline}
          onBack={() => setScreen("patients")}
          onProcessed={(patient, result) => {
            setLastResult(result);
            setScreen("result");
          }}
          onQueuedOffline={async () => {
            await refreshPendingCount();
            setToast("Saved offline — will sync automatically when connected.");
            setScreen("patients");
          }}
        />
      )}

      {screen === "result" && lastResult && (
        <VisitResult
          patient={selectedPatient}
          result={lastResult}
          onDone={() => setScreen("patients")}
        />
      )}

      {screen === "tasks" && (
        <TaskList auth={auth} onBack={() => setScreen("patients")} />
      )}

      <button className="logout-btn" onClick={handleLogout}>Log out</button>
    </div>
  );
}
