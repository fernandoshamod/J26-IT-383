"""Validator for the limited JSON Schema keywords used by this POC contract.

Not a general-purpose JSON Schema implementation. No third-party dependency.
"""
import math,re

def validate_contract(value,schema,path='$'):
    types={'object':lambda x:isinstance(x,dict),'array':lambda x:isinstance(x,list),
           'string':lambda x:isinstance(x,str),'null':lambda x:x is None,
           'boolean':lambda x:isinstance(x,bool),'number':lambda x:isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)}
    if 'type' in schema:
        names=schema['type'] if isinstance(schema['type'],list) else [schema['type']]
        if not any(types[t](value) for t in names):raise ValueError(f'{path}:invalid_type')
    def identical(a,b):return type(a) is type(b) and a==b
    if 'const' in schema and not identical(value,schema['const']):raise ValueError(f'{path}:invalid_constant')
    if 'enum' in schema and not any(identical(value,x) for x in schema['enum']):raise ValueError(f'{path}:invalid_enum')
    if isinstance(value,str) and 'pattern' in schema and not re.search(schema['pattern'],value):raise ValueError(f'{path}:invalid_pattern')
    if isinstance(value,dict):
        for key in schema.get('required',[]):
            if key not in value:raise ValueError(f'{path}:missing:{key}')
        for key,child in schema.get('properties',{}).items():
            if key in value:validate_contract(value[key],child,f'{path}.{key}')
    if isinstance(value,list) and 'items' in schema:
        for i,item in enumerate(value):validate_contract(item,schema['items'],f'{path}[{i}]')
    for rule in schema.get('allOf',[]):
        if 'if' in rule:
            try:validate_contract(value,rule['if'],path);condition=True
            except ValueError:condition=False
            validate_contract(value,rule.get('then' if condition else 'else',{}),path)
        else:validate_contract(value,rule,path)
