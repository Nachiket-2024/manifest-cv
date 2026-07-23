from pydantic import BaseModel, Field


class VerifyAccountSchema(BaseModel):
    # Capped well above any legitimate token's length
    token: str = Field(..., max_length=2048)
