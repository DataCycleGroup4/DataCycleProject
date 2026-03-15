# DataCycleProject

This project's goal was to create a complete end-to-end data analytics solution for data coming from the HES-SO Bellevue campus in Sierre, Switzerland.


Our team decided to use Medallion architecture for this project, with our bronze and silver layer being a bucket in Google Cloud Storage. These scripts are designed to be run on a VM on the school's network and send the data to our bucket after extraction via SBM & SSH.