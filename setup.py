from setuptools import setup
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()
long_description = long_description[23:]
setup(
    name="RESTApiGen",
    version="0.2.0",
    description="REST API auto-generator.",
    url="https://github.com/Saiyam-J/RESTApiGen",
    author="Saiyam Jain",
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.10",
    install_requires=[
        "pymysql >= 1.0.2",
        "inflect",
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
