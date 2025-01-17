from typing import List

from sqlalchemy import or_

from spiffworkflow_backend.models.db import db
from spiffworkflow_backend.models.process_caller import ProcessCallerCacheModel


class ProcessCallerService:
    @staticmethod
    def count() -> int:
        return ProcessCallerCacheModel.query.count()  # type: ignore

    @staticmethod
    def clear_cache() -> None:
        db.session.query(ProcessCallerCacheModel).delete()

    @staticmethod
    def clear_cache_for_process_ids(process_ids: List[str]) -> None:
        db.session.query(ProcessCallerCacheModel).filter(
            or_(
                ProcessCallerCacheModel.process_identifier.in_(process_ids),
                ProcessCallerCacheModel.calling_process_identifier.in_(process_ids),
            )
        ).delete()

    @staticmethod
    def add_caller(process_id: str, called_process_ids: List[str]) -> None:
        for called_process_id in called_process_ids:
            db.session.add(
                ProcessCallerCacheModel(process_identifier=called_process_id, calling_process_identifier=process_id)
            )
        db.session.commit()

    @staticmethod
    def callers(process_id: str) -> List[str]:
        records = (
            db.session.query(ProcessCallerCacheModel)
            .filter(ProcessCallerCacheModel.process_identifier == process_id)
            .all()
        )
        return list(set(map(lambda r: r.calling_process_identifier, records)))  # type: ignore
