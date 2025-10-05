from pydantic import BaseModel


class RedirectUrlSchema(BaseModel):
    redirect_url: str
