// API базовый URL
const API_BASE_V1 = '../api/v1';
const API_BASE_V2 = '../api/v2';
// Текущий пользователь (логин)
let currentUser = null;
let currentUserId = null;
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
        const response = await fetch(`${API_BASE_V1}/auth/refresh`, {
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
    const savedUserId = localStorage.getItem('currentUserId');

    if (savedAccessToken && savedRefreshToken && savedUser) {
        accessToken = savedAccessToken;
        refreshToken = savedRefreshToken;
        currentUser = savedUser;
        currentUserId = savedUserId ? parseInt(savedUserId) : null;
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
        const response = await fetch(`${API_BASE_V1}/users`, {
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
        const response = await fetch(`${API_BASE_V1}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login: username, password: password })
        });

        if (response.ok) {
            const data = await response.json();
            console.log('Ответ API при входе:', data);
            
            // Сохраняем токены и пользователя
            accessToken = data.access_token;
            refreshToken = data.refresh_token;
            currentUser = username;
            currentUserId = data.user_id;
            
            // Сохраняем в localStorage
            localStorage.setItem('accessToken', accessToken);
            localStorage.setItem('refreshToken', refreshToken);
            localStorage.setItem('currentUser', currentUser);
            localStorage.setItem('currentUserId', currentUserId);
            
            showSuccess('Вход выполнен успешно');
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
    currentUserId = null;
    accessToken = null;
    refreshToken = null;
    wallets = [];
    operations = [];
    
    // Очищаем localStorage
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('currentUser');
    localStorage.removeItem('currentUserId');
    
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
    console.log('[LOAD] Начало загрузки данных...');
    
    try {
        // Загружаем кошельки
        await loadWallets();
        console.log('[LOAD] Кошельки загружены');
        
        // Загружаем операции
        await loadOperations();
        console.log('[LOAD] Операции загружены');
        
        // Обновляем общий баланс
        await updateTotalBalance();
        console.log('[LOAD] Баланс обновлен');
        
        // Обновляем селекты
        updateWalletSelects();
        console.log('[LOAD] Селекты обновлены');
        
    } catch (e) {
        console.error('[LOAD] Ошибка загрузки данных:', e);
        
        // При ошибке все равно показываем интерфейс
        wallets = [];
        operations = [];
        renderWalletsTable();
        renderOperationsTable();
        updateWalletSelects();
        await updateTotalBalance();
    }
}

async function loadWallets() {
    try {
        const response = await fetchWithAuth(`${API_BASE_V1}/wallets`);

        if (response.ok) {
            const rawWallets = await response.json();
            wallets = rawWallets.map(w => {
                let balance = 0;
                if (typeof w.balance === 'number') {
                    balance = w.balance;
                } else if (typeof w.balance === 'string') {
                    balance = parseFloat(w.balance) || 0;
                } else if (w.balance != null) {
                    balance = Number(w.balance) || 0;
                }
                
                let creditLimit = null;
                if (w.credit_limit != null) {
                    if (typeof w.credit_limit === 'number') {
                        creditLimit = w.credit_limit;
                    } else if (typeof w.credit_limit === 'string') {
                        creditLimit = parseFloat(w.credit_limit) || 0;
                    } else {
                        creditLimit = Number(w.credit_limit) || 0;
                    }
                }
                
                return {
                    ...w,
                    currency: String(w.currency || '').toLowerCase(),
                    balance: balance,
                    wallet_type: w.wallet_type || 'debit',
                    credit_limit: creditLimit
                };
            });
            renderWalletsTable();
            updateWalletSelects();
        } else if (response.status === 401) {
            wallets = [];
            renderWalletsTable();
            updateWalletSelects();
        } else {
            wallets = [];
            renderWalletsTable();
            updateWalletSelects();
        }
    } catch (e) {
        console.error('Ошибка загрузки кошельков:', e);
        wallets = [];
        renderWalletsTable();
        updateWalletSelects();
    }
}

// Функция загрузки списка операций
async function loadOperations() {
    try {
        const response = await fetchWithAuth(`${API_BASE_V1}/operations`);

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
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">У вас пока нет кошельков</td></tr>';
        return;
    }

    const currencySymbols = {
        'rub': '₽',
        'usd': '$',
        'eur': '€'
    };

    tbody.innerHTML = wallets.map(w => {
        const balance = typeof w.balance === 'number' ? w.balance : (parseFloat(w.balance) || 0);
        const currency = String(w.currency || '').toLowerCase();
        const symbol = currencySymbols[currency] || currency.toUpperCase();
        
        const walletType = w.type || w.wallet_type || 'debit';
        const isCredit = walletType === 'credit';
        
        const creditLimit = isCredit 
            ? (typeof w.credit_limit === 'number' ? w.credit_limit : (parseFloat(w.credit_limit) || 0))
            : null;
        
        // Определяем жирность для баланса
        const balanceFontWeight = balance === 0 ? '' : 'fw-bold';
        
        return `
            <tr>
                <td>${w.name}</td>
                <td><span class="badge bg-secondary">${currency.toUpperCase()}</span></td>
                <td>
                    ${isCredit 
                        ? '<span class="badge bg-warning text-dark">Кредитный</span>' 
                        : '<span class="badge bg-success">Дебетовый</span>'}
                </td>
                <td class="text-end">
                    ${isCredit 
                        ? `<strong>${creditLimit.toFixed(2)} ${symbol}</strong>` 
                        : '<span class="text-muted">—</span>'}
                </td>
                <td class="text-end ${balanceFontWeight}">${balance.toFixed(2)} ${symbol}</td>
            </tr>
        `;
    }).join('');
}

function renderOperationsTable() {
    const tbody = document.getElementById('transactionsTable');
    
    if (operations.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Нет операций</td></tr>';
        return;
    }

    const last10 = operations.slice(-10).reverse();
    
    tbody.innerHTML = last10.map(t => {
        const wallet = wallets.find(w => w.id === t.wallet_id);
        const walletName = wallet ? wallet.name : 'Неизвестно';
        let typeClass, typeIcon, typeLabel;
        if (t.type === 'income') {
            typeClass = 'text-success';
            typeIcon = '';
            typeLabel = 'Доход';
        } else if (t.type === 'expense') {
            typeClass = 'text-danger';
            typeIcon = '';
            typeLabel = 'Расход';
        } else if (t.type === 'transfer') {
            typeClass = 'text-info';
            typeIcon = '';
            typeLabel = 'Перевод';
        } else {
            typeClass = 'text-secondary';
            typeIcon = '';
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
                <td class="text-end ${typeClass}"><strong>${formatCurrency(amount)}</strong></td>
            </tr>
        `;
    }).join('');
}

async function updateTotalBalance() {
    if (wallets.length === 0) {
        document.getElementById('totalBalance').innerHTML = `
            0,00 ₽
            <div class="fs-6 text-muted mt-2">Создайте кошелек для начала</div>
        `;
        return;
    }

    try {
        // Получаем общий баланс в рублях с сервера (с конвертацией валют)
        const response = await fetchWithAuth(`${API_BASE_V1}/balance`);

        if (response.ok) {
            const data = await response.json();
            const total = typeof data.total_balance === 'number' ? data.total_balance : (parseFloat(data.total_balance) || 0);
            document.getElementById('totalBalance').innerHTML = `
                ${formatCurrency(total)}
                <div class="fs-6 text-muted mt-2">Ваш баланс по всем кошелькам</div>
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
                return `<option value="${w.id}">${w.name} - ${formatCurrency(balance)}</option>`;
            }).join('');
        }
    });
}

// Вспомогательная функция для извлечения сообщения об ошибке
function extractErrorMessage(data, defaultMessage = 'Произошла ошибка') {
    if (!data) return defaultMessage;
    
    console.log('[ERROR] Формат ошибки:', data); // Для отладки
    
    // FastAPI HTTPException обычно возвращает {"detail": "сообщение"}
    if (data.detail) {
        if (typeof data.detail === 'string') {
            return data.detail;
        }
        
        // Для ошибок валидации Pydantic (массив ошибок)
        if (Array.isArray(data.detail)) {
            const errors = data.detail.map(err => {
                if (err.msg) return err.msg;
                if (err.message) return err.message;
                return JSON.stringify(err);
            });
            return errors.join(', ');
        }
        
        // Если detail - объект
        if (typeof data.detail === 'object') {
            // Проверяем различные поля в объекте
            if (data.detail.message) return data.detail.message;
            if (data.detail.error) return data.detail.error;
            if (data.detail.msg) return data.detail.msg;
            return JSON.stringify(data.detail);
        }
    }
    
    // Проверяем другие возможные поля
    if (data.message) return data.message;
    if (data.error) return data.error;
    
    return defaultMessage;
}

async function addWallet() {
    if (!accessToken) {
        showError('Сначала войдите в систему');
        return;
    }

    const name = document.getElementById('walletName').value.trim();
    const currency = document.getElementById('walletCurrency').value || 'RUB';
    const balance = parseFloat(document.getElementById('walletBalance').value) || 0;
    const walletType = document.getElementById('walletType').value;
    const creditLimit = walletType === 'credit' 
        ? (parseFloat(document.getElementById('walletCreditLimit').value) || 0)
        : null;

    // Проверяем только пустое поле названия
    if (!name) {
        showError('Введите название кошелька');
        return;
    }

    const walletData = {
        name: name, 
        currency: currency, 
        initial_balance: balance,
        type: walletType
    };
    
    if (walletType === 'credit') {
        walletData.credit_limit = creditLimit;
    }

    try {
        const response = await fetchWithAuth(`${API_BASE_V1}/wallets`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(walletData)
        });

        console.log('[WALLET] Статус создания:', response.status);

        // Пытаемся распарсить JSON
        let data;
        try {
            data = await response.json();
        } catch (parseError) {
            // Если не удалось распарсить JSON
            console.error('[WALLET] Не удалось распарсить ответ:', parseError);
            data = null;
        }
        
        if (response.ok) {
            showSuccess('Кошелек успешно создан');
            closeModal('addWalletModal');
            document.getElementById('walletName').value = '';
            document.getElementById('walletBalance').value = '0';
            document.getElementById('walletType').value = 'debit';
            document.getElementById('walletCreditLimit').value = '0';
            document.getElementById('creditLimitField').style.display = 'none';
            await loadAllData();
        } else {
            // Подробное логирование для отладки
            console.error('[WALLET] Ошибка от сервера:', {
                status: response.status,
                statusText: response.statusText,
                data: data
            });
            
            // Показываем ошибку от бэкенда
            const errorMessage = extractErrorMessage(data, 'Ошибка создания кошелька');
            showError(errorMessage);
        }
    } catch (e) {
        console.error('[WALLET] Ошибка:', e);
        showError('Ошибка подключения: ' + e.message);
    }
}

async function addIncome() {
    if (!accessToken) {
        showError('Сначала войдите в систему');
        return;
    }

    if (wallets.length === 0) {
        showError('Сначала создайте кошелек');
        return;
    }

    const wallet_id = parseInt(document.getElementById('incomeWallet').value);
    const amount = document.getElementById('incomeAmount').value;
    const description = document.getElementById('incomeDescription').value.trim();

    if (!amount || parseFloat(amount) <= 0) {
        showError('Введите корректную сумму');
        return;
    }

    if (!wallet_id) {
        showError('Выберите кошелек');
        return;
    }

    // Находим имя кошелька по ID
    const wallet = wallets.find(w => w.id === wallet_id);
    if (!wallet) {
        showError('Кошелеклек не найден');
        return;
    }

    try {
        const response = await fetchWithAuth(`${API_BASE_V1}/operations/income`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                transaction_id: generateUUID(),
                wallet_name: wallet.name,  // Отправляем ИМЯ кошелька
                amount: parseFloat(amount),
                description: description || 'Доход'
            })
        });

        console.log('[INCOME] Статус:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('[INCOME] Успех:', data);
            showSuccess('Доход добавлен');
            closeModal('addIncomeModal');
            document.getElementById('incomeAmount').value = '';
            document.getElementById('incomeDescription').value = '';
            await loadAllData();
        } else {
            const errorData = await response.json();
            console.error('[INCOME] Ошибка:', errorData);
            showError(errorData.detail || 'Ошибка добавления дохода');
        }
    } catch (e) {
        console.error('[INCOME] Исключение:', e);
        showError('Ошибка подключения: ' + e.message);
    }
}

async function addExpense() {
    if (!accessToken) {
        showError('Сначала войдите в систему');
        return;
    }

    if (wallets.length === 0) {
        showError('Сначала создайте кошелек');
        return;
    }

    const wallet_id = parseInt(document.getElementById('expenseWallet').value);
    const amount = document.getElementById('expenseAmount').value;
    const category = document.getElementById('expenseCategory').value.trim();
    const description = document.getElementById('expenseDescription').value.trim();

    if (!amount || parseFloat(amount) <= 0) {
        showError('Введите корректную сумму');
        return;
    }

    if (!wallet_id) {
        showError('Выберите кошелек');
        return;
    }

    // Находим имя кошелька по ID
    const wallet = wallets.find(w => w.id === wallet_id);
    if (!wallet) {
        showError('Кошелеклеклек не найден');
        return;
    }

    try {
        const response = await fetchWithAuth(`${API_BASE_V1}/operations/expense`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                transaction_id: generateUUID(),
                wallet_name: wallet.name,  // Отправляем ИМЯ кошелька
                amount: parseFloat(amount),
                description: description || category || 'Расход'
            })
        });

        console.log('[EXPENSE] Статус:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('[EXPENSE] Успех:', data);
            showSuccess('Расход добавлен');
            closeModal('addExpenseModal');
            document.getElementById('expenseAmount').value = '';
            document.getElementById('expenseCategory').value = '';
            document.getElementById('expenseDescription').value = '';
            await loadAllData();
        } else {
            const errorData = await response.json();
            console.error('[EXPENSE] Ошибка:', errorData);
            showError(errorData.detail || 'Ошибка добавления расхода');
        }
    } catch (e) {
        console.error('[EXPENSE] Исключение:', e);
        showError('Ошибка подключения: ' + e.message);
    }
}

async function transfer() {
    if (!accessToken) {
        showError('Сначала войдите в систему');
        return;
    }

    if (wallets.length < 2) {
        showError('Для перевода нужно минимум 2 кошелька');
        return;
    }

    const from_wallet_id = parseInt(document.getElementById('transferFrom').value);
    const to_wallet_id = parseInt(document.getElementById('transferTo').value);
    const amount = document.getElementById('transferAmount').value;

    if (!from_wallet_id || !to_wallet_id) {
        showError('Выберите оба кошелька');
        return;
    }

    if (from_wallet_id === to_wallet_id) {
        showError('Нельзя перевести в тот же кошелек');
        return;
    }

    if (!amount || parseFloat(amount) <= 0) {
        showError('Введите корректную сумму');
        return;
    }

    try {
        const response = await fetchWithAuth(`${API_BASE_V1}/operations/transfer`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                transaction_id: generateUUID(),
                from_wallet_id: from_wallet_id,
                to_wallet_id: to_wallet_id,
                amount: parseFloat(amount)
            })
        });

        console.log('[TRANSFER] Статус:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('[TRANSFER] Успех:', data);
            showSuccess('Перевод выполнен');
            closeModal('transferModal');
            document.getElementById('transferAmount').value = '';
            await loadAllData();
        } else {
            const errorData = await response.json();
            console.error('[TRANSFER] Ошибка:', errorData);
            showError(errorData.detail || 'Ошибка перевода');
        }
    } catch (e) {
        console.error('[TRANSFER] Исключение:', e);
        showError('Ошибка подключения: ' + e.message);
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

        const response = await fetchWithAuth(`${API_BASE_V1}/operations?${params}`);

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
                        typeIcon = '';
                        typeLabel = 'Доход';
                    } else if (t.type === 'expense') {
                        typeClass = 'text-danger';
                        typeIcon = '';
                        typeLabel = 'Расход';
                    } else if (t.type === 'transfer') {
                        typeClass = 'text-info';
                        typeIcon = '';
                        typeLabel = 'Перевод';
                    } else {
                        typeClass = 'text-secondary';
                        typeIcon = '';
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
                            <td class="text-end ${typeClass}"><strong>${formatCurrency(amount)}</strong></td>
                        </tr>
                    `;
                }).join('');
            }

            document.getElementById('reportContent').style.display = 'block';
            showSuccess('Отчет сформирован');
        } else {
            const error = await response.json();
            showError(error.message || error.detail || 'Ошибка загрузки отчета');
        }
    } catch (e) {
        console.error('Ошибка загрузки отчета:', e);
        showError('Ошибка подключения к серверу');
    }
}

