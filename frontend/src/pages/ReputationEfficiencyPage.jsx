import React, { useState, useEffect } from 'react';
import { Container, Card, Row, Col, Form, Spinner, Alert, Badge, ProgressBar } from 'react-bootstrap';
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
    const [selectedProduct, setSelectedProduct] = useState('');
    const [efficiencyData, setEfficiencyData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [selectedMetrics, setSelectedMetrics] = useState([]);
    const [dateRange, setDateRange] = useState({
        startDate: '',
        endDate: ''
    });

    useEffect(() => {
        fetchShops();
    }, []);

    useEffect(() => {
        if (selectedShop) {
            fetchProducts();
        } else {
            setProducts([]);
            setSelectedProduct('');
        }
    }, [selectedShop]);

    useEffect(() => {
        if (selectedShop && dateRange.startDate && dateRange.endDate) {
            fetchEfficiencyData();
        }
    }, [selectedShop, selectedProduct, dateRange]);

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
            const params = {
                start_date: dateRange.startDate,
                end_date: dateRange.endDate
            };

            if (selectedProduct) {
                params.product_id = selectedProduct;
            }

            const response = await api.get(`/analytics/efficiency/${selectedShop}`, {
                headers: { 'Authorization': `Bearer ${token}` },
                params
            });
            setEfficiencyData(response.data);
        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка при загрузке данных эффективности');
        } finally {
            setLoading(false);
        }
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
        if (!efficiencyData || selectedMetrics.length === 0) {
            return null;
        }

        // Если есть тренды, используем их для графика по времени
        if (efficiencyData.trends && efficiencyData.trends.length > 0) {
            const datasets = selectedMetrics.map((metric, index) => {
                const colors = ['#ff6384', '#36a2eb', '#cc65fe', '#ffce56', '#4bc0c0', '#9966ff'];
                const color = colors[index % colors.length];

                let data = [];
                let label = metric.name;

                // Используем тренды для построения графика по времени
                if (metric.key === 'negative_percentage') {
                    data = efficiencyData.trends.map(t => t.negative_percent);
                    label = 'Доля негативных (%)';
                } else if (metric.key === 'deleted_percentage') {
                    data = efficiencyData.trends.map(t => t.deleted_percent);
                    label = 'Доля удаленных (%)';
                } else if (metric.key.includes('top_') || metric.key === 'deletion_time') {
                    // Для времени используем среднее значение за период
                    const timeStr = efficiencyData[metric.key] || '0ч 00мин';
                    const hours = parseFloat(timeStr.replace('ч', '').replace('мин', '').split(' ')[0]);
                    const minutes = parseFloat(timeStr.replace('ч', '').replace('мин', '').split(' ')[1] || 0);
                    const avgHours = hours + minutes / 60;
                    data = efficiencyData.trends.map(() => avgHours);
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
            // Если нет трендов, показываем текущие значения
            const datasets = selectedMetrics.map((metric, index) => {
                const colors = ['#ff6384', '#36a2eb', '#cc65fe', '#ffce56', '#4bc0c0', '#9966ff'];
                const color = colors[index % colors.length];

                let data = [];
                let label = metric.name;

                if (metric.key === 'negative_percentage') {
                    data = [efficiencyData.negative_count / efficiencyData.total_reviews * 100];
                    label = 'Доля негативных (%)';
                } else if (metric.key === 'deleted_percentage') {
                    data = [efficiencyData.deleted_count / efficiencyData.total_reviews * 100];
                    label = 'Доля удаленных (%)';
                } else if (metric.key.includes('top_') || metric.key === 'deletion_time') {
                    const timeStr = efficiencyData[metric.key] || '0ч 00мин';
                    const hours = parseFloat(timeStr.replace('ч', '').replace('мин', '').split(' ')[0]);
                    const minutes = parseFloat(timeStr.replace('ч', '').replace('мин', '').split(' ')[1] || 0);
                    data = [hours + minutes / 60];
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
                        <Form.Label className="text-light">Выберите товар</Form.Label>
                        <Form.Select
                            value={selectedProduct}
                            onChange={(e) => setSelectedProduct(e.target.value)}
                            className="bg-dark border-success text-light"
                            disabled={!selectedShop}
                        >
                            <option value="">Все товары</option>
                            {products.map(p =>
                                <option key={p.id} value={p.id}>{p.id}</option>
                            )}
                        </Form.Select>
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

            {efficiencyData && !loading && (
                <>
                    {/* Основные метрики */}
                    <Row className="mb-3">
                        <Col md={4}>
                            <Card className="bg-dark border-success text-center">
                                <Card.Body className="py-3">
                                    <h2 className="text-light mb-1 fw-bold">{formatNumber(efficiencyData.total_reviews)}</h2>
                                    <p className="text-light mb-0 small">Всего отзывов</p>
                                </Card.Body>
                            </Card>
                        </Col>
                        <Col md={4}>
                            <Card className="bg-dark border-success text-center">
                                <Card.Body className="py-3">
                                    <h2 className="text-light mb-1 fw-bold">{formatNumber(efficiencyData.negative_count)}</h2>
                                    <p className="text-light mb-0 small">Негативных</p>
                                </Card.Body>
                            </Card>
                        </Col>
                        <Col md={4}>
                            <Card className="bg-dark border-success text-center">
                                <Card.Body className="py-3">
                                    <h2 className="text-light mb-1 fw-bold">{formatNumber(efficiencyData.deleted_count)}</h2>
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
                                            <span className="text-light fw-bold">{formatPercentage(efficiencyData.negative_count / efficiencyData.total_reviews)}</span>
                                        </div>
                                    </div>
                                    <div className="mb-2">
                                        <div
                                            className={`d-flex justify-content-between align-items-center p-2 rounded cursor-pointer ${isMetricSelected('deleted_percentage') ? 'bg-success' : 'bg-secondary'}`}
                                            onClick={() => handleMetricClick('deleted_percentage', 'Доля удаленных')}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <span className="text-light small">Доля удаленных:</span>
                                            <span className="text-light fw-bold">{formatPercentage(efficiencyData.deleted_count / efficiencyData.total_reviews)}</span>
                                        </div>
                                    </div>
                                    <div className="mb-2">
                                        <div
                                            className={`d-flex justify-content-between align-items-center p-2 rounded cursor-pointer ${isMetricSelected('top_1_time') ? 'bg-success' : 'bg-secondary'}`}
                                            onClick={() => handleMetricClick('top_1_time', 'Среднее время пребывания негатива в ТОП 1')}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <span className="text-light small">Время в ТОП 1:</span>
                                            <span className="text-light fw-bold">{efficiencyData.top_1_time || '0ч 00мин'}</span>
                                        </div>
                                    </div>
                                    <div className="mb-2">
                                        <div
                                            className={`d-flex justify-content-between align-items-center p-2 rounded cursor-pointer ${isMetricSelected('top_3_time') ? 'bg-success' : 'bg-secondary'}`}
                                            onClick={() => handleMetricClick('top_3_time', 'Среднее время пребывания негатива в ТОП 3')}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <span className="text-light small">Время в ТОП 3:</span>
                                            <span className="text-light fw-bold">{efficiencyData.top_3_time || '0ч 00мин'}</span>
                                        </div>
                                    </div>
                                    <div className="mb-2">
                                        <div
                                            className={`d-flex justify-content-between align-items-center p-2 rounded cursor-pointer ${isMetricSelected('top_5_time') ? 'bg-success' : 'bg-secondary'}`}
                                            onClick={() => handleMetricClick('top_5_time', 'Среднее время пребывания негатива в ТОП 5')}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <span className="text-light small">Время в ТОП 5:</span>
                                            <span className="text-light fw-bold">{efficiencyData.top_5_time || '0ч 00мин'}</span>
                                        </div>
                                    </div>
                                    <div className="mb-2">
                                        <div
                                            className={`d-flex justify-content-between align-items-center p-2 rounded cursor-pointer ${isMetricSelected('top_10_time') ? 'bg-success' : 'bg-secondary'}`}
                                            onClick={() => handleMetricClick('top_10_time', 'Среднее время пребывания негатива в ТОП 10')}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <span className="text-light small">Время в ТОП 10:</span>
                                            <span className="text-light fw-bold">{efficiencyData.top_10_time || '0ч 00мин'}</span>
                                        </div>
                                    </div>
                                    <div className="mb-2">
                                        <div
                                            className={`d-flex justify-content-between align-items-center p-2 rounded cursor-pointer ${isMetricSelected('deletion_time') ? 'bg-success' : 'bg-secondary'}`}
                                            onClick={() => handleMetricClick('deletion_time', 'Среднее время удаления негатива')}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <span className="text-light small">Время удаления:</span>
                                            <span className="text-light fw-bold">{efficiencyData.deletion_time || '0ч 00мин'}</span>
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
                                        const count = efficiencyData.ratings_distribution?.[`rating_${rating}`] || 0;
                                        const percentage = efficiencyData.total_reviews > 0
                                            ? (count / efficiencyData.total_reviews) * 100
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
                                                {efficiencyData.total_reviews > 0
                                                    ? (((efficiencyData.ratings_distribution?.[`rating_5`] || 0) * 5 +
                                                        (efficiencyData.ratings_distribution?.[`rating_4`] || 0) * 4 +
                                                        (efficiencyData.ratings_distribution?.[`rating_3`] || 0) * 3 +
                                                        (efficiencyData.ratings_distribution?.[`rating_2`] || 0) * 2 +
                                                        (efficiencyData.ratings_distribution?.[`rating_1`] || 0) * 1) / efficiencyData.total_reviews).toFixed(1)
                                                    : '0.0'}★
                                            </span>
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between align-items-center p-2 bg-secondary rounded">
                                            <span className="text-light small">5★ отзывы</span>
                                            <span className="text-light fw-bold fs-5">
                                                {efficiencyData.ratings_distribution?.[`rating_5`] || 0}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between align-items-center p-2 bg-secondary rounded">
                                            <span className="text-light small">1-2★ отзывы</span>
                                            <span className="text-light fw-bold fs-5">
                                                {(efficiencyData.ratings_distribution?.[`rating_1`] || 0) + (efficiencyData.ratings_distribution?.[`rating_2`] || 0)}
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