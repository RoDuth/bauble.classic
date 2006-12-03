#!/usr/bin/env python
# load all the plugins
# get all the tables
# iterate through the columns
# iterate through the joins

# TODO: use pydoc to get documentation from tables

import os, sys
sys.path.append('.')
from bauble.plugins import tables

html_head='''<html><head>
<style>
.table{
padding-bottom: 10px;
}
.name{
background-color: #778899;
color: white;
padding-left: 5px;
}

.details{
margin-left: 10px;
}
</style>
</head><body>'''

html_tail='''</body>
</html>'''

table_template = '''<div class='table'><h2 class="name">%(name)s (%(table_name)s)</h2>
<div class='details'>
%(columns)s
%(joins)s
</div>
</div>'''

columns_template = '''<h3>Columns</h3>
<ul>%s</ul>'''

column_template = '''<li>%s</li>'''

joins_template = '''<h3>Joins</h3>
<ul>%s</ul>'''
join_template = '''<li>%s</li>'''

print html_head

for name, table in tables.iteritems():
    columns = ''
    for col in table.sqlmeta.columns:
	columns += column_template % col

    if columns != '':
	columns_markup = columns_template % columns
    
    joins = ''
    for join in table.sqlmeta.joins:
	joins += join_template % join.joinMethodName

    joins_markup = ''
    if joins != '':
	joins_markup = joins_template % joins

    print table_template % ({'name': name, 
			     'table_name': table.sqlmeta.table,
			     'columns': columns_markup, 
			     'joins': joins_markup})
    
print html_tail