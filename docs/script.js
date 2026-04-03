document.addEventListener('DOMContentLoaded', function () {
    fetch('catalog/catalog.json')
        .then(response => response.json())
        .then(data => {
            const productGrid = document.getElementById('product-grid');
            if (!productGrid) {
                console.error("Product grid not found!");
                return;
            }

            data.items.forEach(item => {
                const cardWrapper = document.createElement('div');
                cardWrapper.className = "bg-white rounded-lg shadow-md overflow-hidden transform hover:scale-105 transition-transform duration-300 ease-in-out flex flex-col h-full";

                const galleryContainer = document.createElement('div');
                galleryContainer.className = 'gallery-container relative';

                item.images.forEach((image, index) => {
                    const slide = document.createElement('div');
                    slide.className = `gallery-slide ${index === 0 ? 'active' : ''}`;
                    const img = document.createElement('img');
                    img.src = `catalog/images/${image}`;
                    img.alt = `${item.title} - Photo ${index + 1}`;
                    img.className = 'w-full h-full object-cover cursor-pointer';
                    slide.appendChild(img);
                    galleryContainer.appendChild(slide);
                });

                if (item.images.length > 1) {
                    const controlsHTML = `
                        <div class="nav-arrow left absolute top-1/2 left-2 cursor-pointer p-2"><svg class="gallery-arrow-svg" width="12" height="20" viewBox="0 0 12 20" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M10 2L3 10L10 18" stroke="white" stroke-width="3" stroke-linecap="round"/></svg></div>
                        <div class="nav-arrow right absolute top-1/2 right-2 cursor-pointer p-2"><svg class="gallery-arrow-svg" width="12" height="20" viewBox="0 0 12 20" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2 2L9 10L2 18" stroke="white" stroke-width="3" stroke-linecap="round"/></svg></div>
                        <div class="dot-indicators absolute bottom-2 left-1/2 -translate-x-1/2 flex space-x-2">${
                            item.images.map((_, index) => `<div class="dot ${index === 0 ? 'active' : ''}" data-slide-index="${index}"></div>`).join('')
                        }</div>
                        <div class="autoplay-progress"><div class="autoplay-progress-bar"></div></div>
                    `;
                    const template = document.createElement('template');
                    template.innerHTML = controlsHTML;
                    galleryContainer.append(...template.content.children);
                }

                const contentDiv = document.createElement('div');
                contentDiv.className = 'p-6 flex flex-col overflow-y-auto';

                const title = document.createElement('h3');
                title.className = 'text-xl font-bold text-dark-navy mb-2';
                title.textContent = item.title;
                contentDiv.appendChild(title);

                const description = document.createElement('p');
                description.className = 'text-slate-blue mb-4 flex-grow';
                description.textContent = item.description;
                contentDiv.appendChild(description);

                const footerDiv = document.createElement('div');
                footerDiv.className = 'flex justify-between items-center flex-shrink-0';

                const price = document.createElement('span');
                price.className = 'text-2xl font-bold text-dark-navy';
                price.textContent = `${item.price} ₽`;
                footerDiv.appendChild(price);

                const button = document.createElement('button');
                button.className = `bg-dark-navy text-white py-2 px-4 rounded-full hover:bg-peach transition-colors duration-300`;
                if (item.status === 'sold') {
                    button.classList.add('opacity-50', 'cursor-not-allowed');
                    button.disabled = true;
                    button.textContent = 'Продано';
                } else {
                    button.textContent = 'Заказать';
                    button.addEventListener('click', () => {
                        const botUsername = 'project_am_muse_bot'; // Actual bot username
                        const payload = `order_${item.id}`;
                        const botDeepLink = `https://t.me/${botUsername}?start=${payload}`;
                        window.open(botDeepLink, '_blank');
                    });
                }
                footerDiv.appendChild(button);
                
                contentDiv.appendChild(footerDiv);

                cardWrapper.appendChild(galleryContainer);
                cardWrapper.appendChild(contentDiv);

                productGrid.appendChild(cardWrapper);
            });
            
            initAllGalleries(); 
        })
        .catch(error => {
            console.error('Ошибка загрузки каталога:', error);
            if (document.getElementById('product-grid')) {
                document.getElementById('product-grid').innerHTML = '<p class="text-center text-red-500">Не удалось загрузить товары.</p>';
            }
        });

    // Adjust header font size on load and resize
    adjustHeaderFontSize();
    window.addEventListener('resize', adjustHeaderFontSize);
});

