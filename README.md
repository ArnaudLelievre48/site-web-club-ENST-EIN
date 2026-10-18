# Site web du club ENST'EIN

Club scientifique de l'ENSTA, campus de Brest.

## Lancer le site

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app backend run --debug
```

Ouvrir http://127.0.0.1:5000.

## Ajouter une conférence

Le catalogue Python est chargé depuis les fichiers JSON à chaque requête, sans
serveur de base de données ni étape d'import. Les cartes sont rendues par une
boucle Jinja dans `templates/index.html`. Les flèches passent d'une page à l'autre
(trois présentations par page), sans JavaScript. Jusqu'à 1 000 px de large,
toutes les cartes sont visibles en défilement vertical, sans flèches.
La barre du club est en haut jusqu'au rapport largeur/hauteur 4:3, puis sur
le côté au-delà. En paysage peu haut, ses icônes sont plus petites.

Créer un dossier `static/files/<année-universitaire>/<nom-de-la-conférence>/`
avec un fichier `presentation.json` :

```json
{
  "title": "Titre de la conférence",
  "speaker": "Prénom Nom",
  "annee": 1,
  "date": "30-09-2026",
  "summary": "Une courte présentation du sujet.",
  "description": "Un texte plus détaillé pour la page de la présentation.",
  "tags": ["Maths", "Physique"],
  "video": "",
  "published": true
}
```

`annee` désigne l'année d'études de l'intervenant. L'année universitaire est
déduite du dossier parent. `video` peut contenir une URL HTTP(S) de la conférence.
Pour une vidéo YouTube, sa miniature est affichée directement depuis YouTube
(liens `watch`, `youtu.be`, `embed`, `shorts` et `live`). Sans vidéo YouTube,
l'emplacement conserve le fond uni d'origine.
Les présentations sont triées de la plus récente à la plus ancienne ; seules
celles avec `published: true` sont affichées. Un JSON invalide est ignoré et
signalé dans les logs Flask.

Déposer les supports dans le même dossier : `slides.html`, `slides-pdf.pdf` (ou `slides.pdf`),
`slides.pptx` et/ou `instagram.mp4`. Les liens sont ajoutés automatiquement.
Pour des slides HTML, inclure aussi les éventuelles ressources associées
(polices, images, etc.) à l'emplacement attendu par le document.

Un clic sur une carte ouvre sa page dédiée, avec le texte `description`, les
slides, la vidéo YouTube lorsqu'elle est renseignée et les téléchargements.
Sans `description`, le résumé est utilisé. Séparer les paragraphes par `\n\n`.
La navigation utilise les routes Flask, sans JavaScript.

Le lecteur affiche les PDF et les HTML dans un iframe (HTML par défaut s'il existe).
Les PDF utilisent un petit lecteur PDF.js : chaque slide s'ajuste à la largeur
et à la hauteur disponibles, y compris après rotation de l'écran. Les modules
PDF.js (version 6.4.299) sont chargés depuis jsDelivr ; ils nécessitent une
connexion Internet. Le lien vers le PDF original reste disponible si le lecteur
ne peut pas se charger ou si JavaScript est désactivé.
Avec une vidéo YouTube, les deux lecteurs sont côte à côte sur ordinateur et
empilés sur mobile.
Le navigateur ne lit pas directement les PowerPoint : conserver `slides.pptx`
pour le téléchargement et ajouter un export `slides.pdf` pour le lecteur.
Avec LibreOffice, sous Arch Linux :

```sh
sudo pacman -S --needed libreoffice-fresh
libreoffice --headless --convert-to pdf --outdir static/files/2026-27/coubres-cycloidales static/files/2026-27/coubres-cycloidales/slides.pptx
```

Le PDF apparaît automatiquement au prochain chargement de la page.

Les fichiers dans `static/` sont publics, y compris ceux des présentations
masquées avec `published: false` : ce champ contrôle l'affichage du catalogue.
