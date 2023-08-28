from pathlib import Path
import pandas as pd
from prefect import flow, task
from prefect_gcp.cloud_storage import GcsBucket
from prefect_gcp import GcpCredentials


@task(retries=3)
def extract_from_gcs(color: str, year: int, month: int) -> Path:
    """Download data from gcs"""
    # gcs_path = f"data/{color}_tripdata_{year}-{month:02}.parquet"
    gcs_path = f"/data/{color}/{color}_tripdata_{year}-{month:02}.parquet"
    gcs_block = GcsBucket.load("zoom-gcs")
    gcs_block.get_directory(from_path=gcs_path, local_path=f"../data/")
    return Path(f"../{gcs_path}")


@task()
def transform(path: Path) -> pd.DataFrame:
    """Data cleaning"""
    df = pd.read_parquet(path)
    print(
        f"pre: Missing passenger count: {df['passenger_count'].isna().sum()}")
    df["passenger_count"].fillna(0, inplace=True)
    print(
        f"post: Missing passenger count: {df['passenger_count'].isna().sum()}")
    return df

@task()
def write_bq(df: pd.DataFrame) -> None:
    """Write dataframe to Bigquery"""
    gcp_creds = GcpCredentials.load("gcp-creds")
    df.to_gbq(
        destination_table="dezoomcamp"
        project_id= #project id in google cloud
        credentials=gcp_creds.get_credentials_from_service_account()
        chunksize=500_000
        if_exists="append"
    )

@flow()
def etl_gcs_to_bg():
    """Main ETL flow to load data to Big Query datawrehouse"""
    color = "yellow"
    year = 2021
    month = 1

    path = extract_from_gcs(color, year, month)
    print (path)
    df = transform(path)
    write_bq(df)


if __name__ == "__main__":
    etl_gcs_to_bg()