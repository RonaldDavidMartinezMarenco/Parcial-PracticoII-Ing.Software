# SPEC 1: Registro de Usuario

## Historia de Usuario (HU01)
"Como usuario, quiero registrarme en el sistema para poder acceder a sus funcionalidades".

## Requerimiento Funcional (RF01)
"El sistema debe almacenar los datos de la cuenta en la base de datos MySQL cuando se 
complete el formulario de registro con todos los campos válidos".

## 1. Nombre de la funcionalidad
Registro de nuevo usuario en el sistema Sloth-Health.

## 2. Descripción
Proceso mediante el cual un usuario nuevo ingresa su información básica en un formulario 
para crear una cuenta en Sloth-Health. El sistema valida la información y la persiste de 
forma segura en MySQL realizando tres inserciones atómicas: en `users`, `user_whatsapp` 
y `user_settings`.

## 3. Entradas

| Campo               | Tipo   | Validación                                                                 |
|---------------------|--------|----------------------------------------------------------------------------|
| nombre_completo     | String | Obligatorio. Mínimo 3, máximo 100 caracteres. Solo letras y espacios.      |
| correo_electronico  | String | Obligatorio. Formato válido usuario@dominio.com. Único en `users`.         |
| contraseña          | String | Obligatorio. Mínimo 8 caracteres, al menos una mayúscula y un número.      |
| telefono_whatsapp   | String | Obligatorio. Código de país incluido, entre 10 y 15 dígitos. Único en `user_whatsapp`. |

## 4. Proceso

1. Recibir los datos del formulario de registro vía HTTP POST.
2. Aplicar trim() a todos los campos para eliminar espacios invisibles.
3. Validar estructuralmente cada campo según las reglas de la tabla de entradas. 
   Si falla alguna, detener y retornar HTTP 400.
4. Consultar en `users` si el `correo_electronico` ya existe. 
   Si hay duplicidad, retornar HTTP 409.
5. Consultar en `user_whatsapp` si el `telefono_whatsapp` ya existe. 
   Si hay duplicidad, retornar HTTP 409.
6. Aplicar hash bcrypt a la contraseña.
7. Iniciar transacción atómica en MySQL:
   - Insertar en `users`: id (UUID), name, email, password (hash), role = 'user'.
   - Insertar en `user_whatsapp`: id (UUID), user_id (FK), phone_number.
   - Insertar en `user_settings`: id (UUID), user_id (FK), notifications = TRUE, language = 'es'.
8. Si cualquier inserción falla, ejecutar rollback completo.
9. Retornar HTTP 201 con el user_id generado.

## 5. Salidas esperadas

- **HTTP 201 Created:**
```json
{ "message": "Usuario registrado exitosamente", "user_id": "<uuid>" }
```
- **HTTP 400 Bad Request:** Error de validación con detalle del campo inválido.
- **HTTP 409 Conflict:** Correo o teléfono duplicado con mensaje específico.
- **HTTP 500 Internal Server Error:** Fallo en la transacción de base de datos.

## 6. Reglas de negocio

- Las contraseñas nunca deben almacenarse en texto plano ni en logs.
- Un usuario no puede tener más de una cuenta con el mismo correo o teléfono WhatsApp.
- Las tres inserciones (users, user_whatsapp, user_settings) deben ser atómicas.
- El campo `role` se asigna automáticamente como 'user' en el registro público.

## 7. Casos límite

- Espacios invisibles al inicio o final del correo que burlen la validación de duplicidad.
- Caída de conexión con MySQL durante la transacción (timeout entre inserciones).
- Intento de inyección SQL en los campos nombre_completo o correo_electronico.
- Doble clic en el botón de registro que genere dos requests simultáneos con los mismos datos.