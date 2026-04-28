# DataCycleProject

This project's goal was to create a complete end-to-end data analytics solution for data coming from the HES-SO Bellevue campus in Sierre, Switzerland.


Our team decided to use Medallion architecture for this project, with our bronze and silver layer being a bucket in Google Cloud Storage and our gold layer being in BigQuery.

![Solution architecture](/pictures/Group4.drawio.png)

You can find detailed documentation in `documentation`
- `setup.md` contains a full guide on how to set up this solution from scratch
- `technical_documentation.md` specifies how each step works
- `scalability.md` is our assessment on how scalable this system would be in the upcoming months/years
- `gdpr_compliance.md` is our assessment on how our solution conforms to GDPR
- `user_guide.md` explains the data we store and how to use the dashboards
