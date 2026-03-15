import duckdb
import os

con = duckdb.connect()
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")
con.execute("SET s3_endpoint = 'storage.googleapis.com';")
con.execute(f"SET s3_access_key_id = '{os.environ['HMAC_ACCESS_KEY']}';")
con.execute(f"SET s3_secret_access_key = '{os.environ['HMAC_SECRET_KEY']}';")

bronze_base = "s3://data-cycle-lake/raw/bellevueconso/powerconsumption"
silver_base = "s3://data-cycle-lake/processed/cleanbellevueconso/cleanpowerconsumption"

for month in range(1, 13):
    month_str = str(month).zfill(2)

    con.execute(f"""
        COPY (
            SELECT
                STRPTIME(Date, '%d.%m.%Y')::DATE           AS date,
                Heure::TIME                                 AS time,
                TRIM("Unité affichage")                     AS unit,
                TRY_CAST("Valeur Acquisition" AS DECIMAL)   AS value_acquired,
                TRY_CAST(Variation AS DECIMAL)              AS variation
            FROM read_csv_auto(
                '{bronze_base}/{month_str}/*.csv',
                delim=';',
                header=true
            )
            WHERE date IS NOT NULL
              AND value_acquired IS NOT NULL
              AND MONTH(STRPTIME(Date, '%d.%m.%Y')) = {month}
        )
        TO '{silver_base}/{month_str}/'
        (FORMAT PARQUET, COMPRESSION SNAPPY)
    """)
    print(f"Month {month_str} done.")

print("All months written to silver.")