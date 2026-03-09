from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.scenario_entity import ScenarioEntity
from _alembic.services.base_id_service import BaseIdEntityService
from elaborations.services.alembic.scenario_step_service import ScenarioStepService


class ScenarioService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return ScenarioEntity

    def get_by_code(self, session: Session, code: str) -> ScenarioEntity | None:
        normalized_code = str(code or "").strip()
        if not normalized_code:
            return None
        code_attr: InstrumentedAttribute = ScenarioEntity.code
        return session.query(ScenarioEntity).filter(code_attr == normalized_code).one_or_none()

    def delete_on_cascade(self, session:Session, _id):
        ScenarioStepService().delete_by_scenario_id(session,_id)

