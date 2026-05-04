# SPEC 4: API de Datos Estadísticos para el Dashboard

## Historia de Usuario (HU07)
"Como usuario, quiero visualizar un dashboard con mis datos para analizar 
mi progreso de manera clara".

## Requerimiento Funcional (RF24)
"El sistema debe mostrar gráficos interactivos de hábitos alimenticios y estado 
emocional dentro del dashboard web, actualizados con los últimos datos".

## 1. Nombre de la funcionalidad
API de Datos Estadísticos para el Dashboard.

## 2. Descripción
Endpoint protegido por JWT que consulta `habits_logs`, `emotional_logs` y 
`goal_progress` del usuario autenticado para un rango de días configurable. 
Retorna los datos agrupados por fecha en formato JSON consumible por Recharts 
en el frontend React.

## 3. Entradas

| Campo      | Tipo    | Validación                                                                      |
|------------|---------|---------------------------------------------------------------------------------|
| user_id    | UUID    | Obligatorio. Extraído exclusivamente del token JWT. Nunca desde el body.        |
| rango_dias | Entero  | Opcional. Default: 7. Valores permitidos: 7, 14 o 30. Otro valor → HTTP 400.   |

## 4. Proceso

1. Validar el token JWT. Si es inválido o expirado → HTTP 401.
2. Extraer el `user_id` del payload del token.
3. Validar que `rango_dias` sea 7, 14 o 30. Si no se envía, usar 7 por defecto.
4. Calcular fecha_inicio = fecha_actual - rango_dias.
5. Consultar `emotional_logs`: promediar `intensity` agrupado por `log_date`
   filtrando por `user_id` y el rango calculado.
6. Consultar `habits_logs`: contar registros por `log_date` agrupando por `meal_type`
   para el mismo rango y `user_id`.
7. Consultar `goal_progress`: obtener `progress` por `log_date` para metas activas
   del usuario.
8. Para cada fecha del rango sin datos → insertar valor null o 0
   (mantener continuidad del eje X).
9. Formatear los tres conjuntos en arrays de objetos { fecha, valor }.
10. Retornar HTTP 200 con el JSON consolidado.

## 5. Salidas esperadas

- **HTTP 200 OK:**
```json
{
  "emociones_historico": [{ "fecha": "2025-05-01", "promedio_intensidad": 7 }],
  "resumen_comidas": [{ "fecha": "2025-05-01", "total_registros": 3, 
                        "meal_types": ["breakfast", "lunch"] }],
  "progreso_metas": [{ "fecha": "2025-05-01", "progress": 65.50 }]
}
```
- **HTTP 401 Unauthorized:** Token inválido o expirado.
- **HTTP 400 Bad Request:** Valor de rango_dias no permitido.
- **Sin datos:** HTTP 200 con arrays vacíos, nunca HTTP 500.

## 6. Reglas de negocio

- El `user_id` debe extraerse exclusivamente del token JWT, nunca del body.
- Días sin datos deben retornar 0 o null, nunca omitirse del array.
- El endpoint es de solo lectura, no puede modificar ningún dato.
- Las consultas SQL deben filtrar siempre por `user_id` como condición primaria.

## 7. Casos límite

- Usuario nuevo sin ningún registro → retornar arrays vacíos, no HTTP 500.
- `rango_dias` enviado como string "7" en lugar de entero.
- Cambios de zona horaria que alteren el agrupamiento por `log_date`.
- Token JWT que expira exactamente durante la ejecución de la consulta.
