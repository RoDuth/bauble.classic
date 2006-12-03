#
# meta.py
#
from sqlalchemy import *

VERSION_KEY='version'
CREATED_KEY='created'

bauble_meta_table = Table('bauble',
                          Column('id', Integer, primary_key=True),
                          Column('name', String(64), unique=True),
                          Column('value', String(128)),
                          Column('_created', DateTime, default=func.current_timestamp()),
                          Column('_last_updated', DateTime, default=func.current_timestamp(), 
                                 onupdate=func.current_timestamp()))
        
class BaubleMetaTable(object):
    version = 'version'
    created = 'created'
        
    def __str__(self):
        return '%s=%s' % (self.name, self.value
                          )
mapper(BaubleMetaTable, bauble_meta_table)