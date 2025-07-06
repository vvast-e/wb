import React, { useState, useEffect } from 'react';
import { Container, Card, Row, Col, Form, Spinner, Alert, Badge, Table } from 'react-bootstrap';
import { useSearchParams, Link } from 'react-router-dom';
import axios from 'axios';
import DateRangePicker from '../components/DateRangePicker';

const BrandShopsPage = () => {
    const [searchParams] = useSearchParams();
    const [shops, setShops] = useState([]);
    const [selectedShop, setSelectedShop] = useState('');
    const [shopData, setShopData] = useState(null);
    const [shopDataAllTime, setShopDataAllTime] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [dateRange, setDateRange] = useState({
        startDate: '',
        endDate: ''
    });

    useEffect(() => {
        fetchShops();
        const shopFromUrl = searchParams.get('shop');
        if (shopFromUrl) setSelectedShop(shopFromUrl);
    }, [searchParams]);

    useEffect(() => {
        if (selectedShop) {
            fetchShopDataAllTime();
            if (dateRange.startDate && dateRange.endDate) {
                fetchShopData(dateRange.startDate, dateRange.endDate);
            } else {
                setShopData(null);
            }
        }
    }, [selectedShop, dateRange.startDate, dateRange.endDate]);

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

    const fetchShopDataAllTime = async () => {
        setLoading(true);
        setError(null);
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(`${import.meta.env.VITE_API_URL}/analytics/shop/${selectedShop}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            setShopDataAllTime(response.data);
        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка при загрузке данных магазина');
        } finally {
            setLoading(false);
        }
    };

    const fetchShopData = async (startDate, endDate) => {
        setLoading(true);
        setError(null);
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(`${import.meta.env.VITE_API_URL}/analytics/shop/${selectedShop}`, {
                headers: { 'Authorization': `Bearer ${token}` },
                params: {
                    start_date: startDate,
                    end_date: endDate
                }
            });
            setShopData(response.data);
        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка при загрузке данных магазина');
        } finally {
            setLoading(false);
        }
    };

    const handleDateChange = (startDate, endDate) => {
        setDateRange({ startDate, endDate });
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

    const productsToShow = dateRange.startDate && dateRange.endDate && shopData ? shopData.products : (shopDataAllTime ? shopDataAllTime.products : []);
    const statsSource = dateRange.startDate && dateRange.endDate && shopData ? shopData : shopDataAllTime;

    return (
        <Container className="py-4">
            <h2 className="text-light mb-4">Магазины бренда</h2>
            <Row className="mb-4">
                <Col md={6}>
                    <Form.Group>
                        <Form.Label className="text-light">Выберите магазин</Form.Label>
                        <Form.Select
                            value={selectedShop}
                            onChange={(e) => {
                                setSelectedShop(e.target.value);
                                setDateRange({ startDate: '', endDate: '' });
                            }}
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
            {selectedShop && !loading && (
                <>
                    {/* Общая статистика */}
                    <Row className="mb-4">
                        <Col md={4}>
                            <Card className="bg-dark border-success text-center">
                                <Card.Body>
                                    <h4 className="text-warning">
                                        {shopDataAllTime?.market_rating_all_time !== undefined
                                            ? shopDataAllTime.market_rating_all_time.toFixed(2)
                                            : '—'}
                                        <span title="Итоговый рейтинг по правилам маркетплейса, всегда за весь период" style={{ cursor: 'help', color: '#0dcaf0', marginLeft: 6 }}>
                                            ⓘ
                                        </span>
                                    </h4>
                                    <p className="text-light mb-0">Итоговый рейтинг (весь период)</p>
                                </Card.Body>
                            </Card>
                        </Col>
                        {dateRange.startDate && dateRange.endDate && shopData && (
                            <>
                                <Col md={4}>
                                    <Card className="bg-dark border-success text-center">
                                        <Card.Body>
                                            <h4 className="text-info">
                                                {shopData.market_rating_period?.toFixed(2) ?? '—'}
                                                <span title="Рейтинг по правилам маркетплейса за выбранный период" style={{ cursor: 'help', color: '#0dcaf0', marginLeft: 6 }}>
                                                    ⓘ
                                                </span>
                                            </h4>
                                            <p className="text-light mb-0">Рейтинг за период (маркет)</p>
                                        </Card.Body>
                                    </Card>
                                </Col>
                                <Col md={4}>
                                    <Card className="bg-dark border-success text-center">
                                        <Card.Body>
                                            <h4 className="text-info">
                                                {shopData.average_rating_period?.toFixed(2) ?? '—'}
                                                <span title="Средний рейтинг за выбранный период (простое среднее)" style={{ cursor: 'help', color: '#0dcaf0', marginLeft: 6 }}>
                                                    ⓘ
                                                </span>
                                            </h4>
                                            <p className="text-light mb-0">Средний рейтинг за период</p>
                                        </Card.Body>
                                    </Card>
                                </Col>
                            </>
                        )}
                    </Row>
                    <Row className="mb-4">
                        <Col md={3}>
                            <Card className="bg-dark border-success text-center">
                                <Card.Body>
                                    <h4 className="text-success">{statsSource ? formatNumber(statsSource.total_reviews) : '—'}</h4>
                                    <p className="text-light mb-0">Всего отзывов</p>
                                </Card.Body>
                            </Card>
                        </Col>
                        <Col md={3}>
                            <Card className="bg-dark border-success text-center">
                                <Card.Body>
                                    <h4 className="text-danger">{statsSource ? formatNumber(statsSource.negative_reviews) : '—'}</h4>
                                    <p className="text-light mb-0">Негативных отзывов</p>
                                </Card.Body>
                            </Card>
                        </Col>
                        <Col md={3}>
                            <Card className="bg-dark border-success text-center">
                                <Card.Body>
                                    <h4 className="text-info">{statsSource ? formatNumber(statsSource.five_star_reviews) : '—'}</h4>
                                    <p className="text-light mb-0">5-звездочных</p>
                                </Card.Body>
                            </Card>
                        </Col>
                    </Row>
                    {/* Топы */}
                    {statsSource && (
                        <Row className="mb-4">
                            <Col md={4}>
                                <Card className="bg-dark border-success">
                                    <Card.Header className="bg-secondary text-light">
                                        <h5 className="mb-0">Количество негатива</h5>
                                    </Card.Header>
                                    <Card.Body>
                                        {statsSource.negative_tops?.map((item, index) => {
                                            let article = item.product_name;
                                            if (article && article.toLowerCase().startsWith('товар ')) {
                                                article = article.slice(6).trim();
                                            }
                                            return (
                                                <div key={index} className="d-flex justify-content-between align-items-center mb-2">
                                                    {article ? (
                                                        <Link to={`/analytics/review-analyzer?shop=${selectedShop}&product=${article}&negative=true`} className="text-success text-decoration-underline">
                                                            {item.product_name}
                                                        </Link>
                                                    ) : (
                                                        <span className="text-light">{item.product_name}</span>
                                                    )}
                                                    <Badge bg="danger">{item.negative_count}</Badge>
                                                </div>
                                            );
                                        }) || <p className="text-muted">Нет данных</p>}
                                    </Card.Body>
                                </Card>
                            </Col>
                            <Col md={4}>
                                <Card className="bg-dark border-success">
                                    <Card.Header className="bg-secondary text-light">
                                        <h5 className="mb-0">Доля негативных от всех отзывов</h5>
                                    </Card.Header>
                                    <Card.Body>
                                        {statsSource.negative_percentage_tops?.map((item, index) => {
                                            let article = item.product_name;
                                            if (article && article.toLowerCase().startsWith('товар ')) {
                                                article = article.slice(6).trim();
                                            }
                                            return (
                                                <div key={index} className="d-flex justify-content-between align-items-center mb-2">
                                                    {article ? (
                                                        <Link to={`/analytics/review-analyzer?shop=${selectedShop}&product=${article}&negative=true`} className="text-success text-decoration-underline">
                                                            {item.product_name}
                                                        </Link>
                                                    ) : (
                                                        <span className="text-light">{item.product_name}</span>
                                                    )}
                                                    <Badge bg="danger">{item.negative_percentage}%</Badge>
                                                </div>
                                            );
                                        }) || <p className="text-muted">Нет данных</p>}
                                    </Card.Body>
                                </Card>
                            </Col>
                            <Col md={4}>
                                <Card className="bg-dark border-success">
                                    <Card.Header className="bg-secondary text-light">
                                        <h5 className="mb-0">Доля негатива внутри товара</h5>
                                    </Card.Header>
                                    <Card.Body>
                                        {statsSource.internal_negative_tops?.map((item, index) => {
                                            let article = item.product_name;
                                            if (article && article.toLowerCase().startsWith('товар ')) {
                                                article = article.slice(6).trim();
                                            }
                                            return (
                                                <div key={index} className="d-flex justify-content-between align-items-center mb-2">
                                                    {article ? (
                                                        <Link to={`/analytics/review-analyzer?shop=${selectedShop}&product=${article}&negative=true`} className="text-success text-decoration-underline">
                                                            {item.product_name}
                                                        </Link>
                                                    ) : (
                                                        <span className="text-light">{item.product_name}</span>
                                                    )}
                                                    <Badge bg="danger">{item.internal_negative_percentage}%</Badge>
                                                </div>
                                            );
                                        }) || <p className="text-muted">Нет данных</p>}
                                    </Card.Body>
                                </Card>
                            </Col>
                        </Row>
                    )}
                    {/* Сводка по товарам */}
                    <Card className="bg-dark border-success">
                        <Card.Header className="bg-secondary text-light">
                            <h5 className="mb-0">Сводка по товарам</h5>
                        </Card.Header>
                        <Card.Body>
                            <Table striped bordered hover variant="dark">
                                <thead>
                                    <tr>
                                        <th>Товар</th>
                                        <th>
                                            Итоговый рейтинг (весь период)
                                            <span title="По правилам маркетплейса, за всё время" style={{ cursor: 'help', color: '#0dcaf0', marginLeft: 4 }}>ⓘ</span>
                                        </th>
                                        <th>
                                            Итоговый рейтинг (период)
                                            <span title="По правилам маркетплейса, за выбранный период" style={{ cursor: 'help', color: '#0dcaf0', marginLeft: 4 }}>ⓘ</span>
                                        </th>
                                        <th>
                                            Средний рейтинг (период)
                                            <span title="Среднее всех оценок за выбранный период" style={{ cursor: 'help', color: '#0dcaf0', marginLeft: 4 }}>ⓘ</span>
                                        </th>
                                        <th>
                                            Доля негатива (период)
                                            <span title="Доля негативных отзывов за выбранный период" style={{ cursor: 'help', color: '#0dcaf0', marginLeft: 4 }}>ⓘ</span>
                                        </th>
                                        <th>Всего отзывов (период)</th>
                                        <th>Количество оценок (период)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {productsToShow && productsToShow.length > 0 ? productsToShow.map((product, index) => {
                                        let article = product.name;
                                        if (article && article.toLowerCase().startsWith('товар ')) {
                                            article = article.slice(6).trim();
                                        }
                                        return (
                                            <tr key={index}>
                                                <td>
                                                    {article ? (
                                                        <Link to={`/analytics/review-analyzer?shop=${selectedShop}&product=${article}`} className="text-success text-decoration-underline">
                                                            {product.name}
                                                        </Link>
                                                    ) : (
                                                        <span className="text-light">{product.name}</span>
                                                    )}
                                                </td>
                                                <td>
                                                    <Badge bg={getRatingColor(product.market_rating_all_time)}>
                                                        {renderStars(product.market_rating_all_time)} {product.market_rating_all_time?.toFixed(2) ?? '—'}
                                                    </Badge>
                                                </td>
                                                <td>
                                                    <Badge bg={getRatingColor(product.market_rating)}>
                                                        {renderStars(product.market_rating)} {product.market_rating?.toFixed(2) ?? '—'}
                                                    </Badge>
                                                </td>
                                                <td>
                                                    <Badge bg={getRatingColor(product.rating)}>
                                                        {renderStars(product.rating)} {product.rating?.toFixed(2) ?? '—'}
                                                    </Badge>
                                                </td>
                                                <td>
                                                    <Badge bg="danger">
                                                        {product.internal_negative_percentage !== undefined
                                                            ? (
                                                                <Link to={`/analytics/review-analyzer?shop=${selectedShop}&product=${article}&negative=true`} className="text-white text-decoration-none">
                                                                    {product.internal_negative_percentage + '%'}
                                                                </Link>
                                                            )
                                                            : '—'}
                                                    </Badge>
                                                </td>
                                                <td>
                                                    {product.total_reviews !== undefined
                                                        ? formatNumber(product.total_reviews)
                                                        : '—'}
                                                </td>
                                                <td>
                                                    <div className="d-flex flex-column gap-1">
                                                        {[5, 4, 3, 2, 1].map(rating => (
                                                            <div key={rating} className="d-flex justify-content-between">
                                                                <span className="text-light">{rating}★</span>
                                                                <span className="text-light">
                                                                    {product.ratings_count?.[rating] || 0}
                                                                </span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    }) : (
                                        <tr>
                                            <td colSpan={dateRange.startDate && dateRange.endDate && shopData ? 5 : 4} className="text-center text-muted">
                                                Нет данных о товарах
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </Table>
                        </Card.Body>
                    </Card>
                </>
            )}
            {!selectedShop && (
                <Alert variant="info" className="text-center">
                    Выберите магазин для просмотра статистики
                </Alert>
            )}
        </Container>
    );
};

export default BrandShopsPage;