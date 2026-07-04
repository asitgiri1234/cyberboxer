"""
app.services package
-------------------
Business/application logic lives here, keeping route handlers thin. The upload
pipeline is split into focused, single-responsibility services:

* csv_cleaner   -> Pandas preprocessing (column/value normalisation)
* data_validator-> structural validation of the cleaned DataFrames
* upload_service-> orchestration + transactional persistence via SQLAlchemy
"""
