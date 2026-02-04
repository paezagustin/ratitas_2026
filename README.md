# ratitas_2026

# 🔬 Segmentación de WSIs - Ratitas 2026
Proyecto de Doctorado enfocado en la detección y segmentación de estructuras en imágenes histológicas de alta resolución (Whole Slide Images) utilizando YOLO.

---



## 📦 Gestión de Datos (DVC + Google Drive)

Este proyecto utiliza **DVC (Data Version Control)** para gestionar los archivos pesados (WSIs y parches) que no pueden subirse a GitHub. Los datos reales se almacenan en una carpeta privada de Google Drive.

### 🔹 Configuración de Credenciales (Solo la primera vez)
Si es la primera vez que clonas el repo en una máquina nueva o si necesitas reconfigurar tus llaves de acceso de Google Cloud:

```bash
# Vincular tus credenciales propias para evitar bloqueos de Google
dvc remote modify storage_google gdrive_client_id "828635734834-gfml8p7h41ocfb6ce8va2ns58d3nnlqk.apps.googleusercontent.com"
dvc remote modify storage_google gdrive_client_secret "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"

# Autenticarse (Sigue el link que aparecerá en consola)
dvc push
```
---

# Flujo de trabajo diario

| Acción | Comando |
| :--- | :--- |
| **Descargar datos** (al clonar en otra PC) | `dvc pull` |
| **Registrar cambios** (si agregas imágenes/parches) | `dvc add data` |
| **Subir a la nube** | `dvc push` |
| **Sincronizar puntero** (enviar a GitHub) | `git add data.dvc && git commit -m "Update data" && git push` |
| **Verificar estado** | `dvc status` |



# Imágenes que se descartaron para entrenamiento

- 7,8,16,18,19,25,28,29,32,34,35,41,45,47,48

Debido a que son 2 o más placentas y no están todas etiquetadas.