// Функция загрузки групп пользователя
async function loadGroups() {
    if (!accessToken) {
        showError('Сначала войдите в систему');
        return;
    }

    try {
        // Делаем запрос к API
        const response = await fetchWithAuth(`${API_BASE_V2}/users/me/groups`);
        
        if (response.ok) {
            const groups = await response.json();
            renderGroups(groups);
            
            // Показываем модалку
            const modal = new bootstrap.Modal(document.getElementById('groupsModal'));
            modal.show();
        } else if (response.status === 401) {
            showError('Не авторизован');
        } else {
            const error = await response.json();
            showError(error.detail || 'Ошибка загрузки групп');
        }
    } catch (e) {
        console.error('Ошибка загрузки групп:', e);
        showError('Не удалось загрузить группы');
    }
}

// Функция для форматирования относительной даты (сокращенно)
function formatRelativeDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    
    // Сбрасываем время для сравнения календарных дней
    const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const nowOnly = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    // Разница в календарных днях
    const diffTime = nowOnly - dateOnly;
    const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));
    const diffWeeks = Math.floor(diffDays / 7);
    const diffMonths = Math.floor(diffDays / 30);
    const diffYears = Math.floor(diffDays / 365);
    
    if (diffDays === 0) {
        return 'сегодня';
    } else if (diffDays === 1) {
        return 'вчера';
    } else if (diffDays >= 2 && diffDays < 7) {
        return `${diffDays} дн.`;
    } else if (diffDays >= 7 && diffDays < 30) {
        return `${diffWeeks} нед.`;
    } else if (diffDays >= 30 && diffDays < 365) {
        return `${diffMonths} мес.`;
    } else if (diffDays >= 365 && diffDays < 1825) {
        return `${diffYears} г.`;
    } else {
        return 'давно';
    }
}

