#!/usr/bin/env python3
"""Sube un video a YouTube usando la API v3."""

import os
import json
import time
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Alcances para YouTube Upload
YOUTUBE_UPLOAD_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


def get_youtube_service():
    """Crea un servicio de YouTube usando las credenciales del entorno."""
    # Intentar obtener refresh token del entorno
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    if refresh_token:
        # Usar refresh token directamente
        credentials = Credentials(
            None,  # No hay token de acceso inicial
            refresh_token=refresh_token,
            client_options={"client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
                            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", "")},
            token_uri="https://oauth2.googleapis.com/token",
            scopes=YOUTUBE_UPLOAD_SCOPES,
        )
        # Solicitar token de acceso
        credentials.refresh(None)
        return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)

    # Fallback: flujo de OAuth interactivo
    logger = __import__("logging").getLogger(__name__)
    logger.info("Iniciando flujo OAuth interactivo...")
    flow = InstalledAppFlow.from_client_secrets_file(
        os.environ.get("GOOGLE_OAUTH_CLIENT_SECRETS", "client_secret.json"),
        YOUTUBE_UPLOAD_SCOPES,
    )
    credentials = flow.run_local_server(port=0)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)


def subir_a_youtube(video_path, titulo, descripcion, tags=None):
    """Sube un video a YouTube.

    Args:
        video_path: Ruta al archivo de video
        titulo: Título del video
        descripcion: Descripción del video
        tags: Lista de tags (opcional)

    Returns:
        ID del video subido
    """
    try:
        youtube = get_youtube_service()

        body = {
            "snippet": {
                "title": titulo,
                "description": descripcion,
                "tags": tags or [],
                "categoryId": "27",  # Categoría: Educación
            },
            "status": {
                "privacyStatus": "private",  # Cambiar a "public" o "unlisted" después
            },
        }

        # Ejecutar la llamada a la API
        response = youtube.videos().insert(part="snippet,status", body=body).execute()

        video_id = response.get("id")
        logger = __import__("logging").getLogger(__name__)
        logger.info(f"Video subido exitosamente! ID: {video_id}")

        # Esperar un momento y cambiar a público si fue privado
        if os.environ.get("YOUTUBE_PRIVATE_INITIAL", "true").lower() != "false":
            time.sleep(2)
            # Actualizar el status a público
            youtube.videos().update(
                part="status",
                body={
                    "id": video_id,
                    "status": {"privacyStatus": "public"},
                },
            ).execute()
            logger.info("Video cambiado a público")

        return video_id

    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.error(f"Error subiendo a YouTube: {e}")
        raise


def main():
    """Función principal de upload."""
    import logging
    logging.basicConfig(level=logging.INFO)

    video_path = os.environ.get("SHORT_VIDEO_PATH", "")
    titulo = os.environ.get("YOUTUBE_VIDEO_TITLE", "Shorts Factory - Video Automatizado")
    descripcion = os.environ.get("YOUTUBE_VIDEO_DESCRIPTION", "")
    tags_str = os.environ.get("YOUTUBE_VIDEO_TAGS", "")

    if not video_path or not os.path.exists(video_path):
        print(f"Error: No se encuentra el video en {video_path}")
        return

    tags = tags_str.split(",") if tags_str else None

    try:
        video_id = subir_a_youtube(video_path, titulo, descripcion, tags)
        print(f"✓ Video subido a YouTube con ID: {video_id}")
    except Exception as e:
        print(f"✗ Error al subir video: {e}")


if __name__ == "__main__":
    main()