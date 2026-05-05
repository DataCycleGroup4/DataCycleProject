# Compliance assessment

## Lawful basis & transparency

We only use the data provided by our university for its intended purpose, creating an end-to-end data analytics solution for solar panel production in the Bellevue Campus in Sierre. Personal data related to the room bookings is anonymised before being stored in the data lake.

## Purpose limitation

The only data we use is the data provided by the school for the purpose of creating the analytics solution, and it is only used for its intended purpose.

## Data minimisation

For external services like Knime and SAC, we only import the data we need to perform the functionalities we require from those platforms.

## Accuracy

Data is "cleaned" by filling in missing values, and columns that were originally in French are renamed. No data is changed to lead to more accurate results further along the pipeline.

## Storage limitation

Currently we have no set deletion policy. However, as discussed in the scalability report it would be smarter financially to archive data, or if that isn't possible it able to be deleted. GCP, which is where we store our data, is fully GDPR compliant, meaning we can delete all of our data whenever we want.

## Integrity and confidentiality

Our data is encrypted at rest and in transit due to the versions of protocols we use for SMB and SFTP and GCP's encryption. Unauthorised users are not allowed to view data in our data lake or warehouse in GCP and we have row security policies in our PowerBI dashboard.

## Ethics

The only personal data in the pipeline is the first and last name of the user who makes a room reservation, and the professor for whom that room is reserved. Both Powershell scripts that extract the raw data via SMB also anonymise this personal data, leading to us not having any personal data in our GCP storage.

Our full prediction workflow is both documented and included in this repository for transparency.

## Potential problems

All cloud resources used in our project are located in Switzerland, the same region as where the data is generated. If a customer were to utilise this solution, they would need to consider where they store data if its outside of Europe.