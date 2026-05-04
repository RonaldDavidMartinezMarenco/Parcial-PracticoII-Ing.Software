# SPEC 3: Transcripción y Extracción de Datos por IA desde Notas de Voz

## Historia de Usuario (HU06)
"Como usuario, quiero enviar notas de voz mediante WhatsApp para registrar 
información de forma rápida y sencilla".

## Requerimiento Funcional (RF09)
"El sistema debe procesar la información recibida mediante IA para extraer datos 
relevantes sobre salud y dieta cuando llegue un mensaje por WhatsApp".

## 1. Nombre de la funcionalidad
Transcripción y Extracción de Datos por IA desde Notas de Voz.

## 2. Descripción
Cuando el webhook recibe un mensaje de tipo 'audio', el sistema descarga el archivo 
usando el media_id, lo transcribe con Whisper, y pasa el texto resultante a un LLM 
para extraer entidades estructuradas. Los datos se persisten en `habits_logs` + 
`habit_extracted_data` o en `emotional_logs` + `emotional_triggers`. Todo el proceso 
queda trazado en `ai_message_logs` y `message_tool_calls`.

## 3. Entradas

| Campo             | Tipo         | Validación                                                                 |
|-------------------|--------------|----------------------------------------------------------------------------|
| audio_url         | String (URL) | Obligatorio. Debe retornar HTTP 200 y mime-type audio/ogg.                 |
| media_id          | String       | Obligatorio. Formato de identificador único de la API de WhatsApp.         |
| numero_remitente  | String       | Obligatorio. Debe existir en `user_whatsapp` para obtener el user_id.      |

## 4. Proceso

1. Recibir el evento del webhook identificando type = 'audio'.
2. Responder HTTP 200 OK a Meta inmediatamente.
3. Validar que el `numero_remitente` exista en `user_whatsapp`. Si no, detener.
4. Buscar o crear registro activo en `ai_conversations` para ese usuario.
5. Descargar el archivo de audio usando el `media_id` y token de WhatsApp Business API.
6. Enviar el archivo a Whisper para transcripción.
   Registrar en `message_tool_calls`:
   - tool_name = 'whisper_transcription'
   - input_data = { media_id }
   - output_data = { texto_transcrito }
7. Insertar el texto transcrito en `ai_message_logs` con role = 'user'.
8. Enviar el texto al LLM con el siguiente prompt de sistema:
   "Extrae de este texto los alimentos consumidos con su tipo de comida, 
   y el estado de ánimo con su intensidad del 1 al 10. Responde en JSON estructurado."
   Registrar en `message_tool_calls` con tool_name = 'llm_extraction'.
9. Insertar la respuesta del LLM en `ai_message_logs` con role = 'assistant',
   incluyendo model, tokens_used y response_time_ms.
10. Parsear el JSON de respuesta del LLM:
    - Alimentos → insertar en `habits_logs` + `habit_extracted_data`.
    - Emoción → insertar en `emotional_logs` + `emotional_triggers`.
11. Eliminar el archivo de audio del servidor inmediatamente tras la transcripción.
12. Enviar confirmación al usuario: "Registré que comiste [X] y te sientes [Y]".

## 5. Salidas esperadas

- **Éxito:** Audio transcrito, datos guardados, mensaje de confirmación al usuario.
- **Audio incomprensible:** "No pude entender el audio, ¿puedes escribirlo?".
- **Timeout Whisper:** "Hubo un problema procesando tu audio, intenta de nuevo".
- **Confianza LLM insuficiente:** Mensaje pidiendo confirmación antes de guardar.

## 6. Reglas de negocio

- Los archivos de audio deben eliminarse del servidor tras la transcripción.
- Si el LLM no supera el 80% de confianza, pedir confirmación antes de persistir.
- Toda llamada externa (Whisper, LLM) debe registrarse en `message_tool_calls`.
- El campo `intensity` en `emotional_logs` debe ser un entero entre 1 y 10.

## 7. Casos límite

- Audio con mucho ruido de fondo que genera transcripción sin sentido.
- Audio de más de 2 minutos que causa timeout en Whisper.
- LLM responde con texto libre en lugar de JSON estructurado.
- Usuario menciona alimentos en otro idioma que el LLM no reconoce correctamente.