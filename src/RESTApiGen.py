import pymysql, os, argparse, inflect, sys

class RESTApiGenerator:

    '''
    Description: Accepts hostname, username, password and database name
    '''

    def __init__(self):
        parser = argparse.ArgumentParser('RESTApiGen')
        parser.add_argument("-ho", "--host", dest="host", required=False, default="localhost")
        parser.add_argument("-u", "--user", dest="user", required=True)
        parser.add_argument("-p", "--password", dest="password", required=True)
        parser.add_argument("-d", "--database", dest="db", required=True)
        parser.add_argument("-po", "--port", dest="port", required=False, default=3306)
        parser.add_argument("--only-models", action='store_true', help="Only make models")
        parser.add_argument("--use-blueprints", action='store_true', help="Adds all the routes in a single app file")
        parser.add_argument("--disable-foreignkey", action='store_true', help="Disables foreign key checking")
        self.args = parser.parse_args()
        self.p = inflect.engine()
        self.conn()
        

    def conn(self):
        print('Connecting to database')
        try:
            connexion = pymysql.connect(
                host=self.args.host,
                user=self.args.user,
                password=self.args.password,
                port=self.args.port,
                db=self.args.db
            )
        except:
            return "Unable to connect to the database"
        self.cursor = connexion.cursor()
        self.gettables()

    def gettables(self):
        self.cursor.execute("show tables")
        tables = self.cursor.fetchall()
        self.tables = {}
        self.primary = {}
        self.listofprikeys = []
        for table in tables: 
            self.tables[(table[0])] = None
        self.getcolumns()

    def getcolumns(self):

        for table in self.tables:
            self.cursor.execute("explain {}".format(table))
            allcolumns = self.cursor.fetchall()
            columns = []
            for column in allcolumns:
                columndetails = []
                for columninfo in column:
                    columndetails.append(columninfo)
                if 'PRI' in column:
                    self.primary[table]=column[:2]
                    self.listofprikeys.append(column[0])
                columns.append(columndetails)
            self.tables[table] = columns
        self.getrelations()
    def getrelations(self):
        # ------------------- Add method to detect foreign keys that arent primary key to another table later --------
        self.relations = {}
        for table in self.tables:
            self.relations[table] = []
        if not self.args.disable_foreignkey:
            for table in self.tables:
                tablename = self.p.singular_noun(table)
                columns = self.tables[table]
                for column in columns:
                    for primary in self.primary:
                        if '_{}'.format(self.primary[primary][0]) in column[0]:
                            parent = column[0].split('_{}'.format(self.primary[primary][0]))[0]
                            plural = self.p.plural(parent)
                            if plural not in self.tables:
                                raise Exception("{} table is missing. Create the table or run with --disable-foreignkey \nThis is with reference to the {} column in {} table".format(plural, parent+"_"+self.primary[primary][0], table))
                            else:
                                if table not in self.relations[plural]:
                                    self.relations[plural].append(table)
        self.makemodels()

    def convertdtype(self, dtype, length):
        if dtype[:3] == 'int':
            dtype = 'int'

        match dtype:
            case "int":
                dtype = "Integer"
            case "varchar":
                dtype = "String"
            case "float":
                dtype = "Float"
            case "decimal":
                dtype = "Numeric"
            case "text":
                dtype = "String"
            case "datetime":
                dtype = "DateTime"
            case "smallint":
                dtype = "Integer"
            case "tinyint":
                dtype = "Integer"
            case "enum":
                dtype = "Enum"
            case "char":
                dtype = "String"
            case "date":
                dtype = "DateTime"
        if (dtype != 'Integer') and (dtype != "DateTime"):
            dtype = dtype + length
            if dtype[-1] == "d":
                dtype = dtype.replace(" ", ", ")
                dtype = dtype + " = True"
        return dtype
    
    def makemodels(self):
        print("\n\nMaking Models.....\n")
        os.mkdir('Models')
        os.chdir('Models')
        finit = open('__init__.py', 'w')
        if self.args.only_models:
            lines = [
                "from flask import Flask\n",
                "from flask_sqlalchemy import SQLAlchemy\n",
                "app = Flask(__name__)\n",
                "app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@{}:{}/{}'\n".format(
                    self.args.user, self.args.password, self.args.host, self.args.port, self.args.db
                ),
                "app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False\n",
                "db = SQLAlchemy(app)\n"]
            finit.writelines(lines)
            finit.close()
        else:
            lines = ['from __main__ import db\n']
            finit.writelines(lines)
            finit.close()
        
        for table in self.tables:
            tablename = self.p.singular_noun(table)
            f = open("{}_model.py".format(tablename), 'w')
            f.write('from . import db\n')
            model = ['class {}(db.Model):\n'.format(tablename.capitalize()),
                     '\t__tablename__= \'{}\'\n'.format(table)
                     ]
            columns = self.tables[table]
            for column in columns:
                colname = column[0]
                coldatatype = column[1]
                nullable = 'True' if column[2]=='YES' else 'False'
                default= 'None' if column[4]==None else column[4]
                if "(" in coldatatype:
                    y = coldatatype.find("(")
                    x = [coldatatype[:y], coldatatype[y:]]
                else:
                    x = [coldatatype, ""]

                dtype = x[0]
                length = x[1]
                dtype = self.convertdtype(dtype, length)
                if '_' in column[0]:
                    prikey = column[0].split('_')[1]
                    if prikey in self.listofprikeys:
                        parent = column[0].split('_')[0]
                        plural = self.p.plural(parent)
                        if self.primary[plural][0]==prikey:
                            columnstr = "\t{} = db.Column(db.{}, db.ForeignKey(\'{}.{}\'))\n".format(colname,dtype, plural, self.primary[plural][0])
                        else:
                            raise Exception("Invalid Foreign Key reference at {} in table {}. Try running with --disable-foreignkey to disable foreign key checker".format(column[0], table))
                    else:
                        columnstr = '\t{} = db.Column(db.{}, nullable={})\n'.format(column[0], dtype, nullable)
                else:
                    columnstr = '\t{} = db.Column(db.{}, nullable={})\n'.format(column[0], dtype, nullable)

                if colname == self.primary[table][0]:
                    columnstr=columnstr[:-16]+"primary_key=True)\n"
                    returnint = ["Integer", "Numeric"]
                    if dtype in returnint:
                        self.primary[table] += ("int",)
                    elif dtype == "Float":
                        self.primary[table] += ("float",)
                    else:
                        self.primary[table] += ("string",)
                model.append(columnstr)
            for relation in self.relations[table]:
                relationname = self.p.singular_noun(relation)
                backref = "\t{} = db.relationship(\'{}\', backref = db.backref(\"{}Of{}\"))\n".format(relation, relationname.capitalize(), tablename.capitalize(), relation.capitalize())
                model.append(backref)
            model.append("\n\tdef __repr__(self):\n")
            model.append("\t\treturn '<{} %r>' % self.{}\n".format(tablename.capitalize(), self.tables[table][0][0]))
            f.writelines(model)
            f.close()
            print("Finished making {}_model".format(tablename))
        if self.args.only_models:
            print("\nFinished making all Models\n")
            exit()
        else:
            if self.args.use_blueprints:
                self.makeRest()
            else:
                self.makeroutes()


    def makeroutes(self):
        print("\n\nMaking Routes......\n")
        os.chdir('..')
        os.mkdir('Routes')
        os.chdir('Routes')
        finit = open('__init__.py', 'w')
        lines = [
            "from __main__ import app, db\n"
        ]
        for table in self.tables:
            tablename = self.p.singular_noun(table)
            lines.append("from Models.{}_model import {}\n".format(tablename, tablename.capitalize()))
        finit.writelines(lines)
        finit.close()
        for table in self.tables:
            tablename = self.p.singular_noun(table)
            f = open("{}_routes.py".format(tablename), 'w')
            imports = [
                "from flask import request, jsonify\n",
                "from . import *\n\n",
            ]
            f.writelines(imports)
            listresource = {"route":[],"get":[], "post":[]}
            listresource["route"] = [
                "@app.route(\"/{}\", methods = ['GET', 'POST'])\n".format(table),
                "def {}():\n".format(table)
                                    ]
            listresource["get"] = [
                "\tif request.method == 'GET':\n",
                "\t\t{} = {}.query.all()\n".format(table, tablename.capitalize()),
                "\t\tif not {}:\n\t\t\treturn jsonify({{\'message\': \"No {} found\"}}), 404\n\n".format(table, table),
                "\t\tresponse = []\n",
                "\t\tfor {} in {}:\n".format(tablename, table),
                "\t\t\tresponse.append({\n",
            ]
            columns = self.tables[table]
            nullable = []
            auto_increment = []
            for column in columns:
                if column[2] == 'YES':
                    nullable.append(column[0])
                if column[5] == 'auto_increment':
                    auto_increment.append(column[0])
                listresource["get"].append("\t\t\t\t\"{}\":{}.{},\n".format(column[0], tablename, column[0]))
            listresource["get"][-1]=listresource["get"][-1][:-2]+'\n'
            listresource["get"].append("\t\t\t\t})\n\t\treturn jsonify(response)\n\n")

            listresource["post"].append("\tif request.method == 'POST':\n")
            for i in nullable:
                nullchecker = ["\t\tif '{}' in request.get_json():\n\t\t\t{} = request.get_json()['{}']\n".format(i,i,i),
                               "\t\telse:\n\t\t\t{}=None\n".format(i)
                               ]
                listresource["post"].extend(nullchecker)
            listresource["post"].append("\t\tnew_{} = {}(\n".format(tablename, tablename.capitalize()))
            for column in columns:
                if column[0] in nullable:
                    listresource["post"].append("\t\t\t{}={},\n".format(column[0], column[0]))
                elif column[0] in auto_increment:
                    pass
                else:
                    listresource["post"].append("\t\t\t{}=request.get_json()['{}'],\n".format(column[0], column[0]))
            listresource["post"][-1] = listresource["post"][-1][:-2] + '\n'
            listresource["post"].extend(["\t\t\t)\n\t\tdb.session.add(new_{})\n\t\tdb.session.commit()\n".format(tablename),
                                        "\t\treturn jsonify({{\'message\': \"{} added successfully\"}})\n\n".format(tablename)])

            resource = {"route": [], "get": [], "patch": [], "delete": []}
            resource["route"] = [
                "@app.route(\"/{}/<{}:{}_{}>\", methods = ['GET', 'PATCH', 'DELETE'])\n".format(table, self.primary[table][2] ,tablename, self.primary[table][0]),
                "def {}({}_{}):\n".format(tablename, tablename, self.primary[table][0])
            ]
            resource["get"] = [
                "\tif request.method == 'GET':\n",
                "\t\t{} = {}.query.get_or_404({}_{})\n".format(tablename, tablename.capitalize(), tablename, self.primary[table][0]),
                "\t\tresponse = {}\n",
            ]
            if len(self.relations[table]) > 0:
                for column in columns:
                    resource["get"].append("\t\tresponse[\"{}\"] = {}.{}\n".format(column[0], tablename, column[0]))
                for relation in self.relations[table]:
                    singular_relation = self.p.singular_noun(relation)
                    resource["get"].extend([
                        "\t\tresponse[\"{}\"] = []\n".format(relation),
                        "\t\tfor {} in {}.{}:\n".format(singular_relation, tablename, relation),
                        "\t\t\tresponse[\"{}\"].append({{\n".format(relation)
                        ])
                    relationcolumns = self.tables[relation]
                    for column in relationcolumns:
                        resource["get"].append("\t\t\t\t'{}': {}.{},\n".format(column[0], singular_relation, column[0]))
                    resource["get"].append("\t\t\t\t})\n\n")

                resource["get"].append("\t\treturn jsonify(response)\n\n")

            else:
                resource["get"].append("\t\treturn jsonify({\n")
                for column in columns:
                    resource["get"].append("\t\t\t'{}': {}.{},\n".format(column[0], tablename, column[0]))
                resource["get"].append("\t\t\t})\n\n")

            resource["patch"] = [
                "\tif request.method == 'PATCH':\n",
                "\t\t{} = {}.query.get_or_404({}_{})\n".format(tablename, tablename.capitalize(), tablename, self.primary[table][0]),
            ]
            for column in columns:
                resource["patch"].extend([
                    "\t\tif '{}' in request.get_json():\n".format(column[0]),
                    "\t\t\t{}.{} = request.get_json()['{}']\n".format(tablename, column[0], column[0])
                ])
            resource["patch"].extend([
                "\t\tdb.session.commit()\n\n",
                "\t\treturn jsonify({{\'message\': \"{} updated successfully\"}})\n\n".format(tablename)
            ])
            resource["delete"].extend([
                "\tif request.method=='DELETE':\n",
                "\t\t{} = {}.query.get_or_404({}_{})\n".format(tablename, tablename.capitalize(), tablename, self.primary[table][0]),
                "\t\tdb.session.delete({})\n".format(tablename),
                "\t\tdb.session.commit()\n",
                "\t\treturn jsonify({{\'message\': \"{} deleted successfully\"}})\n".format(tablename)
            ])
            f.writelines(listresource["route"])
            f.writelines(listresource["get"])
            f.writelines(listresource["post"])
            f.writelines(resource["route"])
            f.writelines(resource["get"])
            f.writelines(resource["patch"])
            f.writelines(resource["delete"])
            f.close()
            print("Finished making {}_routes".format(tablename))
        self.makeapp()

    def makeapp(self):
        print("\nMaking app.py")
        os.chdir('..')
        f = open("app.py", "w")
        lines = [
            "from flask import Flask\n",
            "from flask_sqlalchemy import SQLAlchemy\n",
            "app = Flask(__name__)\n",
            "app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@{}:{}/{}'\n".format(
                self.args.user, self.args.password, self.args.host, self.args.port, self.args.db
            ),
            "app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False\n",
            "db = SQLAlchemy(app)\n",
            "from Models import *\n",
            ]
        for table in self.tables:
            tablename = self.p.singular_noun(table)
            lines.append("from Routes.{}_routes import *\n".format(tablename))

        lines.extend([
            "\n@app.route(\"/\")\n",
            "def home():\n",
            "\treturn {\"success\":\"true\"}\n\n\n"
            ])
        f.writelines(lines)
        f.writelines(["if __name__ == '__main__':\n", "\tapp.run(host='0.0.0.0', debug=True)"])
        f.close()
        print("\nAll processes complete. Try running app.py to check your APIs")

    def makeRest(self):
        print("\n\nMaking REST APIs......\n")
        os.chdir('..')
        os.mkdir('REST')
        os.chdir('REST')
        finit = open('__init__.py', 'w')
        lines = ["from flask import Flask, request\n",
                 "from flask import Blueprint as Blueprint\n",
                 "from flask_sqlalchemy import SQLAlchemy\n",
                 "from flask_restful import Api, Resource\n",
                 "from datetime import datetime\n"
                 "from flask_marshmallow import Marshmallow\n\n",
                 "app = Flask(__name__)\n",
                 "app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@{}:{}/{}'\n".format(
                     self.args.user, self.args.password, self.args.host, self.args.port, self.args.db
                 ),
                 "app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False\n",
                 "db = SQLAlchemy(app)\n",
                 "ma = Marshmallow(app)\n",
                 "api = Api(app)\n",
                 ]
        finit.writelines(lines)
        _all_ = "["
        for i in self.tables:
            singular = self.p.singular_noun(i)
            _all_ = _all_ + "\"" + singular + "_schema\", "
        _all_ = _all_[:-2] + "]"
        __all__ = "__all__ =" + _all_
        finit.write(__all__)
        dictify = [
            "\n\ndef dictify(table):\n",
            "\tdel table.__dict__['_sa_instance_state']\n",
            '\treturnable = {}\n',
            "\tfor item in table.__dict__:\n",
            '\t\treturnable[item] = str(table.__dict__[item]) if isinstance(table.__dict__[item], datetime) else table.__dict__[item]\n',
            "\treturn returnable\n"
        ]
        finit.writelines(dictify)
        finit.close()
        for table in self.tables:
            tablename = self.p.singular_noun(table)
            f = open("{}_schema.py".format(tablename), 'w')
            imports = ['from . import Api, ma, Blueprint, Resource, request',
                       '\nfrom __main__ import db\n',
                       'from Models.{}_model import {}\n'.format(tablename, tablename.capitalize())]
            if len(self.relations[table]) > 0:
                imports[0] += ', dictify'
            f.writelines(imports)

            schema = ['class {}Schema(ma.Schema):\n'.format(tablename.capitalize()),
                      '\tclass Meta:\n']

            field = "\t\tfields = ("
            columns = self.tables[table]
            fields = []
            nullable = []
            auto_increment = []
            for column in columns:
                field = field + "\'" + column[0] + "\', "
                fields.append(column[0])
                if column[2] == 'YES':
                    nullable.append(column[0])
                if column[5] == 'auto_increment':
                    auto_increment.append(column[0])
            field = field[:-2] + ",)\n"
            schema.append(field)
            schema.extend(['\t\tmodel = {}\n\n'.format(tablename.capitalize()),
                           "{}_schema = {}Schema()\n".format(tablename, tablename.capitalize()),
                           "{}_schema = {}Schema(many=True)\n\n".format(table, tablename.capitalize())])
            listresource = {"get": [], "post": []}

            listresource["get"] = [
                "class {}ListResource(Resource):\n\tdef get(self):\n".format(tablename.capitalize()),
                "\t\t{} = {}.query.all()\n".format(table, tablename.capitalize()),
                "\t\tif not {}:\n\t\t\treturn jsonify({{\'message\': \"No {} found\"}}), 404\n\n".format(table, table),
                "\t\treturn {}_schema.dump({})\n".format(table, table)
            ]
            listresource["post"] = ["\tdef post(self):\n"]
            for i in nullable:
                nullchecker = [
                    "\t\tif '{}' in request.get_json():\n\t\t\t{} = request.get_json()['{}']\n".format(i, i, i),
                    "\t\telse:\n\t\t\t{}=None\n".format(i)
                    ]
                listresource["post"].extend(nullchecker)
            listresource["post"].append("\t\tnew_{} = {}(\n".format(tablename, tablename.capitalize()))
            for fld in fields:
                if fld in nullable:
                    listresource["post"].append("\t\t{}={},\n".format(fld, fld))
                elif fld in auto_increment:
                    pass
                else:
                    listresource["post"].append("\t\t{}=request.get_json()['{}'],\n".format(fld, fld))

            listresource["post"][-1] = listresource["post"][-1][:-2] + '\n'
            listresource["post"].append(
                "\t\t)\n\t\tdb.session.add(new_{})\n\t\tdb.session.commit()\n\t\treturn {}_schema.dump(new_{})\n".format(
                    tablename, tablename, tablename))

            resource = {"get": [], "patch": [], "delete": []}

            resource["get"] = [
                "\nclass {}Resource(Resource):\n\tdef get(self, {}_{}):\n".format(tablename.capitalize(), tablename,
                                                                                  self.primary[table][0]),
                "\t\t{} = {}.query.get_or_404({}_{})\n".format(tablename, tablename.capitalize(), tablename,
                                                               self.primary[table][0])]
            if len(self.relations[table]) > 0:
                resource["get"].append("\t\tresult = {}_schema.dump({})\n".format(tablename, tablename))
                for relation in self.relations[table]:
                    singular_relation = self.p.singular_noun(relation)
                    resource["get"].extend([
                        "\t\tresult[\"{}\"]=[]\n".format(relation),
                        "\t\tfor {} in {}.{}:\n".format(singular_relation, tablename, relation),
                        "\t\t\tresult[\"{}\"].append(dictify({}))\n".format(relation, singular_relation),
                    ])
                resource["get"].append("\t\treturn result\n")

            else:
                resource["get"].append("\t\treturn {}_schema.dump({})\n".format(tablename, tablename))

            resource["patch"] = ["\tdef patch(self, {}_{}):\n".format(tablename, self.primary[table][0])]
            resource["patch"].append("\t\t{} = {}.query.get_or_404({}_{})\n".format(tablename,
                                                                                    tablename.capitalize(),
                                                                                    tablename, self.primary[table][0]))

            for i in fields:
                resource["patch"].append(
                    "\t\tif '{}' in request.get_json():\n\t\t\t{}.{} = request.get_json()['{}']\n".format(i, tablename,
                                                                                                          i, i))
            resource["patch"].append(
                "\t\tdb.session.commit()\n\t\treturn {}_schema.dump({})\n".format(tablename,
                                                                                  tablename,
                                                                                  tablename))

            resource["delete"] = [
                "\tdef delete(self, {}_{}):\n".format(tablename, self.primary[table][0]),
                "\t\t{}= {}.query.get_or_404({}_{})\n".format(tablename, tablename.capitalize(), tablename,
                                                              self.primary[table][0]),
                "\t\tdb.session.delete({})\n\t\tdb.session.commit()\n\t\treturn '', 204\n".format(tablename)]
            api_bp = [
                "def create_api_bp():\n\tapi_bp = Blueprint('{}_api', __name__)\n\tapi = Api(api_bp)\n".format(
                    tablename),
                "\tapi.add_resource({}ListResource, '/{}')".format(tablename.capitalize(), table),
                "\n\tapi.add_resource({}Resource, '/{}/<{}:{}_{}>')\n\treturn api_bp".format(
                    tablename.capitalize(), table, self.primary[table][2], tablename, self.primary[table][0])
            ]
            f.writelines(schema)
            f.writelines(listresource["get"])
            f.writelines(listresource["post"])
            f.writelines(resource["get"])
            f.writelines(resource["patch"])
            f.writelines(resource["delete"])
            f.writelines(api_bp)
            f.close()
            print("Finished making {}_schema".format(tablename))
        self.makebpapp()

    def makebpapp(self):
        print("\nMaking app.py")
        os.chdir('..')
        f = open("app.py", "w")
        lines = [
            "from flask import Flask\n",
            "from flask_sqlalchemy import SQLAlchemy\n",
            "from flask_marshmallow import Marshmallow\n",
            "from flask_restful import Api\n",
            "app = Flask(__name__)\n",
            "app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@{}:{}/{}'\n".format(
                self.args.user, self.args.password, self.args.host, self.args.port, self.args.db
            ),
            "app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False\n",
            "db = SQLAlchemy(app)\n",
            "ma = Marshmallow(app)\n",
            "api = Api(app)\n",
            "from Models import *\n",
            "from REST import *\n",
            "@app.route(\"/\")\n",
            "def home():\n",
            "\treturn {\"success\":\"true\"}\n\n\n"
        ]

        f.writelines(lines)
        for table in self.tables:
            tablename = self.p.singular_noun(table)
            f.write("app.register_blueprint({}_schema.create_api_bp())\n".format(tablename))

        f.writelines(["if __name__ == '__main__':\n","\tapp.run(host='0.0.0.0', debug=True)"])
        f.close()
        print("\nAll processes complete. Try running app.py to check your APIs")        
