import requests


def main(api_base_url: str, api_key: str = "", apply: bool = False):
    headers = {"X-API-Key": api_key} if api_key else {}
    action = "apply" if apply else "dry-run"
    response = requests.post(f"{api_base_url.rstrip('/')}/sync/smartsheet/{action}", headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()
