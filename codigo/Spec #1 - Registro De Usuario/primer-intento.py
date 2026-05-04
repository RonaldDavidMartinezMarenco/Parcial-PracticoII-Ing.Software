# schemas/auth.py
from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    nombre_completo: str
    correo_electronico: EmailStr
    contraseña: str
    telefono_whatsapp: str


# routers/auth.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import uuid

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"])

@router.post("/api/auth/register", status_code=201)
def register_user(data: RegisterRequest, db: Session = Depends(get_db)):

    existing_email = db.query(User).filter(
        User.email == data.correo_electronico
    ).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="El correo ya está registrado")

    existing_phone = db.query(UserWhatsapp).filter(
        UserWhatsapp.phone_number == data.telefono_whatsapp
    ).first()
    if existing_phone:
        raise HTTPException(status_code=409, detail="El teléfono ya está registrado")

    hashed_password = pwd_context.hash(data.contraseña)

    new_user = User(
        id=str(uuid.uuid4()),
        name=data.nombre_completo,
        email=data.correo_electronico,
        password=hashed_password,
        role="user"
    )
    db.add(new_user)

    new_whatsapp = UserWhatsapp(
        id=str(uuid.uuid4()),
        user_id=new_user.id,
        phone_number=data.telefono_whatsapp
    )
    db.add(new_whatsapp)

    db.commit()

    return {"message": "Usuario registrado exitosamente", "user_id": new_user.id}