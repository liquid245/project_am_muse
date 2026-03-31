document.addEventListener('DOMContentLoaded', function () {
    fetch('../catalog/catalog.json')
        .then(response => response.json())
        .then(data => {
            const productGrid = document.getElementById('product-grid');
            data.items.forEach(item => {
                const card = `
                    <div class="bg-white rounded-lg shadow-md overflow-hidden transform hover:scale-105 transition-transform duration-300 ease-in-out">
                        <img src="../catalog/images/${item.images[0]}" alt="${item.title}" class="w-full h-64 object-cover">
                        <div class="p-6">
                            <h3 class="text-xl font-bold text-dark-navy mb-2">${item.title}</h3>
                            <p class="text-slate-blue mb-4">${item.description}</p>
                            <div class="flex justify-between items-center">
                                <span class="text-2xl font-bold text-dark-navy">${item.price} ₽</span>
                                <button
                                    class="bg-dark-navy text-white py-2 px-4 rounded-full hover:bg-peach transition-colors duration-300 ${item.status === 'sold' ? 'opacity-50 cursor-not-allowed' : ''}"
                                    ${item.status === 'sold' ? 'disabled' : ''}
                                >
                                    ${item.status === 'available' ? 'Заказать' : item.status === 'sold' ? 'Продано' : 'Заказать'}
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                productGrid.innerHTML += card;
            });
        })
        .catch(error => {
            console.error('Ошибка загрузки каталога:', error);
            const productGrid = document.getElementById('product-grid');
            productGrid.innerHTML = '<p class="text-center text-red-500">Не удалось загрузить товары. Пожалуйста, попробуйте еще раз позже.</p>';
        });
});
