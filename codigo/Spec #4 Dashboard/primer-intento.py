# routers/dashboard.py
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from auth import get_current_user
from models import EmotionalLog, HabitsLog, GoalProgress
from datetime import date, timedelta

router = APIRouter()

@router.get("/api/dashboard/stats", status_code=200)
def get_dashboard_stats(
    rango_dias: int = Query(default=7),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user["user_id"]

    # Validar rango_dias
    if rango_dias not in [7, 14, 30]:
        raise HTTPException(status_code=400, detail="rango_dias debe ser 7, 14 o 30")

    fecha_inicio = date.today() - timedelta(days=rango_dias)

    # Consulta emociones
    emociones = db.query(
        EmotionalLog.log_date,
        func.avg(EmotionalLog.intensity).label("promedio_intensidad")
    ).filter(
        EmotionalLog.user_id == user_id,
        EmotionalLog.log_date >= fecha_inicio
    ).group_by(EmotionalLog.log_date).all()

    # Consulta comidas
    comidas = db.query(
        HabitsLog.log_date,
        func.count(HabitsLog.id).label("total_registros"),
        HabitsLog.meal_type
    ).filter(
        HabitsLog.user_id == user_id,
        HabitsLog.log_date >= fecha_inicio
    ).group_by(HabitsLog.log_date, HabitsLog.meal_type).all()

    # Consulta metas
    metas = db.query(
        GoalProgress.log_date,
        GoalProgress.progress
    ).filter(
        GoalProgress.log_date >= fecha_inicio
    ).all()

    return {
        "emociones_historico": [
            {"fecha": str(e.log_date), "promedio_intensidad": round(e.promedio_intensidad, 1)}
            for e in emociones
        ],
        "resumen_comidas": [
            {"fecha": str(c.log_date), "total_registros": c.total_registros,
             "meal_types": [c.meal_type]}
            for c in comidas
        ],
        "progreso_metas": [
            {"fecha": str(m.log_date), "progress": float(m.progress)}
            for m in metas
        ]
    }