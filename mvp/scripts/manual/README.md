# Manual verification scripts

Ad-hoc scripts for checking a **running** deployment by hand. They are not part of the
automated test suite and are not collected by pytest — the suite lives in
`mvp/backend/semantic-search-service/app/tests/`.

Start the services first (`mvp/run-local.sh` or `mvp/run-docker.sh`), then:

```bash
python mvp/scripts/manual/check_similarity_api.py
python mvp/scripts/manual/check_polarity_api.py
python mvp/scripts/manual/check_keyword_overlap_api.py
python mvp/scripts/manual/check_anonymous_access.py
```

Each script requires `requests` and targets `http://localhost:8000` (semantic search) or
`http://localhost:5054` (BFF).
