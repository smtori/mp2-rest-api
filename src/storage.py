import logging

logger = logging.getLogger(__name__)


class DatasetStorage:
    def __init__(self):
        self._store = {}
        self._counter = 0

    def save(self, df, filename):
        """Store a copy of the data and return a new integer ID."""
        # New Integer ID
        self._counter += 1
        dataset_id = self._counter

        # Save a copy of the df
        self._store[dataset_id] = {
            "filename": filename,
            "df": df.copy()
        }

        # Log the save
        logger.debug(f"Dataset {filename} (ID: {dataset_id}) saved.")

        return dataset_id

    def get(self, dataset_id):
        """Return a copy of the stored DataFrame, or None."""
        entry = self._store.get(dataset_id)
        if entry is None:
            logger.debug(f"Dataset ID ({dataset_id}) not found.")
            return None

        logger.debug("Retrieved dataset successfully.")

        return entry["df"].copy()

    def get_metadata(self, dataset_id):
        """Return the dataset metadata, or None."""
        entry = self._store.get(dataset_id)
        if entry is None:
            logger.debug(f"Dataset ID ({dataset_id}) not found.")
            return None
        
        df = entry["df"]
        return {
            "id": dataset_id,
            "filename": entry["filename"],
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": [str(c) for c in df.columns],
        }

    def update(self, dataset_id, df):
        """Replace an existing dataset; return True, or False if missing."""
        if dataset_id not in self._store:
            logger.debug("Update failed: dataset ID {dataset_id} not found")
            return False

        self._store[dataset_id]["df"] = df.copy()
        logger.debug("Updated dataset ID {dataset_id}")
        return True

    def clear(self):
        """Clear all data and reset the ID counter."""
        self._store.clear()
        self._counter = 0
