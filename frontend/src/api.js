import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL
});

// Добавляем interceptor для установки Authorization заголовка
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers = config.headers || {};
            if (!config.headers['Authorization']) {
                config.headers['Authorization'] = `Bearer ${token}`;
            }
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Добавляем interceptor для обработки 401
api.interceptors.response.use(
    response => response,
    error => {
        if (error.response && error.response.status === 401) {
            localStorage.removeItem('token');
            // Редирект на логин (или /)
            if (window.location.pathname !== '/') {
                window.location.href = '/';
            }
        }
        return Promise.reject(error);
    }
);

export default api; 