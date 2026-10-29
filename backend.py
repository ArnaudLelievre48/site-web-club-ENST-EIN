"""Catalogue du club, construit depuis les métadonnées dans static/files."""

import json
import os
import re
import subprocess
import unicodedata
from tempfile import TemporaryDirectory
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit
from xml.etree import ElementTree

from flask import Flask, abort, make_response, render_template, request, url_for

app = Flask(__name__)
app.config["SITE_URL"] = os.environ.get("SITE_URL", "")
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
    ("slides.tex", "Code LaTeX de la présentation", False),
    ("sources.zip", "Ensemble de fichiers source de la présentation", False),
)


DOWNLOAD_EXTENSIONS = {
    ".pdf", ".ppt", ".pptx", ".odp", ".html", ".mp4", ".webm", ".zip",
    ".txt", ".csv", ".ipynb", ".py", ".doc", ".docx", ".odt", ".xls", ".xlsx", ".ods",
}


def public_url(path):
    """Construit une URL absolue à partir de l'adresse publique configurée."""
    base = app.config["SITE_URL"] or request.url_root
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


@app.get("/robots.txt")
def robots():
    return app.response_class(
        f"User-agent: *\nAllow: /\n\nSitemap: {public_url(url_for('sitemap'))}\n",
        mimetype="text/plain",
    )


@app.get("/sitemap.xml")
def sitemap():
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ElementTree.register_namespace("", namespace)
    root = ElementTree.Element(f"{{{namespace}}}urlset")
    paths = [url_for("home")]
    paths.extend(
        url_for("presentation_detail", academic_year=presentation["academic_year"],
                slug=presentation["slug"])
        for presentation in load_presentations()
    )
    for path in paths:
        entry = ElementTree.SubElement(root, f"{{{namespace}}}url")
        ElementTree.SubElement(entry, f"{{{namespace}}}loc").text = public_url(path)
    return app.response_class(
        ElementTree.tostring(root, encoding="utf-8", xml_declaration=True),
        mimetype="application/xml",
    )


def search_text(value):
    return "".join(character for character in unicodedata.normalize("NFKD", value.casefold())
                   if not unicodedata.combining(character))


def downloadable_files(catalogue, query):
    """Liste les supports et documents annexes des présentations publiées."""
    terms = search_text(query).split()
    files = []
    for presentation in catalogue:
        directory = FILES_DIR / presentation["academic_year"] / presentation["slug"]
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.name.startswith(".") or path.suffix.lower() not in DOWNLOAD_EXTENSIONS:
                continue
            searchable = search_text(" ".join([
                path.name, presentation["title"], presentation["speaker"],
                presentation["academic_year"], *presentation["tags"],
            ]))
            if all(term in searchable for term in terms):
                files.append({
                    "name": path.name,
                    "filename": path.relative_to(app.static_folder).as_posix(),
                    "format": path.suffix[1:].upper(),
                    "presentation": presentation,
                })
    return files


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


def pdf_thumbnail(directory):
    """Génère et met en cache la première page du PDF quand nécessaire."""
    pdf = next((directory / name for name in ("slides.pdf", "slides-pdf.pdf")
                if (directory / name).is_file()), None)
    if pdf is None:
        return None
    thumbnail = pdf.with_name(f"{pdf.stem}-thumbnail.png")
    try:
        if not thumbnail.is_file() or thumbnail.stat().st_mtime_ns < pdf.stat().st_mtime_ns:
            # Publier uniquement une image complète, même avec plusieurs workers.
            with TemporaryDirectory(prefix=".thumbnail-", dir=directory) as temporary:
                output = Path(temporary) / "first-slide"
                subprocess.run(
                    ["pdftoppm", "-f", "1", "-singlefile", "-scale-to", "960",
                     "-png", str(pdf), str(output)],
                    check=True, timeout=30, capture_output=True,
                )
                output.with_suffix(".png").replace(thumbnail)
        return url_for(
            "static", filename=thumbnail.relative_to(app.static_folder).as_posix(),
            v=thumbnail.stat().st_mtime_ns,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        app.logger.warning("Miniature PDF indisponible (%s) : %s", pdf, exc)
        return None


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
                "thumbnail": youtube_thumbnail(video) or pdf_thumbnail(directory),
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
    pages = max(1, (max(0, len(catalogue) - per_page) + 1) // 2 + 1)
    page = min(max(request.args.get("page", 1, type=int), 1), pages)
    start = min((page - 1) * 2, max(0, len(catalogue) - per_page))
    query = request.args.get("q", "").strip()[:200]
    template = "_download_list.html" if request.headers.get("HX-Request") == "true" else "index.html"
    response = make_response(render_template(
        template, presentations=catalogue,
        page=page, pages=pages, start=start, end=start + per_page,
        files=downloadable_files(catalogue, query), query=query,
    ))
    response.vary.add("HX-Request")
    return response


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
