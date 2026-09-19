from app.job_query import search_jobs


def test_search_jobs_empty_database_returns_empty_page(db_session) -> None:
    result = search_jobs(db_session, page=1, page_size=20)
    assert result.items == []
    assert result.total == 0
    assert result.page == 1
    assert result.page_size == 20
