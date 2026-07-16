"""Shared Pydantic schemas."""

from pydantic import BaseModel


class RedirectUrlSchema(BaseModel):
    """Schema for a redirect URL response."""

    redirect_url: str
