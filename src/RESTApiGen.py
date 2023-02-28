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
        self.enumtables = {}
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
                columns.append(columndetails)
            self.tables[table] = columns[1:]
        self.getrelations()

    def getrelations(self):
        self.relations = {}
        for table in self.tables:
            self.relations[table] = []
        for table in self.tables:
            tablename = self.p.singular_noun(table)
            columns = self.tables[table]
            for column in columns:
                if '_id' in column[0]:
                    parent = column[0].split('_id')[0]
                    plural = self.p.plural(parent)
                    if plural not in self.tables:
                        print("{} table is missing. Create the table or run with --disable-fk".format(plural))
                        raise Exception("{} table is missing. Create the table or run with --disable-fk".format(plural))
                    else:
                        self.relations[plural].append(table)
        self.makemodels()    
    
    def makemodels(self):
        print("\n\nMaking Models.....\n")
        os.mkdir('Models')
        os.chdir('Models')
        finit = open('__init__.py', 'w')
        lines = ['from __main__ import db\n']
        finit.writelines(lines)
        finit.close()
        
        for table in self.tables:
            tablename = self.p.singular_noun(table)
            f = open("{}_model.py".format(tablename), 'w')
            f.write('from . import db\n')
            model = ['class {}(db.Model):\n'.format(tablename.capitalize()),
                     '\t__tablename__= \'{}\'\n'.format(table),
                     '\tid = db.Column(db.Integer, primary_key=True)\n']
            columns = self.tables[table]
            for column in columns:
                colname = column[0]
                coldatatype = column[1]
                if coldatatype[:4] == "enum":
                    if table not in self.enumtables:
                        self.enumtables[table] = {}

                    self.enumtables[table][colname] = ''
                if '_id' in column[0]:
                    parent = column[0].split('_')[0]
                    plural = self.p.plural(parent)
                    columnstr = "\t{} = db.Column(db.Integer, db.ForeignKey(\'{}.id\'))\n".format(colname, plural)
                else:
                    if "(" in coldatatype:
                        y = coldatatype.find("(")
                        x = [coldatatype[:y], coldatatype[y:]]
                    else: 
                        x = [coldatatype, ""]

                    dtype = x[0]
                    length = x[1]
                    
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
                            dtype = "String"
                            self.enumtables[table][colname] = length[2:-2].split("','")
                            length = ""
                        case "char":
                            dtype = "String"
                        case "date":
                            dtype = "DateTime"
                    if (dtype != 'Integer') and (dtype != "DateTime"):
                        dtype = dtype + length
                        if dtype[-1] == "d":
                            dtype = dtype.replace(" ", ", ")
                            dtype = dtype + " = True"
                    columnstr = '\t{} = db.Column(db.{})\n'.format(column[0], dtype)
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
        self.makeRest()

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
            hasenum = table in self.enumtables
            tablename = self.p.singular_noun(table)
            f = open("{}_schema.py".format(tablename), 'w')
            imports = ['from . import Api, ma, Blueprint, Resource, request',
                       '\nfrom __main__ import db\n',
                       'from Models.{}_model import {}\n'.format(tablename, tablename.capitalize())]
            if len(self.relations[table])>0:
                imports[0]+=', dictify'
            f.writelines(imports)
            enumvals = []
            validation = []
            if hasenum:

                for enumcolumn in self.enumtables[table]:
                    f.write("{}vals = {}\n".format(enumcolumn, self.enumtables[table][enumcolumn]))
                    if validation == []:
                        validation = ["\t\tif request.json.get(\'{}\') not in {}vals:\n".format(enumcolumn, enumcolumn),
                                      "\t\t\traise Exception(422)\n"]
                    else:
                        validation[0] = validation[0][:-2] + " and request.json(\'{}\') not in {}vals:\n".format(enumcolumn,
                                                                                                             enumcolumn)
            schema = ['class {}Schema(ma.Schema):\n'.format(tablename.capitalize()),
                      '\tclass Meta:\n']

            field = "\t\tfields = ("
            columns = self.tables[table]
            fields = []
            for column in columns:
                field = field + "\'" + column[0] + "\', "
                fields.append(column[0])
            field = field[:-2] + ",)\n"
            schema.append(field)
            schema.extend(['\t\tmodel = {}\n\n'.format(tablename.capitalize()),
                           "{}_schema = {}Schema()\n".format(tablename, tablename.capitalize()),
                           "{}_schema = {}Schema(many=True)\n\n".format(table, tablename.capitalize())])
            listresource = {"get":[], "post":[]}
            
            listresource["get"] = [
                "class {}ListResource(Resource):\n\tdef get(self):\n".format(tablename.capitalize()),
                "\t\t{} = {}.query.all()\n".format(table, tablename.capitalize()),
                "\t\treturn {}_schema.dump({})\n".format(table,table)
                ]
            listresource["post"]=["\tdef post(self):\n"]
            listresource["post"].extend(validation)
            listresource["post"].append("\t\tnew_{} = {}(\n".format(tablename, tablename.capitalize()))

            for i in fields:
                listresource["post"].append("\t\t{}=request.json.get('{}'),\n".format(i, i))

            listresource["post"].append(
                "\t\t)\n\t\tdb.session.add(new_{})\n\t\tdb.session.commit()\n\t\treturn {}_schema.dump(new_{})\n".format(
                    tablename, tablename, tablename))


            resource = {"get":[], "patch":[], "delete":[]}

            resource["get"] = [
                "\nclass {}Resource(Resource):\n\tdef get(self, {}_id):\n".format(tablename.capitalize(), tablename), 
                "\t\t{} = {}.query.get_or_404({}_id)\n".format(tablename,tablename.capitalize(), tablename)]
            if len(self.relations[table])>0:
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


            resource["patch"] = ["\tdef patch(self, {}_id):\n".format(tablename)]
            resource["patch"].extend(validation)
            resource["patch"].append("\t\t{} = {}.query.get_or_404({}_id)\n".format(tablename,
                                                                           tablename.capitalize(),
                                                                           tablename))

            for i in fields:
                resource["patch"].append(
                    "\t\tif request.json.get('{}') is not None:\n\t\t\t{}.{} = request.json.get('{}')\n".format(i, tablename, i, i))
            resource["patch"].append(
                "\t\tdb.session.commit()\n\t\treturn {}_schema.dump({})\n".format(tablename,
                                                                                                          tablename,
                                                                                                          tablename))

            resource["delete"] = [
                            "\tdef delete(self, {}_id):\n".format(tablename),
                            "\t\t{}= {}.query.get_or_404({}_id)\n".format(tablename, tablename.capitalize(), tablename),
                            "\t\tdb.session.delete({})\n\t\tdb.session.commit()\n\t\treturn '', 204\n".format(tablename)]

            api_bp = [
                "def create_api_bp():\n\tapi_bp = Blueprint('{}_api', __name__)\n\tapi = Api(api_bp)\n".format(
                    tablename),
                "\tapi.add_resource({}ListResource, '/{}')".format(tablename.capitalize(), table),
                "\n\tapi.add_resource({}Resource, '/{}/<int:{}_id>')\n\treturn api_bp".format(
                    tablename.capitalize(), table, tablename)
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
        self.makeapp()

    def makeapp(self):
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

        f.write("app.run(host='0.0.0.0', port=8000, debug=True)")
        f.close()
        print("\nAll processes complete. Try running app.py to check your APIs")        
if len(sys.argv) < 4:
    print("type \"RESTApiGen help\" for Help")

if sys.argv[0] == "help":
    print("Enter your username, password, host and database in this order to generate the code.")
def main():
    RESTApiGenerator()
