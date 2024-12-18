from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db

router = APIRouter()

@router.get("/users")
def read_users(db: Session = Depends(get_db)):
    """
    Devuelve la lista de usuarios.
    """
    return {"message": "Users endpoint is working"}
