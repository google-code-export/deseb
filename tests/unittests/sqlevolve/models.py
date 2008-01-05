"""
Schema Evolution Tests
"""

from django.db import models
from django.conf import settings
import deseb

GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
)

class Person(models.Model):
    name = models.CharField(maxlength=20, default="")
    gender = models.CharField(maxlength=1, choices=GENDER_CHOICES, default=False)
    gender2 = models.CharField(maxlength=1, choices=GENDER_CHOICES, aka='gender_old')
    ssn = models.IntegerField(default=111111111)

    def __unicode__(self):
        return self.name
    
    class Meta:
        aka = ('PersonOld', 'OtherBadName')

class Muebles(models.Model):
    tipo = models.CharField(maxlength=40, default="woot")
    # new fields
    fecha_publicacion = models.DateTimeField('date published', null=True)

class C(models.Model):
    "all with akas"
    c001 = models.AutoField(primary_key=True, aka='xxx')
    c002 = models.BooleanField(aka='xxx')
    c003 = models.CharField(maxlength='256', aka='xxx')
    c004 = models.CommaSeparatedIntegerField(maxlength='256', aka='xxx')
    c005 = models.DateField(aka='xxx')
    c006 = models.DateTimeField(aka='xxx')
    if deseb.version == 'trunk':
        c007 = models.DecimalField(decimal_places=5, max_digits=10, aka='xxx') # not in v0.96
    c008 = models.EmailField(aka='xxx')
    c010 = models.FileField(upload_to='/tmp', aka='xxx')
    c011 = models.FilePathField(aka='xxx')
    if deseb.version == '0.96':
        c012 = models.FloatField(aka='xxx', decimal_places=5, max_digits=10) # for v0.96
    else:
        c012 = models.FloatField(aka='xxx')
    c013 = models.IPAddressField(aka='xxx')
    c014 = models.ImageField(upload_to='/tmp', aka='xxx')
    c015 = models.IntegerField(aka='xxx')
    c016 = models.NullBooleanField(aka='xxx')
#   c017 = models.OrderingField(maxlength='256')
    c018 = models.PhoneNumberField(aka='xxx')
    c019 = models.PositiveIntegerField(aka='xxx')
    c020 = models.PositiveSmallIntegerField(aka='xxx')
    c021 = models.SlugField(aka='xxx')
    c022 = models.SmallIntegerField(aka='xxx')
    c023 = models.TextField(aka='xxx')
    c024 = models.TimeField(aka='xxx')
    c025 = models.URLField(aka='xxx')
    c026 = models.USStateField(aka='xxx')
    c027 = models.XMLField(aka='xxx')

__test__ = {'API_TESTS':"""
>>> import django
>>> from django.core.management.color import color_style
>>> from django.db import backend, models
>>> from django.db import connection
>>> from django.conf import settings
>>> import deseb
>>> import deseb.schema_evolution
>>> app = models.get_apps()[8]
>>> app.__name__
'unittests.sqlevolve.models'
>>> auth_app = models.get_apps()[1]
>>> auth_app.__name__
'django.contrib.auth.models'
>>> cursor = connection.cursor()
>>> style = color_style()
>>> ops, introspection = deseb.schema_evolution.get_operations_and_introspection_classes(style)
>>> import pprint
>>> def print_schema_evolution(app):
...     return pprint.pprint(deseb.schema_evolution.get_sql_evolution(app, style, notify=False))
>>> def print_and_execute(sql): 
...     pprint.pprint(sql)
...     for command in sql: 
...         if command[:2] == '--': continue
...         ret = cursor.execute(command)
>>> def print_and_evolve(app):
...     sql = deseb.schema_evolution.get_sql_evolution(app, style, notify=False)
...     print_and_execute(sql)
"""}

print settings.DATABASE_ENGINE

