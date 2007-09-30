import django
from django.core.exceptions import ImproperlyConfigured
from optparse import OptionParser
from django.utils import termcolors
from django.conf import settings
import os, re, shutil, sys, textwrap
import django.core.management.sql as management
import django.core.management.sql

try: set 
except NameError: from sets import Set as set   # Python 2.3 fallback 

def get_operations_and_introspection_classes(style):
    from django.db import connection
    backend_type = str(connection.__class__).split('.')[3]
    if backend_type=='mysql': import deseb.backends.mysql as backend
    if backend_type=='postgresql': import deseb.backends.postgresql as backend
    if backend_type=='sqlite3': import deseb.backends.sqlite3 as backend
    ops = backend.DatabaseOperations(connection, style)
    introspection = backend.DatabaseIntrospection(connection)
    return ops, introspection

def get_sql_indexes_for_field(model, f, style):
    "Returns the CREATE INDEX SQL statement for a single field"
    from django.db import backend, connection
    output = []
    if f.db_index and not ((f.primary_key or f.unique) and backend.autoindexes_primary_keys):
        unique = f.unique and 'UNIQUE ' or ''
        tablespace = f.db_tablespace or model._meta.db_tablespace
        if tablespace and backend.supports_tablespaces:
            tablespace_sql = ' ' + backend.get_tablespace_sql(tablespace)
        else:
            tablespace_sql = ''
        output.append(
            style.SQL_KEYWORD('CREATE %sINDEX' % unique) + ' ' + \
            style.SQL_TABLE(connection.ops.quote_name('%s_%s' % (model._meta.db_table, f.column))) + ' ' + \
            style.SQL_KEYWORD('ON') + ' ' + \
            style.SQL_TABLE(connection.ops.quote_name(model._meta.db_table)) + ' ' + \
            "(%s)" % style.SQL_FIELD(connection.ops.quote_name(f.column)) + \
            "%s;" % tablespace_sql
        )
    return output
    
def get_sql_evolution_check_for_new_fields(model, new_table_name, style):
    "checks for model fields that are not in the existing data structure"
    from django.db import get_creation_module, models, get_introspection_module, connection

    ops, introspection = get_operations_and_introspection_classes(style)
    
    data_types = get_creation_module().DATA_TYPES
    cursor = connection.cursor()
#    introspection = ops = get_ops_class(connection)
    opts = model._meta
    output = []
    db_table = model._meta.db_table
    if new_table_name: 
        db_table = new_table_name
    existing_fields = introspection.get_columns(cursor,db_table)
    for f in opts.fields:
        if f.column not in existing_fields and (not f.aka or f.aka not in existing_fields and len(set(f.aka) & set(existing_fields))==0):
            col_type = f.db_type()
            if col_type is not None:
                output.extend( ops.get_add_column_sql( db_table, f.column, style.SQL_COLTYPE(col_type), f.null, f.unique, f.primary_key, f.default ) )
                output.extend( get_sql_indexes_for_field(model, f, style) )
    for f in opts.many_to_many:
        if not f.m2m_db_table() in get_introspection_module().get_table_list(cursor):
            output.extend( _get_many_to_many_sql_for_field(model, f, style) )
    return output

def get_sql_evolution_check_for_changed_model_name(klass, style):
    from django.db import get_creation_module, models, get_introspection_module, connection

    ops, introspection = get_operations_and_introspection_classes(style)

    cursor = connection.cursor()
    introspection = get_introspection_module()
#    ops = get_ops_class(connection)
    table_list = introspection.get_table_list(cursor)
    if klass._meta.db_table in table_list:
        return [], None
#    print 'klass._meta.aka', klass._meta.aka
    aka_db_tables = set()
    if klass._meta.aka:
        for x in klass._meta.aka:
            aka_db_tables.add( "%s_%s" % (klass._meta.app_label, x.lower()) )
    matches = list(aka_db_tables & set(table_list))
    if len(matches)==1:
        return ops.get_change_table_name_sql( klass._meta.db_table, matches[0]), matches[0]
    else:
        return [], None
    
def get_sql_evolution_check_for_changed_field_name(klass, new_table_name, style):
    from django.db import get_creation_module, models, get_introspection_module, connection

    ops, introspection = get_operations_and_introspection_classes(style)

    data_types = get_creation_module().DATA_TYPES
    cursor = connection.cursor()
