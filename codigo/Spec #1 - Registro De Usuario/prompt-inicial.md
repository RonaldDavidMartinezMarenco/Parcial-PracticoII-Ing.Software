Eres un desarrollador backend experto en FastAPI y MySQL.

A continuación te presento una especificación técnica en formato Markdown.
Léela completa y genera el código de implementación basándote ESTRICTAMENTE
en lo que dice la spec, sin agregar funcionalidades extra ni omitir ningún paso.

---

# SPEC 1: Registro de Usuario

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

## 6. Reglas de negocio
- Las contraseñas nunca deben almacenarse en texto plano ni en logs.
- Las tres inserciones deben ser atómicas. Si una falla, ninguna se persiste.
- El campo `role` se asigna automáticamente como 'user'.

---

Stack obligatorio: FastAPI, SQLAlchemy, Pydantic v2, MySQL, bcrypt, UUID.