// API базовый URL
const API_BASE = '../api/v1';
// Текущий пользователь (логин)
let currentUser = null;
// JWT токены
let accessToken = null;
let refreshToken = null;
// Данные приложения
let wallets = [];
let operations = [];

// Функция для генерации UUID для идемпотентности операций
function generateUUID() {
    return crypto.randomUUID();
}

// Функция для получения заголовков авторизации
function getAuthHeaders() {
    if (!accessToken) {
        return {};
    }
    return {
        'Authorization': `Bearer ${accessToken}`
    };
}

// Функция для обновления access токена с помощью refresh токена
async function refreshAccessToken() {
    if (!refreshToken) {
        console.log('[REFRESH] Нет refresh токена');
        return false;
    }

    try {
        console.log('[REFRESH] Отправляем запрос на обновление...');
        const response = await fetch(`${API_BASE}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        console.log(`[REFRESH] Статус: ${response.status}`);
        
        if (response.ok) {
            const data = await response.json();
            console.log('[REFRESH] Токен обновлён:', data);
            accessToken = data.access_token;
            refreshToken = data.refresh_token;
            
            localStorage.setItem('accessToken', accessToken);
            localStorage.setItem('refreshToken', refreshToken);
            
            return true;
        } else {
            console.log('[REFRESH] Не удалось обновить токен');
            return false;
        }
    } catch (e) {
        console.error('[REFRESH] Ошибка:', e);
        return false;
    }
}

// Функция для выполнения запроса с автоматическим обновлением токена
async function fetchWithAuth(url, options = {}) {
    console.log(`[AUTH] Запрос: ${options.method || 'GET'} ${url}`);
    console.log(`[AUTH] Токен есть: ${!!accessToken}, Refresh: ${!!refreshToken}`);
    
    // Добавляем заголовки авторизации
    options.headers = {
        ...options.headers,
        ...getAuthHeaders()
    };

    let response = await fetch(url, options);
    console.log(`[AUTH] Статус ответа: ${response.status}`);

    // Если 401 и есть refresh токен - пробуем обновить
    if (response.status === 401 && refreshToken) {
        console.log('[AUTH] Получен 401, пробуем обновить токен...');
        const refreshed = await refreshAccessToken();
        console.log(`[AUTH] Обновление токена: ${refreshed ? 'успешно' : 'НЕ УДАЛОСЬ'}`);
        
        if (refreshed) {
            // Обновляем заголовки с новым токеном
            options.headers = {
                ...options.headers,
                ...getAuthHeaders()
            };
            // Повторяем запрос
            console.log('[AUTH] Повторяем запрос с новым токеном...');
            response = await fetch(url, options);
            console.log(`[AUTH] Статус после обновления: ${response.status}`);
        }
    }

    return response;
}

// Функция для автологина при загрузке страницы
function tryAutoLogin() {
    const savedAccessToken = localStorage.getItem('accessToken');
    const savedRefreshToken = localStorage.getItem('refreshToken');
    const savedUser = localStorage.getItem('currentUser');

    if (savedAccessToken && savedRefreshToken && savedUser) {
        accessToken = savedAccessToken;
        refreshToken = savedRefreshToken;
        currentUser = savedUser;
        showMainSection();
    }
}

// Автологин при загрузке страницы
window.addEventListener('DOMContentLoaded', () => {
    tryAutoLogin();
});

function showToast(title, message, isError = false) {
    const toastEl = document.getElementById('toastNotification');
    const toastTitle = document.getElementById('toastTitle');
    const toastBody = document.getElementById('toastBody');
    const toastHeader = toastEl.querySelector('.toast-header');
    
    toastTitle.textContent = title;
    toastBody.textContent = message;
    
    // Цвета в зависимости от типа
    if (isError) {
        toastHeader.style.background = 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)';
        toastHeader.style.color = 'white';
    } else {
        toastHeader.style.background = 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)';
        toastHeader.style.color = 'white';
    }
    
    const toast = new bootstrap.Toast(toastEl, {
        autohide: true,
        delay: 3000
    });
    toast.show();
}

function showError(message) {
    showToast('❌ Ошибка', message, true);
}

function showSuccess(message) {
    showToast('✅ Успешно', message, false);
}

function closeModal(modalId) {
    const modalEl = document.getElementById(modalId);
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
}

// Функция регистрации нового пользователя
async function register() {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    
    if (!username) {
        showError('Введите логин');
        return;
    }
    if (!password || password.length < 6) {
        showError('Пароль должен быть не менее 6 символов');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login: username, password: password })
        });

        if (response.ok) {
            showSuccess('Регистрация успешна! Выполняется вход...');
            // После успешной регистрации автоматически входим
            await loginAfterRegister(username, password);
        } else {
            const error = await response.json();
            showError(error.message || error.detail || 'Ошибка регистрации');
        }
    } catch (e) {
        showError('Не удалось подключиться к серверу');
    }
}

// Функция входа в систему
async function login() {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    
    if (!username) {
        showError('Введите логин');
        return;
    }
    if (!password) {
        showError('Введите пароль');
        return;
    }

    // Вызываем общую функцию входа
    await loginAfterRegister(username, password);
}

// Функция для входа с явной передачей логина и пароля
async function loginAfterRegister(username, password) {
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login: username, password: password })
        });

        if (response.ok) {
            const data = await response.json();
            
            // Сохраняем токены и пользователя
            accessToken = data.access_token;
            refreshToken = data.refresh_token;
            currentUser = username;
            
            // Сохраняем в localStorage
            localStorage.setItem('accessToken', accessToken);
            localStorage.setItem('refreshToken', refreshToken);
            localStorage.setItem('currentUser', currentUser);
            
            showSuccess('Вход выполнен успешно!');
            showMainSection();
        } else {
            const error = await response.json();
            showError(error.message || error.detail || 'Неверный логин или пароль');
        }
    } catch (e) {
        showError('Не удалось подключиться к серверу');
    }
}

// Функция выхода из системы
function logout() {
    // Очищаем данные в памяти
    currentUser = null;
    accessToken = null;
    refreshToken = null;
    wallets = [];
    operations = [];
    
    // Очищаем localStorage
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('currentUser');
    
    // Переключаем интерфейс
    document.getElementById('authSection').style.display = 'block';
    document.getElementById('mainSection').style.display = 'none';
    document.getElementById('username').value = '';
    document.getElementById('password').value = '';
    
    showSuccess('Вы вышли из системы');
}

function showMainSection() {
    document.getElementById('authSection').style.display = 'none';
    document.getElementById('mainSection').style.display = 'block';
    document.getElementById('currentUser').textContent = currentUser;
    loadAllData();
}

async function loadAllData() {
    await loadWallets();
    await loadOperations();
    await updateTotalBalance();
    updateWalletSelects();
}

// Функция загрузки списка кошельков
async function loadWallets() {
    try {
        const response = await fetchWithAuth(`${API_BASE}/wallets`);

        if (response.ok) {
            const rawWallets = await response.json();
            // Нормализуем данные от бэкенда: приводим валюту к нижнему регистру, баланс к числу
            wallets = rawWallets.map(w => {
                // Преобразуем баланс в число (обрабатываем строки, Decimal и другие типы)
                let balance = 0;
                if (typeof w.balance === 'number') {
                    balance = w.balance;
                } else if (typeof w.balance === 'string') {
                    balance = parseFloat(w.balance) || 0;
                } else if (w.balance != null) {
                    balance = Number(w.balance) || 0;
                }
                
                return {
                    ...w,
                    currency: String(w.currency || '').toLowerCase(),
                    balance: balance
                };
            });
            renderWalletsTable();
            updateWalletSelects();
            await updateTotalBalance();
        } else if (response.status === 401) {
            console.log('Пользователь не авторизован, кошельков нет');
            wallets = [];
            renderWalletsTable();
            updateWalletSelects();
            await updateTotalBalance();
        } else if (response.status === 404) {
            console.log('Эндпоинт GET /wallets не найден, используем пустой список');
            wallets = [];
            renderWalletsTable();
            updateWalletSelects();
            await updateTotalBalance();
        } else {
            console.error('Ошибка загрузки кошельков:', response.status);
            wallets = [];
            renderWalletsTable();
            updateWalletSelects();
            await updateTotalBalance();
        }
    } catch (e) {
        console.error('Ошибка подключения:', e);
        wallets = [];
        renderWalletsTable();
        updateWalletSelects();
        await updateTotalBalance();
    }
}

// Функция загрузки списка операций
async function loadOperations() {
    try {
        const response = await fetchWithAuth(`${API_BASE}/operations`);

        if (response.ok) {
            const rawOperations = await response.json();
            // Нормализуем данные от бэкенда: приводим валюту к нижнему регистру, сумму к числу
            operations = rawOperations.map(op => {
                // Преобразуем сумму в число (обрабатываем строки, Decimal и другие типы)
                let amount = 0;
                if (typeof op.amount === 'number') {
                    amount = op.amount;
                } else if (typeof op.amount === 'string') {
                    amount = parseFloat(op.amount) || 0;
                } else if (op.amount != null) {
                    amount = Number(op.amount) || 0;
                }
                
                return {
                    ...op,
                    currency: String(op.currency || '').toLowerCase(),
                    amount: amount
                };
            });
            renderOperationsTable();
        } else if (response.status === 401) {
            console.log('Пользователь не авторизован, операций нет');
            operations = [];
            renderOperationsTable();
        }
    } catch (e) {
        console.error('Ошибка загрузки операций', e);
    }
}

function renderWalletsTable() {
    const tbody = document.getElementById('walletsTable');
    
    if (wallets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">У вас пока нет кошельков</td></tr>';
        return;
    }

    const currencySymbols = {
        'rub': '₽',
        'usd': '$',
        'eur': '€'
    };

    tbody.innerHTML = wallets.map(w => {
        // Гарантируем что баланс - число
        const balance = typeof w.balance === 'number' ? w.balance : (parseFloat(w.balance) || 0);
        const currency = String(w.currency || '').toLowerCase();
        const symbol = currencySymbols[currency] || currency.toUpperCase();
        return `
            <tr>
                <td><strong>${w.name}</strong></td>
                <td><span class="badge bg-secondary">${currency.toUpperCase()}</span></td>
                <td class="text-end"><strong>${balance.toFixed(2)} ${symbol}</strong></td>
            </tr>
        `;
    }).join('');
}

function renderOperationsTable() {
    const tbody = document.getElementById('transactionsTable');
    
    if (operations.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Нет транзакций</td></tr>';
        return;
    }

    const last10 = operations.slice(-10).reverse();
    
    tbody.innerHTML = last10.map(t => {
        const wallet = wallets.find(w => w.id === t.wallet_id);
        const walletName = wallet ? wallet.name : 'Неизвестно';
        let typeClass, typeIcon, typeLabel;
        if (t.type === 'income') {
            typeClass = 'text-success';
            typeIcon = '➕';
            typeLabel = 'Доход';
        } else if (t.type === 'expense') {
            typeClass = 'text-danger';
            typeIcon = '➖';
            typeLabel = 'Расход';
        } else if (t.type === 'transfer') {
            typeClass = 'text-info';
            typeIcon = '🔄';
            typeLabel = 'Перевод';
        } else {
            typeClass = 'text-secondary';
            typeIcon = '❓';
            typeLabel = 'Неизвестно';
        }
        const date = new Date(t.created_at).toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        // Гарантируем что сумма - число
        const amount = typeof t.amount === 'number' ? t.amount : (parseFloat(t.amount) || 0);
        const currency = String(t.currency || '').toLowerCase();
        
        return `
            <tr>
                <td>${date}</td>
                <td>${typeIcon} <span class="${typeClass}">${typeLabel}</span></td>
                <td>${walletName}</td>
                <td>${t.category || t.description || '-'}</td>
                <td class="text-end ${typeClass}"><strong>${amount.toFixed(2)} ${currency}</strong></td>
            </tr>
        `;
    }).join('');
}

async function updateTotalBalance() {
    if (wallets.length === 0) {
        document.getElementById('totalBalance').innerHTML = `
            0.00 ₽
            <div class="fs-6 text-muted mt-2">Создайте кошелек для начала</div>
        `;
        return;
    }

    try {
        // Получаем общий баланс в рублях с сервера (с конвертацией валют)
        const response = await fetchWithAuth(`${API_BASE}/balance`);

        if (response.ok) {
            const data = await response.json();
            const total = typeof data.total_balance === 'number' ? data.total_balance : (parseFloat(data.total_balance) || 0);
            document.getElementById('totalBalance').innerHTML = `
                ${total.toFixed(2)} ₽
                <div class="fs-6 text-muted mt-2">Общий баланс по всем кошелькам</div>
            `;
        } else {
            // Если запрос не удался - показываем 0
            document.getElementById('totalBalance').innerHTML = `
                0.00 ₽
                <div class="fs-6 text-muted mt-2">Ошибка загрузки баланса</div>
            `;
        }
    } catch (e) {
        console.error('Ошибка загрузки общего баланса:', e);
        // При ошибке показываем 0
        document.getElementById('totalBalance').innerHTML = `
            0.00 ₽
            <div class="fs-6 text-muted mt-2">Ошибка подключения</div>
        `;
    }
}

function updateWalletSelects() {
    const selects = [
        'incomeWallet', 'expenseWallet', 'transferFrom', 'transferTo'
    ];

    const currencySymbols = {
        'rub': '₽',
        'usd': '$',
        'eur': '€'
    };

    selects.forEach(id => {
        const select = document.getElementById(id);
        if (!select) return;
        
        if (wallets.length === 0) {
            select.innerHTML = '<option value="">Сначала создайте кошелек</option>';
        } else {
            select.innerHTML = wallets.map(w => {
                // Гарантируем что баланс - число
                const balance = typeof w.balance === 'number' ? w.balance : (parseFloat(w.balance) || 0);
                const currency = String(w.currency || '').toLowerCase();
                const symbol = currencySymbols[currency] || currency.toUpperCase();
                return `<option value="${w.id}">${w.name} - ${balance.toFixed(2)} ${symbol}</option>`;
            }).join('');
        }
    });
}

async function addWallet() {
    if (!accessToken) {
        showError('Сначала войдите в систему');
        return;
    }

    const name = document.getElementById('walletName').value.trim();
    const currency = document.getElementById('walletCurrency').value;
    const balance = parseFloat(document.getElementById('walletBalance').value) || 0;

    if (!name) {
        showError('Введите название кошелька');
        return;
    }

    try {
        const response = await fetchWithAuth(`${API_BASE}/wallets`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                name: name, 
                currency: currency, 
                initial_balance: balance 
            })
        });

        console.log('[WALLET] Статус создания:', response.status);

        if (response.ok) {
            showSuccess('Кошелек создан!');
            closeModal('addWalletModal');
            document.getElementById('walletName').value = '';
            document.getElementById('walletBalance').value = '0';
            await loadAllData();
        } else if (response.status === 401) {
            // Пробуем ещё раз обновить токен
            const refreshed = await refreshAccessToken();
            if (refreshed) {
                // Повторяем запрос
                const retryResponse = await fetchWithAuth(`${API_BASE}/wallets`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        name: name, 
                        currency: currency, 
                        initial_balance: balance 
                    })
                });
                
                if (retryResponse.ok) {
                    showSuccess('Кошелек создан!');
                    closeModal('addWalletModal');
                    await loadAllData();
                } else {
                    const error = await retryResponse.json();
                    showError(error.detail || 'Ошибка создания кошелька');
                }
            } else {
                showError('Ошибка авторизации. Войдите снова.');
                // Только здесь вызываем logout
                logout();
            }
        } else {
            const error = await response.json();
            showError(error.detail || 'Ошибка создания кошелька');
        }
    } catch (e) {
        console.error('[WALLET] Ошибка:', e);
        showError('Ошибка подключения');
    }
}

async function addIncome() {
    if (wallets.length === 0) {
        showError('Сначала создайте кошелек');
        return;
    }

    const wallet_id = parseInt(document.getElementById('incomeWallet').value);
    const amount = parseFloat(document.getElementById('incomeAmount').value);
    const description = document.getElementById('incomeDescription').value.trim();

    if (!amount || amount <= 0) {
        showError('Введите корректную сумму');
        return;
    }

    const wallet = wallets.find(w => w.id === wallet_id);
    if (!wallet) {
        showError('Кошелек не найден');
        return;
    }

    try {
        const response = await fetchWithAuth(`${API_BASE}/operations/income`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                transaction_id: generateUUID(),
                wallet_name: wallet.name, 
                amount, 
                description
            })
        });

        if (response.ok) {
            showSuccess('Доход добавлен!');
            closeModal('addIncomeModal');
            document.getElementById('incomeAmount').value = '';
            document.getElementById('incomeDescription').value = '';
            await loadAllData();
        } else {
            const error = await response.json();
            showError(error.message || error.detail || 'Ошибка добавления дохода');
        }
    } catch (e) {
        showError('Ошибка подключения');
    }
}

async function addExpense() {
    if (wallets.length === 0) {
        showError('Сначала создайте кошелек');
        return;
    }

    const wallet_id = parseInt(document.getElementById('expenseWallet').value);
    const amount = parseFloat(document.getElementById('expenseAmount').value);
    const category = document.getElementById('expenseCategory').value.trim();
    const description = document.getElementById('expenseDescription').value.trim();

    if (!amount || amount <= 0) {
        showError('Введите корректную сумму');
        return;
    }

    if (!category) {
        showError('Введите категорию');
        return;
    }

    const wallet = wallets.find(w => w.id === wallet_id);
    if (!wallet) {
        showError('Кошелек не найден');
        return;
    }

    try {
        const response = await fetchWithAuth(`${API_BASE}/operations/expense`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                transaction_id: generateUUID(),
                wallet_name: wallet.name, 
                amount, 
                description 
            })
        });

        if (response.ok) {
            showSuccess('Расход добавлен!');
            closeModal('addExpenseModal');
            document.getElementById('expenseAmount').value = '';
            document.getElementById('expenseCategory').value = '';
            document.getElementById('expenseDescription').value = '';
            await loadAllData();
        } else {
            const error = await response.json();
            showError(error.message || error.detail || 'Ошибка добавления расхода');
        }
    } catch (e) {
        showError('Ошибка подключения');
    }
}

async function transfer() {
    if (wallets.length < 2) {
        showError('Для перевода нужно минимум 2 кошелька');
        return;
    }

    const from_wallet_id = parseInt(document.getElementById('transferFrom').value);
    const to_wallet_id = parseInt(document.getElementById('transferTo').value);
    const amount = parseFloat(document.getElementById('transferAmount').value);

    if (from_wallet_id === to_wallet_id) {
        showError('Нельзя перевести в тот же кошелек');
        return;
    }

    if (!amount || amount <= 0) {
        showError('Введите корректную сумму');
        return;
    }

    try {
        const response = await fetchWithAuth(`${API_BASE}/operations/transfer`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                transaction_id: generateUUID(),
                from_wallet_id, 
                to_wallet_id, 
                amount 
            })
        });

        if (response.ok) {
            showSuccess('Перевод выполнен!');
            closeModal('transferModal');
            document.getElementById('transferAmount').value = '';
            await loadAllData();
        } else {
            const error = await response.json();
            showError(error.message || error.detail || 'Ошибка перевода');
        }
    } catch (e) {
        showError('Ошибка подключения');
    }
}

function initReportDates() {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    
    document.getElementById('reportDateFrom').valueAsDate = firstDay;
    document.getElementById('reportDateTo').valueAsDate = tomorrow;
}

async function loadReport() {
    const dateFrom = document.getElementById('reportDateFrom').value;
    const dateTo = document.getElementById('reportDateTo').value;

    if (!dateFrom || !dateTo) {
        showError('Выберите период');
        return;
    }

    if (dateFrom > dateTo) {
        showError('Дата начала не может быть позже даты окончания');
        return;
    }

    try {
        const params = new URLSearchParams({
            date_from: `${dateFrom}T00:00:00`,
            date_to: `${dateTo}T23:59:59`
        });

        const response = await fetchWithAuth(`${API_BASE}/operations?${params}`);

        if (response.ok) {
            const rawReportOperations = await response.json();
            // Нормализуем данные от бэкенда: приводим валюту к нижнему регистру, сумму к числу
            const reportOperations = rawReportOperations.map(op => {
                // Преобразуем сумму в число (обрабатываем строки, Decimal и другие типы)
                let amount = 0;
                if (typeof op.amount === 'number') {
                    amount = op.amount;
                } else if (typeof op.amount === 'string') {
                    amount = parseFloat(op.amount) || 0;
                } else if (op.amount != null) {
                    amount = Number(op.amount) || 0;
                }
                
                return {
                    ...op,
                    currency: String(op.currency || '').toLowerCase(),
                    amount: amount
                };
            });
            const tbody = document.getElementById('reportTable');
            
            if (reportOperations.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Нет операций за выбранный период</td></tr>';
            } else {
                tbody.innerHTML = reportOperations.reverse().map(t => {
                    const wallet = wallets.find(w => w.id === t.wallet_id);
                    const walletName = wallet ? wallet.name : 'Неизвестно';
                    let typeClass, typeIcon, typeLabel;
                    if (t.type === 'income') {
                        typeClass = 'text-success';
                        typeIcon = '➕';
                        typeLabel = 'Доход';
                    } else if (t.type === 'expense') {
                        typeClass = 'text-danger';
                        typeIcon = '➖';
                        typeLabel = 'Расход';
                    } else if (t.type === 'transfer') {
                        typeClass = 'text-info';
                        typeIcon = '🔄';
                        typeLabel = 'Перевод';
                    } else {
                        typeClass = 'text-secondary';
                        typeIcon = '❓';
                        typeLabel = 'Неизвестно';
                    }
                    const date = new Date(t.created_at).toLocaleString('ru-RU', {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                    
                    const currencySymbols = {
                        'rub': '₽',
                        'usd': '$',
                        'eur': '€'
                    };
                    // Гарантируем что сумма - число
                    const amount = typeof t.amount === 'number' ? t.amount : (parseFloat(t.amount) || 0);
                    const currency = String(t.currency || '').toLowerCase();
                    const symbol = currencySymbols[currency] || currency.toUpperCase();
                    
                    return `
                        <tr>
                            <td>${date}</td>
                            <td>${typeIcon} <span class="${typeClass}">${typeLabel}</span></td>
                            <td>${walletName}</td>
                            <td>${t.category || t.description || '-'}</td>
                            <td class="text-end ${typeClass}"><strong>${amount.toFixed(2)} ${symbol}</strong></td>
                        </tr>
                    `;
                }).join('');
            }

            document.getElementById('reportContent').style.display = 'block';
            showSuccess('Отчет сформирован!');
        } else {
            const error = await response.json();
            showError(error.message || error.detail || 'Ошибка загрузки отчета');
        }
    } catch (e) {
        console.error('Ошибка загрузки отчета:', e);
        showError('Ошибка подключения к серверу');
    }
}