// Функция отображения групп в таблице
function renderGroups(groups) {
    const tbody = document.getElementById('groupsTable');
    
    if (!groups || groups.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-muted">
                    Вы пока не состоите ни в одной группе
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = groups.map(group => {
        // Форматируем относительную дату
        const relativeDate = formatRelativeDate(group.created_at);
        
        // Определяем, является ли текущий пользователь создателем
        const isCreator = group.creator === currentUserId;
        
        // Определяем, что показывать в столбце "Создатель"
        const creatorDisplay = isCreator ? 'Вы ⭐' : 'Другой пользователь';
        
        // Количество участников
        const membersCount = group.members ? group.members.length : 0;
        
        // Генерируем точки для участников (не более 15)
        const dotsCount = Math.min(membersCount, 15);
        const dots = '•'.repeat(dotsCount);
        
        return `
            <tr class="group-row" data-group-id="${group.id}" style="cursor: pointer;" title="Открыть группу">
                <td>
                    <strong>${group.name}</strong>
                </td>
                <td>${creatorDisplay}</td>
                <td>${relativeDate}</td>
                <td>
                    <span class="badge bg-primary">${membersCount}</span>
                    <span class="ms-2" title="Участники: ${membersCount}">${dots}</span>
                </td>
            </tr>
        `;
    }).join('');
    
    // Добавляем обработчики кликов на строки
    document.querySelectorAll('.group-row').forEach(row => {
        row.addEventListener('click', function() {
            const groupId = this.getAttribute('data-group-id');
            openGroup(groupId);
        });
    });
}

// Функция открытия группы
async function openGroup(groupId) {
    if (!accessToken) {
        showError('Сначала войдите в систему');
        return;
    }

    try {
        // Делаем запрос к API для получения информации о группе
        const response = await fetchWithAuth(`${API_BASE_V2}/groups/${groupId}`);
        
        if (response.ok) {
            const group = await response.json();
            console.log('[GROUP] Информация о группе:', group);
            
            // Показываем информацию о группе
            displayGroupDetails(group);
            
            // Показываем модалку
            const modal = new bootstrap.Modal(document.getElementById('groupDetailsModal'));
            modal.show();
        } else if (response.status === 401) {
            showError('Не авторизован');
        } else if (response.status === 403) {
            showError('Вы не являетесь участником этой группы');
        } else if (response.status === 404) {
            showError('Группа не найдена');
        } else {
            const error = await response.json();
            showError(extractErrorMessage(error, 'Ошибка загрузки группы'));
        }
    } catch (e) {
        console.error('Ошибка загрузки группы:', e);
        showError('Не удалось загрузить группу');
    }
}

// Глобальная переменная для текущей группы
let currentGroupId = null;

// Отображение деталей группы с балансом
function displayGroupDetails(groupData) {
    
    // Сохраняем ID группы
    currentGroupId = groupData.id;
    
    // Определяем, является ли текущий пользователь создателем
    // Пробуем разные варианты сравнения
    const isCreator = groupData.creator_login === currentUser;
    
    // Обновляем заголовок
    const modalTitle = document.getElementById('groupModalTitle');
    if (modalTitle) {
        modalTitle.textContent = groupData.name || 'Информация о группе';
    }
    
    // Отображаем создателя
    const creatorDisplay = isCreator 
        ? `${groupData.creator_login || currentUser} ⭐` 
        : (groupData.creator_login || `Пользователь ${groupData.creator_id || groupData.creator}`);
    
    const creatorEl = document.getElementById('groupCreator');
    if (creatorEl) {
        creatorEl.textContent = creatorDisplay;
    }
    
    // Отображаем общий баланс
    const balanceElement = document.getElementById('groupTotalBalance');
    if (balanceElement) {
        const balance = parseFloat(groupData.total_balance) || 0;
        balanceElement.textContent = formatCurrency(balance, 'RUB');
    }
    
    // Показываем/скрываем кнопки управления участниками (только для создателя)
    const memberManagementButtons = document.getElementById('memberManagementButtons');
    if (memberManagementButtons) {
        memberManagementButtons.style.display = isCreator ? 'block' : 'none';
    }
    
    // Показываем/скрываем кнопку "Удалить группу" (только для создателя)
    const deleteGroupButton = document.getElementById('deleteGroupButton');
    if (deleteGroupButton) {
        deleteGroupButton.style.display = isCreator ? 'inline-block' : 'none';
    }
    
    // Обновляем количество участников
    const membersCountEl = document.getElementById('groupMembersCount');
    if (membersCountEl && groupData.members) {
        membersCountEl.textContent = groupData.members.length;
    }
    
    // Отображаем участников с балансами
    const membersList = document.getElementById('groupMembersList');
    if (membersList) {
        const balanceMap = {};
        if (groupData.member_balances && Array.isArray(groupData.member_balances)) {
            groupData.member_balances.forEach(mb => {
                balanceMap[mb.login] = parseFloat(mb.effective_balance) || 0;
            });
        }
        
        if (groupData.members && Array.isArray(groupData.members) && groupData.members.length > 0) {
            membersList.innerHTML = groupData.members.map(member => {
                const isCurrentUser = member === currentUser;
                const memberBalance = balanceMap[member] || 0;
                
                let balanceClass;
                let fontWeightClass;
                
                if (memberBalance > 0) {
                    balanceClass = 'text-success';
                    fontWeightClass = 'fw-bold';
                } else if (memberBalance < 0) {
                    balanceClass = 'text-danger';
                    fontWeightClass = 'fw-bold';
                } else {
                    balanceClass = '';
                    fontWeightClass = '';
                }
                
                const formattedBalance = formatCurrency(memberBalance, 'RUB');
                
                return `<li class="list-group-item d-flex justify-content-between align-items-center">
                    <span>${member} ${isCurrentUser ? '⭐' : ''}</span>
                    <span class="${balanceClass} ${fontWeightClass}">${formattedBalance}</span>
                </li>`;
            }).join('');
        } else {
            membersList.innerHTML = '<li class="list-group-item text-muted">Нет участников</li>';
        }
    }
}

// Функция форматирования валюты с параметром
function formatCurrency(amount, currency = 'RUB') {
    const currencyMap = {
        'rub': 'RUB',
        'usd': 'USD',
        'eur': 'EUR',
    };
    
    const currencyCode = currencyMap[currency.toLowerCase()] || currency.toUpperCase();
    
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: currencyCode,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(amount);
}

// Функция показа модального окна создания группы
function showCreateGroupModal() {
    // Закрываем модалку групп
    const groupsModal = bootstrap.Modal.getInstance(document.getElementById('groupsModal'));
    if (groupsModal) {
        groupsModal.hide();
    }
    
    // Показываем модалку создания группы
    const createModal = new bootstrap.Modal(document.getElementById('createGroupModal'));
    createModal.show();
}

// Вспомогательная функция для извлечения сообщения об ошибке
function extractErrorMessage(data, defaultMessage = 'Произошла ошибка') {
    if (!data) return defaultMessage;
    
    // Если есть detail
    if (data.detail) {
        if (typeof data.detail === 'string') {
            return data.detail;
        }
        
        // Для FastAPI HTTPException
        if (Array.isArray(data.detail)) {
            return data.detail.map(err => {
                if (err.msg) return err.msg;
                if (err.message) return err.message;
                return JSON.stringify(err);
            }).join(', ');
        }
        
        // Для объектов с полем message
        if (typeof data.detail === 'object' && data.detail.message) {
            return data.detail.message;
        }
    }
    
    // Проверяем другие поля
    if (data.message) return data.message;
    if (data.error) return data.error;
    
    return defaultMessage;
}

// Функция создания группы
async function createGroup() {
    if (!accessToken) {
        showError('Сначала войдите в систему');
        return;
    }

    const name = document.getElementById('groupName').value.trim();
    const membersInput = document.getElementById('groupMembers').value.trim();

    // Минимальные проверки на пустоту
    if (!name) {
        showError('Введите название группы');
        return;
    }

    if (!membersInput) {
        showError('Добавьте хотя бы одного участника');
        return;
    }

    // Отправляем на бэкенд как есть (даже если один участник)
    const membersLogins = membersInput
        .split(',')
        .map(login => login.trim())
        .filter(login => login.length > 0);

    try {
        const response = await fetchWithAuth(`${API_BASE_V2}/groups`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                members_logins: membersLogins
            })
        });

        console.log('[GROUP] Статус создания:', response.status);

        const data = await response.json();
        
        if (response.ok) {
            console.log('[GROUP] Группа создана:', data);
            
            showSuccess('Группа успешно создана');
            
            // Закрываем модалку создания
            const createModal = bootstrap.Modal.getInstance(document.getElementById('createGroupModal'));
            if (createModal) {
                createModal.hide();
            }
            
            // Очищаем поля
            document.getElementById('groupName').value = '';
            document.getElementById('groupMembers').value = '';
            
            // Перезагружаем список групп
            await loadGroups();
            
            // Показываем модалку групп снова
            const groupsModal = new bootstrap.Modal(document.getElementById('groupsModal'));
            groupsModal.show();
            
        } else {
            // Показываем ошибку от бэкенда
            const errorMessage = extractErrorMessage(data, 'Ошибка создания группы');
            console.error('[GROUP] Ошибка от сервера:', data);
            showError(errorMessage);
        }
    } catch (e) {
        console.error('[GROUP] Исключение:', e);
        showError('Ошибка подключения: ' + e.message);
    }
}

