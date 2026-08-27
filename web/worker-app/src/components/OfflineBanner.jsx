export default function OfflineBanner({ isOnline, pendingCount, onSyncNow }) {
  if (isOnline && pendingCount === 0) return null;
  return (
    <div className={`offline-banner ${isOnline ? "syncing" : "offline"}`}>
      {!isOnline && <span>📴 Offline — visits are being saved on this device</span>}
      {isOnline && pendingCount > 0 && (
        <span>
          🔄 {pendingCount} visit(s) pending sync{" "}
          <button className="link-btn" onClick={onSyncNow}>Sync now</button>
        </span>
      )}
      {!isOnline && pendingCount > 0 && <span> — {pendingCount} queued</span>}
    </div>
  );
}
