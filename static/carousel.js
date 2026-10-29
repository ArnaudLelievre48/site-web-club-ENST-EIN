(() => {
    const wrapper = document.querySelector('.cards-wrapper');
    if (!wrapper) return;
    const track = wrapper.querySelector('.cards');
    const cards = [...track.querySelectorAll('.card')];
    const pages = Number(wrapper.dataset.pages);
    let page = Number(wrapper.dataset.page);
    const desktop = matchMedia('(min-width: 1001px)');
    const arrows = ['left', 'right'].map((direction) => {
        const old = wrapper.querySelector(`.move-${direction}`);
        const link = document.createElement('a');
        link.className = old.className.replace(' disabled', '');
        link.textContent = old.textContent;
        link.setAttribute('aria-label', direction === 'left' ? 'Présentations précédentes' : 'Présentations suivantes');
        old.replaceWith(link);
        return link;
    });
    function urlFor(target) {
        const url = new URL(window.location.href);
        if (target === 1) url.searchParams.delete('page');
        else url.searchParams.set('page', target);
        return url;
    }
    function render() {
        const start = Math.min((page - 1) * 2, Math.max(0, cards.length - 3));
        const offset = cards.length && start ? cards[start].offsetLeft - cards[0].offsetLeft : 0;
        track.style.transform = desktop.matches ? `translateX(-${offset}px)` : '';
        cards.forEach((card, i) => {
            const outside = desktop.matches && (i < start || i >= start + 3);
            card.inert = outside;
            card.classList.toggle('carousel-preview', outside);
        });
        arrows.forEach((link, i) => {
            const target = page + (i === 0 ? -1 : 1);
            const disabled = target < 1 || target > pages;
            link.classList.toggle('disabled', disabled);
            link.setAttribute('aria-disabled', String(disabled));
            link.tabIndex = disabled ? -1 : 0;
            link.href = urlFor(Math.min(pages, Math.max(1, target)));
        });
    }
    arrows.forEach((link, i) => link.addEventListener('click', (event) => {
        event.preventDefault();
        const next = page + (i === 0 ? -1 : 1);
        if (next < 1 || next > pages) return;
        page = next;
        history.pushState({ page }, '', urlFor(page));
        render();
    }));
    window.addEventListener('popstate', () => {
        page = Math.min(pages, Math.max(1, parseInt(new URL(location.href).searchParams.get('page'), 10) || 1));
        render();
    });
    window.addEventListener('resize', render);
    wrapper.classList.add('carousel-ready');
    render();
})();
