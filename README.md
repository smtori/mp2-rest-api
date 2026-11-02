# MP2 REST API

This project is a FastAPI application that lets users upload a CSV file, store it in memory, and clean it through HTTP requests. `GET /health` reports the API's status and version, `POST /upload` accepts a CSV and returns its metadata with a new dataset ID, and `GET /datasets/{id}` returns the stored rows (up to an optional `limit`) along with the total row count. `POST /datasets/{id}/process` takes a JSON configuration, validates the dataset's required and numeric columns, removes duplicates and missing values, optionally removes outliers, and returns a cleaning report. The processing step reuses my MP1 data pipeline, copied into the `data_pipeline/` package, so the same validation and cleaning logic works from both the command line and the API. A request-logging middleware gives every request an eight-character ID, logs its method, path, status code and duration, and returns the ID in an `X-Request-ID` response header.

## Running the API

    python -m pip install -r requirements.txt
    python -m uvicorn main:app --reload

Then open http://127.0.0.1:8000/docs to try the endpoints.

## Running the tests

    python -m pytest tests -v