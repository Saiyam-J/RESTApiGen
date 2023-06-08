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
