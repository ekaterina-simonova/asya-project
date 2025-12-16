from pydantic import BaseModel
from typing import Dict, Optional

class CallRequest(BaseModel):
    destination: str
    caller_id: Optional[str] = None
    context: Optional[str] = "default"
    extension: Optional[str] = "s"
    variables: Optional[Dict[str, str]] = None

class CallResponse(BaseModel):
    success: bool
    call_id: Optional[str] = None
    message: str

class HangupRequest(BaseModel):
    call_id: str