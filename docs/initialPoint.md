# 📋 Especificaciones Técnicas: Captura de Datos y Formulario de Registro

## 1. Visión General del Producto
Este módulo representa el primer punto de conversión digital para una empresa de trayectoria tradicional. El objetivo es capturar leads cualificados mediante una experiencia de usuario (UX) impecable, profesional y altamente accesible.

---

## 2. Definición del Formulario (register.html)

### A. Campos Requeridos
| Campo | Tipo | Validación | Razón de Negocio |
| :--- | :--- | :--- | :--- |
| **Nombre Completo** | `text` | Mínimo 3 caracteres | Identificación personal del cliente. |
| **Correo Electrónico** | `email` | Formato RFC 5322 | Canal principal de contacto y seguimiento. |
| **Interés Principal** | `select` | Selección obligatoria | Segmentación de leads para el equipo de ventas. |
| **Mensaje Adicional** | `textarea` | Opcional | Espacio para necesidades específicas del cliente. |
| **Términos y Privacidad** | `checkbox` | Obligatorio (Checked) | Cumplimiento legal (GDPR/Privacidad). |

### B. Lógica de Validación (JavaScript Vanilla)
Para cumplir con la "Experiencia Pulida" solicitada por el Manager, el script debe:
1. **Interceptar el evento `submit`**: Evitar el envío por defecto para procesar la validación.
2. **Validación de Vacío**: Verificar que ningún campo obligatorio esté en blanco.
3. **Regex de Email**: Validar que la estructura del correo sea real (ej. `nombre@empresa.com`).
4. **Feedback Visual**: 
   - Cambiar bordes de inputs a `border-red-500` si hay error.
   - Mostrar mensajes de error dinámicos debajo de cada campo.
   - Limpiar errores cuando el usuario vuelva a escribir.

---

## 3. Requisitos Técnicos y Buenas Prácticas

### 🏗️ Maquetación con Tailwind CSS v4
- **Layout:** Contenedor centrado (`max-w-lg`) con diseño tipo "Card" sobre fondo neutro.
- **Botones:** Estados de `hover` y `active` claramente diferenciados.
- **Responsive:** Adaptación total a pantallas de smartphone (ancho completo) y escritorio (ancho fijo).

### ♿ Accesibilidad (A11y) - Estándar WCAG
- **Labels Reales:** Uso de etiquetas `<label for="...">` para cada input (no usar solo placeholders).
- **Semántica:** Atributos `aria-required="true"` en campos obligatorios.
- **Alertas:** Mensajes de error con `role="alert"` para que los lectores de pantalla los anuncien de inmediato.

### 🔍 Optimización SEO (Schema.org)
Implementación de un bloque de datos estructurados en el `<head>` para que Google indexe la página como una sección de contacto/registro de la organización:
```json
{
  "@context": "[https://schema.org](https://schema.org)",
  "@type": "ContactPage",
  "name": "Formulario de Aplicación Digital",
  "description": "Punto de contacto oficial para nuevos clientes e interesados."
}