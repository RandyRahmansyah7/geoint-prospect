#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod github;

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            github::github_token_status,
            github::set_github_token,
            github::clear_github_token,
            github::dispatch_backend_job,
            github::backend_job_status,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
