# Project Description
RESTAPIGen is a tool that works with an existing SQL database and autogenerates back-end files based on the structure of the SQL. It creates Models that auto-detects the field type. Further, after creating the Models, it harnesses the combined power of flask-blueprint and flask-marshmallow to create APIs around the pre-generated Models. The final result is a fully-working RESTFul API which is ready to be customized. Statistically, 100% of the developers were able to create a kick-starter boilerplate API which saved several days of monotonous coding.

# Features

- Makes Models and REST files for each table so its easier to modulate and customize as per the needs.
- Integrates flask-blueprints and auto registers the models.
- Accepts requests in the form of application/json and also responds in JSON.
- Auto-detects one-to-one, one-to-many and many-to-many relationships and creates an application level soft link, even if the SQL tables are not hard indexed.
- Responds with an entire set of Collection based on the detected relationship, performs a JOIN wherever required, automatically.
- Makes the following REST APIs for each table
-- `GET` LIST : Retrieve all records from a table
-- `POST` COLLECTION : Insert a record into the table
-- `GET` GET : Retrieve a row or an entire Collection from a table
-- `PATCH` PUT : Update a row with newer data in a table
-- `DELETE` PURGE : Performs a delete operation of a row or a collection in a table

# Usage Instructions

## Requirements as a Developer
- This tool is created to facilitate development of an API for **intermediate to advanced Flask Users**.
- Beginners must learn how to create API using Flask by referring to their documentation.
- The idea of the tool was to eliminate the monotonous coding which could have been automated.
- Before beginning, you must also know how to _semantically_ create your database and establish relationships.
- The tool heavily relies on a semantic approach of how the database was created and columns were named. Example: The Primary Key of Users table does **not** have to be called `UserID`. It is just an `id`.
- Follow naming conventions and semantics. **Tables MUST always be named in Plural and Foreign Keys are always named in Singular**. Example: The JOIN should work on Users.id = Profiles.user_id
- Enjoy, and git gud!

## Installation

```
pip install restapigen
```

## Usage
To run the autogeneration script, use 
```
RESTApiGen --user <username> --database <dbname> --password <password>
RESTApiGen -u <username> -d <dbname> -p <password>
```
## List of arguments
| Argument   | Abbreviation | Usage                            |
|------------|--------------|----------------------------------|
| -\-user     | -u           | Enter the username               |
| -\-password | -p           | Enter the password               |
| -\-database | -d           | Enter the database name          |
| -\-host     | -ho          | (Optional) Enter the hostname    |
| -\-port     | -po          | (Optional) Enter the port number |
--------------------------------------

## Security Warning

- Commands entered in the terminal can be viewed, in most cases it preserves the history.
- It is highly recommended that you store the password as an environment variable and only call the environment variable.
- Since the API Generator cannot access environment variable or identify whether you entered an environment variable name or an actual password, it will consider the literal input as a password.
- **You are advised to modify the source code after generation and secure the app.**
----------------
## License
The code is distributed under MIT license. Read the licence document in the source code to know more.

----------------
## Author
Written by: [Saiyam Jain](https://github.com/Saiyam-J)
Collaborator: [Karma Dice](https://github.com/karmicdice)