if len(sys.argv) < 4:
    print("type \"RESTApiGen help\" for Help")

if sys.argv[0] == "help":
    print("Enter your username, password, host and database in this order to generate the code.")
def main():
    RESTApiGenerator()


# Code Begins Here

# import time
# start = time.time()
# import pymysql, os, shutil, sys
# from inflector import English

# def main():
#     if len(sys.argv) == 1 or sys.argv[1] != "-u" or sys.argv[3] != "-p":
#         raise Exception ("To run RESTfulApiGen run RESTfulApiGen -u <username> -p <password> -db <database_name>")
#     if sys.argv[5] == "--demo" or sys.argv[5] == "--demo-gunicorn":
#         if os.path.exists("./demo.sql"):
#             conn = pymysql.connect(
#             host='localhost',
#             user=sys.argv[2],
#             password=sys.argv[4],
#             db="gain_demo",
#         )
#         else:
#             file = open(r"./demo.sql", 'w')
#             a = '''--- import this demo.sql file in your database and it will automatically generate the tables with some sample data.
#     -- phpMyAdmin SQL Dump
#     -- version 5.2.1
#     -- https://www.phpmyadmin.net/
#     --
#     -- Host: localhost
#     -- Generation Time: Jul 10, 2023 at 06:30 PM
#     -- Server version: 8.0.33
#     -- PHP Version: 8.2.7