#    introspection = ops = get_ops_class(connection)
    opts = klass._meta
    output = []
    db_table = klass._meta.db_table
    if new_table_name: 
        db_table = new_table_name
    for f in opts.fields:
        existing_fields = introspection.get_columns(cursor,db_table)
        if f.column not in existing_fields and f.aka and (f.aka in existing_fields or len(set(f.aka) & set(existing_fields)))==1:
            old_col = None
            if isinstance( f.aka, str ):
                old_col = f.aka
            else:
                old_col = f.aka[0]
            col_type = f.db_type()
            if col_type is not None:
                col_def = style.SQL_COLTYPE(col_type) +' '+ style.SQL_KEYWORD('%sNULL' % (not f.null and 'NOT ' or ''))
                if f.unique:
                    col_def += style.SQL_KEYWORD(' UNIQUE')
                if f.primary_key:
                    col_def += style.SQL_KEYWORD(' PRIMARY KEY')
                output.extend( ops.get_change_column_name_sql( klass._meta.db_table, get_introspection_module().get_indexes(cursor,db_table), old_col, f.column, col_def ) )
    return output
    
def get_sql_evolution_check_for_changed_field_flags(klass, new_table_name, style):

    ops, introspection = get_operations_and_introspection_classes(style)
    
    from django.db import get_creation_module, models, get_introspection_module, connection
    from django.db.models.fields import CharField, SlugField
    from django.db.models.fields.related import RelatedField, ForeignKey
    data_types = get_creation_module().DATA_TYPES
    cursor = connection.cursor()
#    introspection = ops = get_ops_class(connection)
    opts = klass._meta
    output = []
    db_table = klass._meta.db_table
    if new_table_name: 
        db_table = new_table_name
    for f in opts.fields:
        existing_fields = introspection.get_columns(cursor,db_table)
#        print existing_fields
        cf = None # current field, ie what it is before any renames
        if f.column in existing_fields:
            cf = f.column
        elif f.aka in existing_fields:
            cf = f.aka
        elif f.aka and len(set(f.aka) & set(existing_fields))==1:
            cf = f.aka[0]
        else:
            continue # no idea what column you're talking about - should be handled by get_sql_evolution_check_for_new_fields())
        data_type = f.get_internal_type()
        if data_types.has_key(data_type):
            column_flags = introspection.get_known_column_flags(cursor, db_table, cf)
#            print db_table, cf, column_flags
            if column_flags['allow_null']!=f.null or \
                    ( not f.primary_key and isinstance(f, CharField) and column_flags['maxlength']!=str(f.maxlength) ) or \
                    ( not f.primary_key and isinstance(f, SlugField) and column_flags['maxlength']!=str(f.maxlength) ) or \
                    ( column_flags['unique']!=f.unique and ( settings.DATABASE_ENGINE!='postgresql' or not f.primary_key ) ) or \
                    column_flags['primary_key']!=f.primary_key:
                col_type = f.db_type()
                col_type_def = style.SQL_COLTYPE(col_type)
#                col_def = style.SQL_COLTYPE(col_type) +' '+ style.SQL_KEYWORD('%sNULL' % (not f.null and 'NOT ' or ''))
#                if f.unique:
#                    col_def += ' '+ style.SQL_KEYWORD('UNIQUE')
#                if f.primary_key:
#                    col_def += ' '+ style.SQL_KEYWORD('PRIMARY KEY')
                output.extend( ops.get_change_column_def_sql( klass._meta.db_table, cf, col_type_def, f.null, f.unique, f.primary_key, f.default ) )
                    #print db_table, cf, f.maxlength, introspection.get_known_column_flags(cursor, db_table, cf)
    return output

def get_sql_evolution_check_for_dead_fields(klass, new_table_name, style):
    from django.db import get_creation_module, models, get_introspection_module, connection
    from django.db.models.fields import CharField, SlugField
    from django.db.models.fields.related import RelatedField, ForeignKey
    
    ops, introspection = get_operations_and_introspection_classes(style)

    data_types = get_creation_module().DATA_TYPES
    cursor = connection.cursor()
#    introspection = ops = get_ops_class(connection)
    opts = klass._meta
    output = []
    db_table = klass._meta.db_table
    if new_table_name: 
        db_table = new_table_name
    suspect_fields = set(introspection.get_columns(cursor,db_table))
#    print 'suspect_fields = ', suspect_fields
    for f in opts.fields:
