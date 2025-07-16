import React, { useState, useEffect } from 'react';
import { Container, Card, Row, Col, Spinner, Alert, Badge } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import ShopSummaryWidget from '../components/ShopSummaryWidget';

const ShopsSummaryPage = () => {
    const [shopsSummary, setShopsSummary] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        fetchShopsSummary();
    }, []);

    const fetchShopsSummary = async () => {
        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem('token');
            const response = await api.get(`/shops-summary`);
            setShopsSummary(response.data);
        } catch (err) {
            if (err.response?.status === 500) {
                setError('Ошибка сервера при загрузке сводки');
            } else if (err.response?.data?.detail) {
                setError(err.response.data.detail);
            } else {
                setError('Ошибка при загрузке сводки по магазинам');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleShopClick = (shopId) => {
        // Переход к странице магазина
        navigate(`/analytics/brand-shops?shop=${shopId}`);
    };

    const getRatingColor = (rating) => {
        if (rating >= 4) return 'success';
        if (rating >= 3) return 'warning';
        return 'danger';
    };

    const renderStars = (rating) => {
        return '★'.repeat(Math.round(rating)) + '☆'.repeat(5 - Math.round(rating));
    };

    const formatNumber = (num) => {
        return new Intl.NumberFormat('ru-RU').format(num);
    };

    const formatPercentage = (value) => {
        return `${(value * 100).toFixed(1)}%`;
    };

    return (
        <Container className="py-4">
            <h2 className="text-light mb-4">Сводка по магазинам</h2>
            <ShopSummaryWidget shopType="wb" />
            <div className="my-4" />
            <ShopSummaryWidget shopType="ozon" />

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

            {shopsSummary.length > 0 && !loading && (
                <Row>
                    {shopsSummary.map((shop) => (
                        <Col key={shop.id} lg={6} xl={4} className="mb-4">
                            <Card
                                className="bg-dark border-success h-100 shop-card"
                                style={{ cursor: 'pointer', transition: 'transform 0.2s' }}
                                onClick={() => handleShopClick(shop.id)}
                                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
                                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                            >
                                <Card.Header className="bg-secondary text-light">
                                    <h5 className="mb-0">{shop.name}</h5>
                                </Card.Header>
                                <Card.Body>
                                    {/* Основные показатели */}
                                    <Row className="mb-3">
                                        <Col xs={6}>
                                            <div className="text-center">
                                                <h4 className="text-success mb-1">
                                                    {formatNumber(shop.total_reviews)}
                                                </h4>
                                                <small className="text-muted">Всего отзывов</small>
                                            </div>
                                        </Col>
                                        <Col xs={6}>
                                            <div className="text-center">
                                                <h4 className="text-warning mb-1">
                                                    {shop.average_rating?.toFixed(1) || '0.0'}
                                                </h4>
                                                <small className="text-muted">Средний рейтинг</small>
                                            </div>
                                        </Col>
                                    </Row>

                                    {/* Рейтинг звездами */}
                                    <div className="text-center mb-3">
                                        <Badge bg={getRatingColor(shop.average_rating)} className="fs-6">
                                            {renderStars(shop.average_rating)}
                                        </Badge>
                                    </div>

                                    {/* Негативные показатели */}
                                    <Row className="mb-3">
                                        <Col xs={6}>
                                            <div className="text-center">
                                                <h5 className="text-danger mb-1">
                                                    {formatNumber(shop.negative_reviews)}
                                                </h5>
                                                <small className="text-muted">Негативных</small>
                                            </div>
                                        </Col>
                                        <Col xs={6}>
                                            <div className="text-center">
                                                <h5 className="text-info mb-1">
                                                    {formatNumber(shop.five_star_reviews)}
                                                </h5>
                                                <small className="text-muted">5-звездочных</small>
                                            </div>
                                        </Col>
                                    </Row>

                                    {/* Проценты */}
                                    <Row className="mb-3">
                                        <Col xs={6}>
                                            <div className="text-center">
                                                <h6 className="text-danger mb-1">
                                                    {formatPercentage(shop.negative_percentage)}
                                                </h6>
                                                <small className="text-muted">Доля негатива</small>
                                            </div>
                                        </Col>
                                        <Col xs={6}>
                                            <div className="text-center">
                                                <h6 className="text-success mb-1">
                                                    {formatPercentage(shop.five_star_percentage)}
                                                </h6>
                                                <small className="text-muted">Доля 5★</small>
                                            </div>
                                        </Col>
                                    </Row>

                                    {/* Топ товаров */}
                                    {shop.top_products && shop.top_products.length > 0 && (
                                        <div className="mb-3">
                                            <h6 className="text-light mb-2">Топ товаров:</h6>
                                            {shop.top_products.slice(0, 3).map((product, index) => {
                                                let vendor_code = product.name;
                                                if (vendor_code && vendor_code.toLowerCase().startsWith('товар ')) {
                                                    vendor_code = vendor_code.slice(6).trim();
                                                }
                                                return (
                                                    <div key={index} className="d-flex justify-content-between align-items-center mb-1">
                                                        <span className="text-light small" style={{
                                                            overflow: 'hidden',
                                                            textOverflow: 'ellipsis',
                                                            whiteSpace: 'nowrap',
                                                            maxWidth: '70%'
                                                        }}>
                                                            {product.name}
                                                        </span>
                                                        <Badge bg={getRatingColor(product.rating)}>
                                                            {product.rating.toFixed(1)}
                                                        </Badge>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}

                                    {/* Статус */}
                                    <div className="text-center">
                                        <Badge bg="secondary" className="me-2">
                                            {shop.status || 'Активен'}
                                        </Badge>
                                        {shop.is_processing && (
                                            <Badge bg="warning">В обработке</Badge>
                                        )}
                                    </div>
                                </Card.Body>
                                <Card.Footer className="bg-secondary text-center">
                                    <small className="text-light">
                                        Кликните для детального просмотра
                                    </small>
                                </Card.Footer>
                            </Card>
                        </Col>
                    ))}
                </Row>
            )}


        </Container>
    );
};

export default ShopsSummaryPage; 