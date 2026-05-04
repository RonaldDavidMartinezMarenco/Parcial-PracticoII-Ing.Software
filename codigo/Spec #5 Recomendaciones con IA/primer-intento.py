# routers/recommendations.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
from models import HabitsLog, EmotionalLog, Recommendation
import google.generativeai as genai
import uuid
import os

router = APIRouter()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

@router.post("/api/recommendations/generate", status_code=200)
def generate_recommendation(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user["user_id"]

    # Consultar historial de comidas
    historial = db.query(HabitsLog).filter(
        HabitsLog.user_id == user_id
    ).order_by(HabitsLog.log_date.desc()).limit(7).all()

    if not historial:
        raise HTTPException(
            status_code=400,
            detail="Necesitas registrar al menos una comida para recibir recomendaciones"
        )

    # Consultar estado emocional
    estado = db.query(EmotionalLog).filter(
        EmotionalLog.user_id == user_id
    ).order_by(EmotionalLog.log_date.desc()).first()

    emocion = estado.emotion if estado else "desconocido"
    intensidad = estado.intensity if estado else "desconocido"

    # Construir prompt
    alimentos = [h.food_description for h in historial]

    prompt = f"""
    El usuario ha consumido: {alimentos}.
    Estado emocional: {emocion}, intensidad: {intensidad}.
    Genera una recomendación nutricional personalizada.
    """

    # Llamar a Gemini
    response = model.generate_content(prompt)
    content = response.text

    # Guardar recomendación
    new_recommendation = Recommendation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        source="AI",
        content=content
    )
    db.add(new_recommendation)
    db.commit()

    return {"message": "Recomendación generada", "content": content}