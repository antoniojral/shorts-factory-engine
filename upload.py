def main():
    import logging
    logging.basicConfig(level=logging.INFO)

    video_path = os.environ.get("SHORT_VIDEO_PATH", "output/final_short.mp4")
    titulo = os.environ.get("YOUTUBE_VIDEO_TITLE", "Cmo salir de deudas rpido #shorts")
    descripcion = os.environ.get(
        "YOUTUBE_VIDEO_DESCRIPTION",
        "Aprende finanzas personales para principiantes y cmo organizar tu dinero en Mxico y LatAm.\n\n"
        "Descarga la gua gratuita de presupuesto en el link del perfil.\n\n"
        "#shorts #finanzaspersonales #dinero #educacionfinanciera"
    )
    tags_str = os.environ.get("YOUTUBE_VIDEO_TAGS", "")
    default_tags = ["finanzas personales", "finanzas para principiantes", "ahorrar dinero", "finanzas mexico", "educacion financiera"]
    tags = tags_str.split(",") if tags_str else default_tags

    if not video_path or not os.path.exists(video_path):
        print(f"Error: No se encuentra el video en {video_path}")
        return

    try:
        video_id = subir_a_youtube(video_path, titulo, descripcion, tags)
        print(f"Video subido exitosamente con ID: {video_id}")
    except SystemExit as e:
        print(f"Error crtico: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()