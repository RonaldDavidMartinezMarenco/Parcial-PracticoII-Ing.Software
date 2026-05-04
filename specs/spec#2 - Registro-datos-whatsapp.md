# SPEC 2: Registro de Datos vía WhatsApp (Texto)

## Historia de Usuario (HU04)
"Como usuario, quiero registrar mis datos a través de WhatsApp para facilitar 
el ingreso de información diaria".

## Requerimiento Funcional (RF08)
"El sistema debe registrar los datos de hábitos alimenticios y estado emocional 
en la base de datos MySQL cuando reciba un mensaje del usuario por WhatsApp".

## 1. Nombre de la funcionalidad
Recepción y Registro de Mensajes de Texto por WhatsApp.

## 2. Descripción
Un webhook recibe los mensajes de texto enviados por los usuarios a través de la API 
de WhatsApp Business. El sistema identifica al usuario por su número de teléfono, 
registra el mensaje en `ai_message_logs`, clasifica el intent en `conversation_intents`, 
y según la clasificación persiste el dato en `habits_logs` o `emotional_logs` con sus 
respectivas tablas de detalle.

## 3. Entradas

| Campo              | Tipo           | Validación                                                                 |
|--------------------|----------------|----------------------------------------------------------------------------|
| numero_remitente   | String         | Obligatorio. Código de país incluido. Debe existir en `user_whatsapp`.     |
| cuerpo_mensaje     | String         | Obligatorio. Máximo 1000 caracteres. No puede estar vacío ni solo espacios.|
| timestamp_mensaje  | Entero (Unix)  | Obligatorio. No puede ser una marca de tiempo futura.                      |

## 4. Proceso

1. Recibir el payload HTTP POST desde el webhook de WhatsApp Business API.
2. Responder inmediatamente con HTTP 200 OK a Meta (procesamiento asíncrono).
3. Extraer el `numero_remitente` y buscar en `user_whatsapp` para obtener el `user_id`.
   Si no existe, enviar mensaje "No estás registrado en el sistema" y detener.
4. Buscar o crear un registro activo en `ai_conversations` para ese `user_id`.
5. Insertar el mensaje en `ai_message_logs` con role = 'user'.
6. Clasificar el intent del `cuerpo_mensaje`:
   - Referencias emocionales → intent = 'emotional_log'
   - Referencias alimenticias → intent = 'food_log'
   - Ambiguo → intent = 'unknown'
7. Insertar en `conversation_intents` con el intent detectado y confidence.
8. Según el intent:
   - **food_log:** Insertar en `habits_logs` → detalles en `habit_extracted_data`.
   - **emotional_log:** Insertar en `emotional_logs` → disparadores en `emotional_triggers`.
   - **unknown:** Enviar mensaje pidiendo clarificación al usuario.
9. Enviar mensaje de confirmación al usuario con el resumen del registro guardado.

## 5. Salidas esperadas

- **Éxito comida:** Registro en `habits_logs` + `habit_extracted_data`.
  Mensaje al usuario: "Registré tu comida: [descripción]".
- **Éxito emoción:** Registro en `emotional_logs` + `emotional_triggers`.
  Mensaje al usuario: "Registré que te sientes [emoción] con intensidad [valor]".
- **Intent desconocido:** Mensaje al usuario pidiendo que reformule.
- **Usuario no registrado:** Mensaje informando que debe registrarse en la plataforma web.

## 6. Reglas de negocio

- El webhook debe responder HTTP 200 a Meta en menos de 3 segundos.
- No se puede registrar más de un estado emocional por usuario por día.
  Si ya existe, preguntar al usuario si desea sobreescribir.
- El campo `intensity` en `emotional_logs` debe ser un entero entre 1 y 10.
- Todo mensaje recibido debe registrarse en `ai_message_logs` independientemente 
  de si se pudo clasificar.

## 7. Casos límite

- El usuario envía un mensaje vacío o solo con emojis no reconocibles.
- Mensaje híbrido: "Me siento un 6 y comí arroz con pollo" 
  (debe generar dos registros simultáneos).
- El webhook recibe el mismo mensaje duplicado por reenvío de Meta 
  (validar idempotencia por timestamp + numero_remitente).