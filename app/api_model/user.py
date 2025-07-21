from typing import List

from pydantic import BaseModel


class UserOut(BaseModel):
    """Model representing a user in the system.
    Attributes:
        id (int): Unique identifier for the user.
        username (str): Username of the user.
        scopes (List[str]): List of scopes associated with the user.
    """

    id: int
    username: str
    scopes: List[str]

    class Config:
        """Pydantic configuration.
        Attributes:
            from_attributes (bool): Whether to allow model creation from attributes.
        """

        from_attributes = True