#     SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
#     START TRANSACTION;
#     SET time_zone = "+00:00";


#     /*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
#     /*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
#     /*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
#     /*!40101 SET NAMES utf8mb4 */;

#     --
#     -- Database: `gain_demo`
#     --

#     -- --------------------------------------------------------

#     --
#     -- Table structure for table `comments`
#     --

#     CREATE TABLE `comments` (
#     `id` int NOT NULL,
#     `profile_id` int NOT NULL,
#     `post_id` int NOT NULL,
#     `comment` varchar(255) NOT NULL,
#     `created` datetime DEFAULT CURRENT_TIMESTAMP
#     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

#     --
#     -- Dumping data for table `comments`
#     --

#     INSERT INTO `comments` (`id`, `profile_id`, `post_id`, `comment`, `created`) VALUES
#     (1, 1, 3, "Jesse, you asked me if I was in the meth business, or the money business… Neither. I\'m in the empire business.", '2023-07-10 23:39:47'),
#     (2, 1, 11, '“You clearly don’t know who you’re talking to, so let me clue you in. I am not in danger, Skyler. I am the danger. A guy opens his door and gets shot, and you think that of me? No! I am the one who knocks!”', '2023-07-10 23:46:23'),
#     (3, 6, 1, '\"If I Have To Hear One More Time That You Did This For The Family ...\"', '2023-07-10 23:48:26'),
#     (4, 6, 2, '\"Someone Needs To Protect This Family From The Man Who Protects This Family.\"', '2023-07-10 23:49:54'),
#     (5, 6, 8, '\"I Want My Kids Back. I Want My Life Back. Please Tell Me - How Much Is Enough? How Big Does This Pile Have To Be?\"', '2023-07-10 23:51:02'),
#     (6, 1, 9, '\"Say My Name...\"', '2023-07-10 23:52:19'),
#     (7, 4, 1, '\"Ding Ding Ding...\"', '2023-07-10 23:53:27'),
#     (8, 2, 1, '\"Yo, yo, yo. 148, 3-to-the-3-to-the-6-to-the-9. Representin’ the ABQ. What up, b****? Leave it at the tone!\"', '2023-07-10 23:55:16'),
#     (9, 2, 8, ' “Yeah Mr. White! Yeah Science.”', '2023-07-10 23:57:19'),
#     (10, 2, 2, '\"This is my own private domicile, and I will not be harassed\"', '2023-07-10 23:59:06');

