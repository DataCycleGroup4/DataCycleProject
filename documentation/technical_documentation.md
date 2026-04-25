# Technical Documentation
This project provides an end-to-end data analytics solution.

Data is saved in the Google Cloud Platform and a Windows Client virtual machine is used to execute scripts.
This solution uses a medallion architecture pattern. Bronze and silver tier storage is in a GCP cloud storage bucket called `data-cycle-lake` and gold tier storage is in a data warehouse in GCP BigQuery called `DataCycle_Warehouse`.

The workflow is orchestrated by a GCP Cloud Workflow, which runs the `dailyworkflow.yml`file you can find in the root directory of this repository


# Bronze tier
This tier involves extracting the raw data via SMB and SFTP and storing it in our data lake.
We have the following data that needs extracting:

- Solar panel production data
- Room booking data
- Weather forecast data
- Temperature data
- Humidity data
- Power consumption data

We store the CSV and XLS versions of room bookings in bronze tier, but only use CSV later so don't move XLS to silver.

The scripts for bronze tier are:
- `/PS_Scripts/UploadDaily_ToHumidity.ps1 `
    - Extracts data via SMB from address `\\10.130.25.15` that matches pattern `*-Humidity.csv`
- `/PS_Scripts/UploadDaily_ToPowerConsumption.ps1`
    - Extracts data via SMB from address `\\10.130.25.152` that matches pattern `*-Consumption.csv`
- `/PS_Scripts/UploadDaily_ToSolarlogs.ps1`
    - Extracts data via SMB from address `\\10.130.25.152` that matches pattern `*-\d{2}\.(\d{2}).\d{4}.csv` for historical data, and `^min\d{2}(\d{2})\d{2}`for current data

- `/PS_Scripts/UploadDaily_ToTemperature.ps1`
    - Extracts data via SMB from address `\\10.130.25.152` that matches pattern `*-Temperature.csv`
- `/PS_Scripts/UploadWeekly_ToBooking_CSV.ps1`
    - Extracts data via SMB from address `\\10.130.25.152` that matches pattern `RoomAllocations_\d{4}(\d{2}` but from files that end with .csv
- `/PS_Scripts/UploadWeekly_ToBooking_XLS.ps1`
    - Extracts data via SMB from address `\\10.130.25.152` that matches pattern `RoomAllocations_\d{4}(\d{2}` but from files that end with .xls
- /Python_Scripts/Extract_WeatherForecast.py
    - Uses the following variables to extract the data via SFTP
        - `SFTP_HOST = "10.130.25.152"`
        - `SFTP_USER = "Student"`
        - `SFTP_PASS = "3uw.AQ!SWxsDBm2zi3"`
        - `SOURCE_FOLDERS = ["/Meteo/"]`

Data is saved in the `data-cycle-lake/raw` in the subdirectories
- `/bellevuebooking` for room data
- `/bellevueconso` for consumption, temperature, and humidity data
    - `/humidity`
    - `/temperature`
    - `/powerconsumption`
- `/solarlogs` for solar production data
    - `/production`
    - `/productionhistory`
- `/weather`for weather forecast data

# Silver tier

Scripts in this tier clean up any missing values in data, and organise the cleaned data into a separate directory structure within the `data-cycle-lake`

The scripts for the silver tier are:
- `/Python_Scripts/Bronze_to_Silver_Scripts/BookingCSVToSilver.py`
- `/Python_Scripts/Bronze_to_Silver_Scripts/HumidityToSilver.py`
- `/Python_Scripts/Bronze_to_Silver_Scripts/HumidityToSilver.py`
- `/Python_Scripts/Bronze_to_Silver_Scripts/PowerConsumptionToSilver.py`
- `/Python_Scripts/Bronze_to_Silver_Scripts/SolarlogsToSilver.py`
- `/Python_Scripts/Bronze_to_Silver_Scripts/SolarProductionToSilver.py`
- `/Python_Scripts/Bronze_to_Silver_Scripts/TemperatureToSilver.py`

- `/Python_Scripts/Bronze_to_Silver_Scripts/WeatherToSilver.py`

The scripts all use a service account to perform operations. We used the environment variable `SERVICE_ACCOUNT_KEY` link to the .json authentication file for the service account in GCP.

