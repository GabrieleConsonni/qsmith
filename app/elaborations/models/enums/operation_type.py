from enum import Enum

class OperationType(str,Enum):
    DATA = "data"
    DATA_FROM_JSON_ARRAY = "data-from-json-array"
    DATA_FROM_DB = "data-from-db"
    DATA_FROM_QUEUE = "data-from-queue"
    SLEEP = "sleep"
    PUBLISH = "publish"
    SAVE_INTERNAL_DB = "save-internal-db"
    SAVE_EXTERNAL_DB = "save-external-db"
    ASSERT = "assert"
    RUN_SUITE = "run-suite"
    SET_VAR = "set-var"
