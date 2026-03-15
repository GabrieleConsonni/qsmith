from sqlalchemy import desc
from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.test_suite_execution_entity import TestSuiteExecutionEntity
from _alembic.services.base_id_service import BaseIdEntityService


class TestSuiteExecutionService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return TestSuiteExecutionEntity

    def get_all_ordered(self, session: Session, limit: int = 50) -> list[TestSuiteExecutionEntity]:
        return (
            session.query(TestSuiteExecutionEntity)
            .order_by(desc(TestSuiteExecutionEntity.started_at), desc(TestSuiteExecutionEntity.id))
            .limit(limit)
            .all()
        )

    def get_all_by_suite_id(
        self,
        session: Session,
        test_suite_id: str,
        limit: int = 50,
    ) -> list[TestSuiteExecutionEntity]:
        suite_id_attr: InstrumentedAttribute = TestSuiteExecutionEntity.test_suite_id
        return (
            session.query(TestSuiteExecutionEntity)
            .filter(suite_id_attr == test_suite_id)
            .order_by(desc(TestSuiteExecutionEntity.started_at), desc(TestSuiteExecutionEntity.id))
            .limit(limit)
            .all()
        )
