import requests


def main(api_base_url: str, api_key: str = ""):
    headers = {"X-API-Key": api_key} if api_key else {}
    response = requests.get(f"{api_base_url.rstrip('/')}/dashboard/summary", headers=headers, timeout=30)
    response.raise_for_status()
    summary = response.json()
    response = requests.post(f"{api_base_url.rstrip('/')}/jobs/fit-assessments/verified", headers=headers, timeout=60)
    response.raise_for_status()
    fit = response.json()
    response = requests.post(f"{api_base_url.rstrip('/')}/sync/smartsheet/dry-run", headers=headers, timeout=60)
    response.raise_for_status()
    return {"summary": summary, "fit": fit, "smartsheet_dry_run": response.json()}