#        print 'f = ', f
#        print 'f.aka = ', f.aka
        suspect_fields.discard(f.column)
        suspect_fields.discard(f.aka)
        if f.aka: suspect_fields.difference_update(f.aka)
    if len(suspect_fields)>0:
        output.append( '-- warning: the following may cause data loss' )
        for suspect_field in suspect_fields:
            output.extend( ops.get_drop_column_sql( klass._meta.db_table, suspect_field ) )
        output.append( '-- end warning' )
    return output

def get_sql_evolution_check_for_dead_models(table_list, safe_tables, app_name, app_models, style):
    from django.db import connection
    
    ops, introspection = get_operations_and_introspection_classes(style)

    if not app_models: return []
    app_label = app_models[0]._meta.app_label
    safe_tables = set(safe_tables)
    for model in app_models:
        for f in model._meta.many_to_many:
            safe_tables.add(f.m2m_db_table())
    try:
        app_se = __import__(app_name +'.schema_evolution').schema_evolution
        for table_name in app_se.protected_tables:
            safe_tables.add(table_name)
            safe_tables.add(app_label +'_'+ table_name)
    except:
        pass
    delete_tables = set()
    for t in table_list:
        if t.startswith(app_label) and t not in safe_tables:
            delete_tables.add(t)
    return ops.get_drop_table_sql(delete_tables)

def get_sql_evolution(app, style):
    "Returns SQL to update an existing schema to match the existing models."
    return get_sql_evolution_detailed(app, style)[2]

def get_sql_evolution_detailed(app, style):
    "Returns SQL to update an existing schema to match the existing models."

    ops, introspection = get_operations_and_introspection_classes(style)
    
    from django.db import get_creation_module, models, backend, get_introspection_module, connection
#    data_types = get_creation_module().DATA_TYPES
#
#    if not data_types:
#        # This must be the "dummy" database backend, which means the user
#        # hasn't set DATABASE_ENGINE.
#        sys.stderr.write(style.ERROR("Error: Django doesn't know which syntax to use for your SQL statements,\n" +
#            "because you haven't specified the DATABASE_ENGINE setting.\n" +
#            "Edit your settings file and change DATABASE_ENGINE to something like 'postgresql' or 'mysql'.\n"))
#        sys.exit(1)

#    try:
#        ops = get_ops_class(connection)
#    except:
#        # This must be an unsupported database backend
#        sys.stderr.write(style.ERROR("Error: Django doesn't know which syntax to use for your SQL statements, " +
#            "because schema evolution support isn't built into your database backend yet.  Sorry!\n"))
#        sys.exit(1)

#    # First, try validating the models.
#    _check_for_validation_errors()

    # This should work even if a connecton isn't available
    try:
        cursor = connection.cursor()
    except:
        cursor = None

