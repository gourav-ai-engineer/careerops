import requests


def main(api_base_url: str, api_key: str = ""):
    headers = {"X-API-Key": api_key} if api_key else {}
    response = requests.post(f"{api_base_url.rstrip('/')}/jobs/fit-assessments/verified", headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()
