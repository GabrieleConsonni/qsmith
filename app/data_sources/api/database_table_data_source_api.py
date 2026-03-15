from fastapi import APIRouter
from sqlalchemy import MetaData, Table, inspect, select

from _alembic.models.json_payload_entity import JsonPayloadEntity
from _alembic.services.session_context_manager import managed_session
from data_sources.services.alembic.database_connection_service import load_database_connection
from exceptions.app_exception import QsmithAppException
from json_utils.models.dtos.create_json_payload_dto import CreateJsonPayloadDto
from json_utils.models.dtos.update_json_payload_dto import UpdateJsonPayloadDto
from json_utils.models.enums.json_type import JsonType
from json_utils.services.alembic.json_files_service import JsonFilesService
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory_composite import (
    create_sqlalchemy_engine,
)

router = APIRouter(prefix="/data-source")


def _safe_limit(limit: int) -> int:
    if limit <= 0:
        return 1
    if limit > 500:
        return 500
    return limit


def _normalize_object_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"table", "base table"}:
        return "table"
    if normalized == "view":
        return "view"
    raise QsmithAppException(f"Unsupported object type: {value}")


def _validate_database_table_payload(payload: dict):
    if not isinstance(payload, dict):
        raise QsmithAppException("Payload non valido: deve essere un oggetto JSON.")

    connection_id = str(payload.get("connection_id") or "").strip()
    object_name = str(payload.get("object_name") or "").strip()
    object_type = _normalize_object_type(str(payload.get("object_type") or "table"))

    if not connection_id:
        raise QsmithAppException("Payload non valido: connection_id obbligatorio.")
    if not object_name:
        raise QsmithAppException("Payload non valido: object_name obbligatorio.")

    payload["connection_id"] = connection_id
    payload["object_name"] = object_name
    payload["object_type"] = object_type


def _preview_database_object(payload: dict, limit: int) -> dict:
    connection = load_database_connection(payload["connection_id"])
    if not connection:
        raise QsmithAppException(
            f"No database connection found with id [ {payload['connection_id']} ]"
        )

    schema = payload.get("schema") or connection.db_schema or None
    object_name = payload["object_name"]
    object_type = _normalize_object_type(payload.get("object_type", "table"))
    max_rows = _safe_limit(limit)

    engine = create_sqlalchemy_engine(connection)
    inspector = inspect(engine)
    allowed_names = (
        inspector.get_table_names(schema=schema)
        if object_type == "table"
        else inspector.get_view_names(schema=schema)
    )
    if object_name not in allowed_names:
        raise QsmithAppException(
            f"Object [ {object_name} ] not found for type [ {object_type} ]"
        )

    metadata = MetaData()
    table = Table(
        object_name,
        metadata,
        schema=schema,
        autoload_with=engine,
    )
    stmt = select(table).limit(max_rows)
    with engine.connect() as db_connection:
        result = db_connection.execute(stmt)
        rows = [dict(row._mapping) for row in result]

    return {
        "schema": schema,
        "object_name": object_name,
        "object_type": object_type,
        "columns": [str(col.name) for col in table.columns],
        "rows": rows,
        "count": len(rows),
    }


@router.post("/database")
async def insert_database_data_source_api(dto: CreateJsonPayloadDto):
    _validate_database_table_payload(dto.payload if isinstance(dto.payload, dict) else {})

    with managed_session() as session:
        entity = JsonPayloadEntity()
        entity.description = dto.description
        entity.json_type = JsonType.DATABASE_TABLE.value
        entity.payload = dto.payload
        _id = JsonFilesService().insert(session, entity)
        return {"id": _id, "message": "Database datasource added"}


@router.put("/database")
async def update_database_data_source_api(dto: UpdateJsonPayloadDto):
    _validate_database_table_payload(dto.payload if isinstance(dto.payload, dict) else {})

    with managed_session() as session:
        JsonFilesService().update(
            session,
            dto.id,
            description=dto.description,
            json_type=JsonType.DATABASE_TABLE.value,
            payload=dto.payload,
        )
        return {"message": "Database datasource updated"}


@router.get("/database")
async def find_all_database_data_source_api():
    result = []
    with managed_session() as session:
        all_data = JsonFilesService().get_all_by_type(session, JsonType.DATABASE_TABLE)
        for data in all_data:
            result.append(
                {
                    "id": data.id,
                    "description": data.description,
                    "payload": data.payload,
                }
            )
    return result


@router.get("/database/{_id}")
async def find_database_data_source_api(_id: str):
    with managed_session() as session:
        entity: JsonPayloadEntity = JsonFilesService().get_by_id(session, _id)
        if not entity or entity.json_type != JsonType.DATABASE_TABLE.value:
            raise QsmithAppException(f"No database datasource found with id [ {_id} ]")
        return {
            "id": entity.id,
            "description": entity.description,
            "payload": entity.payload,
        }


@router.get("/database/{_id}/preview")
async def preview_database_data_source_api(_id: str, limit: int = 100):
    payload: dict
    with managed_session() as session:
        entity: JsonPayloadEntity = JsonFilesService().get_by_id(session, _id)
        if not entity or entity.json_type != JsonType.DATABASE_TABLE.value:
            raise QsmithAppException(f"No database datasource found with id [ {_id} ]")
        payload = entity.payload if isinstance(entity.payload, dict) else {}

    _validate_database_table_payload(payload)
    return _preview_database_object(payload, limit=limit)


@router.delete("/database/{_id}")
async def delete_database_data_source_api(_id: str):
    with managed_session() as session:
        entity: JsonPayloadEntity = JsonFilesService().get_by_id(session, _id)
        if not entity or entity.json_type != JsonType.DATABASE_TABLE.value:
            raise QsmithAppException(f"No database datasource found with id [ {_id} ]")
        count = JsonFilesService().delete_by_id(session, _id)
        if count == 0:
            raise QsmithAppException(f"No database datasource found with id [ {_id} ]")
        return {"message": "Database datasource deleted successfully"}
