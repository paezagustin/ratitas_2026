# Reglas de código para el asistente

## Formato de salida
- **SIEMPRE** generar código en formato Jupyter Notebook (.ipynb)
- **NUNCA** ejecutar código automáticamente
- Proporcionar el código en bloques de código markdown o como archivo .ipynb descargable

## Estructura del notebook
1. Celdas Markdown para explicaciones
2. Celdas de código con comentarios claros
3. Instrucciones de instalación de dependencias si es necesario

## Prohibiciones
- NO ejecutar código en el entorno del asistente
- NO hacer llamadas a APIs externas automáticamente
- NO crear, modificar o eliminar archivos del sistema automáticamente

## Formato de respuesta
Cuando se pida código:
1. Explicar el enfoque en texto
2. Proporcionar el notebook completo
3. Incluir instrucciones para que el usuario lo ejecute localmente