#     -- --------------------------------------------------------

#     --
#     -- Table structure for table `hashtags`
#     --

#     CREATE TABLE `hashtags` (
#     `id` int NOT NULL,
#     `hashtag` varchar(255) NOT NULL
#     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

#     --
#     -- Dumping data for table `hashtags`
#     --

#     INSERT INTO `hashtags` (`id`, `hashtag`) VALUES
#     (1, 'New Mexico'),
#     (2, 'Albuquerque'),
#     (3, 'Crystal Meth'),
#     (4, 'Guns'),
#     (5, 'RV'),
#     (6, 'Los Pollos Hermanos'),
#     (7, 'Ricin'),
#     (8, 'Lilly Flower'),
#     (9, 'Minerals'),
#     (10, 'Dea');

#     -- --------------------------------------------------------

#     --
#     -- Table structure for table `likes`
#     --

#     CREATE TABLE `likes` (
#     `id` int NOT NULL,
#     `profile_id` int NOT NULL,
#     `post_id` int NOT NULL
#     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

#     --
#     -- Dumping data for table `likes`
#     --

#     INSERT INTO `likes` (`id`, `profile_id`, `post_id`) VALUES
#     (1, 1, 1),
#     (2, 1, 2),
#     (3, 1, 3),
#     (4, 1, 4),
#     (5, 2, 2),
#     (6, 3, 3),
#     (7, 2, 3),
#     (8, 2, 4),
#     (9, 2, 1),
#     (10, 2, 5);

#     -- --------------------------------------------------------

#     --
#     -- Table structure for table `posts`
#     --

#     CREATE TABLE `posts` (
#     `id` int NOT NULL,
#     `profile_id` int NOT NULL,
#     `image` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
#     `caption` varchar(255) NOT NULL,
#     `created` datetime DEFAULT CURRENT_TIMESTAMP
#     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

#     --
#     -- Dumping data for table `posts`
#     --

#     INSERT INTO `posts` (`id`, `profile_id`, `image`, `caption`, `created`) VALUES
#     (1, 1, 'sygixu8r8wwhxvo2kk82uw5w7tz15s.jpeg', '', '2023-07-09 10:25:05'),
#     (2, 1, 'gmt4jyosx16qibarwugn4713jwo68h.jpeg', '', '2023-07-09 10:25:05'),
#     (3, 2, 'uqtebp0517lo4i2g3le8pslovy9zta.mp4', '', '2023-07-09 10:25:05'),
#     (4, 3, 'i9kcr630edolk0yyzh9kp36h998t8b.png', '', '2023-07-09 10:25:05'),
#     (5, 3, 'tdx0xwz08a3my5irondy6ppcuy501z.gif', '', '2023-07-10 23:28:15'),
#     (6, 3, '0t6i5lnph4aub8n9t89mteohfqdo34.png', '', '2023-07-10 23:28:15'),
#     (7, 2, 'l0pxm5n6s3g7rz3tz79mtlg9a41ocp.mp4', '', '2023-07-10 23:29:04'),
#     (8, 1, 'q9mvunvphs0qwap6mofa316lb1bcyt.mp4', '', '2023-07-10 23:29:04'),
#     (9, 4, 'oyfoohdrr3ci1hfjolbj7dusps4hmv.png', '', '2023-07-10 23:29:46'),
#     (10, 5, 'rrkpxyfc9ph33xjz8xi8tsdxs25dy6.png', '', '2023-07-10 23:29:46'),
#     (11, 6, 'apv55iw9xiabo85cssmr1j42fv4lb2.png', '', '2023-07-10 23:45:15');

#     -- --------------------------------------------------------

#     --
#     -- Table structure for table `post_hashtags`
#     --

#     CREATE TABLE `post_hashtags` (
#     `id` int NOT NULL,
#     `post_id` int NOT NULL,
#     `hashtag_id` int NOT NULL
#     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

#     --
#     -- Dumping data for table `post_hashtags`
#     --

#     INSERT INTO `post_hashtags` (`id`, `post_id`, `hashtag_id`) VALUES
#     (1, 1, 1),
#     (2, 1, 2),
#     (3, 4, 7),
#     (4, 3, 7),
#     (5, 8, 7),
#     (6, 2, 7),
#     (7, 1, 3),
#     (8, 1, 4),
#     (9, 1, 5),
#     (10, 5, 8);

#     -- --------------------------------------------------------

#     --
#     -- Table structure for table `profiles`
#     --

#     CREATE TABLE `profiles` (
#     `id` int NOT NULL,
#     `user_id` int NOT NULL,
#     `firstname` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
#     `lastname` varchar(50) NOT NULL,
#     `bio` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
#     `avatar` varchar(255) NOT NULL,
#     `created` datetime DEFAULT CURRENT_TIMESTAMP
#     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

#     --
#     -- Dumping data for table `profiles`
#     --

