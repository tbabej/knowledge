"""
Provides long term storage backend implementations.
"""

import basehash
import uuid

from pony import orm
from knowledge import config
from knowledge import errors

ALPHABET = '123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
db = orm.Database('sqlite', config.DB_FILE, create_db=True)
translator = basehash.base(ALPHABET)

class Mapping(db.Entity):
    knowledge_id = orm.PrimaryKey(str)
    fact_id = orm.Required(str)

db.generate_mapping(create_tables=True)

@orm.db_session
def get(knowledge_id):
    mapping = Mapping.get(knowledge_id=knowledge_id)

    # If mapping not found in the local database, raise an exception
    if mapping is None:
        raise errors.MappingNotFoundException(knowledge_id)

    return mapping.fact_id

@orm.db_session
def put(fact_id):
    knowledge_id = translator.encode(uuid.uuid4().int >> 64).zfill(11)
    Mapping(knowledge_id=knowledge_id, fact_id=fact_id)
    return knowledge_id
