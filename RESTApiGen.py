# import subprocess, os
# input_file1 = subprocess.run(["which", "python3"], stdout=subprocess.PIPE, text=True)
# print(input_file1.stdout)

# with open('RESTApiGen.py', 'r') as read_file, open('Dummy_file_zas', 'w') as write_file:
#     write_file.write("#!{}\n".format(input_file1.stdout))

#     for line in read_file:
#         write_file.write(line)

# os.remove('RESTApiGen.py')
# os.rename('Dummy_file_zas', 'RESTApiGen.py')

#!/home/kingcoda/apigen/bin/python3
import pymysql, os, argparse, inflect, sys
parser = argparse.ArgumentParser()
parser.add_argument("-ho", "--host", required=True)
parser.add_argument("-us", "--user", required=True)
parser.add_argument("-pwd", "--password", required=True)
parser.add_argument("-db", "--database", required=True)
args = parser.parse_args()
p = inflect.engine()


# except:

class RESTApiGenerator:
    '''
    Description: Accepts hostname, username, password and database name
    '''

    def __init__(
            self,
            host=args.host,
            user=args.user,
            password=args.password,
            db=args.database,
            port=3306,
            **kwargs
    ):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.db = db
        self.conn()
    '''
    :param: self
    '''

    def conn(self):
        print('Comm is called')
        try:
            connexion = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port,
                db=self.db
            )
        except:
            print('Nahi hua connect')
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
        print(self.tables)
        self.makemodels()

    # def getrelations(self):

    def makemodels(self):

        os.mkdir('Models')
        os.chdir('Models')
        finit = open('__init__.py', 'w')
        lines = ['from flask import Flask, request\n',
                 'from flask_sqlalchemy import SQLAlchemy\n',
                 'app = Flask(__name__)\n',
                 "app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@{}:{}/{}'\n".format(
                     self.user, self.password, self.host, self.port, self.db
                 ),
                 "app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False\n",
                 'db = SQLAlchemy(app)\n']
        finit.writelines(lines)
        finit.close()
        self.relations = {}
        for table in self.tables:
            self.relations[table] = []
        for table in self.tables:
            tablename = p.singular_noun(table)
            print(tablename)
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
                    plural = p.plural(parent)
                    columnstr = "\t{} = db.Column(db.Integer, db.ForeignKey(\'{}.id\'))\n".format(colname, plural)
                    model.append(columnstr)
                    if plural not in self.tables:
                        print("{} table is missing. Create the table or run with --disable-fk".format(plural))
                        raise Exception("{} table is missing. Create the table or run with --disable-fk".format(plural))
                    else:
                        self.relations[plural].append(table)

                else:
                    x = coldatatype.split("(")
                    dtype = ""
                    length = ""
                    if len(x) == 2:
                        dtype = x[0]
                        length = x[1]
                    else:
                        x = coldatatype.split(" ")
                        dtype = x[0]
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
                        case "double":
                            dtype = "Integer"
                    if (dtype != 'Integer') and (dtype != "DateTime"):
                        dtype = dtype +"("+ length
                        if dtype[-1] == "d":
                            dtype = dtype.replace(" ", ", ")
                            dtype = dtype + " = True"
                    columnstr = '\t{} = db.Column(db.{})\n'.format(column[0], dtype)
                    model.append(columnstr)
            f.writelines(model)
            f.close()
        for table in self.tables:
            tablename = p.singular_noun(table)
            f = open("{}_model.py".format(tablename), 'a')
            model_closing = []
            for relation in self.relations[table]:
                relationname = p.singular_noun(relation)
                backref = "\t{} = db.relation(\'{}\', backref = db.backref(\"{}Of{}\"))\n".format(relation, relationname.capitalize(), tablename, relation.capitalize())
                model_closing.append(backref)
            model_closing.extend([
                "\n\tdef __repr__(self):\n",
                "\t\treturn '<{} %r>' % self.{}\n".format(tablename.capitalize(), self.tables[table][0][0])
            ])
            f.writelines(model_closing)
            f.close()
        self.makeRest()

    def makeRest(self):
        os.chdir('..')
        os.mkdir('REST')
        os.chdir('REST')
        finit = open('__init__.py', 'w')
        lines = ["from flask import Flask, request\n",
                 "from flask import Blueprint as Blueprint\n",
                 "from flask_sqlalchemy import SQLAlchemy\n",
                 "from flask_restful import Api, Resource\n",
                 "from flask_marshmallow import Marshmallow\n\n",
                 "app = Flask(__name__)\n",
                 "app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@{}:{}/{}'\n".format(
                     self.user, self.password, self.host, self.port, self.db
                 ),
                 "app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False\n",
                 "db = SQLAlchemy(app)\n",
                 "ma = Marshmallow(app)\n",
                 "api = Api(app)\n",
                 ]
        finit.writelines(lines)
        _all_ = "["
        for i in self.tables:
            singular = p.singular_noun(i)
            _all_ = _all_ + "\"" + singular + "_schema\", "
        _all_ = _all_[:-2] + "]"
        __all__ = "__all__ =" + _all_
        finit.write(__all__)
        finit.close()
        for table in self.tables:
            hasenum = table in self.enumtables
            tablename = p.singular_noun(table)
            f = open("{}_schema.py".format(tablename), 'w')
            imports = ['from . import db, Api, ma, Blueprint, Resource, request\n',
                       'from Models.{}_model import {}\n'.format(tablename, tablename.capitalize())]
            f.writelines(imports)
            enumvals = []

            validation = []
            if hasenum:

                for enumcolumn in self.enumtables[table]:
                    f.write("{}vals = {}\n".format(enumcolumn, self.enumtables[table][enumcolumn]))
                    if validation == []:
                        validation = ["\t\tif request.form[\'{}\'] in {}vals:\n".format(enumcolumn, enumcolumn),
                                      "\t\t\traise Exception(422)"]
                    else:
                        validation[0] = validation[0][:-2] + " and request.form[\'{}\'] in {}vals:\n".format(enumcolumn,
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
            listresource = [
                "class {}ListResource(Resource):\n\tdef get(self):\n".format(tablename.capitalize()),
                "\t\t{} = {}.query.all()\n\t\treturn {}_schema.dump({})\n".format(table, tablename.capitalize(), table,
                                                                                  table),
                "\tdef post(self):\n"]
            listresource.extend(validation)
            listresource.append("\t\tnew_{} = {}(\n".format(tablename, tablename.capitalize()))


            for i in fields:
                listresource.append("\t\t{}=request.form['{}'],\n".format(i, i))

            listresource.append(
                "\t\t)\n\t\tdb.session.add(new_{})\n\t\tdb.session.commit()\n\t\treturn {}_schema.dump(new_{})\n".format(
                    tablename, tablename, tablename))

            resource = [
                "\nclass {}Resource(Resource):\n\tdef get(self, {}_id):\n".format(tablename.capitalize(), tablename),
                "\t\t{} = {}.query.get_or_404({}_id)\n\t\treturn {}_schema.dump({})\n".format(tablename,
                                                                                              tablename.capitalize(),
                                                                                              tablename, tablename,
                                                                                              tablename),
                "\tdef patch(self, {}_id):\n".format(tablename)]
            resource.extend(validation)
            resource.append("\t\t{} = {}.query.get_or_404({}_id)\n".format(tablename,
                                                               tablename.capitalize(),
                                                               tablename))


            for i in fields:
                resource.append(
                    "\t\tif '{}' in request.form:\n\t\t\t{}.{} = request.form['{}']\n".format(i, tablename, i, i))
            resource.append(
                "\t\tdb.session.add({})\n\t\tdb.session.commit()\n\t\treturn {}_schema.dump({})\n".format(tablename,
                                                                                                          tablename,
                                                                                                          tablename))
            resource.append("\tdef delete(self, profile_id):\n\t\taddress = Address.query.get_or_404(address_id)\n")
            resource.append("\t\tdb.session.delete(address)\n\t\tdb.session.commit()\n\t\treturn '', 204\n")

            api_bp = [
                "def create_api_bp():\n\tapi_bp = Blueprint('{}_api', __name__)\n\tapi = Api(api_bp)\n".format(
                    tablename),
                "\tapi.add_resource({}ListResource, '/{}')".format(tablename.capitalize(), table),
                "\n\tapi.add_resource({}Resource, '/{}/<int:{}_id>')\n\treturn api_bp".format(
                    tablename.capitalize(), table, tablename.capitalize(), tablename, tablename)
            ]
            f.writelines(schema)
            f.writelines(listresource)
            f.writelines(resource)
            f.writelines(api_bp)
            f.close()

        self.makeapp()

    def makeapp(self):
        os.chdir('..')
        print(os.getcwd())
        f = open("app.py", "w")
        lines = [
            "from flask import Flask, request, jsonify\n",
            "from sqlalchemy import ForeignKey\n",
            "from flask_sqlalchemy import SQLAlchemy\n",
            "from flask_marshmallow import Marshmallow\n",
            "from flask_restful import Api, Resource\n",
            "from flask_blueprint import Blueprint\n",
            "app = Flask(__name__)\n",
            "app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@{}:{}/{}'\n".format(
                self.user, self.password, self.host, self.port, self.db
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
            tablename = p.singular_noun(table)
            f.write("app.register_blueprint({}_schema.create_api_bp())\n".format(tablename))

        f.write("app.run(host='0.0.0.0', port=8000, debug=True)")
        f.close()

    # if _ exists in tablename
    # it is a Has and Belongs To Many(or Many to Many)
    # check both the words before and after _
    # for their table name
    #
    # Inside REST create <table>_schema.py
    # os.walk
    # Generate app.py
    # Add blueprint context
    # self.getcolumns()
RESTApiGenerator()

if len(sys.argv) < 4:
    print("type \"RESTAPIGen help\" for Help")

if sys.argv[0] == "help":
    print("Enter your username, password, host and database in this order to generate the code.")
'''
username = sys.argv[0]
password = sys.argv[1]
host = sys.argv[2]
database = sys.argv[3]
RESTApiGenerator(user=username, password=password, host=host, db=database)
'''
