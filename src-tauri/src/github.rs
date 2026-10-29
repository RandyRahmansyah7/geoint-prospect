//! GitHub Actions bridge: the only backend runtime is the `backend.yml` workflow.
//!
//! The personal access token lives in the operating system keychain, never in the repository,
//! the bundle, or the web UI. See docs/backend-runtime.md.

use std::time::Duration;

use keyring::Entry;
use reqwest::header::{ACCEPT, AUTHORIZATION, USER_AGENT};
use serde::{Deserialize, Serialize};

const REPO: &str = "RandyRahmansyah7/geoint-prospect";
const WORKFLOW_FILE: &str = "backend.yml";
const DEFAULT_BRANCH: &str = "main";
const API_BASE: &str = "https://api.github.com";
const KEYRING_SERVICE: &str = "geoint-prospect";
const KEYRING_USER: &str = "github-token";

/// Pipelines the app may request. Anything else never reaches the API.
const ALLOWED_PIPELINES: [&str; 2] = ["healthcheck", "tabular-normalize"];

#[derive(Debug, Clone, Serialize)]
pub struct TokenStatus {
    pub configured: bool,
}

#[derive(Debug, Deserialize)]
pub struct DispatchRequest {
    pub pipeline: String,
    pub request_id: String,
    pub input_path: Option<String>,
    pub dry_run: bool,
}

#[derive(Debug, Serialize)]
pub struct DispatchResult {
    pub request_id: String,
    pub run_title: String,
}

#[derive(Debug, Serialize)]
pub struct JobStatus {
    pub state: String,
    pub conclusion: Option<String>,
    pub url: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Deserialize)]
struct WorkflowRuns {
    workflow_runs: Vec<WorkflowRun>,
}

#[derive(Debug, Deserialize)]
struct WorkflowRun {
    display_title: String,
    status: String,
    conclusion: Option<String>,
    html_url: String,
    created_at: String,
    updated_at: String,
}

fn entry() -> Result<Entry, String> {
    Entry::new(KEYRING_SERVICE, KEYRING_USER).map_err(|e| format!("keychain unavailable: {e}"))
}

fn token() -> Result<String, String> {
    entry()?
        .get_password()
        .map_err(|_| "no GitHub token stored; add one on the System Status page".to_string())
}

fn client() -> Result<reqwest::Client, String> {
    reqwest::Client::builder()
        .timeout(Duration::from_secs(15))
        .build()
        .map_err(|e| format!("http client failed: {e}"))
}

fn validate(request: &DispatchRequest) -> Result<(), String> {
    if !ALLOWED_PIPELINES.contains(&request.pipeline.as_str()) {
        return Err(format!(
            "pipeline '{}' is not allowed; allowed: {}",
            request.pipeline,
            ALLOWED_PIPELINES.join(", ")
        ));
    }
    let id = request.request_id.as_str();
    if id.is_empty()
        || id.len() > 64
        || !id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || "._-".contains(c))
    {
        return Err("request id must be 1-64 characters of [A-Za-z0-9._-]".to_string());
    }
    if let Some(path) = request.input_path.as_deref() {
        if path.starts_with('/') || path.contains("..") || path.is_empty() {
            return Err("input path must be repository-relative and without '..'".to_string());
        }
    }
    Ok(())
}

#[tauri::command]
pub fn github_token_status() -> TokenStatus {
    TokenStatus {
        configured: token().is_ok(),
    }
}

#[tauri::command]
pub fn set_github_token(value: String) -> Result<TokenStatus, String> {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return Err("token must not be empty".to_string());
    }
    entry()?
        .set_password(trimmed)
        .map_err(|e| format!("could not store the token: {e}"))?;
    Ok(TokenStatus { configured: true })
}

#[tauri::command]
pub fn clear_github_token() -> Result<TokenStatus, String> {
    match entry()?.delete_credential() {
        Ok(()) => Ok(TokenStatus { configured: false }),
        Err(keyring::Error::NoEntry) => Ok(TokenStatus { configured: false }),
        Err(e) => Err(format!("could not remove the token: {e}")),
    }
}

#[tauri::command]
pub async fn dispatch_backend_job(request: DispatchRequest) -> Result<DispatchResult, String> {
    validate(&request)?;
    let token = token()?;

    let inputs = serde_json::json!({
        "pipeline": request.pipeline,
        "request_id": request.request_id,
        "input_path": request.input_path.unwrap_or_else(|| "engine/tests/fixtures/observations.csv".to_string()),
        "dry_run": if request.dry_run { "true" } else { "false" },
    });

    let response = client()?
        .post(format!(
            "{API_BASE}/repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
        ))
        .header(ACCEPT, "application/vnd.github+json")
        .header(USER_AGENT, "geoint-prospect")
        .header(AUTHORIZATION, format!("Bearer {token}"))
        .json(&serde_json::json!({ "ref": DEFAULT_BRANCH, "inputs": inputs }))
        .send()
        .await
        .map_err(|e| format!("dispatch failed: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        return Err(format!("GitHub rejected the dispatch ({status}): {body}"));
    }

    Ok(DispatchResult {
        run_title: format!("backend {}", request.request_id),
        request_id: request.request_id,
    })
}

#[tauri::command]
pub async fn backend_job_status(request_id: String) -> Result<Option<JobStatus>, String> {
    let token = token()?;
    let expected = format!("backend {request_id}");

    let response = client()?
        .get(format!(
            "{API_BASE}/repos/{REPO}/actions/runs?event=workflow_dispatch&per_page=50"
        ))
        .header(ACCEPT, "application/vnd.github+json")
        .header(USER_AGENT, "geoint-prospect")
        .header(AUTHORIZATION, format!("Bearer {token}"))
        .send()
        .await
        .map_err(|e| format!("status request failed: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        return Err(format!(
            "GitHub rejected the status request ({status}): {body}"
        ));
    }

    let runs: WorkflowRuns = response
        .json()
        .await
        .map_err(|e| format!("unexpected GitHub response: {e}"))?;

    Ok(runs
        .workflow_runs
        .into_iter()
        .find(|run| run.display_title == expected)
        .map(|run| JobStatus {
            state: run.status,
            conclusion: run.conclusion,
            url: run.html_url,
            created_at: run.created_at,
            updated_at: run.updated_at,
        }))
}
