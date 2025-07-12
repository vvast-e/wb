import React, { useState, useEffect } from 'react';
import { Container, Card, Row, Col, Form, Spinner, Alert, Badge, ProgressBar } from 'react-bootstrap';
import axios from 'axios';
import DateRangePicker from '../components/DateRangePicker';

const ReputationEfficiencyPage = () => {
    const [shops, setShops] = useState([]);
    const [products, setProducts] = useState([]);
    const [selectedShop, setSelectedShop] = useState('');
    const [selectedProduct, setSelectedProduct] = useState('');
    const [efficiencyData, setEfficiencyData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
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
            const response = await axios.get(`${import.meta.env.VITE_API_URL}/analytics/shops`, {
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
            const response = await axios.get(`${import.meta.env.VITE_API_URL}/analytics/shop/${selectedShop}/products`, {
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

            const response = await axios.get(`${import.meta.env.VITE_API_URL}/analytics/efficiency/${selectedShop}`, {
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
                        <Form.Label className="text-light">Выберите товар (опционально)</Form.Label>
                        <Form.Select
                            value={selectedProduct}
                            onChange={(e) => setSelectedProduct(e.target.value)}
                            className="bg-dark border-success text-light"
                            disabled={!selectedShop}
                        >
                            <option value="">Все товары</option>
                            {products.filter(p => !selectedProduct || p.id !== selectedProduct).map(p =>
                                <option key={p.id} value={p.id}>{p.name}</option>
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
                    <Row className="mb-4">
                        <Col md={4}>
                            <Card className="bg-dark border-success text-center">
                                <Card.Body>
                                    <h4 className="text-danger">{formatPercentage(efficiencyData.negative_percentage)}</h4>
                                    <p className="text-light mb-0">Доля негативных отзывов</p>
                                    <small className="text-muted">
                                        {formatNumber(efficiencyData.negative_count)} из {formatNumber(efficiencyData.total_reviews)}
                                    </small>
                                </Card.Body>
                            </Card>
                        </Col>
                        <Col md={4}>
                            <Card className="bg-dark border-success text-center">
                                <Card.Body>
                                    <h4 className="text-warning">{formatPercentage(efficiencyData.deleted_percentage)}</h4>
                                    <p className="text-light mb-0">Доля удаленных отзывов</p>
                                    <small className="text-muted">
                                        {formatNumber(efficiencyData.deleted_count)} из {formatNumber(efficiencyData.total_reviews)}
                                    </small>
                                </Card.Body>
                            </Card>
                        </Col>
                        <Col md={4}>
                            <Card className="bg-dark border-success text-center">
                                <Card.Body>
                                    <h4 className="text-success">{formatNumber(efficiencyData.response_time_avg)}</h4>
                                    <p className="text-light mb-0">Среднее время ответа (часы)</p>
                                </Card.Body>
                            </Card>
                        </Col>
                    </Row>

                    {/* Графики по времени */}
                    <Row className="mb-4">
                        <Col md={6}>
                            <Card className="bg-dark border-success">
                                <Card.Header className="bg-secondary text-light">
                                    <h5 className="mb-0">Динамика негативных отзывов</h5>
                                </Card.Header>
                                <Card.Body>
                                    {efficiencyData.negative_trend?.map((item, index) => (
                                        <div key={index} className="mb-3">
                                            <div className="d-flex justify-content-between align-items-center mb-1">
                                                <span className="text-light">{item.date}</span>
                                                <span className="text-light">{item.count}</span>
                                            </div>
                                            <ProgressBar
                                                now={(item.count / Math.max(...efficiencyData.negative_trend.map(i => i.count))) * 100}
                                                variant="danger"
                                            />
                                        </div>
                                    )) || <p className="text-muted">Нет данных</p>}
                                </Card.Body>
                            </Card>
                        </Col>
                        <Col md={6}>
                            <Card className="bg-dark border-success">
                                <Card.Header className="bg-secondary text-light">
                                    <h5 className="mb-0">Динамика удаленных отзывов</h5>
                                </Card.Header>
                                <Card.Body>
                                    {efficiencyData.deleted_trend?.map((item, index) => (
                                        <div key={index} className="mb-3">
                                            <div className="d-flex justify-content-between align-items-center mb-1">
                                                <span className="text-light">{item.date}</span>
                                                <span className="text-light">{item.count}</span>
                                            </div>
                                            <ProgressBar
                                                now={(item.count / Math.max(...efficiencyData.deleted_trend.map(i => i.count))) * 100}
                                                variant="warning"
                                            />
                                        </div>
                                    )) || <p className="text-muted">Нет данных</p>}
                                </Card.Body>
                            </Card>
                        </Col>
                    </Row>

                    {/* Детальная статистика */}
                    <Card className="bg-dark border-success">
                        <Card.Header className="bg-secondary text-light">
                            <h5 className="mb-0">Детальная статистика</h5>
                        </Card.Header>
                        <Card.Body>
                            <Row>
                                <Col md={6}>
                                    <h6 className="text-light mb-3">Распределение по рейтингам</h6>
                                    {[5, 4, 3, 2, 1].map(rating => {
                                        const count = efficiencyData.ratings_distribution?.[rating] || 0;
                                        const percentage = efficiencyData.total_reviews > 0
                                            ? (count / efficiencyData.total_reviews) * 100
                                            : 0;

                                        return (
                                            <div key={rating} className="mb-2">
                                                <div className="d-flex justify-content-between align-items-center mb-1">
                                                    <span className="text-light">{rating}★</span>
                                                    <span className="text-light">
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
                                <Col md={6}>
                                    <h6 className="text-light mb-3">Статистика обработки</h6>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between align-items-center mb-1">
                                            <span className="text-light">Обработано</span>
                                            <span className="text-light">
                                                {formatNumber(efficiencyData.processed_count || 0)}
                                            </span>
                                        </div>
                                        <ProgressBar
                                            now={efficiencyData.total_reviews > 0
                                                ? ((efficiencyData.processed_count || 0) / efficiencyData.total_reviews) * 100
                                                : 0}
                                            variant="success"
                                        />
                                    </div>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between align-items-center mb-1">
                                            <span className="text-light">В обработке</span>
                                            <span className="text-light">
                                                {formatNumber(efficiencyData.pending_count || 0)}
                                            </span>
                                        </div>
                                        <ProgressBar
                                            now={efficiencyData.total_reviews > 0
                                                ? ((efficiencyData.pending_count || 0) / efficiencyData.total_reviews) * 100
                                                : 0}
                                            variant="warning"
                                        />
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