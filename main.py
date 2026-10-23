import io
import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from src import DatasetInfo, DatasetStorage, HealthResponse, setup_logging

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
storage = DatasetStorage()

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return {"status": "ok", "version": "1.0.0"}

@app.post("/upload", response_model=DatasetInfo)
async def upload_dataset(file: UploadFile = File(...)):
    """Read and store a CSV upload."""
    """Read and store a CSV upload."""
    filename = file.filename or ""

    # Accept CSV files only
    suffix = Path(filename).suffix.lower()
    if suffix != ".csv":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Please upload a .csv file.",
        )

    contents = await file.read()

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as e:
        logger.warning("Failed to parse uploaded file %s: %s", filename, e)
        raise HTTPException(
            status_code=400,
            detail="Could not read the file.",
        )

    dataset_id = storage.save(df, filename)
    logger.info("Uploaded dataset ID %s: %s (%s rows)", dataset_id, filename, len(df))

    metadata = storage.get_metadata(dataset_id)
    return DatasetInfo(**metadata)


@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, limit: int = Query(default=100, ge=1)):
    """Return up to limit rows from a stored dataset."""
    df = storage.get(dataset_id)
    if df is None:
        logger.warning("Dataset ID {dataset_id} not found")
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with ID {dataset_id} not found.",
        )
 
    # head() keeps the stored row order; to_json turns missing values into null
    records = json.loads(df.head(limit).to_json(orient="records"))
 
    logger.info("Returned %s rows from dataset ID {dataset_id}", len(records))
    return {
        "id": dataset_id,
        "data": records,
        "total_rows": len(df),
    }
 