# routers/recommendations.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
from models import (
    HabitsLog, EmotionalLog, Recommendation,
    AiConversation, AiMessageLog, MessageToolCall
)
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import uuid
import time
import json
import os

router = APIRouter()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

KEYWORDS_BIENESTAR = [
    "nutrición", "alimento", "comida", "receta", "proteína",
    "calorías", "bienestar", "emoción", "salud", "dieta", "vitamina"
]


def detect_hallucination(text: str) -> bool:
    text_lower = text.lower()
    return not any(keyword in text_lower for keyword in KEYWORDS_BIENESTAR)


def get_or_create_conversation(db: Session, user_id: str) -> str:
    conversation = db.query(AiConversation).filter(
        AiConversation.user_id == user_id,
        AiConversation.whatsapp_chat_id == "web"
    ).order_by(AiConversation.created_at.desc()).first()

    if not conversation:
        conversation = AiConversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            whatsapp_chat_id="web",
            phone_number="web",
            context={}
        )
        db.add(conversation)
        db.flush()

    return conversation.id


@router.post("/api/recommendations/generate", status_code=200)
def generate_recommendation(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user["user_id"]

    # Paso 3: Consultar historial de comidas
    historial = db.query(HabitsLog).filter(
        HabitsLog.user_id == user_id
    ).order_by(HabitsLog.log_date.desc()).limit(7).all()

    # Paso 5: Validar cold start antes de llamar al LLM
    if not historial:
        raise HTTPException(
            status_code=400,
            detail="Necesitas registrar al menos una comida para recibir recomendaciones"
        )

    # Paso 4: Consultar estado emocional más reciente
    estado = db.query(EmotionalLog).filter(
        EmotionalLog.user_id == user_id
    ).order_by(EmotionalLog.log_date.desc()).first()

    emocion = estado.emotion if estado else "no registrado"
    intensidad = estado.intensity if estado else "no registrado"

    # Paso 6: Construir prompt dinámico con meal_type
    alimentos_detalle = "\n".join([
        f"- {h.meal_type.capitalize()}: {h.food_description}"
        for h in historial
    ])

    prompt = f"""Eres un nutricionista y psicólogo del bienestar.
El usuario ha consumido los siguientes alimentos recientemente:
{alimentos_detalle}

Su estado emocional actual es: {emocion} con una intensidad de {intensidad}/10.

Genera una recomendación nutricional y de bienestar personalizada,
considerando tanto su alimentación como su estado emocional actual."""

    # Obtener o crear conversación activa
    conversation_id = get_or_create_conversation(db, user_id)

    # Paso 7: Llamar a Gemini con timeout y medir tiempo de respuesta
    start_time = time.time()
    try:
        response = gemini_model.generate_content(
            prompt,
            request_options={"timeout": 5}
        )
    except google_exceptions.DeadlineExceeded:
        raise HTTPException(
            status_code=502,
            detail="El servicio de IA no respondió a tiempo, intenta de nuevo"
        )
    except google_exceptions.ServiceUnavailable:
        raise HTTPException(
            status_code=502,
            detail="El servicio de IA no está disponible en este momento"
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Error al conectar con el servicio de IA"
        )

    response_time_ms = int((time.time() - start_time) * 1000)
    content = response.text
    tokens_used = response.usage_metadata.total_token_count

    # Paso 8: Registrar respuesta en ai_message_logs
    message_id = str(uuid.uuid4())
    new_message = AiMessageLog(
        id=message_id,
        ai_conversation_id=conversation_id,
        role="assistant",
        content=content,
        model="gemini-1.5-flash",
        tokens_used=tokens_used,
        response_time_ms=response_time_ms
    )
    db.add(new_message)
    db.flush()

    # Registrar llamada en message_tool_calls
    new_tool_call = MessageToolCall(
        id=str(uuid.uuid4()),
        message_id=message_id,
        tool_name="llm_recommendation",
        input_data=json.dumps({"prompt": prompt}),
        output_data=json.dumps({"respuesta": content})
    )
    db.add(new_tool_call)

    # Paso 9: Validar alucinación antes de persistir
    if detect_hallucination(content):
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="La IA generó una respuesta fuera de contexto"
        )

    # Paso 10: Persistir recomendación
    new_recommendation = Recommendation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        source="AI",
        content=content
    )
    db.add(new_recommendation)
    db.commit()

    return {
        "message": "Recomendación generada",
        "content": content
    }