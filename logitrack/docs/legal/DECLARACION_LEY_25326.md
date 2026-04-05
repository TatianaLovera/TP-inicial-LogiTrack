# Declaración de Aplicabilidad: Ley 25.326 (Protección de Datos Personales)

**Proyecto:** LogiTrack - Sistema Federal de Gestión de Logística y Distribución (MVP)
**Versión:** 1.0
**Fecha:** Abril 2026

---

## 1. Introducción
El presente documento detalla la estrategia de cumplimiento normativo adoptada por el equipo de desarrollo de LogiTrack respecto a la Ley Nacional 25.326 de Protección de los Datos Personales de la República Argentina. El sistema ha sido diseñado bajo el paradigma de *Privacy by Design* (Privacidad desde el Diseño), integrando controles técnicos en cada una de sus funcionalidades core.

## 2. Matriz de Cumplimiento (Artículos vs. Implementación)

| Artículo de la Ley 25.326 | Principio Legal | Implementación Técnica en LogiTrack |
| :--- | :--- | :--- |
| **Art. 2 y 7** | Datos Sensibles y Clasificación | El sistema restringe la captura de información exclusivamente a datos logísticos. Se prohíbe explícitamente la recolección de datos sensibles (salud, religión, afiliación) en la **US-01: Alta de Envío**. |
| **Art. 4** | Calidad y Retención de Datos | Implementación de la **Task-09: Script de disociación de datos para envíos finalizados**. Se anonimizan datos personales tras 30 días de la entrega (sobrescribiendo nombre y DNI), conservando solo zonas logísticas para IA. |
| **Art. 5 y 6** | Consentimiento e Información | Mediante la **Task-11: Implementar checkbox de consentimiento y términos de privacidad**, el formulario de Alta incluye un checkbox obligatorio para asegurar el deber de información sobre el uso logístico de los datos. |
| **Art. 9** | Seguridad de los Datos | Se implementa la ofuscación en la interfaz visual mediante la **US-30: Enmascaramiento de datos personales en listados** y un registro inmutable preventivo en la **US-06: Auditoría de Edición**. |
| **Art. 10** | Deber de Confidencialidad | El sistema utiliza perfiles estructurados en la **US-08: Roles simulados** y la **US-03: Detalle de envío con Acceso Segmentado**, asegurando que roles como el Operador o Transportista solo vean la información estrictamente pertinente a su función. |

## 3. Garantía de Derechos ARCO
LogiTrack facilita el ejercicio de los derechos de Acceso, Rectificación, Cancelación y Oposición mediante las siguientes funciones:

* **Acceso (Art. 14):** Todo titular puede verificar su información a través de la búsqueda exacta en la **US-04** y la vista de la **US-03: Detalle de envío con Acceso Segmentado**.
* **Rectificación (Art. 16):** Errores en la carga de datos son subsanados mediante la **US-26: Edición de datos del envío**, garantizando la actualización del registro original en la base de datos.
* **Supresión (Art. 16):** La baja lógica de los datos se garantiza al finalizar el ciclo de vida del paquete mediante la automatización de la **Task-09**.

## 4. Inteligencia Artificial y Ética de Datos
En cumplimiento con el principio de transparencia, se informa que la **US-23: Clasificación automática de prioridad (ML)** utiliza exclusivamente variables logísticas disociadas (distancia, horarios, peso, tipo de envío). No se procesan datos sensibles del remitente ni del destinatario para evitar cualquier tipo de sesgo algorítmico o discriminación automatizada.

## 5. Conclusión
El equipo de LogiTrack certifica que el tratamiento de la información dentro del MVP se ajusta a los estándares de licitud y seguridad exigidos por la Dirección Nacional de Protección de Datos Personales, asegurando un entorno confiable para la gestión logística federal.