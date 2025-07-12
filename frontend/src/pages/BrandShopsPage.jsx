import React, { useState, useEffect } from 'react';
import { Container, Card, Row, Col, Form, Spinner, Alert, Badge, Table, Button } from 'react-bootstrap';
import { useSearchParams, Link } from 'react-router-dom';
import axios from 'axios';
import DateRangePicker from '../components/DateRangePicker';
import Accordion from 'react-bootstrap/Accordion';

const ShopDashboard = ({ shopId, shopName, data, productsToShow, filteredProducts, getRatingColor, renderStars, formatNumber, selectedShop, hideProductSummary }) => (
    <div className="mb-5">
        <h4 className="text-success mb-3">{shopName}</h4>
        {/* Общая статистика */}
        <Row className="mb-4">
            <Col md={4}>
                <Card className="bg-dark border-success text-center">
                    <Card.Body>
                        <h4 className="text-warning">
                            {data?.market_rating_all_time !== undefined
                                ? data.market_rating_all_time.toFixed(2)
                                : '—'}
                            <span title="Итоговый рейтинг по правилам маркетплейса, всегда за весь период" style={{ cursor: 'help', color: '#0dcaf0', marginLeft: 6 }}>
                                ⓘ
                            </span>
                        </h4>
                        <p className="text-light mb-0">Итоговый рейтинг (весь период)</p>
                    </Card.Body>
                </Card>
            </Col>
            <Col md={4}>
                <Card className="bg-dark border-success text-center">
                    <Card.Body>
                        <h4 className="text-success">{formatNumber(data?.total_reviews) ?? '—'}</h4>
                        <p className="text-light mb-0">Всего отзывов</p>
                    </Card.Body>
                </Card>
            </Col>
            <Col md={4}>
                <Card className="bg-dark border-success text-center">
                    <Card.Body>
                        <h4 className="text-danger">{formatNumber(data?.negative_reviews) ?? '—'}</h4>
                        <p className="text-light mb-0">Негативных отзывов</p>
                    </Card.Body>
                </Card>
            </Col>
        </Row>
        {/* Топы */}
        {data && (
            <Row className="mb-4">
                <Col md={4}>
                    <Card className="bg-dark border-success">
                        <Card.Header className="bg-secondary text-light">
                            <h5 className="mb-0">Количество негатива</h5>
                        </Card.Header>
                        <Card.Body>
                            {data.negative_tops?.map((item, index) => (
                                <div key={index} className="d-flex justify-content-between align-items-center mb-2">
                                    <span className="text-light">{item.product_name}</span>
                                    <Badge bg="danger">{item.negative_count}</Badge>
                                </div>
                            )) || <p className="text-muted">Нет данных</p>}
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={4}>
                    <Card className="bg-dark border-success">
                        <Card.Header className="bg-secondary text-light">
                            <h5 className="mb-0">Доля негативных от всех отзывов</h5>
                        </Card.Header>
                        <Card.Body>
                            {data.negative_percentage_tops?.map((item, index) => (
                                <div key={index} className="d-flex justify-content-between align-items-center mb-2">
                                    <span className="text-light">{item.product_name}</span>
                                    <Badge bg="danger">{item.negative_percentage}%</Badge>
                                </div>
                            )) || <p className="text-muted">Нет данных</p>}
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={4}>
                    <Card className="bg-dark border-success">
                        <Card.Header className="bg-secondary text-light">
                            <h5 className="mb-0">Доля негатива внутри товара</h5>
                        </Card.Header>
                        <Card.Body>
                            {data.internal_negative_tops?.map((item, index) => (
                                <div key={index} className="d-flex justify-content-between align-items-center mb-2">
                                    <span className="text-light">{item.product_name}</span>
                                    <Badge bg="danger">{item.internal_negative_percentage}%</Badge>
                                </div>
                            )) || <p className="text-muted">Нет данных</p>}
                        </Card.Body>
                    </Card>
                </Col>
            </Row>
        )}
        {/* Сводка по товарам */}
        {!hideProductSummary && (
            <Card className="bg-dark border-success">
                <Card.Header className="bg-secondary text-light">
                    <h5 className="mb-0">Сводка по товарам</h5>
                </Card.Header>
                <Card.Body>
                    <Table striped bordered hover variant="dark">
                        <thead>
                            <tr>
                                <th>Товар</th>
                                <th>Итоговый рейтинг (весь период)</th>
                                <th>Итоговый рейтинг (период)</th>
                                <th>Средний рейтинг (период)</th>
                                <th>Доля негатива (период)</th>
                                <th>Всего отзывов (период)</th>
                                <th>Количество оценок (период)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredProducts && filteredProducts.length > 0 ? filteredProducts.map((product, index) => {
                                let article = product.name;
                                if (article && article.toLowerCase().startsWith('товар ')) {
                                    article = article.slice(6).trim();
                                }
                                return (
                                    <tr key={index}>
                                        <td>
                                            <span className="text-success text-decoration-underline">{product.name}</span>
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
                                                    ? product.internal_negative_percentage + '%'
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
                                    <td colSpan={7} className="text-center text-muted">
                                        Нет данных о товарах
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </Table>
                </Card.Body>
            </Card>
        )}
    </div>
);

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
    // --- ДОБАВЛЯЕМ СОСТОЯНИЯ ДЛЯ ФИЛЬТРОВ ---
    const [selectedProducts, setSelectedProducts] = useState([]);
    // --- Диапазоны рейтинга для фильтра ---
    const ratingRanges = [
        { label: '> 4.9', min: 4.9, max: 5.0 },
        { label: '> 4.8', min: 4.8, max: 4.9 },
        { label: '> 4.7', min: 4.7, max: 4.8 },
        { label: '> 4.6', min: 4.6, max: 4.7 },
        { label: '<= 4.5', min: 0, max: 4.5 },
    ];
    const [selectedRatingRange, setSelectedRatingRange] = useState('');
    // --- ДОБАВЛЯЕМ СОСТОЯНИЯ ДЛЯ ПОЛНЫХ ДАННЫХ ВСЕХ МАГАЗИНОВ ---
    const [allShopsData, setAllShopsData] = useState({});

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

    useEffect(() => {
        if (!selectedShop && shops.length > 0) {
            // Получаем полные данные для всех магазинов
            const fetchAll = async () => {
                const token = localStorage.getItem('token');
                const promises = shops.map(shop =>
                    axios.get(`${import.meta.env.VITE_API_URL}/analytics/shop/${shop.id}`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    }).then(res => ({ id: shop.id, data: res.data, name: shop.name }))
                        .catch(() => ({ id: shop.id, data: null, name: shop.name }))
                );
                const results = await Promise.all(promises);
                const dataObj = {};
                results.forEach(({ id, data, name }) => {
                    dataObj[id] = { data, name };
                });
                setAllShopsData(dataObj);
            };
            fetchAll();
        }
    }, [selectedShop, shops]);

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

    // --- ФИЛЬТРАЦИЯ ТОВАРОВ ДЛЯ ТАБЛИЦЫ ---
    const filteredProducts = (productsToShow || []).filter(product => {
        if (!selectedShop) return true;
        // Исправлено: если не выбран ни один товар, показывать все
        const matchProduct = selectedProducts.length === 0 ? true : selectedProducts.includes(product.vendor_code || product.article);
        let matchRating = true;
        if (selectedRatingRange) {
            const range = ratingRanges.find(r => r.label === selectedRatingRange);
            if (range) {
                matchRating = product.rating >= range.min && product.rating < (range.max === 5.0 ? 5.01 : range.max);
            }
        }
        return matchProduct && matchRating;
    });

    // Удаляю объединённый ТОП 10 и возвращаю прежний вид

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
                                setSelectedProducts([]);
                                setSelectedRatingRange('');
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
            {/* Фильтры по товарам и рейтингу */}
            {selectedShop && (productsToShow && productsToShow.length > 0) && (
                <Row className="mb-3 align-items-end">
                    <Col md={6}>
                        <Form.Group>
                            <Form.Label className="text-light">Товары</Form.Label>
                            <div style={{ maxHeight: '180px', overflowY: 'auto', border: '1px solid #198754', borderRadius: 8, padding: 8, background: '#181c1f' }}>
                                {productsToShow.map(product => (
                                    <Form.Check
                                        key={product.vendor_code || product.article}
                                        type="checkbox"
                                        id={`product-checkbox-${product.vendor_code || product.article}`}
                                        label={product.name}
                                        value={product.vendor_code || product.article}
                                        checked={selectedProducts.includes(product.vendor_code || product.article)}
                                        onChange={e => {
                                            const value = e.target.value;
                                            setSelectedProducts(prev =>
                                                prev.includes(value)
                                                    ? prev.filter(a => a !== value)
                                                    : [...prev, value]
                                            );
                                        }}
                                        className="text-light mb-1"
                                    />
                                ))}
                            </div>
                        </Form.Group>
                    </Col>
                    <Col md={5}>
                        <Form.Group>
                            <Form.Label className="text-light">Рейтинг</Form.Label>
                            <div className="d-flex flex-column gap-2">
                                {ratingRanges.map(range => (
                                    <Form.Check
                                        key={range.label}
                                        label={<span style={{ fontSize: '1.1em' }}>{range.label}</span>}
                                        value={range.label}
                                        checked={selectedRatingRange === range.label}
                                        onChange={e => setSelectedRatingRange(e.target.value)}
                                        type="radio"
                                        className="text-light"
                                    />
                                ))}
                                <Form.Check
                                    label={<span style={{ fontSize: '1.1em' }}>Все</span>}
                                    value=""
                                    checked={selectedRatingRange === ''}
                                    onChange={() => setSelectedRatingRange('')}
                                    type="radio"
                                    className="text-light"
                                />
                            </div>
                        </Form.Group>
                    </Col>
                    <Col md={1} className="d-flex align-items-end justify-content-end">
                        <button
                            type="button"
                            className="btn btn-outline-danger btn-sm"
                            onClick={() => {
                                setSelectedProducts([]);
                                setSelectedRatingRange('');
                            }}
                        >
                            Сбросить
                        </button>
                    </Col>
                </Row>
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
                    {/* ТОП 10 по: (аккордеон) */}
                    {shopDataAllTime && (
                        <div className="mb-4">
                            <h5 className="text-light mb-2">ТОП 10 по:</h5>
                            <Accordion defaultActiveKey="0" alwaysOpen className="bg-dark border-success">
                                <Accordion.Item eventKey="0" className="bg-dark border-success">
                                    <Accordion.Header className="bg-secondary text-light">Количество негатива</Accordion.Header>
                                    <Accordion.Body className="bg-dark">
                                        <Card className="bg-dark border-success mb-3">
                                            <Card.Body>
                                                {shopDataAllTime.negative_tops?.length > 0 ? shopDataAllTime.negative_tops.slice(0, 10).map((item, index) => {
                                                    let vendor_code = item.product_name;
                                                    if (vendor_code && vendor_code.toLowerCase().startsWith('товар ')) {
                                                        vendor_code = vendor_code.slice(6).trim();
                                                    }
                                                    return (
                                                        <div key={index} className="d-flex justify-content-between align-items-center mb-2">
                                                            {vendor_code ? (
                                                                <Link to={`/analytics/review-analyzer?shop=${selectedShop}&product=${vendor_code}&negative=true`} className="text-success text-decoration-underline">
                                                                    {item.product_name}
                                                                </Link>
                                                            ) : (
                                                                <span className="text-light">{item.product_name}</span>
                                                            )}
                                                            <Badge bg="danger">{item.negative_count}</Badge>
                                                        </div>
                                                    );
                                                }) : <p className="text-muted">Нет данных</p>}
                                            </Card.Body>
                                        </Card>
                                    </Accordion.Body>
                                </Accordion.Item>
                                <Accordion.Item eventKey="1" className="bg-dark border-success">
                                    <Accordion.Header className="bg-secondary text-light">Доля негативных от всех отзывов</Accordion.Header>
                                    <Accordion.Body className="bg-dark">
                                        <Card className="bg-dark border-success mb-3">
                                            <Card.Body>
                                                {shopDataAllTime.negative_percentage_tops?.length > 0 ? shopDataAllTime.negative_percentage_tops.slice(0, 10).map((item, index) => {
                                                    let vendor_code = item.product_name;
                                                    if (vendor_code && vendor_code.toLowerCase().startsWith('товар ')) {
                                                        vendor_code = vendor_code.slice(6).trim();
                                                    }
                                                    return (
                                                        <div key={index} className="d-flex justify-content-between align-items-center mb-2">
                                                            {vendor_code ? (
                                                                <Link to={`/analytics/review-analyzer?shop=${selectedShop}&product=${vendor_code}&negative=true`} className="text-success text-decoration-underline">
                                                                    {item.product_name}
                                                                </Link>
                                                            ) : (
                                                                <span className="text-light">{item.product_name}</span>
                                                            )}
                                                            <Badge bg="danger">{item.negative_percentage}%</Badge>
                                                        </div>
                                                    );
                                                }) : <p className="text-muted">Нет данных</p>}
                                            </Card.Body>
                                        </Card>
                                    </Accordion.Body>
                                </Accordion.Item>
                                <Accordion.Item eventKey="2" className="bg-dark border-success">
                                    <Accordion.Header className="bg-secondary text-light">Доля негатива внутри товара</Accordion.Header>
                                    <Accordion.Body className="bg-dark">
                                        <Card className="bg-dark border-success mb-3">
                                            <Card.Body>
                                                {shopDataAllTime.internal_negative_tops?.length > 0 ? shopDataAllTime.internal_negative_tops.slice(0, 10).map((item, index) => {
                                                    let vendor_code = item.product_name;
                                                    if (vendor_code && vendor_code.toLowerCase().startsWith('товар ')) {
                                                        vendor_code = vendor_code.slice(6).trim();
                                                    }
                                                    return (
                                                        <div key={index} className="d-flex justify-content-between align-items-center mb-2">
                                                            {vendor_code ? (
                                                                <Link to={`/analytics/review-analyzer?shop=${selectedShop}&product=${vendor_code}&negative=true`} className="text-success text-decoration-underline">
                                                                    {item.product_name}
                                                                </Link>
                                                            ) : (
                                                                <span className="text-light">{item.product_name}</span>
                                                            )}
                                                            <Badge bg="danger">{item.internal_negative_percentage}%</Badge>
                                                        </div>
                                                    );
                                                }) : <p className="text-muted">Нет данных</p>}
                                            </Card.Body>
                                        </Card>
                                    </Accordion.Body>
                                </Accordion.Item>
                            </Accordion>
                        </div>
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
                                    {filteredProducts && filteredProducts.length > 0 ? filteredProducts.map((product, index) => {
                                        let vendor_code = product.name;
                                        if (vendor_code && vendor_code.toLowerCase().startsWith('товар ')) {
                                            vendor_code = vendor_code.slice(6).trim();
                                        }
                                        return (
                                            <tr key={index}>
                                                <td>
                                                    {vendor_code ? (
                                                        <Link to={`/analytics/review-analyzer?shop=${selectedShop}&product=${vendor_code}`} className="text-success text-decoration-underline">
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
                                                                <Link to={`/analytics/review-analyzer?shop=${selectedShop}&product=${vendor_code}&negative=true`} className="text-white text-decoration-none">
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
                                            <td colSpan={dateRange.startDate && dateRange.endDate && shopData ? 7 : 7} className="text-center text-muted">
                                                {selectedShop ? 'Выберите хотя бы один товар для отображения сводки' : 'Нет данных о товарах'}
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </Table>
                        </Card.Body>
                    </Card>
                </>
            )}
            {/* Если магазин не выбран, показываем подробный дашборд для всех магазинов */}
            {!selectedShop && shops && shops.length > 0 && (
                <div>
                    {shops.map(shop => {
                        const shopDataObj = allShopsData[shop.id];
                        if (!shopDataObj || !shopDataObj.data) return (
                            <div key={shop.id} className="mb-5">
                                <Card className="bg-dark border-danger">
                                    <Card.Body>
                                        <span className="text-danger">Ошибка загрузки данных для магазина {shop.name}</span>
                                    </Card.Body>
                                </Card>
                            </div>
                        );
                        const data = shopDataObj.data;
                        const productsToShow = data.products || [];
                        const filteredProducts = productsToShow; // без фильтров
                        return (
                            <ShopDashboard
                                key={shop.id}
                                shopId={shop.id}
                                shopName={shop.name}
                                data={data}
                                productsToShow={productsToShow}
                                filteredProducts={filteredProducts}
                                getRatingColor={getRatingColor}
                                renderStars={renderStars}
                                formatNumber={formatNumber}
                                selectedShop={shop.id}
                                hideProductSummary={true}
                            />
                        );
                    })}
                </div>
            )}
            {!selectedShop && (
                <></>
            )}
        </Container>
    );
};

export default BrandShopsPage;