// Функция показа модалки прикрепления кошелька
function showAttachWalletModal() {
    if (!currentGroupId) {
        showError('Группа не выбрана');
        return;
    }
    
    // Заполняем список кошельков
    const select = document.getElementById('attachWalletSelect');
    if (!select) {
        showError('Модалка прикрепления не найдена');
        return;
    }
    
    if (wallets.length === 0) {
        select.innerHTML = '<option value="">У вас нет кошельков</option>';
    } else {
        select.innerHTML = wallets.map(w => {
            const balance = parseFloat(w.balance) || 0;
            const currency = String(w.currency || 'rub').toLowerCase();
            return `<option value="${w.id}">${w.name} - ${formatCurrency(balance, currency)}</option>`;
        }).join('');
    }
    
    // Показываем модалку
    const modal = new bootstrap.Modal(document.getElementById('attachWalletModal'));
    modal.show();
}

// Функция прикрепления кошелька к группе
async function attachWalletToGroup() {
    if (!currentGroupId) {
        showError('Группа не выбрана');
        return;
    }
    
    const walletId = parseInt(document.getElementById('attachWalletSelect').value);
    
    if (!walletId) {
        showError('Выберите кошелек');
        return;
    }
    
    try {
        const response = await fetchWithAuth(
            `${API_BASE_V2}/groups/${currentGroupId}/wallets/${walletId}`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            }
        );
        
        console.log('[ATTACH_WALLET] Статус:', response.status);
        
        if (response.ok) {
            showSuccess('Кошелек прикреплен к группе');
            
            // Закрываем модалку прикрепления
            const attachModalElement = document.getElementById('attachWalletModal');
            const attachModal = bootstrap.Modal.getInstance(attachModalElement);
            if (attachModal) {
                attachModal.hide();
            }
                      
            // Обновляем информацию о группе
            await viewGroup(currentGroupId);
        } else {
            const data = await response.json();
            const errorMessage = extractErrorMessage(data, 'Ошибка прикрепления кошелька');
            showError(errorMessage);
        }
    } catch (e) {
        console.error('[ATTACH_WALLET] Ошибка:', e);
        showError('Ошибка подключения: ' + e.message);
    }
}

