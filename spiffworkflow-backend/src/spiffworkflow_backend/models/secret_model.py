"""Secret_model."""
from dataclasses import dataclass

from marshmallow import Schema
from sqlalchemy import ForeignKey

from spiffworkflow_backend.models.db import db
from spiffworkflow_backend.models.db import SpiffworkflowBaseDBModel
from spiffworkflow_backend.models.user import UserModel


@dataclass()
class SecretModel(SpiffworkflowBaseDBModel):
    """SecretModel."""

    __tablename__ = "secret"
    id: int = db.Column(db.Integer, primary_key=True)
    key: str = db.Column(db.String(50), unique=True, nullable=False)
    value: str = db.Column(db.Text(), nullable=False)
    user_id: int = db.Column(ForeignKey(UserModel.id), nullable=False, index=True)  # type: ignore
    updated_at_in_seconds: int = db.Column(db.Integer)
    created_at_in_seconds: int = db.Column(db.Integer)


class SecretModelSchema(Schema):
    """SecretModelSchema."""

    class Meta:
        """Meta."""

        model = SecretModel
        fields = ["key", "value", "user_id"]
