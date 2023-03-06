from setuptools import setup
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()
setup(
    name="RESTApiGen",
    version="0.1.4",
    url="https://github.com/Saiyam-J/RESTApiGen",
    author="Saiyam Jain",
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
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