function initGallery(galleryNode, options = {}) {
    const { isFullscreen = false } = options;
    let currentIndex = 0;
    let autoplayInterval = null;
    let userHasInteracted = false;

    const slides = galleryNode.querySelectorAll('.gallery-slide');
    const dots = galleryNode.querySelectorAll('.dot');
    const leftArrow = galleryNode.querySelector('.nav-arrow.left');
    const rightArrow = galleryNode.querySelector('.nav-arrow.right');

    const openFullscreen = (gallery) => {
        const overlay = document.createElement('div');
        overlay.className = 'fullscreen-overlay';

        const content = document.createElement('div');
        content.className = 'fullscreen-content';
        
        const clonedGallery = gallery.cloneNode(true);
        const newCurrentIndex = gallery === galleryNode ? currentIndex : 0;
        clonedGallery.querySelectorAll('.gallery-slide').forEach((s, i) => s.classList.toggle('active', i === newCurrentIndex));
        clonedGallery.querySelectorAll('.dot').forEach((d, i) => d.classList.toggle('active', i === newCurrentIndex));

        content.appendChild(clonedGallery);
        
        const closeButton = document.createElement('div');
        closeButton.className = 'fullscreen-close-button';
        closeButton.innerHTML = `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18 2L2 18" stroke="white" stroke-width="3" stroke-linecap="round"/><path d="M2 2L18 18" stroke="white" stroke-width="3" stroke-linecap="round"/></svg>`;

        overlay.appendChild(closeButton);
        overlay.appendChild(content);
        document.body.appendChild(overlay);

        initGallery(clonedGallery, { isFullscreen: true });

        const closeFullscreen = () => {
            document.body.removeChild(overlay);
            document.removeEventListener('keydown', onKeydown);
        };
        
        closeButton.addEventListener('click', closeFullscreen);
        const onKeydown = (e) => {
            if (e.key === 'Escape') {
                closeFullscreen();
            } else if (e.key === 'ArrowLeft') {
                const leftArrow = clonedGallery.querySelector('.nav-arrow.left');
                if (leftArrow) leftArrow.click();
            } else if (e.key === 'ArrowRight') {
                const rightArrow = clonedGallery.querySelector('.nav-arrow.right');
                if (rightArrow) rightArrow.click();
            }
        };

        overlay.addEventListener('click', (e) => { if (e.target === overlay) closeFullscreen(); });
        document.addEventListener('keydown', onKeydown);
    };
    
    slides.forEach(slide => {
        slide.querySelector('img').addEventListener('click', () => openFullscreen(galleryNode));
    });

    if (slides.length <= 1) return;

    const showSlide = (index) => {
        slides.forEach((slide, i) => slide.classList.toggle('active', i === index));
        dots.forEach((dot, i) => dot.classList.toggle('active', i === index));
        currentIndex = index;

        if (galleryNode.classList.contains('is-autoplaying')) {
            galleryNode.classList.remove('is-autoplaying');
            void galleryNode.offsetWidth; // Trigger reflow to restart animation
            galleryNode.classList.add('is-autoplaying');
        }
    };

    const startAutoplay = () => {
        if (userHasInteracted) return;
        stopAutoplay();
        galleryNode.classList.add('is-autoplaying');
        autoplayInterval = setInterval(() => {
            const newIndex = (currentIndex + 1) % slides.length;
            showSlide(newIndex);
        }, 6000);
    };

    const stopAutoplay = () => {
        clearInterval(autoplayInterval);
        galleryNode.classList.remove('is-autoplaying');
        autoplayInterval = null;
    };



    const handleInteraction = () => {
        userHasInteracted = true;
        stopAutoplay();
    };

    leftArrow.addEventListener('click', (e) => { e.stopPropagation(); handleInteraction(); showSlide((currentIndex - 1 + slides.length) % slides.length); });
    rightArrow.addEventListener('click', (e) => { e.stopPropagation(); handleInteraction(); showSlide((currentIndex + 1) % slides.length); });
    dots.forEach(dot => dot.addEventListener('click', (e) => { e.stopPropagation(); handleInteraction(); showSlide(parseInt(e.currentTarget.dataset.slide-index)); }));

    if (!isFullscreen) {
        galleryNode.addEventListener('mouseenter', () => {
            if (!userHasInteracted) {
                startAutoplay();
            }
        });
        galleryNode.addEventListener('mouseleave', () => {
            stopAutoplay();
            userHasInteracted = false;
        });
    }
}

function initAllGalleries() {
    document.querySelectorAll('.gallery-container').forEach(gallery => initGallery(gallery));
}

// Helper to measure text width
const measureTextWidth = (text, font) => {
    const canvas = measureTextWidth.canvas || (measureTextWidth.canvas = document.createElement('canvas'));
    const context = canvas.getContext('2d');
    context.font = font;
    const metrics = context.measureText(text);
    return metrics.width;
};

