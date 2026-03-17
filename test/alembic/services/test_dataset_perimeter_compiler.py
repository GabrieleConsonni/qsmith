from sqlalchemy import Column, Integer, MetaData, String, Table

import pytest

from app.data_sources.services.dataset_perimeter_compiler import DatasetPerimeterCompiler


def _build_orders_table() -> Table:
    metadata = MetaData()
    return Table(
        "orders",
        metadata,
        Column("id", Integer),
        Column("status", String),
        Column("note", String),
    )


def test_dataset_perimeter_compiler_rejects_duplicate_selected_columns():
    table = _build_orders_table()

    with pytest.raises(ValueError, match="Duplicate selected column 'id'"):
        DatasetPerimeterCompiler.compile(
            table,
            {"selected_columns": ["id", "id"]},
        )


def test_dataset_perimeter_compiler_rejects_unknown_fields():
    table = _build_orders_table()

    with pytest.raises(ValueError, match="Filter field 'missing' does not exist."):
        DatasetPerimeterCompiler.compile(
            table,
            {
                "filter": {
                    "logic": "AND",
                    "conditions": [
                        {"field": "missing", "operator": "eq", "value": 1},
                    ],
                }
            },
        )


def test_dataset_perimeter_compiler_binds_values_instead_of_inlining_them():
    table = _build_orders_table()
    malicious_value = "READY' OR 1=1 --"

    compilation = DatasetPerimeterCompiler.compile(
        table,
        {
            "selected_columns": ["id", "status"],
            "filter": {
                "logic": "AND",
                "conditions": [
                    {"field": "status", "operator": "eq", "value": malicious_value},
                ],
            },
            "sort": [{"field": "id", "direction": "desc"}],
        },
        limit=100,
    )
    compiled_stmt = compilation.stmt.compile()
    compiled_sql = str(compiled_stmt)

    assert malicious_value not in compiled_sql
    assert malicious_value in compiled_stmt.params.values()
    assert compilation.columns == ["id", "status"]