#     INSERT INTO `profiles` (`id`, `user_id`, `firstname`, `lastname`, `bio`, `avatar`, `created`) VALUES
#     (1, 1, 'Walter', 'White', 'Walter Hartwell White Sr., also known by his alias Heisenberg, is a fictional character and the protagonist of the American crime drama television series Breaking Bad, portrayed by Bryan Cranston. White was a skilled chemist and co-founder of a technology firm before he accepted a buy-out from his partners. ', 'walterHwhite.png', '2023-07-10 00:00:00'),
#     (2, 2, 'Jesse', 'Pinkman', 'Jesse Bruce Pinkman is a fictional character and one of the main characters of the American crime drama television series Breaking Bad, played by Aaron Paul. He is a crystal meth cook and dealer who works with his former high school chemistry teacher, Walter White.', 'jesseBpinkman.png', '2023-07-10 00:00:00'),
#     (3, 3, 'Gustavo', 'Fring', 'Gustavo \'Gus\' Fring is a fictional character portrayed by Giancarlo Esposito in the Breaking Bad franchise, serving as the main antagonist of the crime drama series Breaking Bad and a major character in its prequel Better Call Saul.', 'gustavofring.png', '2023-07-10 00:00:00'),
#     (4, 4, 'Hector', 'Salamanca', 'Don Hector Salamanca, nicknamed Tío by his nephews, is the elderly don of the Cartel, and an associate of cartel boss Don Eladio Vuente and don Juan Bolsa. A member of the Salamanca family, Hector is the son of Abuelita, the uncle of twins Marco and Leonel, Lalo, and Tuco, and is the grandfather of Joaquin.', 'hectorsalamanca.png', '2023-07-10 00:00:00'),
#     (5, 5, 'Saul', 'Goodman', 'James Morgan \'Jimmy\' McGill, better known by his business name Saul Goodman, is a character created by Vince Gilligan and Peter Gould and portrayed by Bob Odenkirk in the television franchise Breaking Bad.', 'saulgoodman.png', '2023-07-10 00:00:00'),
#     (6, 6, 'Skyler', 'White', 'Skyler White is a fictional character and the tritagonist of Breaking Bad, portrayed by Anna Gunn. For her performance, Gunn received critical acclaim, with some critics even lauding her character as the template for television anti-heroines.', 'skylerHwhite.png', '2023-07-10 23:44:24');

#     -- --------------------------------------------------------

#     --
#     -- Table structure for table `users`
#     --

#     CREATE TABLE `users` (
#     `id` int NOT NULL,
#     `username` varchar(32) NOT NULL,
#     `email` varchar(50) NOT NULL,
#     `password` varchar(32) NOT NULL,
#     `created` datetime DEFAULT CURRENT_TIMESTAMP
#     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

#     --
#     -- Dumping data for table `users`
#     --

#     INSERT INTO `users` (`id`, `username`, `email`, `password`, `created`) VALUES
#     (1, 'heisenberg', 'walterwhite@methamphetamine.com', 'DrugEmpire', '2023-07-09 10:40:01'),
#     (2, 'Mr.Driscoll', 'jessepinkman@alaska.com', 'CrystalDealer', '2023-07-09 10:40:01'),
#     (3, 'You_Can_Call_Me_Gus', 'gustavofring@lospolloshermanos.com', 'Entrepreneur', '2023-07-09 10:46:25'),
#     (4, 'Don_Hector', 'hectorsalamanca@revenge.com', 'DingDingDing', '2023-07-09 10:46:25'),
#     (5, 'Saul_Badman', 'saulgoodman@lawyer.com', 'Better_Call_Saul', '2023-07-09 10:51:51'),
#     (6, 'Sky_liar___White', 'skylerwhite@sky.com', 'I_*__*__TED', '2023-07-10 23:43:44');

#     --
#     -- Indexes for dumped tables
#     --

#     --
#     -- Indexes for table `comments`
#     --
#     ALTER TABLE `comments`
#     ADD PRIMARY KEY (`id`);

#     --
#     -- Indexes for table `hashtags`
#     --
#     ALTER TABLE `hashtags`
#     ADD PRIMARY KEY (`id`);

#     --
#     -- Indexes for table `likes`
#     --
#     ALTER TABLE `likes`
#     ADD PRIMARY KEY (`id`);

#     --
#     -- Indexes for table `posts`
#     --
#     ALTER TABLE `posts`
#     ADD PRIMARY KEY (`id`),
#     ADD UNIQUE KEY `image` (`image`);

#     --
#     -- Indexes for table `post_hashtags`
#     --
#     ALTER TABLE `post_hashtags`
#     ADD PRIMARY KEY (`id`);

#     --
#     -- Indexes for table `profiles`
#     --
#     ALTER TABLE `profiles`
#     ADD PRIMARY KEY (`id`);

#     --
#     -- Indexes for table `users`
#     --
#     ALTER TABLE `users`
#     ADD PRIMARY KEY (`id`);

#     --
#     -- AUTO_INCREMENT for dumped tables
#     --

#     --
#     -- AUTO_INCREMENT for table `comments`
#     --
#     ALTER TABLE `comments`
#     MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

#     --
#     -- AUTO_INCREMENT for table `hashtags`
#     --
#     ALTER TABLE `hashtags`
#     MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

#     --
#     -- AUTO_INCREMENT for table `likes`
#     --
#     ALTER TABLE `likes`
#     MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

#     --
#     -- AUTO_INCREMENT for table `posts`
#     --
#     ALTER TABLE `posts`
#     MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

#     --
#     -- AUTO_INCREMENT for table `post_hashtags`
#     --
#     ALTER TABLE `post_hashtags`
#     MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

#     --
#     -- AUTO_INCREMENT for table `profiles`
#     --
#     ALTER TABLE `profiles`
#     MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

#     --
#     -- AUTO_INCREMENT for table `users`
#     --
#     ALTER TABLE `users`
#     MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;
#     COMMIT;

#     /*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
#     /*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
#     /*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
#         '''
#             file.write(a)
#             file.close()
#             print("import this demo.sql file in your database and it will automatically generate the tables with some sample data.\nAfter importing the database re-run the previous command i.e. RESTfulAPIGen.py -u username -p password --demo")
#             exit()

#     else:
#         conn = pymysql.connect(
#         host='localhost',
#         user=sys.argv[2],
#         password=sys.argv[4],
#         db=sys.argv[6],
#         )

#     tables = []
#     cur = conn.cursor()
#     cur.execute("SHOW TABLES;")
#     temp = list(cur.fetchall())
#     for i in temp:    
#         for element in list(i):
#             tables.append(element)

#     # ------------------------- RESTfulAPIGen Starts ---------------------------------------------------------
#     for i in tables:
#         if i[-1:] == "s" or i[-2:] == "es" or i[-3:] == "ies" or i != English().pluralize(i):
#             pass
#         else:
#             raise Exception("There is an error in `{}` table.".format(i))

#     for i in tables:
#         cur.execute("EXPLAIN {}".format(i))
#         l1 = list(cur.fetchall())
#         for j in range(len(l1)):
#             # exit()
#             if l1[j][0][-1:] == "s" and l1[j][0][-2:] == "ss" or l1[j][0] != English().pluralize(i):
#                 pass
#             else:
#                 if l1[j][0][-1] == "s" or l1[j][0][-2:] == "es" or l1[j][0][-3:] == "ies" or l1[j][0][-6:-3] == "ies" or l1[j][0][-5:-3] == "es" and l1[j][0][-4:-3] == "s" : 
#                     raise Exception("`{}` column of `{}` table is plural. Try to fix it.".format(l1[j][0],i))

#     print("Making Models...")
#     if os.path.exists("./models"):
#         os.remove("./models/__init__.py")
#         shutil.rmtree("./models")
#         print("models folder exists. It will be deleted automatically so no worries. Chill maro!!! Continuing...")
#         os.mkdir("models")
#     else:
#         os.mkdir("models")

#     file = open(r"./models/__init__.py",'w')
#     if len(sys.argv) > 7 or sys.argv[5] == "--demo-gunicorn" :
#         if sys.argv[5] == "--demo-gunicorn" or sys.argv[7] == "--gunicorn":
#             file.write("from app import db")
#     else:
#         file.write("from __main__ import db")
#     file.write("\n")
#     file.close()


