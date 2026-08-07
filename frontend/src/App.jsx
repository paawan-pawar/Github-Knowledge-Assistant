import { useEffect, useRef, useState } from "react";
import ImportScreen from "./components/ImportScreen";
import ScanningScreen from "./components/ScanningScreen";
import Workspace from "./components/Workspace";
import { api, ApiError } from "./api/client";

const ACTIVE_STATUSES = new Set(["pending", "fetching", "chunking", "embedding"]);
const POLL_INTERVAL_MS = 1200;

export default function App() {
  const [repo, setRepo] = useState(null);
  const [importError, setImportError] = useState(null);
  const [importing, setImporting] = useState(false);
  const pollHandle = useRef(null);

  useEffect(() => () => clearInterval(pollHandle.current), []);

  function pollStatus(repoId) {
    clearInterval(pollHandle.current);
    pollHandle.current = setInterval(async () => {
      try {
        const updated = await api.getRepo(repoId);
        setRepo(updated);
        if (!ACTIVE_STATUSES.has(updated.status)) {
          clearInterval(pollHandle.current);
        }
      } catch {
        clearInterval(pollHandle.current);
      }
    }, POLL_INTERVAL_MS);
  }

  async function handleImport(url, branch, forceReindex = false) {
    setImporting(true);
    setImportError(null);
    try {
      const created = await api.importRepo(url, branch, forceReindex);
      setRepo(created);
      if (ACTIVE_STATUSES.has(created.status)) {
        pollStatus(created.repo_id);
      }
    } catch (err) {
      setImportError(err instanceof ApiError ? err.message : "Something went wrong. Is the backend running?");
    } finally {
      setImporting(false);
    }
  }

  function handleReindex() {
    if (!repo) return;
    handleImport(repo.url, repo.ref === repo.default_branch ? null : repo.ref, true);
  }

  function handleClose() {
    clearInterval(pollHandle.current);
    setRepo(null);
    setImportError(null);
  }

  if (!repo) {
    return <ImportScreen onImport={handleImport} error={importError} isSubmitting={importing} />;
  }

  if (ACTIVE_STATUSES.has(repo.status) || repo.status === "error") {
    return (
      <ScanningScreen
        repo={repo}
        onRetry={() => handleImport(repo.url, null, true)}
        onBack={handleClose}
      />
    );
  }

  return <Workspace repo={repo} onReindex={handleReindex} onClose={handleClose} />;
}
