# schemas/auth.py
from pydantic import BaseModel, EmailStr, field_validator
import re

class RegisterRequest(BaseModel):
    nombre_completo: str
    correo_electronico: EmailStr
    contraseña: str
    telefono_whatsapp: str

    @field_validator('nombre_completo')
    @classmethod
    def validate_nombre(cls, v):
        v = v.strip()
        if len(v) < 3 or len(v) > 100:
            raise ValueError('El nombre debe tener entre 3 y 100 caracteres')
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$', v):
            raise ValueError('El nombre solo puede contener letras y espacios')
        return v

    @field_validator('correo_electronico')
    @classmethod
    def validate_correo(cls, v):
        return v.strip().lower()

    @field_validator('contraseña')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Mínimo 8 caracteres')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Debe contener al menos una mayúscula')
        if not re.search(r'[0-9]', v):
            raise ValueError('Debe contener al menos un número')
        return v

    @field_validator('telefono_whatsapp')
    @classmethod
    def validate_telefono(cls, v):
        v = v.strip()
        if not re.match(r'^\d{10,15}$', v):
            raise ValueError('Debe contener entre 10 y 15 dígitos numéricos')
        return v


# models/user.py
from sqlalchemy import Column, String, Enum, Boolean
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    role = Column(Enum('user', 'admin', 'professional'), nullable=False)

class UserWhatsapp(Base):
    __tablename__ = "user_whatsapp"
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, unique=True)
    phone_number = Column(String(20), nullable=False, unique=True)

class UserSettings(Base):
    __tablename__ = "user_settings"
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, unique=True)
    notifications = Column(Boolean, default=True)
    language = Column(String(10), default='es')


# routers/auth.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from schemas.auth import RegisterRequest
from models.user import User, UserWhatsapp, UserSettings
from database import get_db
import uuid

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"])

@router.post("/api/auth/register", status_code=201)
def register_user(data: RegisterRequest, db: Session = Depends(get_db)):

    if db.query(User).filter(User.email == data.correo_electronico).first():
        raise HTTPException(status_code=409, detail="El correo ya está registrado")

    if db.query(UserWhatsapp).filter(
        UserWhatsapp.phone_number == data.telefono_whatsapp
    ).first():
        raise HTTPException(status_code=409, detail="El teléfono ya está registrado")

    hashed_password = pwd_context.hash(data.contraseña)
    user_id = str(uuid.uuid4())

    try:
        new_user = User(
            id=user_id,
            name=data.nombre_completo,
            email=data.correo_electronico,
            password=hashed_password,
            role="user"
        )
        db.add(new_user)

        new_whatsapp = UserWhatsapp(
            id=str(uuid.uuid4()),
            user_id=user_id,
            phone_number=data.telefono_whatsapp
        )
        db.add(new_whatsapp)

        new_settings = UserSettings(
            id=str(uuid.uuid4()),
            user_id=user_id,
            notifications=True,
            language='es'
        )
        db.add(new_settings)

        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error interno al registrar el usuario"
        )

    return {
        "message": "Usuario registrado exitosamente",
        "user_id": user_id
    }