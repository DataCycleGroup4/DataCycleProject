# DataCycleProject

This project's goal was to create a complete end-to-end data analytics solution for data coming from the HES-SO Bellevue campus in Sierre, Switzerland.


Our team decided to use Medallion architecture for this project, with our bronze and silver layer being a bucket in Google Cloud Storage. These scripts are designed to be run on a VM on the school's network and send the data to our bucket after extraction via SBM & SSH.

# PS_Scripts

These files retrieve data from the SMB fileshare on the network the VM is located on and send it to the correct folder in GCP

# Python_Scripts

Currently contains a directory with scripts used to clean bronze layer data and send it to silver layer convert to Parquet + the script to extract raw weather forecast data