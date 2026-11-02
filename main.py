import io
import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from src import (
    DatasetInfo,
    DatasetStorage,
    HealthResponse,
    setup_logging,
    ProcessConfig,
    ProcessingReport,
    log_requests
)
from data_pipeline import (
    create_cleaning_report,
    process_data,
    validate_dataframe
)

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)
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

    # to_json turns missing values into null
    records = json.loads(df.head(limit).to_json(orient="records"))

    logger.info("Returned %s rows from dataset ID {dataset_id}", len(records))
    return {
        "id": dataset_id,
        "data": records,
        "total_rows": len(df),
    }


@app.post(
    "/datasets/{dataset_id}/process",
    response_model=ProcessingReport,
)
def process_dataset(dataset_id: int, config: ProcessConfig):
    """Validate and process a stored dataset using MP1 functions."""
    # Retrieve a copy (missing-dataset check stays outside the try block)
    df = storage.get(dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")

    # Request model
    config_dict = config.model_dump()
    required_columns = config_dict["validation"]["required_columns"]
    numeric_columns = config_dict["validation"]["numeric_columns"]

    missing_numeric = [col for col in numeric_columns if col not in df.columns]
    if missing_numeric:
        raise HTTPException(
            status_code=400,
            detail=f"Numeric columns not found in dataset: {missing_numeric}",
        )

    try:
        rows_before_validation = len(df)
        validated_df = validate_dataframe(
            df,
            required_columns=required_columns,
            numeric_columns=numeric_columns,
        )
        validation_rows_removed = rows_before_validation - len(validated_df)

        # Copy before processing
        validated_copy = validated_df.copy()

        processed_df = process_data(validated_df, config_dict)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    cleaning_report = create_cleaning_report(validated_copy, processed_df)

    # Update storage
    storage.update(dataset_id, processed_df)

    logger.info(
        "Processed dataset: id=%d, validation_removed=%d, rows_before=%d, rows_after=%d",
        dataset_id,
        validation_rows_removed,
        cleaning_report["rows_before"],
        cleaning_report["rows_after"],
    )

    return {
        "id": dataset_id,
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": cleaning_report,
    }
