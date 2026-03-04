from enum import Enum

class OperationType(str,Enum):
    PUBLISH = "publish"
    SAVE_INTERNAL_DB = "save-internal-db"
    SAVE_EXTERNAL_DB = "save-external-db"
    ASSERT = "assert"
