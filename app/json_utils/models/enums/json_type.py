from enum import Enum


class JsonType(str,Enum):
    BROKER_CONNECTION = "broker-connection"
    DATABASE_CONNECTION = "database-connection"
    DATABASE_TABLE = "database-table"
    SCENARIO = "scenario"
    JSON_ARRAY = "json-array"
