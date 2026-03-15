import duckdb

con = duckdb.connect()
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")
con.execute("SET s3_endpoint = 'storage.googleapis.com';")
con.execute("SET s3_access_key_id = 'HMAC_KEY';")
con.execute("SET s3_secret_access_key = 'HMAC_SECRET';")