if settings.DATABASE_ENGINE == 'mysql':
    __test__['API_TESTS'] += """
# the table as it is supposed to be
>>> create_table_sql = deseb.schema_evolution.get_sql_all(auth_app, color_style())

# make sure we don't evolve an unedited table
>>> print_and_evolve(auth_app) #m1
[]

# the table as it is supposed to be
>>> create_table_sql = deseb.schema_evolution.get_sql_all(app, color_style())

# make sure we don't evolve an unedited table
>>> print_and_evolve(app) #m2
[]

# delete a column, so it looks like we've recently added a field
>>> print_and_execute(ops.get_drop_column_sql( 'sqlevolve_person', 'gender' ))
['ALTER TABLE `sqlevolve_person` DROP COLUMN `gender`;']
>>> print_and_evolve(app) #m3
['ALTER TABLE `sqlevolve_person` ADD COLUMN `gender` varchar(1);',
 "UPDATE `sqlevolve_person` SET `gender` = '1' WHERE `gender` IS NULL;",
 'ALTER TABLE `sqlevolve_person` MODIFY COLUMN `gender` varchar(1) NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;'); cursor.execute(create_table_sql[0])
0\n0

# add a column, so it looks like we've recently deleted a field
>>> cursor.execute('ALTER TABLE `sqlevolve_person` ADD COLUMN `gender_nothere` varchar(1) NOT NULL;')
0
>>> print_and_evolve(app) #m4
['-- warning: the following may cause data loss',
 u'ALTER TABLE `sqlevolve_person` DROP COLUMN `gender_nothere`;',
 '-- end warning']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;'); cursor.execute(create_table_sql[0])
0\n0

# rename column, so it looks like we've recently renamed a field
>>> cursor.execute('ALTER TABLE `sqlevolve_person` CHANGE COLUMN `gender2` `gender_old` varchar(1) NOT NULL;')
0
>>> print_and_evolve(app) #m5
['ALTER TABLE `sqlevolve_person` CHANGE COLUMN `gender_old` `gender2` varchar(1) NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;'); cursor.execute(create_table_sql[0])
0\n0

# rename table, so it looks like we've recently renamed a model
>>> cursor.execute('ALTER TABLE `sqlevolve_person` RENAME TO `sqlevolve_personold`')
0
>>> print_and_evolve(app) #m6
['ALTER TABLE `sqlevolve_personold` RENAME TO `sqlevolve_person`;']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;'); cursor.execute(create_table_sql[0])
0\n0

# change column flags, so it looks like we've recently changed a column flag
>>> cursor.execute('ALTER TABLE `sqlevolve_person` MODIFY COLUMN `name` varchar(10) NULL;')
0
>>> print_and_evolve(app) #m7
[u"UPDATE `sqlevolve_person` SET `name` = '' WHERE `name` IS NULL;",
 'ALTER TABLE `sqlevolve_person` MODIFY COLUMN `name` varchar(20) NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;'); cursor.execute(create_table_sql[0])
0\n0

# delete a datetime column, so it looks like we've recently added a datetime field
>>> print_and_execute(ops.get_drop_column_sql( 'sqlevolve_muebles', 'fecha_publicacion' ))
['ALTER TABLE `sqlevolve_muebles` DROP COLUMN `fecha_publicacion`;']
>>> print_and_evolve(app) #m8
['ALTER TABLE `sqlevolve_muebles` ADD COLUMN `fecha_publicacion` datetime;']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_muebles;'); cursor.execute(create_table_sql[1])
0\n0

# delete a column with a default value, so it looks like we've recently added a column
>>> print_and_execute(ops.get_drop_column_sql( 'sqlevolve_muebles', 'tipo' ))
['ALTER TABLE `sqlevolve_muebles` DROP COLUMN `tipo`;']
>>> print_and_execute(ops.get_drop_column_sql( 'sqlevolve_person', 'ssn' ))
['ALTER TABLE `sqlevolve_person` DROP COLUMN `ssn`;']
>>> print_and_evolve(app) #m9
['ALTER TABLE `sqlevolve_person` ADD COLUMN `ssn` integer;',
 'UPDATE `sqlevolve_person` SET `ssn` = 111111111 WHERE `ssn` IS NULL;',
 'ALTER TABLE `sqlevolve_person` MODIFY COLUMN `ssn` integer NOT NULL;',
 'ALTER TABLE `sqlevolve_muebles` ADD COLUMN `tipo` varchar(40);',
 u"UPDATE `sqlevolve_muebles` SET `tipo` = 'woot' WHERE `tipo` IS NULL;",
 'ALTER TABLE `sqlevolve_muebles` MODIFY COLUMN `tipo` varchar(40) NOT NULL;']
"""

