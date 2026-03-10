from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.test_suite_entity import TestSuiteEntity
from _alembic.services.base_id_service import BaseIdEntityService
from elaborations.services.alembic.suite_item_service import SuiteItemService


class TestSuiteService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return TestSuiteEntity

    def get_by_code(self, session: Session, code: str) -> TestSuiteEntity | None:
        normalized_code = str(code or "").strip()
        if not normalized_code:
            return None
        code_attr: InstrumentedAttribute = TestSuiteEntity.code
        return session.query(TestSuiteEntity).filter(code_attr == normalized_code).one_or_none()

    def delete_on_cascade(self, session: Session, _id: str):
        SuiteItemService().delete_by_suite_id(session, _id)
