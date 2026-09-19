import requests


def main(api_base_url: str, source_text: str, api_key: str = ""):
    headers = {"X-API-Key": api_key} if api_key else {}
    response = requests.post(f"{api_base_url.rstrip('/')}/pipeline/ingest", json={"text": source_text}, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()
