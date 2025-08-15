import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import DateRangePicker from './DateRangePicker';
import { Line } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
} from 'chart.js';
import api from '../api';
import { eachDayOfInterval, format } from 'date-fns';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
);

const filterOptions = [
    {
        group: 'Тип', options: [
            { label: 'Негативные', value: 'negative', color: '#0dcaf0' },
            { label: 'Доля негативных', value: 'negative_share', color: '#82ca9d' },
            { label: 'Удалённые', value: 'deleted', color: '#ff7300' },
            { label: 'Доля удаленных', value: 'deleted_share', color: '#ffc107' },
        ]
    },
    {
        group: 'Только отзывы с', options: [
            { label: '5★', value: '5' },
            { label: '4★', value: '4' },
            { label: '3★', value: '3' },
            { label: '2★', value: '2' },
            { label: '1★', value: '1' },
        ]
    },
];

const API_URL = import.meta.env.VITE_API_URL || '';

const ShopSummaryWidget = ({ shopType }) => {
    const navigate = useNavigate();
    const [brands, setBrands] = useState([]);
    const [products, setProducts] = useState([]);
    const [selectedBrand, setSelectedBrand] = useState('');
    const [selectedProducts, setSelectedProducts] = useState([]);
    const [dateRange, setDateRange] = useState({ startDate: '', endDate: '' });
    const [selectedFilter, setSelectedFilter] = useState('');
    const [search, setSearch] = useState('');

    const [loadingBrands, setLoadingBrands] = useState(false);
    const [loadingProducts, setLoadingProducts] = useState(false);
    const [loadingChart, setLoadingChart] = useState(false);

    const [errorBrands, setErrorBrands] = useState(null);
    const [errorProducts, setErrorProducts] = useState(null);
    const [errorChart, setErrorChart] = useState(null);

    const [chartData, setChartData] = useState([]);
    const [totalReviews, setTotalReviews] = useState(0);

    // --- Получение брендов ---
    useEffect(() => {
        setLoadingBrands(true);
        setErrorBrands(null);
        const token = localStorage.getItem('token');
        api.get(`${API_URL}/brands`, {
            params: { shop: shopType },
            headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        })
            .then(res => {
                // res.data: [{ name: str }, ...]
                setBrands(Array.isArray(res.data) ? res.data : []);
            })
            .catch(e => {
                if (e.response?.status === 404) {
                    setErrorBrands('Бренды не найдены');
                } else if (e.response?.status === 500) {
                    setErrorBrands('Ошибка сервера');
                } else {
                    setErrorBrands('Ошибка загрузки брендов');
                }
            })
            .finally(() => setLoadingBrands(false));
    }, [shopType]);

    // --- Получение товаров ---
    useEffect(() => {
        if (!selectedBrand) {
            setProducts([]);
            setSelectedProducts([]);
            return;
        }
        setLoadingProducts(true);
        setErrorProducts(null);
        const token = localStorage.getItem('token');

        console.log('[DEBUG] Запрос товаров для бренда:', selectedBrand);

        api.get(`${API_URL}/products`, {
            params: {
                shop: shopType,
                brand_id: selectedBrand
            },
            headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        })
            .then(res => {
                console.log('[DEBUG] Полученные товары:', res.data);
                setProducts(res.data);
            })
            .catch(e => {
                console.error('[DEBUG] Ошибка получения товаров:', e);
                if (e.response?.status === 404) {
                    setErrorProducts('Товары не найдены');
                } else if (e.response?.status === 500) {
                    setErrorProducts('Ошибка сервера');
                } else {
                    setErrorProducts('Ошибка загрузки товаров');
                }
            })
            .finally(() => setLoadingProducts(false));
    }, [shopType, selectedBrand]);

    // --- Подготовка параметров для фильтрации ---
    const chartKeys = useMemo(() => {
        if (!selectedFilter) return [];
        // Создаем ключи для каждого товара
        const keys = selectedProducts.map(productId => {
            const product = products.find(p => p.id === productId);
            return product ? `${selectedFilter}_${productId}` : null;
        }).filter(Boolean);

        console.log('[DEBUG] chartKeys обновлены:', {
            selectedFilter,
            selectedProducts,
            products: products.length,
            keys
        });

        return keys;
    }, [selectedFilter, selectedProducts, products]);

    // --- Получение данных для графика ---
    useEffect(() => {
        console.log('[DEBUG] useEffect для графика сработал:', {
            dateRange: !!dateRange.startDate && !!dateRange.endDate,
            chartKeysLength: chartKeys.length,
            selectedFilter,
            selectedProducts,
            productsLength: products.length
        });

        if (!dateRange.startDate || !dateRange.endDate || chartKeys.length === 0) {
            console.log('[DEBUG] Условия не выполнены для отправки запроса:', {
                hasStartDate: !!dateRange.startDate,
                hasEndDate: !!dateRange.endDate,
                chartKeysLength: chartKeys.length
            });
            setChartData([]);
            setTotalReviews(0);
            return;
        }

        console.log('[DEBUG] Все условия выполнены, отправляем запрос');
        setLoadingChart(true);
        setErrorChart(null);

        console.log('[DEBUG] Запрос данных для графика:', {
            shopType,
            selectedBrand,
            selectedProducts,
            dateRange,
            selectedFilter,
            chartKeys
        });

        // Создаем запросы для каждого товара
        const requests = selectedProducts.map(productId => {
            const params = {
                shop: shopType,
                brand_id: selectedBrand || undefined,
                product_id: productId,
                date_from: dateRange.startDate,
                date_to: dateRange.endDate,
                metrics: selectedFilter,
            };
            const token = localStorage.getItem('token');
            console.log('[DEBUG] Параметры запроса:', params);
            return api.get(`${API_URL}/reviews/summary`, {
                params,
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
            });
        });

        Promise.all(requests)
            .then(responses => {
                console.log('[DEBUG] Ответы от сервера:', responses.map(r => r.data));
                // Объединяем данные по датам
                const allData = {};
                let totalReviewsSum = 0;

                responses.forEach((res, index) => {
                    const productId = selectedProducts[index];
                    const product = products.find(p => p.id === productId);
                    const productName = product ? product.name : `товар ${productId}`;

                    if (res.data.by_day) {
                        res.data.by_day.forEach(dayData => {
                            if (!allData[dayData.date]) {
                                allData[dayData.date] = { date: dayData.date };
                            }
                            allData[dayData.date][`${selectedFilter}_${productId}`] = dayData[selectedFilter] || 0;
                        });
                    }

                    totalReviewsSum += res.data.total_reviews || 0;
                });

                console.log('[DEBUG] Обработанные данные:', { allData, totalReviewsSum });
                setChartData(Object.values(allData));
                setTotalReviews(totalReviewsSum);
            })
            .catch(e => {
                console.error('[DEBUG] Ошибка при получении данных:', e);
                if (e.response?.status === 404) {
                    setErrorChart('Данные не найдены');
                } else if (e.response?.status === 500) {
                    setErrorChart('Ошибка сервера');
                } else {
                    setErrorChart('Ошибка загрузки данных для графика');
                }
            })
            .finally(() => setLoadingChart(false));
    }, [shopType, selectedBrand, selectedProducts, dateRange, selectedFilter, products]);

    // --- Фильтрация фильтров по поиску ---
    const filteredFilterOptions = filterOptions.map(group => ({
        ...group,
        options: group.options.filter(opt =>
            opt.label.toLowerCase().includes(search.toLowerCase())
        )
    })).filter(group => group.options.length > 0);

    // --- Для графика: показывать все дни периода ---
    const getAllDatesInRange = (start, end) => {
        if (!start || !end) return [];
        try {
            return eachDayOfInterval({ start: new Date(start), end: new Date(end) })
                .map(date => format(date, 'yyyy-MM-dd'));
        } catch {
            return [];
        }
    };
    const allDates = useMemo(() => getAllDatesInRange(dateRange.startDate, dateRange.endDate), [dateRange]);
    const mergedChartData = useMemo(() => {
        if (!allDates.length) return [];
        return allDates.map(dateStr => {
            const found = chartData.find(d => d.date === dateStr);
            if (found) return found;
            const empty = { date: dateStr };
            chartKeys.forEach(key => { empty[key] = 0; });
            return empty;
        });
    }, [allDates, chartData, chartKeys]);

    // --- Функции для управления товарами ---
    const addProduct = (productId) => {
        console.log('[DEBUG] Добавление товара:', productId);
        if (!selectedProducts.includes(productId)) {
            const newSelectedProducts = [...selectedProducts, productId];
            console.log('[DEBUG] Новый список товаров:', newSelectedProducts);
            setSelectedProducts(newSelectedProducts);
        } else {
            console.log('[DEBUG] Товар уже выбран:', productId);
        }
    };

    const removeProduct = (productId) => {
        console.log('[DEBUG] Удаление товара:', productId);
        const newSelectedProducts = selectedProducts.filter(id => id !== productId);
        console.log('[DEBUG] Новый список товаров после удаления:', newSelectedProducts);
        setSelectedProducts(newSelectedProducts);
    };

    const getSelectedProductNames = () => {
        return selectedProducts.map(id => {
            const product = products.find(p => p.id === id);
            return product ? product.name : id;
        });
    };

    // --- Получение названий для легенды графика ---
    const getLegendNames = () => {
        return selectedProducts.map(productId => {
            const product = products.find(p => p.id === productId);
            return product ? product.name : `товар ${productId}`;
        });
    };

    // --- Функция для перехода к странице магазина ---
    const handleOpenShop = () => {
        navigate(`/analytics/brand-shops?shop=${shopType}`);
    };

    // --- Функция для сброса всех параметров ---
    const handleResetParameters = () => {
        console.log('[DEBUG] Сброс параметров');
        setSelectedBrand('');
        setSelectedProducts([]);
        setDateRange({ startDate: '', endDate: '' });
        setSelectedFilter('');
        setSearch('');
        console.log('[DEBUG] Параметры сброшены');
    };

    const prepareChartData = () => {
        if (!mergedChartData || mergedChartData.length === 0 || chartKeys.length === 0) {
            return null;
        }

        const datasets = chartKeys.map((key, index) => {
            const colors = ['#ff6384', '#36a2eb', '#cc65fe', '#ffce56', '#4bc0c0', '#9966ff'];
            const color = colors[index % colors.length];

            return {
                label: getLegendNames()[index] || key,
                data: mergedChartData.map(item => item[key] || 0),
                borderColor: color,
                backgroundColor: color + '20',
                tension: 0.1,
                fill: false
            };
        });

        return {
            labels: mergedChartData.map(item => item.date),
            datasets
        };
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    color: '#ffffff'
                }
            },
            title: {
                display: true,
                text: 'Динамика показателей',
                color: '#ffffff'
            }
        },
        scales: {
            x: {
                ticks: {
                    color: '#ffffff'
                },
                grid: {
                    color: '#333333'
                }
            },
            y: {
                ticks: {
                    color: '#ffffff'
                },
                grid: {
                    color: '#333333'
                }
            }
        }
    };

    // --- UI ---
    return (
        <div className="bg-dark text-light rounded p-3 mb-3" style={{ border: '1.5px solid #21c55d' }}>
            <div className="d-flex justify-content-between align-items-center mb-2">
                <h5 className="mb-0">{shopType === 'wb' ? 'Wildberries' : 'Ozon'} — краткая сводка</h5>
                <button
                    className="btn btn-outline-success btn-sm"
                    onClick={handleOpenShop}
                    title={`Открыть страницу ${shopType === 'wb' ? 'Wildberries' : 'Ozon'}`}
                >
                    <i className="fas fa-external-link-alt me-1"></i>
                    Открыть магазин
                </button>
            </div>

            {/* Виджет даты сверху слева */}
            <div className="mb-3">
                <label className="small mb-1">Период:</label><br />
                <DateRangePicker
                    onDateChange={(start, end) => setDateRange({ startDate: start, endDate: end })}
                    initialStartDate={dateRange.startDate}
                    initialEndDate={dateRange.endDate}
                />
            </div>

            {/* Фильтры ниже даты */}
            <div className="d-flex gap-2 mb-2 align-items-end">
                <div>
                    <label className="small mb-1">Бренд:</label><br />
                    {loadingBrands ? (
                        <div className="text-muted small">Загрузка...</div>
                    ) : errorBrands ? (
                        <div className="text-danger small">{errorBrands}</div>
                    ) : (
                        <select
                            className="form-select form-select-sm bg-secondary text-light"
                            value={selectedBrand}
                            onChange={e => {
                                setSelectedBrand(e.target.value);
                                setSelectedProducts([]);
                            }}
                        >
                            <option value="">Выбрать бренд</option>
                            {brands.map(b => <option key={b.name} value={b.name}>{b.name}</option>)}
                        </select>
                    )}
                </div>
                <div>
                    <label className="small mb-1">Товары:</label><br />
                    {loadingProducts ? (
                        <div className="text-muted small">Загрузка...</div>
                    ) : errorProducts ? (
                        <div className="text-danger small">{errorProducts}</div>
                    ) : (
                        <select
                            className="form-select form-select-sm bg-secondary text-light"
                            value=""
                            onChange={e => {
                                console.log('[DEBUG] Выбор товара в селекте:', e.target.value);
                                if (e.target.value) {
                                    addProduct(e.target.value);
                                    e.target.value = "";
                                }
                            }}
                            disabled={!selectedBrand}
                        >
                            <option value="">Добавить товар</option>
                            {products.filter(p => !selectedProducts.includes(p.id)).map(p => {
                                console.log('[DEBUG] Товар в селекте:', p);
                                return (
                                    <option key={p.id} value={p.id}>{p.id}</option>
                                );
                            })}
                        </select>
                    )}
                </div>
                <div>
                    <label className="small mb-1">Всего отзывов:</label>
                    <div className="fs-6 fw-bold text-light">{loadingChart ? '...' : totalReviews}</div>
                </div>
            </div>

            {/* Выбранные товары */}
            {selectedProducts.length > 0 && (
                <div className="mb-2">
                    <label className="fw-bold small">Выбранные товары:</label>
                    <div className="d-flex flex-wrap gap-1 mt-1">
                        {getSelectedProductNames().map((name, index) => (
                            <div key={selectedProducts[index]} className="badge bg-success d-flex align-items-center">
                                <span className="me-1 small">{name}</span>
                                <button
                                    type="button"
                                    className="btn-close btn-close-white"
                                    style={{ fontSize: '0.4em' }}
                                    onClick={() => removeProduct(selectedProducts[index])}
                                    aria-label="Удалить товар"
                                ></button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Основной контент - график и параметры */}
            <div className="d-flex gap-3">
                {/* График - увеличенный */}
                <div className="flex-grow-1 bg-secondary rounded p-2" style={{ minWidth: 0 }}>
                    {errorChart ? (
                        <div className="text-danger text-center">{errorChart}</div>
                    ) : loadingChart ? (
                        <div className="text-center text-muted">Загрузка...</div>
                    ) : (dateRange.startDate && dateRange.endDate && chartKeys.length > 0 && mergedChartData.length > 0) ? (
                        <div style={{ height: '400px' }}>
                            <Line data={prepareChartData()} options={chartOptions} />
                        </div>
                    ) : (
                        <div className="text-center text-muted">Выберите период и параметр для отображения</div>
                    )}
                </div>

                {/* Параметр отображения - справа на весь виджет */}
                <div style={{ width: 280 }}>
                    <div className="bg-secondary rounded p-2 h-100">
                        <div className="d-flex justify-content-between align-items-center mb-2">
                            <h6 className="mb-0 fw-bold">Параметр для отображения:</h6>
                            <button
                                type="button"
                                className="btn btn-outline-warning btn-sm"
                                onClick={handleResetParameters}
                                title="Сбросить параметры"
                                style={{
                                    minWidth: '32px',
                                    height: '32px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center'
                                }}
                            >
                                <i className="fas fa-undo" style={{ fontSize: '12px' }}></i>
                            </button>
                        </div>
                        <input
                            type="text"
                            className="form-control form-control-sm mb-2 bg-dark text-light"
                            placeholder="Поиск параметра..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                        />
                        <div style={{ maxHeight: 180, overflowY: 'auto' }}>
                            {filteredFilterOptions.map(group => (
                                <div key={group.group} className="mb-2">
                                    <div className="fw-bold small mb-1">{group.group}</div>
                                    {group.options.map(opt => (
                                        <div key={opt.value} className="form-check">
                                            <input
                                                className="form-check-input"
                                                type="radio"
                                                name="filterOption"
                                                id={opt.value + shopType}
                                                checked={selectedFilter === opt.value}
                                                onChange={() => setSelectedFilter(opt.value)}
                                            />
                                            <label className="form-check-label" htmlFor={opt.value + shopType}>
                                                {opt.label}
                                            </label>
                                        </div>
                                    ))}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ShopSummaryWidget; 