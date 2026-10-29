"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  backendJobStatus,
  clearGithubToken,
  dispatchBackendJob,
  githubTokenStatus,
  isDesktop,
  setGithubToken,
  type JobStatus,
} from "@/lib/desktop";

const POLL_MS = 5000;
const PIPELINES = ["healthcheck", "tabular-normalize"] as const;

const inputClass =
  "h-7 rounded-md border border-border bg-background px-2 text-xs outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring/50 disabled:opacity-60";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] font-medium text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}

export default function SystemStatusPage() {
  const desktop = isDesktop();
  const [tokenConfigured, setTokenConfigured] = useState<boolean | null>(null);
  const [tokenDraft, setTokenDraft] = useState("");
  const [pipeline, setPipeline] = useState<string>(PIPELINES[0]);
  const [dryRun, setDryRun] = useState(true);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!desktop) return;
    githubTokenStatus()
      .then((result) => setTokenConfigured(result.configured))
      .catch(() => setTokenConfigured(null));
  }, [desktop]);

  const stopPolling = useCallback(() => {
    if (timer.current) {
      clearInterval(timer.current);
      timer.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const poll = useCallback(
    async (id: string) => {
      try {
        const result = await backendJobStatus(id);
        setStatus(result);
        if (result?.state === "completed") stopPolling();
      } catch (error) {
        setMessage(error instanceof Error ? error.message : String(error));
        stopPolling();
      }
    },
    [stopPolling],
  );

  async function saveToken() {
    setBusy(true);
    setMessage(null);
    try {
      const result = await setGithubToken(tokenDraft);
      setTokenConfigured(result.configured);
      setTokenDraft("");
      setMessage("Token stored in the operating system keychain.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }

  async function forgetToken() {
    setBusy(true);
    setMessage(null);
    try {
      const result = await clearGithubToken();
      setTokenConfigured(result.configured);
      setMessage("Token removed from the keychain.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }

  async function runJob() {
    setBusy(true);
    setMessage(null);
    setStatus(null);
    const id = crypto.randomUUID();
    try {
      await dispatchBackendJob({ pipeline, request_id: id, dry_run: dryRun });
      setRequestId(id);
      setMessage("Run dispatched. GitHub Actions queues it before it starts.");
      stopPolling();
      timer.current = setInterval(() => void poll(id), POLL_MS);
      void poll(id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex max-w-2xl flex-col gap-4 p-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-sm font-medium">System Status</h1>
        <p className="text-xs text-muted-foreground">
          Backend jobs run in GitHub Actions, never on this machine. The app dispatches the workflow
          and reads the run status back.
        </p>
      </header>

      {!desktop && (
        <p className="rounded-md border border-border bg-muted/40 px-2 py-1.5 text-xs text-muted-foreground">
          Desktop app required: start it with <code className="font-mono">npm run desktop:dev</code> to
          manage the token and dispatch jobs.
        </p>
      )}

      <div className="flex flex-col gap-3 rounded-md border border-border p-3">
        <h2 className="text-xs font-medium">GitHub credentials</h2>
        <Field label="Status">
          <span className="text-xs text-muted-foreground">
            {tokenConfigured === null
              ? "unknown"
              : tokenConfigured
                ? "token stored in the keychain"
                : "no token stored"}
          </span>
        </Field>
        <Field label="Fine-grained token (Actions: read and write)">
          <div className="flex items-center gap-2">
            <input
              type="password"
              value={tokenDraft}
              onChange={(event) => setTokenDraft(event.target.value)}
              placeholder="github_pat_…"
              aria-label="GitHub token"
              disabled={!desktop || busy}
              className={`${inputClass} w-64`}
            />
            <Button size="sm" onClick={saveToken} disabled={!desktop || busy || !tokenDraft.trim()}>
              Save
            </Button>
            <Button size="sm" variant="outline" onClick={forgetToken} disabled={!desktop || busy}>
              Clear
            </Button>
          </div>
        </Field>
      </div>

      <div className="flex flex-col gap-3 rounded-md border border-border p-3">
        <h2 className="text-xs font-medium">Backend job</h2>
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Pipeline">
            <select
              value={pipeline}
              onChange={(event) => setPipeline(event.target.value)}
              aria-label="Pipeline"
              disabled={!desktop || busy}
              className={inputClass}
            >
              {PIPELINES.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </Field>
          <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(event) => setDryRun(event.target.checked)}
              disabled={!desktop || busy}
            />
            dry run (validate only)
          </label>
          <Button size="sm" onClick={runJob} disabled={!desktop || busy || !tokenConfigured}>
            Run job
          </Button>
        </div>

        <div className="flex flex-col gap-1 text-xs">
          <span className="text-muted-foreground">
            request id:{" "}
            <code className="font-mono">{requestId ?? "—"}</code>
          </span>
          <span className="text-muted-foreground">
            state: <span className="font-medium">{status?.state ?? "not started"}</span>
            {status?.conclusion ? ` (${status.conclusion})` : ""}
          </span>
          {status?.url && (
            <a
              className="text-blue-700 underline underline-offset-2"
              href={status.url}
              target="_blank"
              rel="noreferrer"
            >
              open the run log
            </a>
          )}
          {status?.state === "completed" && (
            <span className="text-muted-foreground">
              Persistent results are published by the workflow; artifacts expire after 7 days.
            </span>
          )}
        </div>

        {message && <p className="text-xs text-muted-foreground">{message}</p>}
      </div>
    </section>
  );
}
