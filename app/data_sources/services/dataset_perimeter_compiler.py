from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.sql import Select
from sqlalchemy.sql.schema import Table


SUPPORTED_OPERATORS = {
    "eq",
    "neq",
    "gt",
    "gte",
    "lt",
    "lte",
    "contains",
    "starts_with",
    "ends_with",
    "in",
    "not_in",
    "is_null",
    "is_not_null",
}
STRING_OPERATORS = {"contains", "starts_with", "ends_with"}


@dataclass
class DatasetQueryCompilation:
    stmt: Select
    columns: list[str]
    normalized_perimeter: dict | None


class DatasetPerimeterCompiler:
    @classmethod
    def normalize(cls, perimeter_json: dict | None) -> dict | None:
        if perimeter_json in (None, {}):
            return None
        if not isinstance(perimeter_json, dict):
            raise ValueError("perimeter must be an object.")

        normalized: dict[str, Any] = {}

        raw_selected_columns = perimeter_json.get("selected_columns")
        if raw_selected_columns is not None:
            if not isinstance(raw_selected_columns, list):
                raise ValueError("selected_columns must be an array.")
            selected_columns: list[str] = []
            for item in raw_selected_columns:
                column_name = str(item or "").strip()
                if not column_name:
                    raise ValueError("selected_columns items must be non-empty strings.")
                if column_name in selected_columns:
                    raise ValueError(f"Duplicate selected column '{column_name}'.")
                selected_columns.append(column_name)
            normalized["selected_columns"] = selected_columns

        raw_filter = perimeter_json.get("filter")
        if raw_filter is not None:
            if not isinstance(raw_filter, dict):
                raise ValueError("filter must be an object.")
            logic = str(raw_filter.get("logic") or "AND").strip().upper()
            if logic not in {"AND", "OR"}:
                raise ValueError("filter.logic must be AND or OR.")
            raw_conditions = raw_filter.get("conditions") or []
            if not isinstance(raw_conditions, list):
                raise ValueError("filter.conditions must be an array.")
            conditions: list[dict[str, Any]] = []
            for index, raw_condition in enumerate(raw_conditions):
                if not isinstance(raw_condition, dict):
                    raise ValueError(f"filter.conditions[{index}] must be an object.")
                field = str(raw_condition.get("field") or "").strip()
                if not field:
                    raise ValueError(f"filter.conditions[{index}].field is required.")
                operator = str(raw_condition.get("operator") or "").strip().lower()
                if operator not in SUPPORTED_OPERATORS:
                    raise ValueError(
                        f"filter.conditions[{index}].operator '{operator}' is not supported."
                    )
                has_value = "value" in raw_condition
                if operator in {"is_null", "is_not_null"}:
                    value = None
                else:
                    if not has_value:
                        raise ValueError(
                            f"filter.conditions[{index}].value is required for operator '{operator}'."
                        )
                    value = raw_condition.get("value")
                if operator in {"in", "not_in"}:
                    if not isinstance(value, list) or not value:
                        raise ValueError(
                            f"filter.conditions[{index}].value must be a non-empty array for operator '{operator}'."
                        )
                if operator in STRING_OPERATORS and not isinstance(value, str):
                    raise ValueError(
                        f"filter.conditions[{index}].value must be a string for operator '{operator}'."
                    )
                conditions.append(
                    {
                        "field": field,
                        "operator": operator,
                        "value": value,
                    }
                )
            normalized["filter"] = {
                "logic": logic,
                "conditions": conditions,
            }

        raw_sort = perimeter_json.get("sort")
        if raw_sort is not None:
            if not isinstance(raw_sort, list):
                raise ValueError("sort must be an array.")
            sort_items: list[dict[str, str]] = []
            for index, raw_sort_item in enumerate(raw_sort):
                if not isinstance(raw_sort_item, dict):
                    raise ValueError(f"sort[{index}] must be an object.")
                field = str(raw_sort_item.get("field") or "").strip()
                if not field:
                    raise ValueError(f"sort[{index}].field is required.")
                direction = str(raw_sort_item.get("direction") or "asc").strip().lower()
                if direction not in {"asc", "desc"}:
                    raise ValueError(f"sort[{index}].direction must be 'asc' or 'desc'.")
                sort_items.append(
                    {
                        "field": field,
                        "direction": direction,
                    }
                )
            normalized["sort"] = sort_items

        return normalized or None

    @classmethod
    def compile(
        cls,
        table: Table,
        perimeter_json: dict | None,
        *,
        limit: int | None = None,
    ) -> DatasetQueryCompilation:
        normalized = cls.normalize(perimeter_json)
        available_columns = {str(column.name): column for column in table.columns}
        selected_columns = list(available_columns.keys())

        if normalized and normalized.get("selected_columns"):
            selected_columns = normalized["selected_columns"]
            for column_name in selected_columns:
                if column_name not in available_columns:
                    raise ValueError(f"Selected column '{column_name}' does not exist.")

        stmt = select(*[available_columns[column_name] for column_name in selected_columns])

        if normalized and normalized.get("filter", {}).get("conditions"):
            conditions = [
                cls._compile_condition(available_columns, condition)
                for condition in normalized["filter"]["conditions"]
            ]
            if normalized["filter"]["logic"] == "OR":
                stmt = stmt.where(or_(*conditions))
            else:
                stmt = stmt.where(and_(*conditions))

        if normalized and normalized.get("sort"):
            order_by = []
            for sort_item in normalized["sort"]:
                field = sort_item["field"]
                if field not in available_columns:
                    raise ValueError(f"Sort field '{field}' does not exist.")
                column = available_columns[field]
                order_by.append(column.desc() if sort_item["direction"] == "desc" else column.asc())
            stmt = stmt.order_by(*order_by)

        if limit is not None:
            stmt = stmt.limit(limit)

        return DatasetQueryCompilation(
            stmt=stmt,
            columns=selected_columns,
            normalized_perimeter=normalized,
        )

    @classmethod
    def _compile_condition(cls, available_columns: dict[str, Any], condition: dict[str, Any]):
        field = condition["field"]
        if field not in available_columns:
            raise ValueError(f"Filter field '{field}' does not exist.")
        column = available_columns[field]
        operator = condition["operator"]
        value = condition.get("value")

        if operator == "eq":
            return column.is_(None) if value is None else column == value
        if operator == "neq":
            return column.is_not(None) if value is None else column != value
        if operator == "gt":
            return column > value
        if operator == "gte":
            return column >= value
        if operator == "lt":
            return column < value
        if operator == "lte":
            return column <= value
        if operator == "contains":
            return column.contains(value)
        if operator == "starts_with":
            return column.startswith(value)
        if operator == "ends_with":
            return column.endswith(value)
        if operator == "in":
            return column.in_(value)
        if operator == "not_in":
            return column.not_in(value)
        if operator == "is_null":
            return column.is_(None)
        if operator == "is_not_null":
            return column.is_not(None)
        raise ValueError(f"Unsupported operator '{operator}'.")
