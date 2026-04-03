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
                cardWrapper.className = "bg-white rounded-lg shadow-md overflow-hidden transform hover:scale-105 transition-transform duration-300 ease-in-out";

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
    dots.forEach(dot => dot.addEventListener('click', (e) => { e.stopPropagation(); handleInteraction(); showSlide(parseInt(e.currentTarget.dataset.slideIndex)); }));

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
