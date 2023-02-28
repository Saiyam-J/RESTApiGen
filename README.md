# Project Description
This is a tool that reads from a existing SQL database and autogenerates back-end files of it, including models and REST APIs, by using Sqlalchemym, Flask and Blueprints.

# Features

- Supports SQLAlchemy 0.8.x - 2.0.x
- Makes Models and REST files for each table so its easier to modulate.
- Integrates flask-blueprints to connect the schemas to the app.py
- Accepts requests in the form of application/json
- Makes models that include relationships by detecting foreign keys.
- Fetching a record from a table with foreign keys returns a json with data which is joint by the foreign key.
- Makes the following REST APIs for each table
-- GET all records from a table
-- POST a record in a table
-- GET a specific record from a table
-- PATCH a specific record in a table
-- DELETE a specific record in a table

# Usage Instructions
## Installation
To install, use
```
pip install restapigen
```
## Usage
To run the autogeneration script, use 
```
RESTApiGen --user <username> --database <dbname> --password <password>
RESTApiGen -u <username> -d <dbname> -p <password>
```
## List of arguements
| arguement | abbreviated arg | 


