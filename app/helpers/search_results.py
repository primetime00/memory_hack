from __future__ import annotations

import ctypes
import sqlite3
from typing import Union

from app.helpers.directory_utils import memory_directory

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]



class SearchResults:
    directory = memory_directory

    def __init__(self, name='results', store_size=4, db_path=memory_directory.joinpath('results.db'), append=False):
        self.db_path = db_path
        self.table = name
        self.table_stack = [self.table]
        self.table_count = 1
        self.connection: sqlite3.Connection = sqlite3.connect(str(self.db_path.absolute()), check_same_thread=False)



    def __len__(self):
        try:
            return self.connection.execute("SELECT COUNT(address) FROM {};".format(self.table_stack[-1])).fetchone()[0]
        except:
            return 0

    def commit(self):
        self.connection.commit()

    def get_results(self, _offset=0, _count=-1, table_name=None):
        if not table_name:
            return self.connection.execute('''SELECT address, value from "{}" ORDER BY address ASC LIMIT {} OFFSET {}'''.format(self.table_stack[-1], _count, _offset))
        else:
            return self.connection.execute('''SELECT address, value from "{}" ORDER BY address ASC LIMIT {} OFFSET {}'''.format(table_name, _count, _offset))

    def get_results_unordered(self):
        return self.connection.execute('''SELECT address, value from "{}"'''.format(self.table_stack[-1]))

    def delete_database(self):
        if self.connection is not None:
            self.connection.close()
        self.db_path.unlink(missing_ok=True)
        self.table_stack = [self.table]
        self.table_count = 1
        self.connection = sqlite3.connect(str(self.db_path.absolute()), check_same_thread=False)

    def clear_results(self):
        for tbl in self.table_stack:
            self.connection.execute('''DROP TABLE IF EXISTS "{}";'''.format(tbl))

    def create_result_table(self):
        self.connection.execute('''CREATE TABLE IF NOT EXISTS "{}" (
                 id         integer     PRIMARY KEY,
                 address    integer     NOT NULL,
                 value      blob        NOT NULL
                 );'''.format(self.table_stack[-1]))

    def create_address_index(self):
        self.connection.execute('''drop index if exists address_index''')
        self.connection.execute('''create index address_index on {}(address)'''.format(self.table_stack[-1]))

    def increment_result_table(self):
        nm = self.table + '_{}'.format(self.table_count)
        self.table_count += 1
        self.table_stack.append(nm)
        self.create_result_table()

    def revert_result_table(self):
        if len(self.table_stack) == 1:
            return
        nm = self.table_stack.pop()
        self.connection.execute('''DROP TABLE IF EXISTS "{}";'''.format(nm))
        self.table_count -= 1

    def add_results(self, result_list: list):
        self.connection.executemany('''INSERT INTO "{}" (address, value) VALUES (?, ?)'''.format(self.table_stack[-1]), result_list)

    def get_store_size(self):
        sql = '''SELECT value FROM "{}" LIMIT 1'''.format(self.table_stack[0])
        return len(self.connection.execute(sql).fetchone()[0])

    def close(self):
        if self.is_open():
            self.connection.close()
            self.connection = None

    def is_open(self):
        return self.connection is not None

    def open(self):
        self.connection = sqlite3.connect(str(self.db_path.absolute()), check_same_thread=False)
