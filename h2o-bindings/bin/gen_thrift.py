#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
from builtins import range
from collections import OrderedDict
import bindings as bi

# Thrift reserved words.  We can't use these as field names.  :-(
thrift_reserved_words = set(["from", "type", "exception", "lambda", "required"])


class ThriftTypeTranslator(bi.TypeTranslator):
    def __init__(self):
        bi.TypeTranslator.__init__(self)
        self.types["float"] = "double"
        self.types["byte"]  = "i8"
        self.types["short"] = "i16"
        self.types["int"]   = "i32"
        self.types["long"]  = "i64"
        self.types["boolean"] = "bool"
        self.types["string"] = "String"
        self.types["Polymorphic"] = "PrimitiveUnion"
        self.make_array = lambda itype: "list<%s>" % itype
        self.make_array2 = lambda itype: "list<list<%s>>" % itype
        self.make_map = lambda ktype, vtype: "map<%s,%s>" % (ktype, vtype)
        self.make_key = lambda itype, schema: "String"

type_adapter = ThriftTypeTranslator()
def translate_type(h2o_type, schema):
    return type_adapter.translate(h2o_type, schema)


def add_schema_to_dependency_array(schema, ordered_schemas, schemas_map):
    """
    This is a helper function to order all schemas according to their usage. For example, if schema A uses schemas B
    and C, then they should be reordered as {B, C, A}.
      :param schema: schema object that we are processing right now
      :param ordered_schemas: an OrderedDict of schemas that were already encountered. This is also the "output"
        variable -- all schemas/enums that are needed will be recorded here in the correct order of their supposed
        declaration.
      :param schemas_map: dictionary(schemaname => schemaobject)
    """
    ordered_schemas[schema["name"]] = schema
    for field in schema["fields"]:
        field_schema_name = field["schema_name"]
        if field_schema_name is None: continue
        if field_schema_name in ordered_schemas: continue
        if field["type"].startswith("enum"):
            ordered_schemas[field_schema_name] = field["values"]
        else:
            field_schema = schemas_map[field_schema_name]
            if field_schema["name"] not in ordered_schemas:
                add_schema_to_dependency_array(field_schema, ordered_schemas, schemas_map)


def generate_thrift(ordered_schemas):
    yield "#-------------------------------------------------------------------------------"
    yield "# Thrift bindings for H2O Machine Learning."
    yield "#"
    yield "# This file is auto-generated by h2o-3/h2o-bindings/bin/gen_thrift.py"
    yield "# Copyright 2016 H2O.ai;  Apache License Version 2.0 (see LICENSE for details)"
    yield "#-------------------------------------------------------------------------------"
    yield ""
    yield "namespace * water.bindings.structs"
    yield ""
    yield "union PrimitiveUnion {"
    yield "  1: bool bool_field"
    yield "  2: byte byte_field"
    yield "  3: i16 i16_field"
    yield "  4: i32 i32_field"
    yield "  5: i64 i64_field"
    yield "  6: double double_field"
    yield "  7: binary binary_field"
    yield "  8: string string_field"
    yield "}"
    yield ""
    for name, v in ordered_schemas.items():
        generator = generate_enum if type(v) is list else generate_struct
        for line in generator(name, v):
            yield line


def generate_enum(name, values):
    bi.vprint("Generating enum " + name)
    yield "enum %s {" % name
    for i,value in enumerate(values):
        yield "  %s = %d," % (value, i+1)
    yield "}"
    yield ""


def generate_struct(name, schema):
    bi.vprint("Generating struct " + name)
    yield "struct %s {" % name
    yield ""
    for i, field in enumerate(schema["fields"]):
        if field["name"] == "__meta": continue
        thrift_type = translate_type(field["type"], field["schema_name"])
        name = field["name"]
        if name in thrift_reserved_words:
            name += "_"
        required = "required" if field["required"] else "optional"
        yield bi.wrap(field["help"], indent="  # ")
        yield "  {num}: {req} {type} {name},".format(num=i, req=required, type=thrift_type, name=name)
        yield ""
    yield "}"
    yield ""


# ----------------------------------------------------------------------------------------------------------------------
#    MAIN
# ----------------------------------------------------------------------------------------------------------------------
def main():
    bi.init("Thrift", "thrift")

    schemas_map = bi.schemas_map()
    ordered_schemas = OrderedDict()
    for name, schema in schemas_map.items():
        add_schema_to_dependency_array(schema, ordered_schemas, schemas_map)

    bi.write_to_file("water/bindings/structs/H2O.thrift", generate_thrift(ordered_schemas))

    type_adapter.vprint_translation_map()


if __name__ == "__main__":
    main()