if settings.DATABASE_ENGINE == 'postgresql' or settings.DATABASE_ENGINE == 'postgresql_psycopg2' :
    __test__['API_TESTS'] += """
# the table as it is supposed to be
>>> create_table_sql = deseb.schema_evolution.get_sql_all(app, color_style())

# make sure we don't evolve an unedited table
>>> print_and_evolve(app) #p1
[]

# delete a column, so it looks like we've recently added a field
>>> print_and_execute(ops.get_drop_column_sql( 'sqlevolve_person', 'gender' ))
['ALTER TABLE "sqlevolve_person" DROP COLUMN "gender";']
>>> print_and_evolve(app) #p2
['ALTER TABLE "sqlevolve_person" ADD COLUMN "gender" varchar(1);',
 'UPDATE "sqlevolve_person" SET "gender" = \\'f\\' WHERE "gender" IS NULL;',
 'ALTER TABLE "sqlevolve_person" ALTER COLUMN "gender" SET NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;'); cursor.execute(create_table_sql[0])

# add a column, so it looks like we've recently deleted a field
>>> print_and_execute(ops.get_add_column_sql( 'sqlevolve_person', 'gender_nothere', 'varchar(1)', True, False, False, None ))
['ALTER TABLE "sqlevolve_person" ADD COLUMN "gender_nothere" varchar(1);']
>>> print_and_evolve(app) #p3
['-- warning: the following may cause data loss',
 u'ALTER TABLE "sqlevolve_person" DROP COLUMN "gender_nothere";',
 '-- end warning']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;'); cursor.execute(create_table_sql[0])

# rename column, so it looks like we've recently renamed a field
>>> print_and_execute(ops.get_change_column_name_sql( 'sqlevolve_person', {}, 'gender2', 'gender_old', 'varchar(1)', False ))
['ALTER TABLE "sqlevolve_person" RENAME COLUMN "gender2" TO "gender_old";']
>>> print_and_evolve(app) #p4
['ALTER TABLE "sqlevolve_person" RENAME COLUMN "gender_old" TO "gender2";']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;'); cursor.execute(create_table_sql[0])

# rename table, so it looks like we've recently renamed a model
>>> print_and_execute(ops.get_change_table_name_sql( 'sqlevolve_personold', 'sqlevolve_person' ))
['ALTER TABLE "sqlevolve_person" RENAME TO "sqlevolve_personold";']
>>> print_and_evolve(app) #p5
['ALTER TABLE "sqlevolve_personold" RENAME TO "sqlevolve_person";']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;'); cursor.execute(create_table_sql[0])

# rename the sequence, so it looks like we renamed the sequence
>>> cursor.execute('ALTER TABLE "sqlevolve_person" DROP COLUMN "id";')
>>> cursor.execute('ALTER TABLE "sqlevolve_person" ADD COLUMN "strangename" serial;')
>>> cursor.execute('ALTER TABLE "sqlevolve_person" RENAME COLUMN "strangename" TO "id";')
>>> print_and_evolve(app) #p6.1
[u'ALTER TABLE "sqlevolve_person_strangename_seq" RENAME TO "sqlevolve_person_id_seq";',
 u'ALTER TABLE "sqlevolve_person" ALTER COLUMN "id" SET DEFAULT nextval(\\'sqlevolve_person_id_seq\\'::regclass);']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;'); cursor.execute(create_table_sql[0])

# remove id and add integer id, so it looks like we removed primary key constraint
#>>> cursor.execute('ALTER TABLE "sqlevolve_person" DROP COLUMN "id";')
#>>> cursor.execute('ALTER TABLE "sqlevolve_person" ADD COLUMN "id" integer;')
#>>> print_and_evolve(app) #p6.2

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;'); cursor.execute(create_table_sql[0])

# change column flags, so it looks like we've recently changed a column flag
>>> from django.db.models.fields import NOT_PROVIDED
>>> updates = {
...     'update_type': False,
...     'update_length': True,
...     'update_unique': False,
...     'update_null': False,
...     'update_primary': False,
...     'update_sequences': False,
... }
>>> print_and_execute(ops.get_change_column_def_sql( 'sqlevolve_person', 'name', 'varchar(10)', True, False, NOT_PROVIDED, updates ))
['ALTER TABLE "sqlevolve_person" ALTER COLUMN "name" TYPE varchar(10);']
>>> print_and_evolve(app) #p7
['ALTER TABLE "sqlevolve_person" ALTER COLUMN "name" TYPE varchar(20);']
>>> cursor.execute('ALTER TABLE "sqlevolve_person" DROP COLUMN "name";')
>>> cursor.execute('ALTER TABLE "sqlevolve_person" ADD COLUMN "name" varchar(10);')
>>> print_and_evolve(app) #p8
['ALTER TABLE "sqlevolve_person" ALTER COLUMN "name" TYPE varchar(20);',
 u'UPDATE "sqlevolve_person" SET "name" = \\'\\' WHERE "name" IS NULL;',
 'ALTER TABLE "sqlevolve_person" ALTER COLUMN "name" SET NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;'); cursor.execute(create_table_sql[0])

# delete a datetime column pair, so it looks like we've recently added a datetime field
>>> print_and_execute(ops.get_drop_column_sql( 'sqlevolve_muebles', 'fecha_publicacion' ))
['ALTER TABLE "sqlevolve_muebles" DROP COLUMN "fecha_publicacion";']
>>> print_and_evolve(app) #p9
['ALTER TABLE "sqlevolve_muebles" ADD COLUMN "fecha_publicacion" timestamp with time zone;']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_muebles;'); cursor.execute(create_table_sql[1])

# delete a column with a default value, so it looks like we've recently added a column
>>> print_and_execute(ops.get_drop_column_sql( 'sqlevolve_muebles', 'tipo' ))
['ALTER TABLE "sqlevolve_muebles" DROP COLUMN "tipo";']
>>> print_and_execute(ops.get_drop_column_sql( 'sqlevolve_person', 'ssn' ))
['ALTER TABLE "sqlevolve_person" DROP COLUMN "ssn";']
>>> print_and_evolve(app) #p10
['ALTER TABLE "sqlevolve_person" ADD COLUMN "ssn" integer;',
 'UPDATE "sqlevolve_person" SET "ssn" = 111111111 WHERE "ssn" IS NULL;',
 'ALTER TABLE "sqlevolve_person" ALTER COLUMN "ssn" SET NOT NULL;',
 'ALTER TABLE "sqlevolve_muebles" ADD COLUMN "tipo" varchar(40);',
 u'UPDATE "sqlevolve_muebles" SET "tipo" = \\'woot\\' WHERE "tipo" IS NULL;',
 'ALTER TABLE "sqlevolve_muebles" ALTER COLUMN "tipo" SET NOT NULL;']
"""