// Функция показа модалки открепления кошелька
function showDetachWalletModal() {
    if (!currentGroupId) {
        showError('Группа не выбрана');
        return;
    }
    
    // Заполняем список кошельков
    const select = document.getElementById('detachWalletSelect');
    if (!select) {
        showError('Модалка открепления не найдена');
        return;
    }
    
    if (wallets.length === 0) {
        select.innerHTML = '<option value="">У вас нет кошельков</option>';
    } else {
        select.innerHTML = wallets.map(w => {
            const balance = parseFloat(w.balance) || 0;
            const currency = String(w.currency || 'rub').toLowerCase();
            return `<option value="${w.id}">${w.name} - ${formatCurrency(balance, currency)}</option>`;
        }).join('');
    }
    
    // Показываем модалку
    const modal = new bootstrap.Modal(document.getElementById('detachWalletModal'));
    modal.show();
}

// Функция открепления кошелька от группы
async function detachWalletFromGroup() {
    if (!currentGroupId) {
        showError('Группа не выбрана');
        return;
    }
    
    const walletId = parseInt(document.getElementById('detachWalletSelect').value);
    
    if (!walletId) {
        showError('Выберите кошелек');
        return;
    }
    
    try {
        const response = await fetchWithAuth(
            `${API_BASE_V2}/groups/${currentGroupId}/wallets/${walletId}`,
            {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            }
        );
        
        console.log('[DETACH_WALLET] Статус:', response.status);
        
        if (response.ok) {
            showSuccess('Кошелек откреплен от группы');
            
            // Закрываем модалку открепления
            const detachModalElement = document.getElementById('detachWalletModal');
            const detachModal = bootstrap.Modal.getInstance(detachModalElement);
            if (detachModal) {
                detachModal.hide();
            }
                       
            // Обновляем информацию о группе
            await viewGroup(currentGroupId);
        } else {
            const data = await response.json();
            const errorMessage = extractErrorMessage(data, 'Ошибка открепления кошелька');
            showError(errorMessage);
        }
    } catch (e) {
        console.error('[DETACH_WALLET] Ошибка:', e);
        showError('Ошибка подключения: ' + e.message);
    }
}

