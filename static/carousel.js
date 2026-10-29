(() => {
    const wrapper = document.querySelector('.cards-wrapper');
    if (!wrapper) return;
    const track = wrapper.querySelector('.cards');
    const cards = [...track.querySelectorAll('.card')];
    if (!cards.length) return;
    const pages = Number(wrapper.dataset.pages);
    let page = Number(wrapper.dataset.page);
    const desktop = matchMedia('(min-width: 1001px)');
    const viewport = wrapper.querySelector('.cards-viewport');
    const pageStart = () => Math.min((page - 1) * 2, Math.max(0, cards.length - 3));
    const readIndex = () => Math.min(Math.max(0, cards.length - 1), Math.max(0,
        (parseInt(new URL(location.href).searchParams.get('card'), 10) || pageStart() + 1) - 1));
    let activeIndex = readIndex();
    const arrows = ['left', 'right'].map((direction) => {
        const old = wrapper.querySelector(`.move-${direction}`);
        const link = document.createElement('a');
        link.className = old.className.replace(' disabled', '');
        link.textContent = old.textContent;
        link.setAttribute('aria-label', direction === 'left' ? 'Présentations précédentes' : 'Présentations suivantes');
        old.replaceWith(link);
        return link;
    });
    function urlFor(target, index) {
        const url = new URL(window.location.href);
        if (target === 1) url.searchParams.delete('page');
        else url.searchParams.set('page', target);
        if (!desktop.matches) url.searchParams.set('card', index + 1);
        else url.searchParams.delete('card');
        return url;
    }
    function destination(direction) {
        const index = activeIndex + direction;
        const targetPage = desktop.matches ? page + direction : Math.min(pages, Math.floor(index / 2) + 1);
        return { index, page: targetPage, disabled: desktop.matches
            ? targetPage < 1 || targetPage > pages : index < 0 || index >= cards.length };
    }
    function render() {
        const start = desktop.matches ? pageStart() : activeIndex;
        const axis = desktop.matches ? 'offsetLeft' : 'offsetTop';
        const offset = cards.length ? cards[start][axis] - cards[0][axis] : 0;
        if (desktop.matches) {
            viewport.style.height = '';
            track.style.transform = `translateX(-${offset}px)`;
        } else if (cards.length) {
            const peek = 56;
            viewport.style.height = `${cards[start].offsetHeight + 2 * peek}px`;
            track.style.transform = `translateY(${peek - offset}px)`;
        }
        cards.forEach((card, i) => {
            const outside = i < start || i >= start + (desktop.matches ? 3 : 1);
            card.inert = outside;
            card.classList.toggle('carousel-preview', outside);
        });
        arrows.forEach((link, i) => {
            const target = destination(i === 0 ? -1 : 1);
            const disabled = target.disabled;
            link.classList.toggle('disabled', disabled);
            link.setAttribute('aria-disabled', String(disabled));
            link.tabIndex = disabled ? -1 : 0;
            link.href = urlFor(Math.min(pages, Math.max(1, target.page)), Math.min(cards.length - 1, Math.max(0, target.index)));
            link.setAttribute('aria-label', desktop.matches
                ? (i === 0 ? 'Présentations précédentes' : 'Présentations suivantes')
                : (i === 0 ? 'Présentation précédente' : 'Présentation suivante'));
        });
    }
    function move(direction) {
        const next = destination(direction);
        if (next.disabled) return;
        page = next.page;
        activeIndex = desktop.matches ? pageStart() : next.index;
        history.pushState({ page }, '', urlFor(page, activeIndex));
        render();
    }
    arrows.forEach((link, i) => link.addEventListener('click', (event) => {
        event.preventDefault();
        move(i === 0 ? -1 : 1);
    }));
    let touchStart = null;
    let suppressClick = false;
    viewport.addEventListener('touchstart', (event) => {
        suppressClick = false;
        touchStart = !desktop.matches && event.touches.length === 1
            ? { x: event.touches[0].clientX, y: event.touches[0].clientY } : null;
    }, { passive: true });
    viewport.addEventListener('touchend', (event) => {
        if (!touchStart) return;
        const dx = event.changedTouches[0].clientX - touchStart.x;
        const dy = event.changedTouches[0].clientY - touchStart.y;
        touchStart = null;
        if (Math.abs(dy) < 40 || Math.abs(dy) <= Math.abs(dx)) return;
        suppressClick = true;
        move(dy < 0 ? 1 : -1);
    });
    viewport.addEventListener('touchcancel', () => { touchStart = null; });
    viewport.addEventListener('click', (event) => {
        if (!suppressClick) return;
        event.preventDefault();
        suppressClick = false;
    }, true);
    viewport.addEventListener('keydown', (event) => {
        if (desktop.matches || !['ArrowUp', 'ArrowDown'].includes(event.key)) return;
        event.preventDefault();
        move(event.key === 'ArrowUp' ? -1 : 1);
        cards[activeIndex]?.focus({ preventScroll: true });
    });
    window.addEventListener('popstate', () => {
        page = Math.min(pages, Math.max(1, parseInt(new URL(location.href).searchParams.get('page'), 10) || 1));
        activeIndex = readIndex();
        render();
    });
    window.addEventListener('resize', render);
    wrapper.classList.add('carousel-ready');
    render();
    const observer = new ResizeObserver(render);
    cards.forEach((card) => observer.observe(card));
})();