#     for i in tables:
#         file = open(r"models/{}_models.py".format(i),'w')
#         file.write("from . import db\nclass {}(db.Model):".format(English().singularize(i.title())))
#         file.write("\n\t__tablename__='{}'".format(i))
#         cur.execute("EXPLAIN {}".format(i))
#         l1 = list(cur.fetchall())
#         for j in range(len(l1)):
#             x = l1[j][1].split("(")
#             if l1[j][3] == "PRI":
#                 if l1[j][1] == "int":
#                     file.write("\n\t{} = db.Column(db.Integer, primary_key=True)".format(l1[j][0]))
#                 elif x[0] == "varchar":
#                     print(l1[j][0])
#                     print(x[1])
#                     print(l1[j][3])
#                     file.write("\n\t{} = db.Column(db.String({}, primary_key=True)".format(l1[j][0], x[1]))
#             else:
#                 if l1[j][0][-3:] == "_id":
#                     if l1[j][1] == "int":
#                         file.write("\n\t{} = db.Column(db.Integer, db.ForeignKey('{}.id'))".format(l1[j][0],English().pluralize(l1[j][0][:-3])))
#                 else:
#                     if l1[j][1] == "int":
#                         file.write("\n\t{} = db.Column(db.Integer)".format(l1[j][0]))
#                     elif x[0] == "varchar":
#                         file.write("\n\t{} = db.Column(db.String({})".format(l1[j][0], x[1]))
#                     elif x[0] == "float":
#                         file.write("\n\t{} = db.Column(db.Float)".format(l1[j][0]))
#                     elif x[0] == "decimal":
#                         file.write("\n\t{} = db.Column(db.Numeric({})".format(l1[j][0], x[1]))
#                     elif x[0] == "text":
#                         file.write("\n\t{} = db.Column(db.String)".format(l1[j][0]))
#                     elif x[0] == "datetime":
#                         file.write("\n\t{} = db.Column(db.DateTime)".format(l1[j][0]))
#                     elif x[0] == "smallint":
#                         file.write("\n\t{} = db.Column(db.Integer)".format(l1[j][0]))
#                     elif x[0] == "tinyint":
#                         file.write("\n\t{} = db.Column(db.Integer)".format(l1[j][0]))
#                     elif x[0] == "enum":
#                         file.write("\n\t{} = db.Column(db.Enum({})".format(l1[j][0], x[1]))
#                     elif x[0] == "date":
#                         file.write("\n\t{} = db.Column(db.DateTime)".format(l1[j][0]))
#                     elif x[0] == "char":
#                         file.write("\n\t{} = db.Column(db.String({})".format(l1[j][0], x[1]))

#         file.write("\n")            
#         file.close()
#     # Columns Completed

#     for i in tables:
#         # print(i)
#         if "_" in i:
#             # print(i)
#             a = i.split("_")
#             file = open(r"models/{}_models.py".format(English().pluralize(a[0])),'a')
#             file.write("\n\t{} = db.relationship('{}', backref='{}Of{}', secondary='{}', overlaps='{}Of{}', viewonly=True)".format(i,English().singularize(a[1].title()),a[1].title(),a[0].title(),i,English().pluralize(a[0]).title(),English().pluralize(a[1]).title()))
#             file.close()
#             file = open(r"models/{}_models.py".format(a[1]),'a')
#             file.write("\n\t{} = db.relationship('{}', backref='{}Of{}', secondary='{}', overlaps='{}Of{}', viewonly=True)".format(i,English().singularize(a[0]).title(),English().pluralize(a[0]).title(),English().pluralize(a[1]).title(),i,a[1].title(),a[0].title()))
#             file.close()
#     # Many to Many Completed

#     for i in tables:
#         if "_" in i:
#             pass
#         else:
#             cur.execute("EXPLAIN {}".format(i))
#             l1 = list(cur.fetchall())
#             for j in range(len(l1)):
#                 if l1[j][0][-3:] == "_id":
#                     a = l1[j][0][:-3]
#                     b = English().pluralize(i)
#                     c = English().singularize(i).title()
#                     d = English().pluralize(i).title(),"Of",English().singularize(l1[j][0][:-3]).title()
#                     d = d[0]+d[1]+English().singularize(d[2]).title()
#                     file = open(r"models/{}_models.py".format(English().pluralize(a)),'a')
#                     file.write("\n\t{} = db.relationship('{}', backref = db.backref('{}'))".format(b,c,d))
#                     file.close()

#     for i in tables:
#         cur.execute("EXPLAIN {}".format(i))
#         l1 = list(cur.fetchall())
#         for j in range(len(l1)):
#             if l1[j][0][-3:] == "_id":
#                 file = open(r"models/{}_models.py".format(i), 'a')
#                 file.write("\n\t{} = db.relationship('{}', backref = db.backref('{}Of{}'))".format(English().pluralize(l1[j][0][:-3]),English().singularize(l1[j][0][:-3]).title(),English().singularize(l1[j][0][:-3]).title(),English().singularize(i).title()))

#     for i in tables:
#         file = open(r"models/{}_models.py".format(i),'a')
#         file.write("\n\tdef __repr__(self):")
#         file.write("\n\t\treturn '<{} %r>' % self.id".format(English().singularize(i).title()))
#         file.write("\n")
#         file.close()

#     # Relationships Completed
#     print("Models Completed...")

#     print("Making Routes...")
#     if os.path.exists("./routes"):
#         shutil.rmtree("./routes")
#         print("Routes folder exists. It will be automatically deleted so no worries. Chill maro!!! Continuing...")
#         os.mkdir("./routes")
#     else:
#         os.mkdir("routes")

#     file = open(r"./routes/{}.py".format('__init__'),'a')
#     if len(sys.argv) > 7 or sys.argv[5] == "--demo-gunicorn":
#         if sys.argv[5] == "--demo-gunicorn" or sys.argv[7] == "--gunicorn":
#             file.write("from app import app, db")
#     else:
#         file.write("from __main__ import app, db")
#     for i in tables:
#         file.write("\nfrom {}.{}_models import {}".format("models",i,English().singularize(i).title()))
#     file.close()

#     for i in tables:
#         cur.execute("EXPLAIN {}".format(i))
#         file = open(r"./routes/{}_routes.py".format(i),'a')
#         file.write("from flask import request, jsonify")
#         file.write("\nfrom {}.{}_models import {}".format("models",i,English().singularize(i).title()))
#         if len(sys.argv) > 7 or sys.argv[5] == "--demo-gunicorn":
#             if sys.argv[5] == "--demo-gunicorn" or sys.argv[7] == "--gunicorn":
#                 file.write("\nfrom app import app, db")
#         else:
#             file.write("\nfrom __main__ import app, db")
#         file.write("\nclass {}_Routes:".format(English().singularize(format(i).title())))
#         file.write("\n\tdef {}(self):".format(i))
#         file.write("\n\t\tif request.method == 'GET':")
#         file.write("\n\t\t\t{} = {}.query.all()".format(i,English().singularize(i).title()))
#         file.write("\n\t\t\tif not {}:".format(i))
#         file.write('''\n\t\t\t\treturn jsonify({{'message': "No {} found"}}), 404'''.format(i))
#         file.write("\n\n\t\t\tresponse = []")
#         file.write("\n\t\t\tfor {} in {}:".format(English().singularize(i),i))
#         file.write('''\n\t\t\t\tresponse.append({''')
#         l1 = list(cur.fetchall())
#         for j in range(len(l1)-1):
#             file.write('''\n\t\t\t\t\t"{}": {}.{},'''.format(l1[j][0],English().singularize(i),l1[j][0]))
#         file.write('''\n\t\t\t\t\t"{}": {}.{}'''.format(l1[-1][0],English().singularize(i),l1[-1][0]))
#         file.write('''\n\t\t\t\t\t})''')
#         file.write('''\n\t\t\treturn jsonify(response)\n''')
#         file.close()
#     # GET COMPLETED

#     for i in tables:
#         cur.execute("EXPLAIN {}".format(i))
#         file = open(r"./routes/{}_routes.py".format(i),'a')
#         file.write("\n\t\tif request.method == 'POST':")
#         file.write("\n\t\t\tnew_{} = {}".format(English().singularize(i),English().singularize(i).title()))
#         l1 = list(cur.fetchall())
#         file.write('''\t(''')
#         for j in range(1,len(l1)-1):
#                 file.write('''\n\t\t\t\t{}=request.get_json()['{}'],'''.format(l1[j][0],l1[j][0]))
#         file.write('''\n\t\t\t\t{}=request.get_json()['{}']'''.format(l1[-1][0],l1[-1][0]))
#         file.write('''\n\t\t\t\t)''')
#         file.write('''\n\t\t\tdb.session.add(new_{})'''.format(English().singularize(i)))
#         file.write('''\n\t\t\tdb.session.commit()''')
#         file.write('''\n\t\t\treturn jsonify({{'message': "{} added successfully."}}), 200'''.format(English().singularize(i)))
#         file.close()
#     # POST COMPLETED