// Функция для просмотра группы
async function viewGroup(groupId) {
    currentGroupId = groupId;  // Сохраняем ID
    
    try {
        const response = await fetchWithAuth(`${API_BASE_V2}/groups/${groupId}`);
        
        if (response.ok) {
            const groupData = await response.json();
            displayGroupDetails(groupData);
            
            const modal = new bootstrap.Modal(document.getElementById('groupDetailsModal'));
            modal.show();
        } else {
            const errorData = await response.json();
            showError(extractErrorMessage(errorData, 'Ошибка получения группы'));
        }
    } catch (e) {
        console.error('[GROUP] Ошибка:', e);
        showError('Ошибка подключения: ' + e.message);
    }
}

// Обработчик для всех модалок при скрытии
document.addEventListener('hidden.bs.modal', function(event) {
    // Небольшая задержка для плавного закрытия
    setTimeout(() => {
        // Проверяем, есть ли еще открытые модалки
        const openModals = document.querySelectorAll('.modal.show');
        
        if (openModals.length === 0) {
            // Удаляем ВСЕ backdrop'ы
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());
            
            // Восстанавливаем body
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        }
    }, 150); // Задержка 150мс для завершения анимации
});

// Обработчик для модалок при показе
document.addEventListener('shown.bs.modal', function(event) {
    // Убеждаемся, что backdrop только один
    const backdrops = document.querySelectorAll('.modal-backdrop');
    if (backdrops.length > 1) {
        // Оставляем только последний backdrop
        for (let i = 0; i < backdrops.length - 1; i++) {
            backdrops[i].remove();
        }
    }
});

// Функция выхода из группы
async function leaveGroup() {
    if (!currentGroupId) {
        showError('Группа не выбрана');
        return;
    }
    
    // Подтверждение действия
    if (!confirm('Вы уверены, что хотите покинуть группу?')) {
        return;
    }
    
    try {
        const response = await fetchWithAuth(
            `${API_BASE_V2}/groups/${currentGroupId}/members/me`,
            {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            }
        );
        
        console.log('[LEAVE_GROUP] Статус:', response.status);
        
        if (response.ok) {
            showSuccess('Вы вышли из группы');
            
            // Закрываем модалку группы
            const groupModalElement = document.getElementById('groupDetailsModal');
            const groupModal = bootstrap.Modal.getInstance(groupModalElement);
            if (groupModal) {
                groupModal.hide();
            }
            
            // Закрываем модалку списка групп, если она открыта
            const groupsModalElement = document.getElementById('groupsModal');
            const groupsModal = bootstrap.Modal.getInstance(groupsModalElement);
            if (groupsModal) {
                groupsModal.hide();
            }
            
            // Сбрасываем currentGroupId
            currentGroupId = null;
            
            // Перезагружаем список групп
            await loadGroups();
        } else {
            let errorMessage = 'Ошибка выхода из группы';
            try {
                const data = await response.json();
                errorMessage = extractErrorMessage(data, errorMessage);
            } catch (e) {
                // Игнорируем ошибку парсинга
            }
            showError(errorMessage);
        }
    } catch (e) {
        console.error('[LEAVE_GROUP] Ошибка:', e);
        showError('Ошибка подключения: ' + e.message);
    }
}

