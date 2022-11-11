
from setuptools import setup

# Metadata goes in setup.cfg. These are here for GitHub's dependency graph.
setup(
    name="RESTApiGen",
    version="0.0.1",
    install_requires=[
        "pymysql >= 1.0.2",
        "python_version >= '3.10'",
        "Inflector >=3.0.1",
        "flask",
        "flask-sqlalchemy",
        "flask-restful",
        "flask-blueprint",
    ],
)
