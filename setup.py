from setuptools import setup

setup(
    name="RESTApiGen",
    version="0.1.2",
    install_requires=[
        "pymysql >= 1.0.2",
        "python_version >= 3.10",
        "inflector >=3.0.1",
        "flask",
        "flask-sqlalchemy",
        "flask-restful",
        "flask-blueprint",
        "flask-marshmallow",
        "marshmallow-sqlalchemy",
        "cryptography"
    ],
    entry_points = {
        "console_scripts" : [
            "RESTApiGen = RESTApiGen:main"
        ]
    }
)