if settings.DATABASE_ENGINE == 'sqlite3':
    __test__['API_TESTS'] += """
# the table as it is supposed to be
>>> create_table_sql = deseb.schema_evolution.get_sql_all(app, color_style())

# make sure we don't evolve an unedited table
>>> print_and_evolve(app) #sq1
[]

# delete a column, so it looks like we've recently added a field
>>> cursor.execute( 'DROP TABLE "sqlevolve_person";' ).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute( 'CREATE TABLE "sqlevolve_person" ( "id" integer NOT NULL UNIQUE PRIMARY KEY, "name" varchar(20) NOT NULL, "gender" varchar(1) NOT NULL );' ).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> print_and_evolve(app) #sq2
['ALTER TABLE "sqlevolve_person" ADD COLUMN "gender2" varchar(1) NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute(create_table_sql[0]).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>

# add a column, so it looks like we've recently deleted a field
>>> cursor.execute( 'DROP TABLE "sqlevolve_person";' ).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute( 'CREATE TABLE "sqlevolve_person" ( "id" integer NOT NULL UNIQUE PRIMARY KEY, "name" varchar(20) NOT NULL, "gender" varchar(1) NOT NULL, "gender2" varchar(1) NOT NULL, "gender_new" varchar(1) NOT NULL );' ).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute( 'insert into "sqlevolve_person" values (1,2,3,4,5);' ).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> print_and_evolve(app) #sq3
['-- warning: the following may cause data loss', u'-- FYI: sqlite does not support deleting columns, so we create a new "gender_new" and delete the old  (ie, this could take a while)', 'ALTER TABLE "sqlevolve_person" RENAME TO "sqlevolve_person_1337_TMP";', 'CREATE TABLE "sqlevolve_person" (\\n    "id" integer NOT NULL UNIQUE PRIMARY KEY,\\n    "name" varchar(20) NOT NULL,\\n    "gender" varchar(1) NOT NULL,\\n    "gender2" varchar(1) NOT NULL\\n)\\n;', 'INSERT INTO "sqlevolve_person" SELECT "id","name","gender","gender2" FROM "sqlevolve_person_1337_TMP";', 'DROP TABLE "sqlevolve_person_1337_TMP";', '-- end warning']
>>> for s in sql: cursor.execute(s).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute('select * from "sqlevolve_person";').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.fetchall()[0]
(1, u'2', u'3', u'4')

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute(create_table_sql[0]).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>

# rename column, so it looks like we've recently renamed a field
>>> cursor.execute('DROP TABLE "sqlevolve_person"').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute('').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute('CREATE TABLE "sqlevolve_person" ("id" integer NOT NULL UNIQUE PRIMARY KEY, "name" varchar(20) NOT NULL, "gender" varchar(1) NOT NULL, "gender_old" varchar(1) NOT NULL );').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute( 'insert into "sqlevolve_person" values (1,2,3,4);' ).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> sql = print_and_evolve(app) #sq4
>>> print sql
['-- FYI: sqlite does not support renaming columns, so we create a new "sqlevolve_person" and delete the old  (ie, this could take a while)', 'ALTER TABLE "sqlevolve_person" RENAME TO "sqlevolve_person_1337_TMP";', 'CREATE TABLE "sqlevolve_person" (\\n    "id" integer NOT NULL UNIQUE PRIMARY KEY,\\n    "name" varchar(20) NOT NULL,\\n    "gender" varchar(1) NOT NULL,\\n    "gender2" varchar(1) NOT NULL\\n)\\n;', 'INSERT INTO "sqlevolve_person" SELECT "id","name","gender","gender_old" FROM "sqlevolve_person_1337_TMP";', 'DROP TABLE "sqlevolve_person_1337_TMP";']
>>> for s in sql: cursor.execute(s).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute('select * from "sqlevolve_person";').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.fetchall()[0]
(1, u'2', u'3', u'4')

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute(create_table_sql[0]).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>

# rename table, so it looks like we've recently renamed a model
>>> print_and_execute(ops.get_change_table_name_sql( 'sqlevolve_personold', 'sqlevolve_person' ))
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> print_and_evolve(app) #sq5
['ALTER TABLE "sqlevolve_personold" RENAME TO "sqlevolve_person";']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_personold;').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute(create_table_sql[0]).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>

# change column flags, so it looks like we've recently changed a column flag
>>> cursor.execute('DROP TABLE "sqlevolve_person";').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute('CREATE TABLE "sqlevolve_person" ( "id" integer NOT NULL UNIQUE PRIMARY KEY, "name" varchar(20) NOT NULL, "gender" varchar(1) NOT NULL, "gender2" varchar(1) NULL);').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> print_and_evolve(app) #sq6
['-- FYI: sqlite does not support changing columns, so we create a new "sqlevolve_person" and delete the old  (ie, this could take a while)',
 'ALTER TABLE "sqlevolve_person" RENAME TO "sqlevolve_person_1337_TMP";',
 'CREATE TABLE "sqlevolve_person" (\\n    "id" integer NOT NULL UNIQUE PRIMARY KEY,\\n    "name" varchar(20) NOT NULL,\\n    "gender" varchar(1) NOT NULL,\\n    "gender2" varchar(1) NOT NULL\\n)\\n;',
 'INSERT INTO "sqlevolve_person" SELECT "id","name","gender","gender2" FROM "sqlevolve_person_1337_TMP";',
 'DROP TABLE "sqlevolve_person_1337_TMP";']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_person;').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute(create_table_sql[0]).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>

# delete a datetime column pair, so it looks like we've recently added a datetime field
>>> print_and_execute(['DROP TABLE sqlevolve_muebles;','CREATE TABLE "sqlevolve_muebles" ("id" integer NOT NULL UNIQUE PRIMARY KEY,"tipo" varchar(40) NOT NULL);'])
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> print_and_evolve(app) #sq7
['ALTER TABLE "sqlevolve_muebles" ADD COLUMN "fecha_publicacion" datetime NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE sqlevolve_muebles;').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute(create_table_sql[1]).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>

# delete a column with a default value, so it looks like we've recently added a column
>>> print_and_execute(['DROP TABLE sqlevolve_muebles;','CREATE TABLE "sqlevolve_muebles" ("id" integer NOT NULL UNIQUE PRIMARY KEY,"fecha_publicacion" datetime NOT NULL);'])
>>> print_and_evolve(app) #sq8
['ALTER TABLE "sqlevolve_muebles" ADD COLUMN "tipo" varchar(40) NOT NULL DEFAULT "woot";']
"""

