from pathlib import Path
import pandas as pd
from prefect import flow, task
from prefect_gcp.cloud_storage import GcsBucket
from prefect.tasks import task_input_hash
from datetime import timedelta

@task(retries=3, cache_key_fn=task_input_hash, cache_expiration=timedelta(days=1))
def fetch(url: str) -> pd.DataFrame:
    """Read data from web then convert it to dataframe"""
    df = pd.read_csv(url)
    return df


@task(log_prints=True)
def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Fix dtype issues"""
    df["tpep_pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"])
    df["tpep_dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"])
    print(df.head(2))
    print(f"columns: {df.dtypes}")
    print(f"rows: {len(df)}")
    return df


@task
def write_local(df: pd.DataFrame, color: str, dataset_file: str) -> Path:
    """Write dataframe as a parquet file"""
    path = Path(f"data/{color}/{dataset_file}.parquet")
    df.to_parquet(path, compression="gzip")
    return path


@task()
def write_gcs(path: Path) -> None:
    """Upoading local file to Google cloud storage"""
    gcs_block = GcsBucket.load("zoom-gcs")
    gcs_block.upload_from_path(from_path=f"{path}", to_path=path)
    return


@flow()
def etl_web_to_gcs(year, month, color) -> None:
    """Main ETL function"""
    dataset_file = f"{color}_tripdata_{year}-{month:02}"
    dataset_url = f"https://github.com/DataTalksClub/nyc-tlc-data/releases/download/{color}/{dataset_file}.csv.gz"

    df = fetch(dataset_url)
    df_cleaned = clean_df(df)
    path = write_local(df_cleaned, color, dataset_file)
    write_gcs(path)


@flow()
def etl_parent_flow(
    months: list[int] = [1, 2], year: int = 2021, color: str = "yellow"
):
    for month in months:
        etl_web_to_gcs(year, month, color)


if __name__ == "__main__":
    color = "yellow"
    months = [1]
    year = 2021
    etl_parent_flow(months, year, color)
