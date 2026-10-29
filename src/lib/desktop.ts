/**
 * Tauri bridge. The desktop shell is the only place that talks to GitHub Actions
 * (see docs/backend-runtime.md); in a plain browser these calls report that the desktop
 * app is required instead of pretending to work.
 */

export type TokenStatus = { configured: boolean };

export type JobStatus = {
  state: string;
  conclusion: string | null;
  url: string;
  created_at: string;
  updated_at: string;
};

export type DispatchRequest = {
  pipeline: string;
  request_id: string;
  input_path?: string;
  dry_run: boolean;
};

type TauriGlobal = {
  core: {
    invoke<T>(command: string, args?: Record<string, unknown>): Promise<T>;
  };
};

declare global {
  interface Window {
    __TAURI__?: TauriGlobal;
  }
}

export function isDesktop(): boolean {
  return typeof window !== "undefined" && Boolean(window.__TAURI__);
}

function invoke<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  const tauri = typeof window === "undefined" ? undefined : window.__TAURI__;
  if (!tauri) {
    return Promise.reject(new Error("Desktop app required: start it with npm run desktop:dev."));
  }
  return tauri.core.invoke<T>(command, args);
}

export const githubTokenStatus = () => invoke<TokenStatus>("github_token_status");

export const setGithubToken = (value: string) => invoke<TokenStatus>("set_github_token", { value });

export const clearGithubToken = () => invoke<TokenStatus>("clear_github_token");

export const dispatchBackendJob = (request: DispatchRequest) =>
  invoke<{ request_id: string; run_title: string }>("dispatch_backend_job", { request });

export const backendJobStatus = (requestId: string) =>
  invoke<JobStatus | null>("backend_job_status", { requestId });
