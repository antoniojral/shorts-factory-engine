#!/usr/bin/env python3
"""Motor principal de la fábrica de YouTube Shorts."""

import json
import os
import random
import asyncio
import logging
from pathlib import Path

from google import genai
from google.genai import types
import edge_tts
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, ColorClip

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CONFIG = {
    "model": "gemini-1.5-flash",
    "voice": "es-MX-JorgeNeural",
    "video_width": 1080,
    "video_height": 1920,
    "video_fps": 30,
    "gu_duration_target": 50,
}


async def generar_voz(guion, archivo_salida):
    """Genera archivo de audio usando edge-tts con voz es-MX-JorgeNeural."""
    try:
        communicate = edge_tts.Communicate(guion, CONFIG["voice"], rate="+0%", volume="+0%")
        async with communicate.save(archivo_salida) as f:
            logger.info(f"Audio generado: {archivo_salida}")
        return True
    except Exception as e:
        logger.error(f"Error al generar voz: {e}")
        return False


def descargar_videos_pexels(cantidad=3):
    """Descarga videos de Pexels con relacion 9:16."""
    videos = []
    query = "finance business money hands"

    try:
        url = "https://api.pexels.com/v1/search"
        headers = {
            "Authorization": os.environ.get("PEXELS_API_KEY", ""),
        }
        params = {
            "query": query,
            "orientation": "portrait",
            "per_page": cantidad,
        }

        respuesta = requests.get(url, headers=headers, params=params, timeout=15)

        if respuesta.status_code != 200:
            logger.warning(f"Error Pexels API: {respuesta.status_code}")
            return []

        datos = respuesta.json()
        fotos = datos.get("photos", [])

        for i, foto in enumerate(fotos):
            video_url = foto.get("video_files", [{}])[0].get("link", "")
            if video_url:
                video_resp = requests.get(video_url, timeout=30)
                if video_resp.status_code == 200:
                    nombre_archivo = INPUT_DIR / f"pexel_{i+1}.mp4"
                    with open(nombre_archivo, "wb") as f:
                        f.write(video_resp.content)
                    videos.append(str(nombre_archivo))
                    logger.info(f"Video {i+1} descargado: {nombre_archivo}")

        return videos

    except Exception as e:
        logger.error(f"Error descargando videos Pexels: {e}")
        return False


def main():
    logger.info("=== Iniciando Fábrica de YouTube Shorts ===")

    # Cargar temas
    temas = cargar_temas()
    if not temas:
        logger.error("No se pudieron cargar los temas de topics.json")
        return

    # Seleccionar tema aleatorio
    tema = random.choice(temas)
    logger.info(f"Tema seleccionado: {tema}")

    # Inicializar cliente Gemini
    try:
        cliente_gemini = genai.Client()
    except Exception as e:
        logger.error(f"Error inicializando Gemini client: {e}")
        return

    # Generar guion
    guion = generar_guion(tema, cliente_gemini)

    # Generar archivo de audio temporal
    audio_temp = INPUT_DIR / "guion_audio.mp3"

    # Ejecutar edge-tts async
    try:
        asyncio.run(generar_voz(guion, str(audio_temp)))
    except Exception as e:
        logger.error(f"Error en edge-tts: {e}")
        return

    # Descargar videos de Pexels
    videos_p = descargar_videos_pexels(cantidad=3)

    # Ensamblar video final
    output_path = OUTPUT_DIR / "final_short.mp4"

    # Crear video con moviepy
    try:
        # Cargar audio
        audio_clip = AudioFileClip(str(audio_temp))
        duracion_audio = audio_clip.duration

        # Si tenemos videos de Pexels
        if videos_p and len(videos_p) > 0:
            clips_video = []
            duracion_por_video = duracion_audio / len(videos_p)

            for i, video_path in enumerate(videos_p):
                try:
                    clip = VideoFileClip(video_path)
                    segmento_duracion = min(clip.duration, duracion_por_video * (i + 1) - duracion_por_video * i)
                    clip = clip.set_duration(segmento_duracion)

                    # Si el video no es 9:16, recortarlo
                    if clip.w / clip.h != 1080 / 1920:
                        clip = clip.resized(new_size=(1080, 1920))

                    clips_video.append(clip)
                except Exception as e:
                    logger.warning(f"Error procesando video {video_path}: {e}")
                    # Crear fondo para este segmento
                    fondo = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=segmento_duracion)
                    clips_video.append(fondo)

            # Asegurar que tengamos el número correcto de clips
            while len(clips_video) < len(videos_p):
                fondo = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=duracion_audio / len(videos_p))
                clips_video.append(fondo)

            # Concatenar clips
            if clips_video:
                video_final = concatenate_videoclips(clips_video, method="compose")
            else:
                video_final = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=duracion_audio)
        else:
            # Sin videos de Pexels, usar fondo negro
            video_final = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=duracion_audio)

        # Poner audio al video
        if audio_clip:
            video_final = video_final.set_audio(audio_clip)

        # Exportar
        video_final.write_videofile(
            str(output_path),
            fps=CONFIG["video_fps"],
            codec="libx264",
            audio_codec="aac",
            verbose=False,
            logger=None
        )

        logger.info(f"Video final guardado: {output_path}")

        # Mostrar duración
        import subprocess
        try:
            result = subprocess.run(
                ["ffprobe", "-i", str(output_path), "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"],
                capture_output=True, text=True, timeout=10
            )
            duracion = result.stdout.strip()
            logger.info(f"Duración del video: {duracion} segundos")
        except Exception:
            logger.info("Video creado exitosamente")

        # Cerrar clips
        audio_clip.close()
        video_final.close()

    except Exception as e:
        logger.error(f"Error ensamblando video final: {e}")

    logger.info("=== Proceso completado ===")


if __name__ == "__main__":
    main()