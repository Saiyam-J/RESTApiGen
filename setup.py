from setuptools import setup

setup(
    name="RESTApiGen",
    version="0.0.1",
    install_requires=[
        "pymysql >= 1.0.2",
        "python_version >= '3.10'",
        "inflect >=6.0.2",
        "flask",
        "flask-sqlalchemy",
        "flask-restful",
        "flask-blueprint",
    ],
    entry_points = {
        "console_scripts" : [
            "RESTApiGen = RESTApiGen:main"
        ]
    }
)