// Function to adjust header font size dynamically
function adjustHeaderFontSize() {
    const leftHeader = document.querySelector('.site-header-text-left');
    const rightHeader = document.querySelector('.site-header-text-right');
    const logo = document.querySelector('header img');
    const headerGrid = document.querySelector('header .grid');

    if (!leftHeader || !rightHeader || !logo || !headerGrid) {
        console.warn("Could not find all header elements for font adjustment.");
        return;
    }

    const MIN_PADDING = 5; // Minimum padding in pixels
    const MAX_FONT_SIZE = 50; // Max font size in pixels, matching original text-5xl

    // Ensure logo has loaded to get accurate width
    if (logo.naturalWidth === 0) {
        logo.onload = adjustHeaderFontSize;
        return;
    }

    const logoWidth = logo.offsetWidth;
    const gridWidth = headerGrid.offsetWidth;

    // Calculate available width for each text element
    // grid is 3 columns. Each text div is 1 column. Logo is 1 column.
    // Assuming equal column distribution, each column is gridWidth / 3.
    // However, Tailwind's grid might not distribute equally if content is too large.
    // Let's calculate based on actual space available for text.
    // The total width for the two text blocks and the logo is `gridWidth`.
    // The logo occupies its `logoWidth`. The remaining width is `gridWidth - logoWidth`.
    // This remaining width is shared by the two text blocks.
    // We also have `pr-4` (padding-right: 1rem = 16px) and `pl-4` (padding-left: 1rem = 16px) on the text divs.
    // And implicit padding of 5px from screen edge.
    // The grid also has `px-4` on the header, meaning 16px padding on each side of the container.
    // So, the actual available width for the *whole grid content* is `gridWidth - (16px * 2)`.

    // A simpler approach: get the bounding client rect of the text containers themselves.
    const leftHeaderRect = leftHeader.getBoundingClientRect();
    const rightHeaderRect = rightHeader.getBoundingClientRect();

    // Calculate max available width for left text (up to logo, minus padding)
    // and for right text (from logo to end, minus padding).
    // The left header has `pr-4` (16px). The right header has `pl-4` (16px).
    // The space between text and logo:
    // Left text right edge + pr-4 to logo left edge - (logo's implicit gap)
    // Let's assume the grid structure implies that the available space for `leftHeader`
    // is `logo.getBoundingClientRect().left - leftHeaderRect.left - MIN_PADDING`.
    // And for `rightHeader` is `rightHeaderRect.right - logo.getBoundingClientRect().right - MIN_PADDING`.
    // This is problematic with `pr-4` and `pl-4` on the text divs themselves.

    // Let's simplify and consider the *total* available horizontal space for the text divs,
    // assuming they are roughly 1/3 of the container each in a 3-column grid.
    // The actual "padding" comes from `pr-4` and `pl-4` and `mx-auto` on the header.

    // A more direct way: the "grid grid-cols-3 items-center" suggests 3 columns.
    // If the logo is in the middle column, and the text divs are in the first and third.
    // We can assume each text div is roughly `(gridWidth - logoWidth) / 2` in ideal scenario.

    // Let's try to get the actual column widths if possible.
    // Or, calculate based on the bounding box of the whole header container.

    const headerContainer = document.querySelector('header.container');
    const headerContainerRect = headerContainer.getBoundingClientRect();

    // Available width for left text: from left edge of headerContainer to left edge of logo, minus MIN_PADDING
    // and minus its own right padding (pr-4 = 16px)
    const availableWidthLeft = logo.getBoundingClientRect().left - headerContainerRect.left - MIN_PADDING - 16;
    // Available width for right text: from right edge of logo to right edge of headerContainer, minus MIN_PADDING
    // and minus its own left padding (pl-4 = 16px)
    const availableWidthRight = headerContainerRect.right - logo.getBoundingClientRect().right - MIN_PADDING - 16;

    let currentFontSize = MAX_FONT_SIZE;
    const step = 1; // Decrement by 1px each time

    // Adjust left header
    let leftText = leftHeader.textContent.trim();
    while (currentFontSize > 10) { // Don't go below a reasonable minimum
        leftHeader.style.fontSize = `${currentFontSize}px`;
        const currentFont = window.getComputedStyle(leftHeader).font;
        const textWidth = measureTextWidth(leftText, currentFont);
        if (textWidth <= availableWidthLeft) {
            break;
        }
        currentFontSize -= step;
    }
    leftHeader.style.fontSize = `${currentFontSize}px`;

    // Adjust right header
    currentFontSize = MAX_FONT_SIZE; // Reset for the right header
    let rightText = rightHeader.textContent.trim();
    while (currentFontSize > 10) {
        rightHeader.style.fontSize = `${currentFontSize}px`;
        const currentFont = window.getComputedStyle(rightHeader).font;
        const textWidth = measureTextWidth(rightText, currentFont);
        if (textWidth <= availableWidthRight) {
            break;
        }
        currentFontSize -= step;
    }
    rightHeader.style.fontSize = `${currentFontSize}px`;
}
