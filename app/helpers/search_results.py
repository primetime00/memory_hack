from __future__ import annotations

import ctypes
import sqlite3
from contextlib import contextmanager
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

    @contextmanager
    def db(self):
        conn = sqlite3.connect(str(self.db_path.absolute()), check_same_thread=False)
        yield conn
        conn.commit()
        conn.close()

    def __len__(self):
        with self.db() as conn:
            return self.get_number_of_results(conn, -1)

    def get_number_of_results(self, connection: sqlite3.Connection, index):
        try:
            return connection.execute("SELECT COUNT(address) FROM {};".format(self.table_stack[index])).fetchone()[0]
        except:
            return 0

    def get_results(self, connection: sqlite3.Connection, _offset=0, _count=-1, table_name=None):
        if not table_name:
            return connection.execute('''SELECT address, value from "{}" ORDER BY address ASC LIMIT {} OFFSET {}'''.format(self.table_stack[-1], _count, _offset))
        else:
            return connection.execute('''SELECT address, value from "{}" ORDER BY address ASC LIMIT {} OFFSET {}'''.format(table_name, _count, _offset))

    def get_results_unordered(self, connection: sqlite3.Connection, index=-1):
        return connection.execute('''SELECT address, value from "{}"'''.format(self.table_stack[index]))

    def delete_database(self):
        self.db_path.unlink(missing_ok=True)
        self.table_stack = [self.table]
        self.table_count = 1

    def clear_results(self, connection: sqlite3.Connection):
        for tbl in self.table_stack:
            connection.execute('''DROP TABLE IF EXISTS "{}";'''.format(tbl))

    def create_result_table(self, connection: sqlite3.Connection):
        connection.execute('''CREATE TABLE IF NOT EXISTS "{}" (
                 id         integer     PRIMARY KEY,
                 address    integer     NOT NULL,
                 value      blob        NOT NULL
                 );'''.format(self.table_stack[-1]))

    def create_address_index(self, connection: sqlite3.Connection):
        connection.execute('''drop index if exists address_index''')
        connection.execute('''create index address_index on {}(address)'''.format(self.table_stack[-1]))

    def increment_result_table(self, connection: sqlite3.Connection):
        nm = self.table + '_{}'.format(self.table_count)
        self.table_count += 1
        self.table_stack.append(nm)
        self.create_result_table(connection)

    def revert_result_table(self, connection: sqlite3.Connection):
        if len(self.table_stack) == 1:
            return
        nm = self.table_stack.pop()
        connection.execute('''DROP TABLE IF EXISTS "{}";'''.format(nm))
        self.table_count -= 1

    def add_results(self, connection: sqlite3.Connection, result_list: list):
        connection.executemany('''INSERT INTO "{}" (address, value) VALUES (?, ?)'''.format(self.table_stack[-1]), result_list)

    def get_store_size(self, connection: sqlite3.Connection):
        sql = '''SELECT value FROM "{}" LIMIT 1'''.format(self.table_stack[0])
        return len(connection.execute(sql).fetchone()[0])

