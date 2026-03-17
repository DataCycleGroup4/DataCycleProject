import duckdb
import os

con = duckdb.connect()
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")
con.execute("SET s3_endpoint = 'storage.googleapis.com';")
con.execute(f"SET s3_access_key_id = '{os.environ['HMAC_ACCESS_KEY']}';")
con.execute(f"SET s3_secret_access_key = '{os.environ['HMAC_SECRET_KEY']}';")