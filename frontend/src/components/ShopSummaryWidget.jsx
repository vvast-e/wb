import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import DateRangePicker from './DateRangePicker';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LabelList
} from 'recharts';
import api from '../api';
import { eachDayOfInterval, format } from 'date-fns';

const filterOptions = [
    {
        group: 'Тип', options: [
            { label: 'Негативные', value: 'negative', color: '#0dcaf0' },
            { label: 'Доля негативных', value: 'negative_share', color: '#82ca9d' },
            { label: 'Удалённые', value: 'deleted', color: '#ff7300' },
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
    {
        group: 'Удаленные', options: [
            { label: 'Удаленные', value: 'deleted' },
            { label: 'Доля удаленных от', value: 'deleted_share' },
        ]
    },
    {
        group: 'Итоговый рейтинг', options: [
            { label: '5.0', value: '5.0' },
            { label: '4.9', value: '4.9' },
            { label: '4.8', value: '4.8' },
            { label: '4.7', value: '4.7' },
            { label: '4.6', value: '4.6' },
            { label: '4.5', value: '4.5' },
            { label: '< 4.5', value: '<4.5' },
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
    const [loadingTops, setLoadingTops] = useState(false);

    const [errorBrands, setErrorBrands] = useState(null);
    const [errorProducts, setErrorProducts] = useState(null);
    const [errorChart, setErrorChart] = useState(null);
    const [errorTops, setErrorTops] = useState(null);

    const [chartData, setChartData] = useState([]);
    const [totalReviews, setTotalReviews] = useState(0);
    const [topsProducts, setTopsProducts] = useState([]);
    const [topsReasons, setTopsReasons] = useState([]);

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
        api.get(`${API_URL}/products`, {
            params: { shop: shopType, brand_id: selectedBrand },
            headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        })
            .then(res => setProducts(res.data))
            .catch(e => {
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
        return selectedProducts.map(productId => {
            const product = products.find(p => p.id === productId);
            return product ? `${selectedFilter}_${productId}` : null;
        }).filter(Boolean);
    }, [selectedFilter, selectedProducts, products]);

    const barColors = useMemo(() => {
        const colors = ['#0dcaf0', '#82ca9d', '#ff7300', '#ffc107', '#dc3545', '#6f42c1', '#fd7e14', '#20c997'];
        return chartKeys.map((key, index) => ({
            key,
            color: colors[index % colors.length]
        }));
    }, [chartKeys]);

    // --- Получение данных для графика ---
    useEffect(() => {
        if (!dateRange.startDate || !dateRange.endDate || chartKeys.length === 0) {
            setChartData([]);
            setTotalReviews(0);
            return;
        }
        setLoadingChart(true);
        setErrorChart(null);

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
            return api.get(`${API_URL}/reviews/summary`, {
                params,
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
            });
        });

        Promise.all(requests)
            .then(responses => {
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

                setChartData(Object.values(allData));
                setTotalReviews(totalReviewsSum);
            })
            .catch(e => {
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

    // --- Получение топов ---
    useEffect(() => {
        if (!dateRange.startDate || !dateRange.endDate) {
            setTopsProducts([]);
            setTopsReasons([]);
            return;
        }
        setLoadingTops(true);
        setErrorTops(null);
        const paramsBase = {
            shop: shopType,
            brand_id: selectedBrand || undefined,
            product_ids: selectedProducts.length > 0 ? selectedProducts.join(',') : undefined,
            date_from: dateRange.startDate,
            date_to: dateRange.endDate,
        };
        const token = localStorage.getItem('token');
        Promise.all([
            api.get(`${API_URL}/reviews/tops`, {
                params: { ...paramsBase, type: 'products_negative' },
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
            }),
            api.get(`${API_URL}/reviews/tops`, {
                params: { ...paramsBase, type: 'reasons_negative' },
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
            })
        ])
            .then(([productsRes, reasonsRes]) => {
                setTopsProducts(productsRes.data || []);
                setTopsReasons(reasonsRes.data || []);
            })
            .catch(e => {
                if (e.response?.status === 404) {
                    setErrorTops('Топы не найдены');
                } else if (e.response?.status === 500) {
                    setErrorTops('Ошибка сервера');
                } else {
                    setErrorTops('Ошибка загрузки топов');
                }
            })
            .finally(() => setLoadingTops(false));
    }, [shopType, selectedBrand, selectedProducts, dateRange]);

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
        if (!selectedProducts.includes(productId)) {
            setSelectedProducts([...selectedProducts, productId]);
        }
    };

    const removeProduct = (productId) => {
        setSelectedProducts(selectedProducts.filter(id => id !== productId));
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

    // --- UI ---
    return (
        <div className="bg-dark text-light rounded p-4 mb-4" style={{ border: '1.5px solid #21c55d' }}>
            <div className="d-flex justify-content-between align-items-center mb-3">
                <h4 className="mb-0">{shopType === 'wb' ? 'Wildberries' : 'Ozon'} — краткая сводка</h4>
                <button
                    className="btn btn-outline-success btn-sm"
                    onClick={handleOpenShop}
                    title={`Открыть страницу ${shopType === 'wb' ? 'Wildberries' : 'Ozon'}`}
                >
                    <i className="fas fa-external-link-alt me-1"></i>
                    Открыть магазин
                </button>
            </div>

            {/* Верхний блок с фильтрами */}
            <div className="d-flex gap-3 mb-3 align-items-end">
                <div>
                    <label>Бренд:</label><br />
                    {loadingBrands ? (
                        <div className="text-muted">Загрузка...</div>
                    ) : errorBrands ? (
                        <div className="text-danger small">{errorBrands}</div>
                    ) : (
                        <select
                            className="form-select bg-secondary text-light"
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
                    <label>Товары:</label><br />
                    {loadingProducts ? (
                        <div className="text-muted">Загрузка...</div>
                    ) : errorProducts ? (
                        <div className="text-danger small">{errorProducts}</div>
                    ) : (
                        <select
                            className="form-select bg-secondary text-light"
                            value=""
                            onChange={e => {
                                if (e.target.value) {
                                    addProduct(e.target.value);
                                    e.target.value = "";
                                }
                            }}
                            disabled={!selectedBrand}
                        >
                            <option value="">Добавить товар</option>
                            {products.filter(p => !selectedProducts.includes(p.id)).map(p =>
                                <option key={p.id} value={p.id}>{p.name}</option>
                            )}
                        </select>
                    )}
                </div>
                <div>
                    <label>Период:</label><br />
                    <DateRangePicker
                        onDateChange={(start, end) => setDateRange({ startDate: start, endDate: end })}
                        initialStartDate={dateRange.startDate}
                        initialEndDate={dateRange.endDate}
                    />
                </div>
                <div>
                    <label>Всего отзывов:</label>
                    <div className="fs-5 fw-bold">{loadingChart ? '...' : totalReviews}</div>
                </div>
            </div>

            {/* Выбранные товары */}
            {selectedProducts.length > 0 && (
                <div className="mb-3">
                    <label className="fw-bold">Выбранные товары:</label>
                    <div className="d-flex flex-wrap gap-2 mt-2">
                        {getSelectedProductNames().map((name, index) => (
                            <div key={selectedProducts[index]} className="badge bg-success d-flex align-items-center">
                                <span className="me-2">{name}</span>
                                <button
                                    type="button"
                                    className="btn-close btn-close-white"
                                    style={{ fontSize: '0.5em' }}
                                    onClick={() => removeProduct(selectedProducts[index])}
                                    aria-label="Удалить товар"
                                ></button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Основной контент - график и параметры */}
            <div className="d-flex gap-4">
                {/* График - увеличенный */}
                <div className="flex-grow-1 bg-secondary rounded p-3" style={{ minWidth: 0 }}>
                    {errorChart ? (
                        <div className="text-danger text-center">{errorChart}</div>
                    ) : loadingChart ? (
                        <div className="text-center text-muted">Загрузка...</div>
                    ) : (dateRange.startDate && dateRange.endDate && chartKeys.length > 0 && mergedChartData.length > 0) ? (
                        <div style={{ width: '100%', overflowX: 'auto' }}>
                            <div style={{ width: Math.max(mergedChartData.length * 70, 500) }}>
                                <ResponsiveContainer width="100%" height={400}>
                                    <BarChart
                                        data={mergedChartData}
                                        margin={{ top: 20, right: 30, left: 10, bottom: 30 }}
                                        barGap={8}
                                    >
                                        <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                                        <XAxis dataKey="date" stroke="#fff" />
                                        <YAxis stroke="#fff" />
                                        <Tooltip formatter={(value) => value} />
                                        <Legend />
                                        {barColors.map(({ key, color }, index) => {
                                            const productName = getLegendNames()[index];
                                            return (
                                                <Bar key={key} dataKey={key} fill={color} radius={[4, 4, 0, 0]} name={productName}>
                                                    <LabelList dataKey={key} position="top" fill="#fff" fontSize={13} />
                                                </Bar>
                                            );
                                        })}
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center text-muted">Выберите период и параметр для отображения</div>
                    )}
                </div>

                {/* Параметр отображения - справа на весь виджет */}
                <div style={{ width: 300 }}>
                    <div className="bg-secondary rounded p-3 h-100">
                        <h6 className="mb-3 fw-bold">Параметр для отображения:</h6>
                        <input
                            type="text"
                            className="form-control mb-3 bg-dark text-light"
                            placeholder="Поиск параметра..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                        />
                        <div style={{ maxHeight: 200, overflowY: 'auto' }}>
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

                        {/* Топы под параметрами */}
                        <div className="mt-4">
                            {errorTops ? (
                                <div className="text-danger">{errorTops}</div>
                            ) : loadingTops ? (
                                <div className="text-muted">Загрузка...</div>
                            ) : (
                                <>
                                    <div className="mb-3">
                                        <div className="fw-bold mb-2 text-light">Топ товаров по количеству негатива</div>
                                        <ol className="ps-3 mb-0">
                                            {topsProducts.map((item, idx) => (
                                                <li key={item.name} className="small d-flex justify-content-between align-items-center mb-1">
                                                    <span>{item.name}</span>
                                                    <span className="badge bg-success ms-2">{item.value}</span>
                                                </li>
                                            ))}
                                        </ol>
                                    </div>
                                    <div className="mb-3">
                                        <div className="fw-bold mb-2 text-light">Топ причин негатива</div>
                                        <ol className="ps-3 mb-0">
                                            {topsReasons.map((item, idx) => (
                                                <li key={item.name} className="small d-flex justify-content-between align-items-center mb-1">
                                                    <span>{item.name}</span>
                                                    <span className="badge bg-success ms-2">{item.value}</span>
                                                </li>
                                            ))}
                                        </ol>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ShopSummaryWidget; 