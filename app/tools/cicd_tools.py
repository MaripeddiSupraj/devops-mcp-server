import os
import requests
from app.utils.logger import logger

GITHUB_REQUEST_TIMEOUT_SECONDS = 15

def get_github_headers() -> dict:
    """Helper to build GitHub API headers."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    # Use token if available for higher rate limits or private repos
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def get_github_pipeline_status(owner: str, repo: str) -> dict:
    """
    Get the status of the most recent GitHub Actions pipeline runs for a repository.
    """
    logger.info(f"Fetching pipeline status for {owner}/{repo}")
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
    
    try:
        response = requests.get(
            url,
            headers=get_github_headers(),
            params={"per_page": 10},
            timeout=GITHUB_REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
        
        runs = []
        for run in data.get("workflow_runs", []):
            runs.append({
                "id": run.get("id"),
                "name": run.get("name"),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "branch": run.get("head_branch"),
                "commit_message": run.get("head_commit", {}).get("message", "").split("\n")[0],
                "created_at": run.get("created_at"),
                "html_url": run.get("html_url")
            })
            
        return {"status": "success", "repository": f"{owner}/{repo}", "recent_runs": runs}
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch GitHub runs: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "hint": "Ensure the repository exists and is accessible. Set GITHUB_TOKEN environment variable for private repos."
        }

def get_github_failed_jobs(owner: str, repo: str, run_id: int) -> dict:
    """
    Get the specifically failed jobs from a GitHub Actions workflow run.
    Useful for an AI to quickly see which specific tests or build steps failed
    without parsing the entire pipeline context.
    """
    logger.info(f"Fetching failed jobs for {owner}/{repo} run {run_id}")
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
    
    try:
        response = requests.get(
            url,
            headers=get_github_headers(),
            timeout=GITHUB_REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
        
        failed_jobs = []
        for job in data.get("jobs", []):
            if job.get("conclusion") == "failure":
                # Find the specific steps that failed within the job
                failed_steps = [
                    step.get("name") for step in job.get("steps", []) 
                    if step.get("conclusion") == "failure"
                ]
                
                failed_jobs.append({
                    "job_name": job.get("name"),
                    "completed_at": job.get("completed_at"),
                    "failed_steps": failed_steps,
                    "html_url": job.get("html_url")
                })
                
        return {
            "status": "success", 
            "repository": f"{owner}/{repo}", 
            "run_id": run_id, 
            "failed_jobs": failed_jobs
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch GitHub jobs: {e}")
        return {"status": "error", "message": str(e)}
