Eres un desarrollador backend experto en FastAPI y MySQL.

A continuación te presento una especificación técnica en formato Markdown.
Léela completa y genera el código de implementación basándote ESTRICTAMENTE
en lo que dice la spec, sin agregar funcionalidades extra ni omitir ningún paso.

---

# SPEC 5: Generación Automatizada de Recomendaciones con IA

## Historia de Usuario (HU09)
"Como usuario, quiero recibir recomendaciones personalizadas para mejorar
mi bienestar físico y emocional".

## Requerimiento Funcional (RF21)
"El sistema debe generar recomendaciones de recetas personalizadas cuando
analice los hábitos históricos del usuario".

## 1. Nombre de la funcionalidad
Generación Automatizada de Recomendaciones Nutricionales y de Bienestar con IA.

## 2. Descripción
El sistema consulta `habits_logs` y `emotional_logs` del usuario autenticado para
construir un contexto dinámico que se envía como prompt a un LLM. La recomendación
generada se persiste en `recommendations` con `source = 'AI'` y se retorna al frontend.
Todo queda trazado en `ai_message_logs` y `message_tool_calls`.

## 3. Entradas

| Campo               | Tipo   | Validación                                                               |
|---------------------|--------|--------------------------------------------------------------------------|
| user_id             | UUID   | Obligatorio. Validado contra el token JWT. Nunca desde el body.          |
| historial_comidas   | Array  | Construido desde `habits_logs`. Mínimo 1 registro requerido.             |
| estado_animo_actual | Entero | Construido desde `emotional_logs`. Valor entre 1 y 10 (campo intensity). |

## 4. Proceso
1. Validar el token JWT. Si es inválido → HTTP 401.
2. Extraer el `user_id` del token.
3. Consultar `habits_logs`: últimos 7 registros ordenados por `log_date` DESC.
4. Consultar `emotional_logs`: registro más reciente del usuario
   (campos `emotion` e `intensity`).
5. Si no hay registros en `habits_logs` → HTTP 400:
   "Necesitas registrar al menos una comida para recibir recomendaciones".
6. Construir prompt dinámico inyectando:
   - Lista de alimentos consumidos
   - Tipos de comida (meal_type)
   - Último estado emocional con su intensidad
7. Enviar prompt al LLM. Registrar en `message_tool_calls`:
   - tool_name = 'llm_recommendation'
   - input_data = { prompt }
   - output_data = { respuesta }
8. Insertar respuesta del LLM en `ai_message_logs`:
   - role = 'assistant'
   - tokens_used, response_time_ms
9. Validar que la respuesta contenga contenido de nutrición o bienestar.
   Si no → HTTP 502 sin persistir.
10. Insertar en `recommendations`:
    - user_id, source = 'AI', content = texto de la recomendación.
11. Retornar HTTP 200 con el contenido.

## 5. Salidas esperadas

- **HTTP 200 OK:**
{ "message": "Recomendación generada", "content": "<texto de la recomendación>" }
- **HTTP 400 Bad Request:** Sin historial suficiente.
- **HTTP 401 Unauthorized:** Token inválido.
- **HTTP 502 Bad Gateway:** LLM no responde o alucinación detectada.

## 6. Reglas de negocio
- `recommendations.source` siempre debe ser 'AI' para recomendaciones automáticas.
- La llamada al LLM debe tener un timeout máximo configurado.
- El `user_id` nunca debe aceptarse desde el body, solo desde el JWT.
- Si se detecta alucinación, no persistir la recomendación y retornar HTTP 502.

## 7. Casos límite
- Cold start: usuario sin registros en `habits_logs` → HTTP 400 sin llamar al LLM.
- Alucinación: LLM responde con contenido irrelevante → no persistir, HTTP 502.
- Alimentos con caracteres sin sentido en `habits_logs` que confunden el prompt.
- LLM responde correctamente pero supera el timeout configurado → HTTP 502.

---

Stack obligatorio: FastAPI, SQLAlchemy, PyJWT, OpenAI Python SDK, MySQL.