#     for i in tables:
#         cur.execute("EXPLAIN {}".format(i))
#         file = open(r"./routes/{}_routes.py".format(i),'a')
#         file.write('''\n\tdef {}(self, {}_id, extended=False):'''.format(English().singularize(i),English().singularize(i)))
#         file.write("\n\t\tif request.method == 'GET':")
#         file.write("\n\t\t\t{} = {}.query.get_or_404({}_id)".format(English().singularize(i),English().singularize(i).title(),English().singularize(i)))
#         file.write("\n\t\t\tresponse = {}")
#         l1 = cur.fetchall()
#         file.close()

#     filename = []
#     tablename = []
#     allfilename = []
#     for i in tables:
#         cur.execute("EXPLAIN {}".format(i))
#         l1 = list(cur.fetchall())
#         allfilename.append("{}_id".format(English().singularize(i)))
#         for j in range(len(l1)):
#             if l1[j][0][-3:] == "_id":
#                 filename.append(l1[j][0])
#                 tablename.append(i)

#     allfilenames = [i for i in allfilename if i not in filename]

#     temp = filename
#     temp = sorted(list(set(temp)))

#     for i in range(len(temp)):
#         cur.execute("EXPLAIN {}".format(English().pluralize(temp[i][:-3])))
#         l1 = list(cur.fetchall())
#         # print(English().pluralize(temp[i][:-3]))
#         file = open(r"./routes/{}_routes.py".format(English().pluralize(temp[i][:-3])),'a')
#         for j in range(len(l1)):
#             file.write('''\n\t\t\tresponse["{}"] = {}.{}'''.format(l1[j][0],English().singularize(English().pluralize(temp[i][:-3])),l1[j][0]))
#         file.close()
#         # exit()

#     for i in range(len(filename)):
#         if "_" in tablename[i]:
#             # print(English().pluralize(filename[i][:-3]))
#             # print(tablename[i])
#             if tablename[i][0] == filename[i][:-3][0]:
#                 t = tablename[i].split("_")
#                 cur.execute("EXPLAIN {}".format(t[1]))
#                 l1 = list(cur.fetchall())
#                 file = open(r"./routes/{}_routes.py".format(English().pluralize(filename[i][:-3])),'a')
#                 file.write("\n\t\t\tif extended:")
#                 file.write('\n\t\t\t\tresponse["{}"] = []'.format(t[1]))
#                 file.write('''\n\t\t\t\tfor {} in {}.{}:'''.format(English().singularize(t[1]),English().singularize(filename[i][:-3]),tablename[i]))
#                 file.write('''\n\t\t\t\t\tresponse["{}"].append({{'''.format(t[1]))
#                 for j in range(len(l1)-1):
#                     file.write("\n\t\t\t\t\t'{}': {}.{},".format(l1[j][0],English().singularize(t[1]),l1[j][0]))
#                 file.write("\n\t\t\t\t\t'{}': {}.{}".format(l1[-1][0],English().singularize(t[1]),l1[-1][0]))
#                 file.write('''\n\t\t\t\t\t})\n''')
#                 file.close()
#             else:
#                 t = tablename[i].split("_")
#                 cur.execute("EXPLAIN {}".format(English().pluralize(t[0])))
#                 l1 = list(cur.fetchall())
#                 file = open(r"./routes/{}_routes.py".format(English().pluralize(filename[i][:-3])),'a')
#                 file.write("\n\t\t\tif extended:")
#                 file.write('\n\t\t\t\tresponse["{}"] = []'.format(English().pluralize(t[0])))
#                 file.write('''\n\t\t\t\tfor {} in {}.{}:'''.format(English().singularize(t[0]),English().singularize(filename[i][:-3]),tablename[i]))
#                 file.write('''\n\t\t\t\t\tresponse["{}"].append({{'''.format(English().pluralize(t[0])))
#                 for j in range(len(l1)-1):
#                     file.write("\n\t\t\t\t\t'{}': {}.{},".format(l1[j][0],English().singularize(t[0]),l1[j][0]))
#                 file.write("\n\t\t\t\t\t'{}': {}.{}".format(l1[-1][0],English().singularize(t[0]),l1[-1][0]))
#                 file.write('''\n\t\t\t\t\t})\n''')
#                 file.close()

#     # MANY TO MANY ROUTES COMPLETED

#         else:
#             cur.execute("EXPLAIN {}".format(tablename[i]))
#             l1 = list(cur.fetchall())
#             file = open(r"./routes/{}_routes.py".format(English().pluralize(filename[i][:-3])),'a')
#             file.write("\n\t\t\tif extended:")
#             file.write('\n\t\t\t\tresponse["{}"] = []'.format(tablename[i]))
#             file.write('''\n\t\t\t\tfor {} in {}.{}:'''.format(English().singularize(tablename[i]),English().singularize(filename[i][:-3]),tablename[i]))
#             file.write('''\n\t\t\t\t\tresponse["{}"].append({{'''.format(tablename[i]))
#             for j in range(len(l1)-1):
#                 file.write("\n\t\t\t\t\t\t'{}': {}.{},".format(l1[j][0],English().singularize(tablename[i]),l1[j][0]))
#             file.write("\n\t\t\t\t\t\t'{}': {}.{}".format(l1[-1][0],English().singularize(tablename[i]),l1[-1][0]))
#             file.write('''\n\t\t\t\t\t\t})\n''')
#             file.close()

#     # ONE TO MANY ROUTES COMPLETED

#     for i in temp:
#         cur.execute("EXPLAIN {}".format(English().pluralize(i[:-3])))
#         l1 = list(cur.fetchall())
#         for j in range(len(l1)):
#             if l1[j][0][-3:] == "_id":
#                 file = open(r"routes/{}_routes.py".format(English().pluralize(i[:-3])),'a')
#                 file.write("\n\t\t\tif extended:")
#                 file.write('\n\t\t\t\tresponse["{}"] = []'.format(English().pluralize(l1[j][0][:-3])))
#                 file.write('''\n\t\t\t\tresponse["{}"].append({{'''.format(English().pluralize(l1[j][0][:-3])))
#                 cur.execute("EXPLAIN {}".format(English().pluralize(l1[j][0][:-3])))
#                 l2 = list(cur.fetchall())
#                 for k in range(len(l2)-1):
#                     file.write("\n\t\t\t\t\t'{}': {}.{}.{},".format(l2[k][0],English().singularize(i[:-3]),English().pluralize(l1[j][0][:-3]),l2[k][0]))
#                 file.write("\n\t\t\t\t\t'{}': {}.{}.{}".format(l2[-1][0],English().singularize(i[:-3]),English().pluralize(l1[j][0][:-3]),l2[-1][0]))
#                 file.write('''\n\t\t\t\t\t})\n''')
                
#                 for k in range(len(l2)):
#                     if l2[k][0][-3:] == "_id":
#                         # print(l2[k][0], l1[j][0], i[:-3])
#                         file.write("\n\t\t\tif extended:")
#                         file.write('\n\t\t\t\tresponse["{}"] = []'.format(English().singularize(l2[k][0][:-3])))
#                         file.write('''\n\t\t\t\tresponse["{}"].append({{'''.format(English().singularize(l2[k][0][:-3])))
#                         cur.execute("EXPLAIN {}".format(English().pluralize(l2[k][0][:-3])))
#                         l3 = list(cur.fetchall())
#                         for l in range(len(l3)-1):
#                             file.write("\n\t\t\t\t\t'{}': {}.{}.{}.{},".format(l3[l][0],English().singularize(i[:-3]),English().pluralize(l1[j][0][:-3]),English().pluralize(l2[k][0][:-3]),l3[l][0]))
#                         file.write("\n\t\t\t\t\t'{}': {}.{}.{}.{}".format(l3[-1][0],English().singularize(i[:-3]),English().pluralize(l1[j][0][:-3]),English().pluralize(l2[k][0][:-3]),l3[-1][0]))
#                         file.write('''\n\t\t\t\t\t})\n''')
#                 file.close()

#     # _id COLUMNs EXTENDED IN MANY TO MANY

#     for i in range(len(temp)):
#         file = open(r"./routes/{}_routes.py".format(English().pluralize(temp[i][:-3])),'a')
#         file.write("\n\t\t\treturn jsonify(response)")
#         file.close()