#    introspection = get_introspection_module()
    app_name = app.__name__.split('.')[-2]

    final_output = []

    schema_fingerprint = introspection.get_schema_fingerprint(cursor, app)
    try:
        # is this a schema we recognize?
        app_se = __import__(app_name +'.schema_evolution').schema_evolution
        schema_recognized = schema_fingerprint in app_se.fingerprints
        if schema_recognized:
            sys.stderr.write(style.NOTICE("Notice: Current schema fingerprint for '%s' is '%s' (recognized)\n" % (app_name, schema_fingerprint)))
            available_upgrades = []
            for (vfrom, vto), upgrade in app_se.evolutions.iteritems():
                if vfrom == schema_fingerprint:
                    try:
                        distance = app_se.fingerprints.index(vto)-app_se.fingerprints.index(vfrom)
                        available_upgrades.append( ( vfrom, vto, upgrade, distance ) )
                        sys.stderr.write(style.NOTICE("\tan upgrade from %s to %s is available (distance: %i)\n" % ( vfrom, vto, distance )))
                    except:
                        available_upgrades.append( ( vfrom, vto, upgrade, -1 ) )
                        sys.stderr.write(style.NOTICE("\tan upgrade from %s to %s is available, but %s is not in schema_evolution.fingerprints\n" % ( vfrom, vto, vto )))
            if len(available_upgrades):
                best_upgrade = available_upgrades[0]
                for an_upgrade in available_upgrades:
                    if an_upgrade[3] > best_upgrade[3]:
                        best_upgrade = an_upgrade
                final_output.extend( best_upgrade[2] )
                return schema_fingerprint, False, final_output
        else:
            sys.stderr.write(style.NOTICE("Notice: Current schema fingerprint for '%s' is '%s' (unrecognized)\n" % (app_name, schema_fingerprint)))
    except:
        # sys.stderr.write(style.NOTICE("Notice: Current schema fingerprint for '%s' is '%s' (no schema_evolution module found)\n" % (app_name, schema_fingerprint)))
        pass # ^^^ lets not be chatty

    # stolen and trimmed from syncdb so that we know which models are about 
    # to be created (so we don't check them for updates)
    table_list = get_introspection_module().get_table_list(cursor)
    seen_models = django.core.management.sql.installed_models(table_list)
    created_models = set()
    pending_references = {}
    
    model_list = models.get_models(app)
    for model in model_list:
        # Create the model's database table, if it doesn't already exist.
        aka_db_tables = set()
        if model._meta.aka:
            for x in model._meta.aka:
                aka_db_tables.add( "%s_%s" % (model._meta.app_label, x.lower()) )
        if model._meta.db_table in table_list or len(aka_db_tables & set(table_list))>0:
            continue
        sql, references = _get_sql_model_create(model, seen_models, style)
        final_output.extend(sql)
        seen_models.add(model)
        created_models.add(model)
        table_list.append(model._meta.db_table)

    # get the existing models, minus the models we've just created
    app_models = models.get_models(app)
    for model in created_models:
        if model in app_models:
            app_models.remove(model)

    seen_tables = set()

    for model in app_models:
        if model._meta.db_table: seen_tables.add(model._meta.db_table)
        
        output, new_table_name = get_sql_evolution_check_for_changed_model_name(model, style)
        if new_table_name: seen_tables.add(new_table_name)
        final_output.extend(output)
        
        output = get_sql_evolution_check_for_changed_field_flags(model, new_table_name, style)
        final_output.extend(output)
    
        output = get_sql_evolution_check_for_changed_field_name(model, new_table_name, style)
        final_output.extend(output)
        
        output = get_sql_evolution_check_for_new_fields(model, new_table_name, style)
        final_output.extend(output)
        
        output = get_sql_evolution_check_for_dead_fields(model, new_table_name, style)
        final_output.extend(output)
        
    output = get_sql_evolution_check_for_dead_models(table_list, seen_tables, app_name, app_models, style)
    final_output.extend(output)
        
    return schema_fingerprint, True, final_output


def _get_sql_model_create(model, known_models, style):
    """
    Get the SQL required to create a single model.

    Returns list_of_sql, pending_references_dict
    """
    from django.db import backend, models, connection
    
    ops, introspection = get_operations_and_introspection_classes(style)

    opts = model._meta
    final_output = []
    table_output = []
    pending_references = {}
    for f in opts.fields:
        col_type = f.db_type()
        tablespace = f.db_tablespace or opts.db_tablespace
        if col_type is None:
            # Skip ManyToManyFields, because they're not represented as
            # database columns in this table.
            continue
        # Make the definition (e.g. 'foo VARCHAR(30)') for this field.
        field_output = [style.SQL_FIELD(connection.ops.quote_name(f.column)),
            style.SQL_COLTYPE(col_type)]
        field_output.append(style.SQL_KEYWORD('%sNULL' % (not f.null and 'NOT ' or '')))
        if (f.unique and (not f.primary_key or backend.allows_unique_and_pk)) or (f.primary_key and ops.pk_requires_unique):
            field_output.append(style.SQL_KEYWORD('UNIQUE'))
        if f.primary_key:
            field_output.append(style.SQL_KEYWORD('PRIMARY KEY'))
        if tablespace and backend.supports_tablespaces and (f.unique or f.primary_key) and backend.autoindexes_primary_keys:
            # We must specify the index tablespace inline, because we
            # won't be generating a CREATE INDEX statement for this field.
            field_output.append(backend.get_tablespace_sql(tablespace, inline=True))
        if f.rel:
            if f.rel.to in known_models:
                field_output.append(style.SQL_KEYWORD('REFERENCES') + ' ' + \
                    style.SQL_TABLE(ops.quote_name(f.rel.to._meta.db_table)) + ' (' + \
                    style.SQL_FIELD(ops.quote_name(f.rel.to._meta.get_field(f.rel.field_name).column)) + ')' #+
#                    backend.get_deferrable_sql()
                )
            else:
                # We haven't yet created the table to which this field
                # is related, so save it for later.
                pr = pending_references.setdefault(f.rel.to, []).append((model, f))
        table_output.append(' '.join(field_output))
    if opts.order_with_respect_to:
        table_output.append(style.SQL_FIELD(ops.quote_name('_order')) + ' ' + \
            style.SQL_COLTYPE(models.IntegerField().db_type()) + ' ' + \
            style.SQL_KEYWORD('NULL'))
    for field_constraints in opts.unique_together:
        table_output.append(style.SQL_KEYWORD('UNIQUE') + ' (%s)' % \
            ", ".join([ops.quote_name(style.SQL_FIELD(opts.get_field(f).column)) for f in field_constraints]))

    full_statement = [style.SQL_KEYWORD('CREATE TABLE') + ' ' + style.SQL_TABLE(connection.ops.quote_name(opts.db_table)) + ' (']
    for i, line in enumerate(table_output): # Combine and add commas.
        full_statement.append('    %s%s' % (line, i < len(table_output)-1 and ',' or ''))
    full_statement.append(')')
    if opts.db_tablespace and backend.supports_tablespaces:
        full_statement.append(backend.get_tablespace_sql(opts.db_tablespace))
    full_statement.append(';')
    final_output.append('\n'.join(full_statement))

    if opts.has_auto_field and hasattr(backend, 'get_autoinc_sql'):
        # Add any extra SQL needed to support auto-incrementing primary keys
        autoinc_sql = backend.get_autoinc_sql(opts.db_table)
        if autoinc_sql:
            for stmt in autoinc_sql:
                final_output.append(stmt)

    return final_output, pending_references

