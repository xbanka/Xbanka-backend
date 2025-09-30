from pydantic import BaseModel, ConfigDict

class AffiliateCodename(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    codename: str