Pandas is used to extract the data from the bronze tier and load it into dataframes.
We run the cleaning operations on the dataframes, delete pre-existing data in order to avoid duplicates, then convert the final clean dataframe into a parquet file for more efficient storage usage. data from days is partitioned into the silver tier using *hive partitioning*. Each day's data is written in a separate folder that is named according to the structure `date=yyyy-mm-dd" in its month folder.

A final filepath looks like `data-cycle-lake/processed/cleansolarlogs/cleanproduction/02/date=2023-02-20/xyz.parquet`

Data is saved in the `data-cycle-lake/processed` in the subdirectories
- `/cleanbellevuebooking` for room data
- `/cleanbellevueconso` for consumption, temperature, and humidity data
    - `/cleanhumidity`
    - `/cleantemperature`
    - `/cleanpowerconsumption`
- `/cleansolarlogs` for solar production data
    - `/cleanproduction`
    - `/cleanproductionhistory`
- `/cleanweather`for weather forecast data

# Gold tier

In the gold tier we move our data from parquet files in the bucket to structured tables in a data warehouse in BigQuery.

Our warehouse is organised into a galaxy schema with the following tables

### Dimensions
- DimTime
- DimRoom
- DimReservation
- DimInverter
- DimForecast
- DimErrors

### Fact tables
- Power_FactTable
- Prediction_FactTable
- Rooms_FactTable
- Weather_FactTable

BigQuery doesn't support incremental random integers, so for IDs we use UUID strings (which it can generate)

The data warehouse's schema can be reconstructed by running the SQL script `/SQL_Scripts/make_tables.sql`

If you need to drop the tables, there is a script for that: `/SQL_Scripts/kill_tables.sql`

### Scripts
For this tier we have multiple files, all found in `/gold-layer-etl`
- `/etl` contains all scripts to load the data into each table
- `/utils` contains 2 files:
    - `gcs_reader.py` which has the function `read_parquet_from_gcs` needed to read the data for loading into tables
    - `bq_writer.py` which has the functions to write data into the BigQuery data warehouse
- `main.py` main file which orchestrates the process, calling the necessary functions for a given date
- `config.py` contains all paths needed, the run date, and the tables
- `backfill.py`runs main.py for a date range (used to fill the data warehouse if it's empty)


# Orchestration

All of these scripts are executed in order by a GCP Cloud Workflow daily, starting at 9am. You can see the whole process in the file `/dailyworkflow.yml`.

In order for the workflow to able to execute the tasks on the Windows VM, the VM needs to be listening to a request. This is achieved by running the script `/start_manager.bat` via Windows Task Scheduler on the VM every day at 8.50am. This will launch the file `manager.py`, which executes the requested task and sends a response to the workflow, letting it start the next step.

# Knime

This solution includes a Knime workflow that reads data from the `data-cycle-lake` bucket in GCP, and predicts the next day's consumption & production data with Random Forest models.
![Knime workflow](/Workflow.png)

## Explanation
The workflow begins by connecting to our GCP service account via credentials generated and stored in a .json file saved in the same private space as the workflow. We then connect to our storage bucket, from which the flow moves into 5 parallel loops to read:
- Booking data
- Solar production data
- Weather forecast data
- Energy consumption data

Weather data is read twice in parallel within 2 different date ranges.

When the file runs, it dynamically generates multiple dates:
- Today's date (at run-time)
- Tomorrow's Date
- The date 1 week before today

These dates are used as flow variables for row filters to limit our loaded data. The models for predicting solar production data are trained on the data of the past 7 days, and the model for consumption is trained on every date starting from January 1st 2023.

Values are aggregated in GroupBy nodes to structure our training data properly, then fed into learner nodes to train the models. Here's the config for each learner:


Once the models are trained, the predictions are made and appended to the Prediction_FactTable and the wofklow finishes. 

The workflow is triggered by the script `trigger_knime.py` found in the root directory. The script triggers the deployed version of the workflow in the Knime Edu-Hub cloud via a POST request to the API of the workflow at `https://api.edu-hub.knime.com/api-doc/?url=/deployments/rest:6e336bc0-ff6b-4f8a-91da-996781d84209/open-api#/`.

# PowerBI
The dashboards in PowerBI import a cached version of the data in the data warehouse, allowing for the data to be used.

You can find detailed documentation for this in user_guide.md

# SAC
Due to account permission constraints, we are only able to load data into SAC manually. This is done via CSV files generated by the script `SQL_Scripts/sac_data_to_csv.sql`

You can find detailed documentation for this in user_guide.md