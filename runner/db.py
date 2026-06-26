from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from runner.models import DbCheck


def run_db_check(database_url: str, check: DbCheck) -> list[dict[str, Any]]:
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(check.query, check.params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
