// PDF.js dessine les slides à la taille du lecteur, y compris après une rotation.
const source = "https://cdn.jsdelivr.net/npm/pdfjs-dist@6.4.299/";
const canvas = document.querySelector("#canvas");
const container = document.querySelector("#slide");
const previous = document.querySelector("#previous");
const next = document.querySelector("#next");
const counter = document.querySelector("#page-number");
let pdf;
let pageNumber = 1;
let renderTask;
let revision = 0;

function showError() {
    document.querySelector("#error").hidden = false;
    container.setAttribute("aria-busy", "false");
    counter.textContent = "PDF indisponible";
}

async function render() {
    if (!pdf) return;
    const currentRevision = ++revision;
    const pendingTask = renderTask;
    if (pendingTask) {
        pendingTask.cancel();
        try { await pendingTask.promise; } catch (error) {
            if (error.name !== "RenderingCancelledException") throw error;
        }
    }
    const page = await pdf.getPage(pageNumber);
    if (currentRevision !== revision) return;
    const original = page.getViewport({ scale: 1 });
    const scale = Math.min(
        Math.max(1, container.clientWidth - 8) / original.width,
        Math.max(1, container.clientHeight - 8) / original.height,
    );
    const viewport = page.getViewport({ scale });
    const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.ceil(viewport.width * pixelRatio);
    canvas.height = Math.ceil(viewport.height * pixelRatio);
    canvas.style.width = `${viewport.width}px`;
    canvas.style.height = `${viewport.height}px`;
    canvas.setAttribute("aria-label", `Slide ${pageNumber} sur ${pdf.numPages}`);
    counter.textContent = `${pageNumber} / ${pdf.numPages}`;
    previous.disabled = pageNumber === 1;
    next.disabled = pageNumber === pdf.numPages;
    container.setAttribute("aria-busy", "true");
    const task = page.render({
        canvasContext: canvas.getContext("2d"),
        viewport,
        transform: [pixelRatio, 0, 0, pixelRatio, 0, 0],
    });
    renderTask = task;
    try {
        await task.promise;
        if (currentRevision === revision) {
            canvas.dataset.rendered = "true";
            container.setAttribute("aria-busy", "false");
        }
    } catch (error) {
        if (error.name !== "RenderingCancelledException") throw error;
    } finally {
        if (renderTask === task) renderTask = null;
    }
}

previous.addEventListener("click", () => {
    if (pageNumber > 1) { pageNumber--; render().catch(showError); }
});
next.addEventListener("click", () => {
    if (pdf && pageNumber < pdf.numPages) { pageNumber++; render().catch(showError); }
});
new ResizeObserver(() => render().catch(showError)).observe(container);

try {
    const pdfjs = await import(`${source}legacy/build/pdf.mjs`);
    pdfjs.GlobalWorkerOptions.workerSrc = `${source}legacy/build/pdf.worker.mjs`;
    pdf = await pdfjs.getDocument({
        url: document.body.dataset.pdfUrl,
        cMapUrl: `${source}cmaps/`,
        cMapPacked: true,
        standardFontDataUrl: `${source}standard_fonts/`,
        wasmUrl: `${source}wasm/`,
        isEvalSupported: false,
    }).promise;
    await render();
} catch (error) {
    showError();
}
