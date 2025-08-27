import React, { useState, useEffect } from 'react';
import { Container, Card, Row, Col, Form, Spinner, Alert, Badge, ProgressBar } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
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
import DateRangePicker from '../components/DateRangePicker';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
);

const ReputationEfficiencyPage = () => {
    const [shops, setShops] = useState([]);
    const [products, setProducts] = useState([]);
    const [selectedShop, setSelectedShop] = useState('');
    const [selectedProducts, setSelectedProducts] = useState([]); // мультивыбор товаров
    const [productSearchTerm, setProductSearchTerm] = useState(''); // поиск по товарам
    const [efficiencyData, setEfficiencyData] = useState(null); // данные для одиночного режима или агрегата
    const [efficiencyDataByProduct, setEfficiencyDataByProduct] = useState(null); // данные по каждому товару при сравнении
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [selectedMetrics, setSelectedMetrics] = useState([]);
    const [dateRange, setDateRange] = useState({
        startDate: '',
        endDate: ''
    });

    const navigate = useNavigate();

    // Утилиты для времени HH:MM:SS
    const parseTimeToSeconds = (timeStr) => {
        if (!timeStr) return 0;
        const [hh = '0', mm = '0', ss = '0'] = String(timeStr).split(':');
        const h = parseFloat(hh) || 0;
        const m = parseFloat(mm) || 0;
        const s = parseFloat(ss) || 0;
        return h * 3600 + m * 60 + s;
    };

    const formatSecondsToHHMMSS = (totalSeconds) => {
        const sec = Math.max(0, Math.round(totalSeconds || 0));
        const h = Math.floor(sec / 3600);
        const m = Math.floor((sec % 3600) / 60);
        const s = sec % 60;
        const pad = (n) => String(n).padStart(2, '0');
        return `${pad(h)}:${pad(m)}:${pad(s)}`;
    };

    useEffect(() => {
        fetchShops();
    }, []);

    useEffect(() => {
        if (selectedShop) {
            fetchProducts();
        } else {
            setProducts([]);
            setSelectedProducts([]);
            setProductSearchTerm('');
        }
    }, [selectedShop]);

    useEffect(() => {
        if (selectedShop && dateRange.startDate && dateRange.endDate) {
            fetchEfficiencyData();
        }
    }, [selectedShop, selectedProducts, dateRange]);

    const fetchShops = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await api.get(`/analytics/shops`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            setShops(response.data);
        } catch (err) {
            setError('Ошибка при загрузке магазинов');
        }
    };

    const fetchProducts = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await api.get(`/analytics/shop/${selectedShop}/products`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            setProducts(response.data);
        } catch (err) {
            console.error('Ошибка при загрузке товаров:', err);
        }
    };

    const fetchEfficiencyData = async () => {
        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem('token');
            const baseParams = {
                start_date: dateRange.startDate,
                end_date: dateRange.endDate
            };

            // Нет выбранных товаров → агрегат по магазину (как сейчас)
            if (!selectedProducts || selectedProducts.length === 0) {
                const response = await api.get(`/analytics/efficiency/${selectedShop}`, {
                    headers: { 'Authorization': `Bearer ${token}` },
                    params: baseParams
                });
                setEfficiencyData(response.data);
                setEfficiencyDataByProduct(null);
                return;
            }

            // Один товар → одиночный режим (как сейчас)
            if (selectedProducts.length === 1) {
                const response = await api.get(`/analytics/efficiency/${selectedShop}`, {
                    headers: { 'Authorization': `Bearer ${token}` },
                    params: { ...baseParams, product_id: selectedProducts[0] }
                });
                setEfficiencyData(response.data);
                setEfficiencyDataByProduct(null);
                return;
            }

            // Несколько товаров → сравнение, параллельные запросы
            const requests = selectedProducts.map(pid =>
                api.get(`/analytics/efficiency/${selectedShop}`, {
                    headers: { 'Authorization': `Bearer ${token}` },
                    params: { ...baseParams, product_id: pid }
                }).then(res => ({ pid, data: res.data }))
            );

            const results = await Promise.all(requests);
            const byProduct = {};
            results.forEach(({ pid, data }) => {
                byProduct[pid] = data;
            });
            setEfficiencyDataByProduct(byProduct);
            setEfficiencyData(null);
        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка при загрузке данных эффективности');
        } finally {
            setLoading(false);
        }
    };

    const navigateToReviewBase = (type) => {
        const params = new URLSearchParams();
        if (selectedShop) params.set('shop', selectedShop);
        if (selectedProducts && selectedProducts.length > 0) {
            params.set('product', selectedProducts.join(','));
        }
        if (dateRange.startDate) params.set('date_from', dateRange.startDate);
        if (dateRange.endDate) params.set('date_to', dateRange.endDate);

        if (type === 'negative') params.set('negative', 'true');
        if (type === 'deleted') params.set('deleted', 'true');

        navigate(`/analytics/review-analyzer?${params.toString()}`);
    };

    const handleDateChange = (startDate, endDate) => {
        setDateRange({ startDate, endDate });
    };

    const formatNumber = (num) => {
        return new Intl.NumberFormat('ru-RU').format(num);
    };

    const formatPercentage = (value) => {
        return `${(value * 100).toFixed(1)}%`;
    };

    const handleMetricClick = (metricKey, metricName) => {
        setSelectedMetrics(prev => {
            const isSelected = prev.find(m => m.key === metricKey);
            if (isSelected) {
                return prev.filter(m => m.key !== metricKey);
            } else if (prev.length < 2) {
                return [...prev, { key: metricKey, name: metricName }];
            }
            return prev;
        });
    };

    const isMetricSelected = (metricKey) => {
        return selectedMetrics.find(m => m.key === metricKey);
    };

    const prepareChartData = () => {
        if (selectedMetrics.length === 0) {
            return null;
        }

        const colors = ['#ff6384', '#36a2eb', '#cc65fe', '#ffce56', '#4bc0c0', '#9966ff'];

        // Режим сравнения: несколько товаров
        if (efficiencyDataByProduct && Object.keys(efficiencyDataByProduct).length > 1) {
            const productIds = Object.keys(efficiencyDataByProduct);
            const firstProduct = efficiencyDataByProduct[productIds[0]];
            const hasTrends = firstProduct?.trends && firstProduct.trends.length > 0;

            const datasets = [];
            productIds.forEach((pid, pIndex) => {
                const pdata = efficiencyDataByProduct[pid];
                selectedMetrics.forEach((metric, mIndex) => {
                    // Для временных метрик (часы) при сравнении 2+ товаров не строим линии по каждому товару
                    if (metric.key.includes('top_') || metric.key === 'deletion_time') {
                        return;
                    }
                    let data = [];
                    let label = `${pid} — ${metric.name}`;
                    if (hasTrends) {
                        if (metric.key === 'negative_percentage') {
                            data = pdata.trends.map(t => t.negative_percent);
                        } else if (metric.key === 'deleted_percentage') {
                            data = pdata.trends.map(t => t.deleted_percent);
                        }
                    } else {
                        if (metric.key === 'negative_percentage') {
                            const val = pdata.total_reviews > 0 ? (pdata.negative_count / pdata.total_reviews) * 100 : 0;
                            data = [val];
                        } else if (metric.key === 'deleted_percentage') {
                            const val = pdata.total_reviews > 0 ? (pdata.deleted_count / pdata.total_reviews) * 100 : 0;
                            data = [val];
                        }
                    }

                    datasets.push({
                        label,
                        data,
                        borderColor: colors[pIndex % colors.length],
                        backgroundColor: colors[pIndex % colors.length] + '20',
                        borderDash: mIndex === 1 ? [6, 4] : undefined,
                        tension: 0.1,
                        fill: false
                    });
                });
            });

            // Добавляем агрегированную (среднюю) линию для метрик времени при сравнении нескольких товаров
            selectedMetrics.forEach((metric) => {
                if (metric.key.includes('top_') || metric.key === 'deletion_time') {
                    // среднее по выбранным товарам
                    const values = productIds
                        .map(pid => efficiencyDataByProduct[pid]?.[metric.key])
                        .filter(Boolean)
                        .map(parseTimeToSeconds);
                    const avgSeconds = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0;
                    const avgHours = avgSeconds / 3600;
                    const pointsCount = (hasTrends ? (firstProduct.trends?.length || 1) : 1);
                    const data = Array(pointsCount).fill(avgHours);
                    datasets.push({
                        label: `Среднее — ${metric.name} (часы)`,
                        data,
                        borderColor: '#ffffff',
                        backgroundColor: '#ffffff20',
                        borderDash: [4, 4],
                        tension: 0.1,
                        fill: false
                    });
                }
            });

            return {
                labels: (hasTrends ? firstProduct.trends.map(t => t.date) : ['Текущий период']),
                datasets
            };
        }

        // Одиночный режим (как было)
        if (!efficiencyData) return null;

        if (efficiencyData.trends && efficiencyData.trends.length > 0) {
            const datasets = selectedMetrics.map((metric, index) => {
                const color = colors[index % colors.length];
                let data = [];
                let label = metric.name;
                if (metric.key === 'negative_percentage') {
                    data = efficiencyData.trends.map(t => t.negative_percent);
                    label = 'Доля негативных (%)';
                } else if (metric.key === 'deleted_percentage') {
                    data = efficiencyData.trends.map(t => t.deleted_percent);
                    label = 'Доля удаленных (%)';
                } else if (metric.key.includes('top_') || metric.key === 'deletion_time') {
                    const timeStr = efficiencyData[metric.key] || '00:00:00';
                    const timeParts = timeStr.split(':');
                    const hours = parseFloat(timeParts[0] || 0);
                    const minutes = parseFloat(timeParts[1] || 0);
                    const seconds = parseFloat(timeParts[2] || 0);
                    const totalHours = hours + minutes / 60 + seconds / 3600;
                    data = efficiencyData.trends.map(() => totalHours);
                    label = `${metric.name} (часы)`;
                }
                return {
                    label,
                    data,
                    borderColor: color,
                    backgroundColor: color + '20',
                    tension: 0.1,
                    fill: false
                };
            });
            return {
                labels: efficiencyData.trends.map(t => t.date),
                datasets
            };
        } else {
            const datasets = selectedMetrics.map((metric, index) => {
                const color = colors[index % colors.length];
                let data = [];
                let label = metric.name;
                if (metric.key === 'negative_percentage') {
                    data = [efficiencyData.total_reviews > 0 ? (efficiencyData.negative_count / efficiencyData.total_reviews) * 100 : 0];
                    label = 'Доля негативных (%)';
                } else if (metric.key === 'deleted_percentage') {
                    data = [efficiencyData.total_reviews > 0 ? (efficiencyData.deleted_count / efficiencyData.total_reviews) * 100 : 0];
                    label = 'Доля удаленных (%)';
                } else if (metric.key.includes('top_') || metric.key === 'deletion_time') {
                    const timeStr = efficiencyData[metric.key] || '00:00:00';
                    const timeParts = timeStr.split(':');
                    const hours = parseFloat(timeParts[0] || 0);
                    const minutes = parseFloat(timeParts[1] || 0);
                    const seconds = parseFloat(timeParts[2] || 0);
                    const totalHours = hours + minutes / 60 + seconds / 3600;
                    data = [totalHours];
                    label = `${metric.name} (часы)`;
                }
                return {
                    label,
                    data,
                    borderColor: color,
                    backgroundColor: color + '20',
                    tension: 0.1,
                    fill: false
                };
            });
            return {
                labels: ['Текущий период'],
                datasets
            };
        }
    };

    const computeAggregateForSelected = () => {
        if (!efficiencyDataByProduct) return null;
        const ids = Object.keys(efficiencyDataByProduct);
        if (ids.length === 0) return null;
        const aggregate = {
            total_reviews: 0,
            negative_count: 0,
            deleted_count: 0
        };
        ids.forEach(pid => {
            const d = efficiencyDataByProduct[pid];
            aggregate.total_reviews += d.total_reviews || 0;
            aggregate.negative_count += d.negative_count || 0;
            aggregate.deleted_count += d.deleted_count || 0;
        });
        return aggregate;
    };

    const computeAverageTimeForSelected = (timeKey) => {
        if (!efficiencyDataByProduct) return null;
        const ids = Object.keys(efficiencyDataByProduct);
        if (ids.length === 0) return null;
        const values = ids
            .map(pid => efficiencyDataByProduct[pid]?.[timeKey])
            .filter(Boolean)
            .map(parseTimeToSeconds);
        if (values.length === 0) return null;
        const avg = values.reduce((a, b) => a + b, 0) / values.length;
        return formatSecondsToHHMMSS(avg);
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
                text: 'Метрики эффективности',
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

    return (
        <Container className="py-4">
            <h2 className="text-light mb-4">Эффективность отдела репутации</h2>

            <Row className="mb-4">
                <Col md={6}>
                    <Form.Group className="mb-3">
                        <Form.Label className="text-light">Выберите магазин</Form.Label>
                        <Form.Select
                            value={selectedShop}
                            onChange={(e) => setSelectedShop(e.target.value)}
                            className="bg-dark border-success text-light"
                        >
                            <option value="">Выберите магазин...</option>
                            {shops.map(shop => (
                                <option key={shop.id} value={shop.id}>
                                    {shop.name}
                                </option>
                            ))}
                        </Form.Select>
                    </Form.Group>
                </Col>
                <Col md={6}>
                    <Form.Group className="mb-3">
                        <Form.Label className="text-light">Выберите товары</Form.Label>
                        <div className="bg-dark border border-success rounded p-2">
                            {products.length === 0 ? (
                                <small className="text-muted">Загружаем товары...</small>
                            ) : (
                                <>
                                    {/* Поиск */}
                                    <div className="mb-2">
                                        <Form.Control
                                            type="text"
                                            placeholder="Поиск товаров..."
                                            className="bg-dark border-success text-light"
                                            onChange={(e) => {
                                                const searchTerm = e.target.value.toLowerCase();
                                                setProductSearchTerm(searchTerm);
                                            }}
                                        />
                                    </div>

                                    {/* Статистика выбора */}
                                    <div className="d-flex justify-content-between align-items-center mb-2">
                                        <small className="text-muted">
                                            Выбрано: {selectedProducts.length} из {products.length}
                                        </small>
                                        <div>
                                            <button
                                                type="button"
                                                className="btn btn-sm btn-outline-success me-2"
                                                onClick={() => setSelectedProducts(products.map(p => p.id))}
                                            >
                                                Выбрать все
                                            </button>
                                            <button
                                                type="button"
                                                className="btn btn-sm btn-outline-secondary"
                                                onClick={() => setSelectedProducts([])}
                                            >
                                                Сброс
                                            </button>
                                        </div>
                                    </div>

                                    {/* Список товаров с прокруткой */}
                                    <div style={{ maxHeight: '150px', overflowY: 'auto' }}>
                                        {(() => {
                                            const filtered = products.filter(p => !productSearchTerm || p.id.toLowerCase().includes(productSearchTerm));
                                            const selectedSet = new Set(selectedProducts);
                                            const selectedList = filtered.filter(p => selectedSet.has(p.id));
                                            const unselectedList = filtered.filter(p => !selectedSet.has(p.id));
                                            const visible = [...selectedList, ...unselectedList];
                                            return visible.map(p => (
                                                <div key={p.id} className="mb-1">
                                                    <Form.Check
                                                        type="checkbox"
                                                        id={`product-${p.id}`}
                                                        label={p.id}
                                                        checked={selectedProducts.includes(p.id)}
                                                        onChange={(e) => {
                                                            if (e.target.checked) {
                                                                setSelectedProducts([...selectedProducts, p.id]);
                                                            } else {
                                                                setSelectedProducts(selectedProducts.filter(id => id !== p.id));
                                                            }
                                                        }}
                                                        className="text-light"
                                                    />
                                                </div>
                                            ));
                                        })()}
                                        {products.filter(p => !productSearchTerm || p.id.toLowerCase().includes(productSearchTerm)).length === 0 && (
                                            <small className="text-muted">Товары не найдены</small>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>
                        <small className="text-muted">Ничего не выбрано — показываем все товары; выберите 1+ для сравнения</small>
                    </Form.Group>
                </Col>
            </Row>

            {selectedShop && (
                <DateRangePicker
                    onDateChange={handleDateChange}
                    initialStartDate={dateRange.startDate}
                    initialEndDate={dateRange.endDate}
                />
            )}

            {error && (
                <Alert variant="danger" className="mb-4">
                    {error}
                </Alert>
            )}

            {loading && (
                <div className="d-flex justify-content-center mt-5">
                    <Spinner animation="border" variant="success" />
                </div>
            )}

            {(efficiencyData || efficiencyDataByProduct) && !loading && (
                <>
                    {/* Основные метрики */}
                    <Row className="mb-3">
                        <Col md={4}>
                            <Card className="bg-dark border-success text-center" onClick={() => navigateToReviewBase('all')} style={{ cursor: 'pointer' }}>
                                <Card.Body className="py-3">
                                    <h2 className="text-light mb-1 fw-bold">{formatNumber((efficiencyData?.total_reviews) ?? (computeAggregateForSelected()?.total_reviews || 0))}</h2>
                                    <p className="text-light mb-0 small">Всего отзывов</p>
                                </Card.Body>
                            </Card>
                        </Col>
                        <Col md={4}>
                            <Card className="bg-dark border-success text-center" onClick={() => navigateToReviewBase('negative')} style={{ cursor: 'pointer' }}>
                                <Card.Body className="py-3">
                                    <h2 className="text-light mb-1 fw-bold">{formatNumber((efficiencyData?.negative_count) ?? (computeAggregateForSelected()?.negative_count || 0))}</h2>
                                    <p className="text-light mb-0 small">Негативных</p>
                                </Card.Body>
                            </Card>
                        </Col>
                        <Col md={4}>
                            <Card className="bg-dark border-success text-center" onClick={() => navigateToReviewBase('deleted')} style={{ cursor: 'pointer' }}>
                                <Card.Body className="py-3">
                                    <h2 className="text-light mb-1 fw-bold">{formatNumber((efficiencyData?.deleted_count) ?? (computeAggregateForSelected()?.deleted_count || 0))}</h2>
                                    <p className="text-light mb-0 small">Удалено</p>
                                </Card.Body>
                            </Card>
                        </Col>
                    </Row>

                    {/* Список метрик и график */}
                    <Row className="mb-3">
                        <Col md={6}>
                            <Card className="bg-dark border-success">
                                <Card.Header className="bg-secondary text-light py-2">
                                    <h6 className="mb-0">Метрики эффективности</h6>
                                    <small className="text-muted">Кликните для добавления на график (максимум 2)</small>
                                </Card.Header>
                                <Card.Body>
                                    <div className="mb-2">
                                        <div
                                            className={`d-flex justify-content-between align-items-center p-2 rounded cursor-pointer ${isMetricSelected('negative_percentage') ? 'bg-success' : 'bg-secondary'}`}
                                            onClick={() => handleMetricClick('negative_percentage', 'Доля негативных')}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <span className="text-light small">Доля негативных:</span>
                                            <span className="text-light fw-bold">{
                                                efficiencyData ? formatPercentage(efficiencyData.total_reviews > 0 ? (efficiencyData.negative_count / efficiencyData.total_reviews) : 0)
                                                    : (() => {
                                                        const agg = computeAggregateForSelected();
                                                        if (!agg || agg.total_reviews === 0) return formatPercentage(0);
                                                        return formatPercentage(agg.negative_count / agg.total_reviews);
                                                    })()
                                            }</span>
                                        </div>
                                    </div>
                                    <div className="mb-2">
                                        <div
                                            className={`d-flex justify-content-between align-items-center p-2 rounded cursor-pointer ${isMetricSelected('deleted_percentage') ? 'bg-success' : 'bg-secondary'}`}
                                            onClick={() => handleMetricClick('deleted_percentage', 'Доля удаленных')}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <span className="text-light small">Доля удаленных:</span>
                                            <span className="text-light fw-bold">{
                                                efficiencyData ? formatPercentage(efficiencyData.total_reviews > 0 ? (efficiencyData.deleted_count / efficiencyData.total_reviews) : 0)
                                                    : (() => {
                                                        const agg = computeAggregateForSelected();
                                                        if (!agg || agg.total_reviews === 0) return formatPercentage(0);
                                                        return formatPercentage(agg.deleted_count / agg.total_reviews);
                                                    })()
                                            }</span>
                                        </div>
                                    </div>
                                    <div className="mb-2">
                                        <div
                                            className={`d-flex justify-content-between align-items-center p-2 rounded cursor-pointer ${isMetricSelected('top_1_time') ? 'bg-success' : 'bg-secondary'}`}
                                            onClick={() => handleMetricClick('top_1_time', 'Среднее время пребывания негатива в ТОП 1')}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <span className="text-light small">Время в ТОП 1:</span>
                                            <span className="text-light fw-bold">{
                                                efficiencyData?.top_1_time || computeAverageTimeForSelected('top_1_time') || '—'
                                            }</span>
                                        </div>
                                    </div>
                                    <div className="mb-2">
                                        <div
                                            className={`d-flex justify-content-between align-items-center p-2 rounded cursor-pointer ${isMetricSelected('top_3_time') ? 'bg-success' : 'bg-secondary'}`}
                                            onClick={() => handleMetricClick('top_3_time', 'Среднее время пребывания негатива в ТОП 3')}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <span className="text-light small">Время в ТОП 3:</span>
                                            <span className="text-light fw-bold">{
                                                efficiencyData?.top_3_time || computeAverageTimeForSelected('top_3_time') || '—'
                                            }</span>
                                        </div>
                                    </div>
                                    <div className="mb-2">
                                        <div
                                            className={`d-flex justify-content-between align-items-center p-2 rounded cursor-pointer ${isMetricSelected('top_5_time') ? 'bg-success' : 'bg-secondary'}`}
                                            onClick={() => handleMetricClick('top_5_time', 'Среднее время пребывания негатива в ТОП 5')}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <span className="text-light small">Время в ТОП 5:</span>
                                            <span className="text-light fw-bold">{
                                                efficiencyData?.top_5_time || computeAverageTimeForSelected('top_5_time') || '—'
                                            }</span>
                                        </div>
                                    </div>
                                    <div className="mb-2">
                                        <div
                                            className={`d-flex justify-content-between align-items-center p-2 rounded cursor-pointer ${isMetricSelected('top_10_time') ? 'bg-success' : 'bg-secondary'}`}
                                            onClick={() => handleMetricClick('top_10_time', 'Среднее время пребывания негатива в ТОП 10')}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <span className="text-light small">Время в ТОП 10:</span>
                                            <span className="text-light fw-bold">{
                                                efficiencyData?.top_10_time || computeAverageTimeForSelected('top_10_time') || '—'
                                            }</span>
                                        </div>
                                    </div>
                                    <div className="mb-2">
                                        <div
                                            className={`d-flex justify-content-between align-items-center p-2 rounded cursor-pointer ${isMetricSelected('deletion_time') ? 'bg-success' : 'bg-secondary'}`}
                                            onClick={() => handleMetricClick('deletion_time', 'Среднее время удаления негатива')}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <span className="text-light small">Время удаления:</span>
                                            <span className="text-light fw-bold">{
                                                efficiencyData?.deletion_time || computeAverageTimeForSelected('deletion_time') || '—'
                                            }</span>
                                        </div>
                                    </div>
                                </Card.Body>
                            </Card>
                        </Col>
                        <Col md={6}>
                            <Card className="bg-dark border-success">
                                <Card.Header className="bg-secondary text-light py-2">
                                    <h6 className="mb-0">График метрик</h6>
                                    {selectedMetrics.length > 0 && (
                                        <small className="text-muted">
                                            Выбрано: {selectedMetrics.map(m => m.name).join(', ')}
                                        </small>
                                    )}
                                </Card.Header>
                                <Card.Body>
                                    {selectedMetrics.length > 0 ? (
                                        <div style={{ height: '250px' }}>
                                            <Line data={prepareChartData()} options={chartOptions} />
                                        </div>
                                    ) : (
                                        <p className="text-muted text-center">Выберите метрики для отображения на графике</p>
                                    )}
                                </Card.Body>
                            </Card>
                        </Col>
                    </Row>

                    {/* Детальная статистика */}
                    <Card className="bg-dark border-success">
                        <Card.Header className="bg-secondary text-light py-2">
                            <h6 className="mb-0">Детальная статистика</h6>
                        </Card.Header>
                        <Card.Body>
                            <Row>
                                <Col md={8}>
                                    <h6 className="text-light mb-3">Распределение по рейтингам</h6>
                                    {[5, 4, 3, 2, 1].map(rating => {
                                        const totalReviews = (efficiencyData?.total_reviews) ?? (computeAggregateForSelected()?.total_reviews || 0);
                                        const count = efficiencyData?.ratings_distribution?.[`rating_${rating}`] || 0; // в режиме сравнения детальная раскладка по сумме недоступна → показываем только если одиночный режим
                                        const percentage = totalReviews > 0
                                            ? (count / totalReviews) * 100
                                            : 0;

                                        return (
                                            <div key={rating} className="mb-2">
                                                <div className="d-flex justify-content-between align-items-center mb-1">
                                                    <span className="text-light fw-bold">{rating}★</span>
                                                    <span className="text-light fw-bold">
                                                        {formatNumber(count)} ({percentage.toFixed(1)}%)
                                                    </span>
                                                </div>
                                                <ProgressBar
                                                    now={percentage}
                                                    variant={rating >= 4 ? 'success' : rating >= 3 ? 'warning' : 'danger'}
                                                />
                                            </div>
                                        );
                                    })}
                                </Col>
                                <Col md={4}>
                                    <h6 className="text-light mb-3">Быстрая статистика</h6>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between align-items-center p-2 bg-secondary rounded">
                                            <span className="text-light small">Средний рейтинг</span>
                                            <span className="text-light fw-bold fs-5">
                                                {efficiencyData?.total_reviews > 0
                                                    ? (((efficiencyData.ratings_distribution?.[`rating_5`] || 0) * 5 +
                                                        (efficiencyData.ratings_distribution?.[`rating_4`] || 0) * 4 +
                                                        (efficiencyData.ratings_distribution?.[`rating_3`] || 0) * 3 +
                                                        (efficiencyData.ratings_distribution?.[`rating_2`] || 0) * 2 +
                                                        (efficiencyData.ratings_distribution?.[`rating_1`] || 0) * 1) / efficiencyData.total_reviews).toFixed(1)
                                                    : '—'}★
                                            </span>
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between align-items-center p-2 bg-secondary rounded">
                                            <span className="text-light small">5★ отзывы</span>
                                            <span className="text-light fw-bold fs-5">
                                                {efficiencyData?.ratings_distribution?.[`rating_5`] || '—'}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between align-items-center p-2 bg-secondary rounded">
                                            <span className="text-light small">1-2★ отзывы</span>
                                            <span className="text-light fw-bold fs-5">
                                                {efficiencyData ? ((efficiencyData.ratings_distribution?.[`rating_1`] || 0) + (efficiencyData.ratings_distribution?.[`rating_2`] || 0)) : '—'}
                                            </span>
                                        </div>
                                    </div>
                                </Col>
                            </Row>
                        </Card.Body>
                    </Card>
                </>
            )}

            {!selectedShop && (
                <Alert variant="info" className="text-center">
                    Выберите магазин для просмотра эффективности
                </Alert>
            )}
        </Container>
    );
};

export default ReputationEfficiencyPage; 