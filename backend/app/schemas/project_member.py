"""Project member schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.project_member import ProjectMemberRole


class ProjectMemberOut(BaseModel):
    id: int
    project_id: int
    user_id: int
    role: ProjectMemberRole
    added_at: datetime
    # Convenience: embed minimal user info so the UI doesn't need a second call.
    user_full_name: str
    user_email: str

    model_config = ConfigDict(from_attributes=True)


class ProjectMemberAdd(BaseModel):
    user_id: int
    role: ProjectMemberRole = ProjectMemberRole.CONTRIBUTOR


class ProjectMemberUpdate(BaseModel):
    role: ProjectMemberRole
