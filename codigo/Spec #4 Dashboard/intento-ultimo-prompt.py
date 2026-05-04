# routers/dashboard.py
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from auth import get_current_user
from models import EmotionalLog, HabitsLog, GoalProgress, Goal
from datetime import date, timedelta
from collections import defaultdict

router = APIRouter()

def generate_date_range(fecha_inicio: date, fecha_fin: date) -> list:
    delta = (fecha_fin - fecha_inicio).days
    return [str(fecha_inicio + timedelta(days=i)) for i in range(delta + 1)]


@router.get("/api/dashboard/stats", status_code=200)
def get_dashboard_stats(
    rango_dias: int = Query(default=7),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Castear y validar rango_dias
    try:
        rango_dias = int(rango_dias)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="rango_dias debe ser un entero")

    if rango_dias not in [7, 14, 30]:
        raise HTTPException(status_code=400, detail="rango_dias debe ser 7, 14 o 30")

    user_id = current_user["user_id"]
    fecha_fin = date.today()
    fecha_inicio = fecha_fin - timedelta(days=rango_dias)
    fechas_rango = generate_date_range(fecha_inicio, fecha_fin)

    # --- Consulta 1: emociones ---
    emociones_raw = db.query(
        EmotionalLog.log_date,
        func.avg(EmotionalLog.intensity).label("promedio_intensidad")
    ).filter(
        EmotionalLog.user_id == user_id,
        EmotionalLog.log_date >= fecha_inicio,
        EmotionalLog.log_date <= fecha_fin
    ).group_by(EmotionalLog.log_date).all()

    emociones_map = {
        str(e.log_date): round(float(e.promedio_intensidad), 1)
        for e in emociones_raw
    }

    emociones_historico = [
        {
            "fecha": fecha,
            "promedio_intensidad": emociones_map.get(fecha, None)
        }
        for fecha in fechas_rango
    ]

    # --- Consulta 2: comidas agrupadas por fecha ---
    comidas_raw = db.query(
        HabitsLog.log_date,
        HabitsLog.meal_type,
        func.count(HabitsLog.id).label("count")
    ).filter(
        HabitsLog.user_id == user_id,
        HabitsLog.log_date >= fecha_inicio,
        HabitsLog.log_date <= fecha_fin
    ).group_by(HabitsLog.log_date, HabitsLog.meal_type).all()

    comidas_map = defaultdict(lambda: {"total_registros": 0, "meal_types": []})
    for c in comidas_raw:
        fecha_str = str(c.log_date)
        comidas_map[fecha_str]["total_registros"] += c.count
        comidas_map[fecha_str]["meal_types"].append(c.meal_type)

    resumen_comidas = [
        {
            "fecha": fecha,
            "total_registros": comidas_map[fecha]["total_registros"] if fecha in comidas_map else 0,
            "meal_types": comidas_map[fecha]["meal_types"] if fecha in comidas_map else []
        }
        for fecha in fechas_rango
    ]

    # --- Consulta 3: progreso de metas (con JOIN para filtrar por user_id) ---
    metas_raw = db.query(
        GoalProgress.log_date,
        GoalProgress.progress
    ).join(
        Goal, GoalProgress.goal_id == Goal.id
    ).filter(
        Goal.user_id == user_id,
        GoalProgress.log_date >= fecha_inicio,
        GoalProgress.log_date <= fecha_fin
    ).all()

    metas_map = {str(m.log_date): float(m.progress) for m in metas_raw}

    progreso_metas = [
        {
            "fecha": fecha,
            "progress": metas_map.get(fecha, None)
        }
        for fecha in fechas_rango
    ]

    return {
        "emociones_historico": emociones_historico,
        "resumen_comidas": resumen_comidas,
        "progreso_metas": progreso_metas
    }