#     for i in allfilenames:
#         file = open(r"./routes/{}_routes.py".format(English().pluralize(i[:-3])),'a')
#         # file.write('\n\t\t\tresponse["{}"] = []'.format(i[:-3]))
#         cur.execute("EXPLAIN {}".format(English().pluralize(i[:-3])))
#         l1 = list(cur.fetchall())
#         for j in range(len(l1)):
#             file.write("\n\t\t\tresponse['{}']= {}.{}".format(l1[j][0],i[:-3],l1[j][0]))
#         # file.write("\n\t\t\tresponse['{}']: {}.{}".format(l1[-1][0],i[:-3],l1[-1][0]))
#         file.close()

#     for i in allfilenames:
#         cur.execute("EXPLAIN {}".format(English().pluralize(i[:-3])))
#         l1 = list(cur.fetchall())
#         for j in range(len(l1)):
#             if l1[j][0][-3:] == "_id":
#                 file = open(r"routes/{}_routes.py".format(English().pluralize(i[:-3])),'a')
#                 file.write("\n\t\t\tif extended:")
#                 file.write('\n\t\t\t\tresponse["{}"] = []'.format(English().pluralize(l1[j][0][:-3])))
#                 file.write('''\n\t\t\t\tresponse["{}"].append({{'''.format(English().pluralize(l1[j][0][:-3])))
#                 cur.execute("EXPLAIN {}".format(English().pluralize(l1[j][0][:-3])))
#                 l2 = list(cur.fetchall())
#                 for k in range(len(l2)-1):
#                     file.write("\n\t\t\t\t\t'{}': {}.{}.{},".format(l2[k][0],English().singularize(i[:-3]),English().pluralize(l1[j][0][:-3]),l2[k][0]))
#                 file.write("\n\t\t\t\t\t'{}': {}.{}.{}".format(l2[-1][0],English().singularize(i[:-3]),English().pluralize(l1[j][0][:-3]),l2[-1][0]))
#                 file.write('''\n\t\t\t\t\t})\n''')
                
#                 for k in range(len(l2)):
#                     if l2[k][0][-3:] == "_id":
#                         # print(l2[k][0], l1[j][0], i[:-3])
#                         file.write("\n\t\t\tif extended:")
#                         file.write('\n\t\t\t\tresponse["{}"] = []'.format(English().singularize(l2[k][0][:-3])))
#                         file.write('''\n\t\t\t\tresponse["{}"].append({{'''.format(English().singularize(l2[k][0][:-3])))
#                         cur.execute("EXPLAIN {}".format(English().pluralize(l2[k][0][:-3])))
#                         l3 = list(cur.fetchall())
#                         for l in range(len(l3)-1):
#                             file.write("\n\t\t\t\t\t'{}': {}.{}.{}.{},".format(l3[l][0],English().singularize(i[:-3]),English().pluralize(l1[j][0][:-3]),English().pluralize(l2[k][0][:-3]),l3[l][0]))
#                         file.write("\n\t\t\t\t\t'{}': {}.{}.{}.{}".format(l3[-1][0],English().singularize(i[:-3]),English().pluralize(l1[j][0][:-3]),English().pluralize(l2[k][0][:-3]),l3[-1][0]))
#                         file.write('''\n\t\t\t\t\t})\n''')
                        
#                 file.close()


#     # _id COLUMNs EXTENDED IN ONE TO MANY

#     for i in range(len(allfilenames)):
#         file = open(r"./routes/{}_routes.py".format(English().pluralize(allfilenames[i][:-3])),'a')
#         file.write("\n\t\t\treturn jsonify(response)")
#         file.close()

#     # GET ONE COMPLETED

#     for i in tables:
#         file = open(r"./routes/{}_routes.py".format(i),'a')
#         file.write("\n\n\t\tif request.method == 'PATCH':")
#         file.write("\n\t\t\t{} = {}.query.get_or_404({}_id)".format(English().singularize(i),English().singularize(i).title(),English().singularize(i)))
#         cur.execute("EXPLAIN {}".format(i))
#         l1 = list(cur.fetchall())
#         for j in range(1,len(l1)):
#             file.write("\n\t\t\tif '{}' in request.get_json():".format(l1[j][0]))
#             file.write("\n\t\t\t\t{}.{} = request.get_json()['{}']".format(English().singularize(i),l1[j][0],l1[j][0]))
#         file.write("\n\t\t\tdb.session.commit()")
#         file.write('''\n\n\t\t\treturn jsonify({{'message': "{} updated successfully."}}), 200'''.format(English().singularize(i)))
#         file.close()

#     # PUT COMPLETED

#     for i in tables:
#         file = open(r"./routes/{}_routes.py".format(i),'a')
#         file.write("\n\n\t\tif request.method=='DELETE':")
#         file.write("\n\t\t\t\t{} = {}.query.get_or_404({}_id)".format(English().singularize(i),English().singularize(i).title(),English().singularize(i)))
#         file.write("\n\t\t\t\tdb.session.delete({})".format(English().singularize(i)))
#         file.write("\n\t\t\t\tdb.session.commit()")
#         file.write('''\n\t\t\t\treturn jsonify({{'message': "{} deleted successfully."}}), 200\n'''.format(English().singularize(i)))
#         file.close()

#     # DELETE COMPLETED
#     print("Routes Completed...")

#     if os.path.exists("./app.py"):
#         os.remove("./app.py")
#         print("app.py folder exists. It will be automatically deleted so no worries. Chill maro!!! Continuing...")
#         file = open(r"./app.py",'w')
#     else:
#         file = open(r"./app.py",'w')

#     file.write("from flask import Flask, request")
#     file.write("\nfrom flask_sqlalchemy import SQLAlchemy")
#     if len(sys.argv) > 7:
#         if sys.argv[7] == "--gunicorn":
#             file.write("\nfrom flask_cors import CORS")            
#             file.write("\napp = Flask(__name__)")
#             file.write('''\ncors = CORS(app, origins=["http://localhost:5000"], support_credentials=True)''')
#             file.write("\napp.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@localhost/{}'".format(sys.argv[2],sys.argv[4],sys.argv[6]))
#     elif sys.argv[5] == "--demo-gunicorn":
#         file.write("\nfrom flask_cors import CORS")            
#         file.write("\napp = Flask(__name__)")
#         file.write('''\ncors = CORS(app, origins=["http://localhost:5000"], support_credentials=True)''')
#         file.write("\napp.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@localhost/{}'".format(sys.argv[2],sys.argv[4],"gain_demo"))
#     elif sys.argv[5] == "--demo":
#         file.write("\napp = Flask(__name__)")
#         file.write("\napp.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@localhost/{}'".format(sys.argv[2],sys.argv[4],"gain_demo"))
#     else:
#         file.write("\napp = Flask(__name__)")
#         file.write("\napp.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@localhost/{}'".format(sys.argv[2],sys.argv[4],sys.argv[6]))
#     file.write("\napp.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False")
#     file.write("\ndb = SQLAlchemy(app)")
#     file.write('''\n\n@app.route("/")''')
#     file.write("\ndef home():")
#     file.write('''\n\treturn {"success":"true"}''')
#     file.write("\n\n")
#     for i in tables:
#         file.write('''@app.route("/{}", methods = ['GET', 'POST'])'''.format(i))
#         file.write("\ndef {}_App():".format(i.title()))
#         file.write("\n\t\tfrom routes.{}_routes import {}_Routes".format(i, English().singularize(i).title()))
#         file.write("\n\t\treturn {}_Routes().{}()\n\n".format(English().singularize(i).title(),i))

#     for i in tables:
#         file.write('''@app.route("/{}/<int:{}_id>", methods = ['GET', 'PATCH', 'DELETE'])'''.format(i,English().singularize(i)))
#         file.write("\ndef {}_App({}_id):".format(i,English().singularize(i)))
#         file.write("\n\t\tfrom routes.{}_routes import {}_Routes".format(i, English().singularize(i).title()))
#         file.write("\n\t\treturn {}_Routes().{}({}_id, True if request.args.get('extended') else False)\n\n".format(English().singularize(i).title(),English().singularize(i),English().singularize(i)))
#     file.write("\n\nif __name__ == '__main__':")
#     file.write("\n\tapp.run(host='0.0.0.0', debug=True, port=3000)")
#     file.write("\n")
#     file.close()


#     conn.close()
#     end = time.time() - start
#     print("It took {} seconds only.".format(end))


# main()