// Функция удаления группы
async function deleteGroup() {
    if (!currentGroupId) {
        showError('Группа не выбрана');
        return;
    }
    
    // Подтверждение действия
    if (!confirm('Вы уверены, что хотите удалить группу? Это действие нельзя отменить.')) {
        return;
    }
    
    try {
        const response = await fetchWithAuth(
            `${API_BASE_V2}/groups/${currentGroupId}`,
            {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            }
        );
        
        console.log('[DELETE_GROUP] Статус:', response.status);
        
        if (response.ok) {
            showSuccess('Группа удалена');
            
            // Закрываем модалку группы
            const groupModalElement = document.getElementById('groupDetailsModal');
            const groupModal = bootstrap.Modal.getInstance(groupModalElement);
            if (groupModal) {
                groupModal.hide();
            }
            
            // Закрываем модалку списка групп, если она открыта
            const groupsModalElement = document.getElementById('groupsModal');
            const groupsModal = bootstrap.Modal.getInstance(groupsModalElement);
            if (groupsModal) {
                groupsModal.hide();
                }
            
            // Сбрасываем currentGroupId
            currentGroupId = null;
            
            // Перезагружаем список групп
            await loadGroups();
        } else {
            let errorMessage = 'Ошибка удаления группы';
            try {
                const data = await response.json();
                errorMessage = extractErrorMessage(data, errorMessage);
            } catch (e) {
                // Игнорируем ошибку парсинга
            }
            showError(errorMessage);
        }
    } catch (e) {
        console.error('[DELETE_GROUP] Ошибка:', e);
        showError('Ошибка подключения: ' + e.message);
    }
}

