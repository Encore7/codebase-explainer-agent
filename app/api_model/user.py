from typing import List

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    username: str
    scopes: List[str]

    class Config:
        from_attributes = True
