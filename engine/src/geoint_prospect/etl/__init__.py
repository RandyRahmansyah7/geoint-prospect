"""ETL foundations: metadata contracts, ingest, transform, SQL, validation."""

from geoint_prospect.etl.contracts import DataFormat, DatasetMetadata
from geoint_prospect.etl.ingest import read_dataset
from geoint_prospect.etl.pipeline import run_pipeline
from geoint_prospect.etl.query import run_sql
from geoint_prospect.etl.transform import filter_time, with_provenance
from geoint_prospect.etl.validate import validate_table

__all__ = [
    "DataFormat",
    "DatasetMetadata",
    "filter_time",
    "read_dataset",
    "run_pipeline",
    "run_sql",
    "validate_table",
    "with_provenance",
]