def _get_many_to_many_sql_for_field(model, f, style):
    from django.db import backend, models, connection
    from django.contrib.contenttypes import generic

    ops, introspection = get_operations_and_introspection_classes(style)

    opts = model._meta
    final_output = []
    if not isinstance(f.rel, generic.GenericRel):
        tablespace = f.db_tablespace or opts.db_tablespace
        if tablespace and backend.supports_tablespaces and backend.autoindexes_primary_keys:
            tablespace_sql = ' ' + backend.get_tablespace_sql(tablespace, inline=True)
        else:
            tablespace_sql = ''
        table_output = [style.SQL_KEYWORD('CREATE TABLE') + ' ' + \
            style.SQL_TABLE(connection.ops.quote_name(f.m2m_db_table())) + ' (']
        table_output.append('    %s %s %s%s,' % \
            (style.SQL_FIELD(connection.ops.quote_name('id')),
            style.SQL_COLTYPE(models.AutoField(primary_key=True).db_type()),
            style.SQL_KEYWORD('NOT NULL PRIMARY KEY'),
            tablespace_sql))
        table_output.append('    %s %s %s %s (%s)%s,' % \
            (style.SQL_FIELD(connection.ops.quote_name(f.m2m_column_name())),
            style.SQL_COLTYPE(models.ForeignKey(model).db_type()),
            style.SQL_KEYWORD('NOT NULL REFERENCES'),
            style.SQL_TABLE(connection.ops.quote_name(opts.db_table)),
            style.SQL_FIELD(connection.ops.quote_name(opts.pk.column)),
#            backend.get_deferrable_sql()))
            ''))
        table_output.append('    %s %s %s %s (%s)%s,' % \
            (style.SQL_FIELD(connection.ops.quote_name(f.m2m_reverse_name())),
            style.SQL_COLTYPE(models.ForeignKey(f.rel.to).db_type()),
            style.SQL_KEYWORD('NOT NULL REFERENCES'),
            style.SQL_TABLE(connection.ops.quote_name(f.rel.to._meta.db_table)),
            style.SQL_FIELD(connection.ops.quote_name(f.rel.to._meta.pk.column)),
#            backend.get_deferrable_sql()))
            ''))
        table_output.append('    %s (%s, %s)%s' % \
            (style.SQL_KEYWORD('UNIQUE'),
            style.SQL_FIELD(connection.ops.quote_name(f.m2m_column_name())),
            style.SQL_FIELD(connection.ops.quote_name(f.m2m_reverse_name())),
            tablespace_sql))
        table_output.append(')')
        if opts.db_tablespace and backend.supports_tablespaces:
            # f.db_tablespace is only for indices, so ignore its value here.
            table_output.append(backend.get_tablespace_sql(opts.db_tablespace))
        table_output.append(';')
        final_output.append('\n'.join(table_output))

        # Add any extra SQL needed to support auto-incrementing PKs
        autoinc_sql = ops.get_autoinc_sql(f.m2m_db_table())
        if autoinc_sql:
            for stmt in autoinc_sql:
                final_output.append(stmt)

    return final_output