// Функция показа модалки добавления участника
function showAddMemberModal() {
    if (!currentGroupId) {
        showError('Группа не выбрана');
        return;
    }
    
    // Создаем модалку динамически
    const modalHTML = `
        <div class="modal fade" id="addMemberModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Добавить участника</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Логин участника</label>
                            <input type="text" class="form-control" id="newMemberLogin" placeholder="Введите логин">
                        </div>
                    </div>
                    <div class="modal-footer d-flex justify-content-between">
                        <button type="button" class="btn btn-success" onclick="addMemberToGroup()">Добавить</button>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Удаляем существующую модалку, если есть
    const existingModal = document.getElementById('addMemberModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Добавляем новую модалку
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Показываем модалку
    const modal = new bootstrap.Modal(document.getElementById('addMemberModal'));
    modal.show();
}

// Функция добавления участника в группу
async function addMemberToGroup() {
    if (!currentGroupId) {
        showError('Группа не выбрана');
        return;
    }
    
    const login = document.getElementById('newMemberLogin').value.trim();
    
    if (!login) {
        showError('Введите логин участника');
        return;
    }
    
    try {
        const response = await fetchWithAuth(
            `${API_BASE_V2}/groups/${currentGroupId}/members`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ login: login })
            }
        );
        
        console.log('[ADD_MEMBER] Статус:', response.status);
        
        if (response.ok) {
            showSuccess('Участник добавлен');
            
            // Закрываем модалку добавления
            const addModalElement = document.getElementById('addMemberModal');
            const addModal = bootstrap.Modal.getInstance(addModalElement);
            if (addModal) {
                addModal.hide();
        }
    
            // Удаляем модалку из DOM
    setTimeout(() => {
                addModalElement.remove();
    }, 300);
            
            // Обновляем информацию о группе
            await viewGroup(currentGroupId);
        } else {
            let errorMessage = 'Ошибка добавления участника';
            try {
                const data = await response.json();
                errorMessage = extractErrorMessage(data, errorMessage);
            } catch (e) {
                // Игнорируем ошибку парсинга
            }
            showError(errorMessage);
        }
    } catch (e) {
        console.error('[ADD_MEMBER] Ошибка:', e);
        showError('Ошибка подключения: ' + e.message);
    }
}

// Функция показа модалки удаления участника
function showRemoveMemberModal() {
    if (!currentGroupId) {
        showError('Группа не выбрана');
        return;
    }
    
    // Получаем список участников из текущей группы
    const membersList = document.getElementById('groupMembersList');
    if (!membersList) {
        showError('Список участников не найден');
        return;
    }
    
    // Извлекаем логины участников из списка
    const members = [];
    const memberItems = membersList.querySelectorAll('li');
    memberItems.forEach(item => {
        const span = item.querySelector('span:first-child');
        if (span) {
            // Убираем звездочку у текущего пользователя
            const login = span.textContent.replace('⭐', '').trim();
            members.push(login);
        }
    });
    
    // Фильтруем текущего пользователя (нельзя удалить самого себя)
    const availableMembers = members.filter(login => login !== currentUser);
    
    if (availableMembers.length === 0) {
        showError('Нет участников для удаления');
        return;
    }
    
    // Создаем модалку динамически
    const modalHTML = `
        <div class="modal fade" id="removeMemberModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Удалить участника</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Выберите участника</label>
                            <select class="form-select" id="removeMemberSelect">
                                ${availableMembers.map(login => 
                                    `<option value="${login}">${login}</option>`
                                ).join('')}
                            </select>
                        </div>
                    </div>
                    <div class="modal-footer d-flex justify-content-between">
                        <button type="button" class="btn btn-danger" onclick="removeMemberFromGroup()">Удалить</button>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Удаляем существующую модалку, если есть
    const existingModal = document.getElementById('removeMemberModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Добавляем новую модалку
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Показываем модалку
    const modal = new bootstrap.Modal(document.getElementById('removeMemberModal'));
    modal.show();
}

// Функция удаления участника из группы
async function removeMemberFromGroup() {
    if (!currentGroupId) {
        showError('Группа не выбрана');
        return;
    }
    
    const login = document.getElementById('removeMemberSelect').value;
    
    if (!login) {
        showError('Выберите участника');
        return;
    }
    
    // Подтверждение действия
    if (!confirm(`Вы уверены, что хотите удалить участника "${login}"?`)) {
        return;
    }
    
    try {
        // Сначала получаем информацию о группе, чтобы найти ID пользователя
        const groupResponse = await fetchWithAuth(`${API_BASE_V2}/groups/${currentGroupId}`);
        
        if (!groupResponse.ok) {
            showError('Не удалось получить информацию о группе');
            return;
        }
        
        const groupData = await groupResponse.json();
        
        // Ищем пользователя по логину
        // Предполагаем, что API возвращает members с id и login
        let userId = null;
        
        if (groupData.members && Array.isArray(groupData.members)) {
            // Если members - массив объектов с id и login
            if (groupData.members[0] && typeof groupData.members[0] === 'object') {
                const member = groupData.members.find(m => m.login === login);
                if (member) {
                    userId = member.id;
                }
            } else {
                // Если members - массив строк (логинов), нужно получить id пользователя
                // В этом случае можно попробовать другой подход
                // Например, использовать email или другой идентификатор
                console.log('[REMOVE_MEMBER] Members - массив строк, нужен id пользователя');
                showError('Невозможно определить ID пользователя. Обратитесь к администратору.');
                return;
            }
        }
        
        if (!userId) {
            showError('Пользователь не найден');
            return;
        }
        
        const response = await fetchWithAuth(
            `${API_BASE_V2}/groups/${currentGroupId}/members/${userId}`,
            {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            }
        );
        
        console.log('[REMOVE_MEMBER] Статус:', response.status);
        
        if (response.ok) {
            showSuccess('Участник удален');
            
            // Закрываем модалку удаления
            const removeModalElement = document.getElementById('removeMemberModal');
            const removeModal = bootstrap.Modal.getInstance(removeModalElement);
            if (removeModal) {
                removeModal.hide();
            }
            
            // Удаляем модалку из DOM
            setTimeout(() => {
                    removeModalElement.remove();
            }, 300);
            
            // Обновляем информацию о группе
            await viewGroup(currentGroupId);
        } else {
            let errorMessage = 'Ошибка удаления участника';
            try {
                const data = await response.json();
                errorMessage = extractErrorMessage(data, errorMessage);
            } catch (e) {
                // Игнорируем ошибку парсинга
            }
            showError(errorMessage);
        }
    } catch (e) {
        console.error('[REMOVE_MEMBER] Ошибка:', e);
        showError('Ошибка подключения: ' + e.message);
    }
}

// Функция обновления списка кошельков в модалке удаления
function updateDeleteWalletSelect() {
    const select = document.getElementById('deleteWalletSelect');
    if (!select) return;
    
    if (wallets.length === 0) {
        select.innerHTML = '<option value="">У вас нет кошельков</option>';
        return;
    }
    
    const currencySymbols = {
        'rub': '₽',
        'usd': '$',
        'eur': '€'
    };
    
    select.innerHTML = wallets.map(w => {
        const balance = parseFloat(w.balance) || 0;
        const currency = String(w.currency || 'rub').toLowerCase();
        const symbol = currencySymbols[currency] || currency.toUpperCase();
        return `<option value="${w.id}">${w.name} - ${balance.toFixed(2)} ${symbol}</option>`;
    }).join('');
}

// Функция удаления кошелька
async function deleteWallet() {
    if (!accessToken) {
        showError('Сначала войдите в систему');
        return;
    }
    
    const walletId = parseInt(document.getElementById('deleteWalletSelect').value);
    
    if (!walletId) {
        showError('Выберите кошелек для удаления');
        return;
    }
    
    // Находим кошелек для отображения в подтверждении
    const wallet = wallets.find(w => w.id === walletId);
    if (!wallet) {
        showError('Кошелек не найден');
        return;
    }
    
    // Подтверждение удаления
    if (!confirm(`Вы уверены, что хотите удалить кошелек "${wallet.name}"?\nВсе операции с этим кошельком будут удалены!`)) {
        return;
    }
    
    try {
        const response = await fetchWithAuth(`${API_BASE_V2}/wallets/${walletId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log('[DELETE_WALLET] Статус:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('[DELETE_WALLET] Успех:', data);
            
            showSuccess(data.message || 'Кошелек успешно удален');
            
            // Закрываем модалку
            const modalElement = document.getElementById('deleteWalletModal');
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            }
            
            // Перезагружаем все данные
            await loadAllData();
        } else {
            let errorMessage = 'Ошибка удаления кошелька';
            try {
                const errorData = await response.json();
                errorMessage = extractErrorMessage(errorData, errorMessage);
            } catch (e) {
                // Игнорируем ошибку парсинга
            }
            showError(errorMessage);
        }
    } catch (e) {
        console.error('[DELETE_WALLET] Ошибка:', e);
        showError('Ошибка подключения: ' + e.message);
    }
}

// Функция удаления группы
async function deleteGroup() {
    if (!currentGroupId) {
        showError('Группа не выбрана');
        return;
    }
    
    // Подтверждение удаления
    if (!confirm('Вы уверены, что хотите удалить группу?\n\nВнимание!\n- Все участники будут исключены из группы\n- Все прикрепленные кошельки будут откреплены\n- Это действие нельзя отменить!')) {
        return;
    }
    
    try {
        const response = await fetchWithAuth(
            `${API_BASE_V2}/groups/${currentGroupId}`,
            {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            }
        );
        
        console.log('[DELETE_GROUP] Статус:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('[DELETE_GROUP] Успех:', data);
            
            showSuccess(data.message || 'Группа успешно удалена');
            
            // Закрываем модалку группы
            const groupModalElement = document.getElementById('groupDetailsModal');
            const groupModal = bootstrap.Modal.getInstance(groupModalElement);
            if (groupModal) {
                groupModal.hide();
            }
            
            // Закрываем модалку списка групп, если она открыта
            const groupsModalElement = document.getElementById('groupsModal');
            const groupsModal = bootstrap.Modal.getInstance(groupsModalElement);
            if (groupsModal) {
                groupsModal.hide();
            }
            
            // Сбрасываем currentGroupId
            currentGroupId = null;
            
            // Перезагружаем список групп
            await loadGroups();
            
        } else {
            let errorMessage = 'Ошибка удаления группы';
            try {
                const errorData = await response.json();
                errorMessage = extractErrorMessage(errorData, errorMessage);
            } catch (e) {
                // Игнорируем ошибку парсинга
            }
            showError(errorMessage);
        }
    } catch (e) {
        console.error('[DELETE_GROUP] Ошибка:', e);
        showError('Ошибка подключения: ' + e.message);
    }
}
