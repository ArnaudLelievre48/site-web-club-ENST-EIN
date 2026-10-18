"""Catalogue du club, construit depuis les métadonnées dans static/files."""

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from flask import Flask, abort, render_template, request

app = Flask(__name__)
FILES_DIR = Path(app.static_folder) / "files"
MONTHS = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)
SUPPORTS = (
    ("slides.html", "Voir les slides", False),
    ("slides-pdf.pdf", "PDF", True),
    ("slides.pdf", "PDF", True),
    ("slides.pptx", "PowerPoint", True),
    ("instagram.mp4", "Vidéo de présentation", False),
)


def youtube_video_id(video):
    """Extrait l'identifiant des liens YouTube classiques, courts et intégrés."""
    url = urlsplit(video)
    host = (url.hostname or "").lower()
    parts = url.path.strip("/").split("/")
    video_id = ""
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parts[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"}:
        if parts[0] == "watch":
            video_id = parse_qs(url.query).get("v", [""])[0]
        elif len(parts) == 2 and parts[0] in {"embed", "shorts", "live"}:
            video_id = parts[1]
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        return video_id
    return None


def youtube_thumbnail(video):
    video_id = youtube_video_id(video)
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else None


def load_presentations():
    """Les JSON alimentent la base en mémoire à chaque chargement de page."""
    presentations = []
    for metadata_path in sorted(FILES_DIR.glob("*/*/presentation.json")):
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Les métadonnées doivent être un objet JSON")
            if data.get("published") is not True:
                continue
            for field in ("title", "speaker", "summary"):
                if not isinstance(data.get(field), str) or not data[field].strip():
                    raise ValueError(f"Champ manquant ou invalide : {field}")
            date = datetime.strptime(data["date"], "%d-%m-%Y").date()
            tags = data.get("tags", [])
            if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
                raise ValueError("Les tags doivent être une liste de textes")
            directory = metadata_path.parent
            supports = [
                {
                    "filename": (directory / filename).relative_to(app.static_folder).as_posix(),
                    "label": label,
                    "download": download,
                }
                for filename, label, download in SUPPORTS
                if (directory / filename).is_file()
            ]
            video = data.get("video", "")
            if not isinstance(video, str) or urlsplit(video).scheme not in ("http", "https"):
                video = ""
            description = data.get("description", data["summary"])
            if not isinstance(description, str):
                description = data["summary"]
            video_id = youtube_video_id(video)
            presentations.append({
                "slug": directory.name,
                "title": data["title"], "speaker": data["speaker"],
                "summary": data["summary"], "speaker_year": data.get("annee"),
                "description": description,
                "tags": tags, "video": video, "supports": supports,
                "thumbnail": youtube_thumbnail(video),
                "video_embed": f"https://www.youtube-nocookie.com/embed/{video_id}" if video_id else None,
                "academic_year": directory.parent.name, "date": date,
                "date_label": f"{date.day} {MONTHS[date.month - 1]} {date.year}",
            })
        except (OSError, ValueError, KeyError, TypeError) as exc:
            app.logger.warning("Présentation ignorée (%s) : %s", metadata_path, exc)
    return sorted(presentations, key=lambda presentation: presentation["date"], reverse=True)


@app.get("/")
def home():
    catalogue = load_presentations()
    per_page = 3
    pages = max(1, (len(catalogue) + per_page - 1) // per_page)
    page = min(max(request.args.get("page", 1, type=int), 1), pages)
    start = (page - 1) * per_page
    return render_template(
        "index.html", presentations=catalogue,
        page=page, pages=pages, start=start, end=start + per_page,
    )


@app.get("/presentations/<academic_year>/<slug>")
def presentation_detail(academic_year, slug):
    catalogue = load_presentations()
    for index, presentation in enumerate(catalogue):
        if presentation["academic_year"] == academic_year and presentation["slug"] == slug:
            viewers = [
                support for support in presentation["supports"]
                if support["filename"].endswith((".pdf", ".html"))
            ]
            # Privilégier la version interactive quand elle existe.
            viewers.sort(key=lambda support: not support["filename"].endswith(".html"))
            selected = request.args.get("format", "")
            viewer = next(
                (support for support in viewers if support["filename"].endswith(f".{selected}")),
                viewers[0] if viewers else None,
            )
            return render_template(
                "presentation.html", presentation=presentation,
                viewers=viewers, viewer=viewer, return_page=index // 3 + 1,
            )
    abort(404)


@app.get("/presentations/<academic_year>/<slug>/pdf")
def pdf_viewer(academic_year, slug):
    for presentation in load_presentations():
        if presentation["academic_year"] == academic_year and presentation["slug"] == slug:
            for support in presentation["supports"]:
                if (support["filename"].endswith(".pdf")
                        and support["filename"].rsplit("/", 1)[-1] == request.args.get("filename")):
                    return render_template("pdf_viewer.html", presentation=presentation, pdf=support)
    abort(404)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
