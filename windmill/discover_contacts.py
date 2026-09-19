import requests


def main(api_base_url: str, job_id: int, company_name: str, company_domain: str, source_urls: list[str], api_key: str = ""):
    headers = {"X-API-Key": api_key} if api_key else {}
    payload = {"company_name": company_name, "company_domain": company_domain, "source_urls": source_urls[:20], "job_id": job_id, "role_keywords": []}
    response = requests.post(f"{api_base_url.rstrip('/')}/contacts/discover", json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()
