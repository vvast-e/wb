import React, { useState, useEffect } from 'react';
import { Container, Card, Row, Col, Badge, Spinner, Alert, Pagination } from 'react-bootstrap';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import ReviewFilters from '../components/ReviewFilters';

const ReviewAnalyzerPage = () => {
    const [searchParams] = useSearchParams();
    const [reviews, setReviews] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [shops, setShops] = useState([]);
    const [filters, setFilters] = useState({});
    const [pagination, setPagination] = useState({
        page: 1,
        perPage: 9,
        total: 0
    });
    const [products, setProducts] = useState([]);

    useEffect(() => {
        fetchShops();
    }, []); // Только загрузка магазинов при первой загрузке

    // Применяем URL параметры к фильтрам
    useEffect(() => {
        const shopFromUrl = searchParams.get('shop');
        const productFromUrl = searchParams.get('product');
        const negativeFromUrl = searchParams.get('negative');

        console.log('URL параметры:', { shopFromUrl, productFromUrl, negativeFromUrl });

        setFilters(prevFilters => ({
            ...prevFilters,
            shop: shopFromUrl || '',
            product: productFromUrl || '',
            negative: negativeFromUrl || ''
        }));
    }, [searchParams]);

    useEffect(() => {
        const timeoutId = setTimeout(() => {
            fetchReviews();
        }, 300); // Добавляем задержку в 300мс

        return () => clearTimeout(timeoutId);
    }, [filters, pagination.page, pagination.perPage]);

    useEffect(() => {
        if (filters.shop) {
            fetchProducts(filters.shop);
        } else {
            setProducts([]);
        }
    }, [filters.shop]);

    useEffect(() => {
        if (reviews && reviews.length > 0) {
            console.log('Отзывы на странице:', reviews.map(r => r.id), reviews);
        }
    }, [reviews]);

    const fetchShops = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(`${import.meta.env.VITE_API_URL}/analytics/shops`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            setShops(response.data);
        } catch (err) {
            console.error('Ошибка при загрузке магазинов:', err);
        }
    };

    const fetchProducts = async (shopId) => {
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(`${import.meta.env.VITE_API_URL}/analytics/shop/${shopId}/products`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            setProducts(response.data || []);
        } catch (err) {
            setProducts([]);
        }
    };

    const fetchReviews = async () => {
        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem('token');
            const params = {
                page: pagination.page,
                per_page: pagination.perPage,
                ordering: '-created_at',
            };
            if (filters.search) params.search = filters.search;
            if (filters.rating) params.rating = Number(filters.rating);
            if (filters.shop) params.shop = filters.shop;
            if (filters.product) params.product = filters.product;
            if (filters.lastNDays && Number(filters.lastNDays) > 0) {
                const now = new Date();
                const from = new Date(now.getTime() - Number(filters.lastNDays) * 24 * 60 * 60 * 1000);
                params.date_from = from.toISOString().slice(0, 10);
            } else {
                if (filters.dateFrom) params.date_from = filters.dateFrom;
                if (filters.dateTo) params.date_to = filters.dateTo;
            }
            if (filters.negative !== '' && filters.negative !== null && filters.negative !== undefined) {
                params.negative = filters.negative === 'true' ? true : filters.negative === 'false' ? false : undefined;
            }
            if (filters.deleted !== '' && filters.deleted !== null && filters.deleted !== undefined) {
                params.deleted = filters.deleted === 'true' ? true : filters.deleted === 'false' ? false : undefined;
            }

            console.log('Отправляем запрос с фильтрами:', params);
            console.log('filters.negative:', filters.negative, 'тип:', typeof filters.negative);

            const response = await axios.get(`${import.meta.env.VITE_API_URL}/analytics/reviews`, {
                headers: { 'Authorization': `Bearer ${token}` },
                params
            });

            console.log('Полученные отзывы:', response.data.reviews);
            // Логируем первые 3 отзыва для проверки структуры
            if (response.data.reviews && response.data.reviews.length > 0) {
                response.data.reviews.slice(0, 3).forEach((review, index) => {
                    console.log(`Отзыв ${index + 1}:`, {
                        id: review.id,
                        pros_text: review.pros_text,
                        cons_text: review.cons_text,
                        main_text: review.main_text
                    });
                });
            }

            setReviews(response.data.reviews || []);
            setPagination(prev => ({
                ...prev,
                total: response.data.total || 0
            }));
        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка при загрузке отзывов');
        } finally {
            setLoading(false);
        }
    };

    const handleFiltersChange = (newFilters) => {
        setFilters(newFilters);
        setPagination(prev => {
            if (prev.page !== 1) {
                return { ...prev, page: 1 };
            }
            return prev;
        });
    };

    const handlePageChange = (page) => {
        setPagination(prev => ({ ...prev, page }));
    };

    const getRatingColor = (rating) => {
        if (rating >= 4) return 'success';
        if (rating >= 3) return 'warning';
        return 'danger';
    };

    const getSentimentColor = (sentiment) => {
        if (sentiment === 'positive') return 'success';
        if (sentiment === 'negative') return 'danger';
        return 'secondary';
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString('ru-RU');
    };

    const renderStars = (rating) => {
        const num = Number(rating) || 0;
        return '★'.repeat(num);
    };

    // Функция для парсинга текста отзыва на блоки
    const parseReviewBlocks = (text) => {
        if (!text) return {};
        const blocks = {};
        const regex = /(?:Комментарий: ([\s\S]*?))?(?:\n)?(?:Достоинства: ([\s\S]*?))?(?:\n)?(?:Недостатки: ([\s\S]*))?$/m;
        const match = text.match(regex);
        let found = false;
        if (match) {
            if (match[2] && match[2].trim()) { blocks.pros = match[2].trim(); found = true; }
            if (match[3] && match[3].trim()) { blocks.cons = match[3].trim(); found = true; }
            if (match[1] && match[1].trim()) { blocks.comment = match[1].trim(); found = true; }
        }
        if (!found) {
            blocks.comment = text;
        }
        return blocks;
    };

    if (loading && reviews.length === 0) {
        return (
            <Container className="d-flex justify-content-center mt-5">
                <Spinner animation="border" variant="success" />
            </Container>
        );
    }

    return (
        <Container className="py-4">
            <h2 className="text-light mb-4">База отзывов</h2>

            <div className="border border-success rounded p-3 mb-4 bg-dark">
                <ReviewFilters
                    onFiltersChange={handleFiltersChange}
                    shops={shops}
                    products={products}
                    initialFilters={filters}
                />
            </div>

            {error && (
                <Alert variant="danger" className="mb-4">
                    {error}
                </Alert>
            )}

            <div className="mb-3">
                <span className="text-light">
                    Найдено отзывов: {pagination.total}
                </span>
            </div>

            {reviews.map((review) => (
                <Card key={`${review.id}_${pagination.page}`} className="mb-3 bg-dark border-success">
                    <Card.Body>
                        <Row>
                            <Col md={8}>
                                <div className="d-flex justify-content-between align-items-start mb-2">
                                    <div>
                                        <Badge
                                            bg={getRatingColor(review.rating)}
                                            className="me-2"
                                        >
                                            {renderStars(review.rating)}
                                        </Badge>
                                        <Badge bg="secondary" className="me-2">
                                            {review.shop_name}
                                        </Badge>
                                        {review.sentiment && (
                                            <Badge bg={getSentimentColor(review.sentiment)}>
                                                {review.sentiment === 'positive' ? 'Позитивный' :
                                                    review.sentiment === 'negative' ? 'Негативный' : 'Нейтральный'}
                                            </Badge>
                                        )}
                                    </div>
                                    <small className="text-muted">
                                        <strong>Дата:</strong> {formatDate(review.created_at)}
                                    </small>
                                </div>

                                <p className="text-light mb-2">
                                    <strong>Автор:</strong> {review.author_name}
                                </p>

                                <p className="text-light mb-2">
                                    <strong>Товар:</strong> {review.product_name?.split(' ')[1] || review.product_name}
                                </p>

                                {/* Новый раздельный вывод */}
                                {review.pros_text && (
                                    <p className="text-light mb-2"><strong>Достоинства:</strong> {review.pros_text.replace(/^Комментарий:/i, '').trim()}</p>
                                )}
                                {review.cons_text && (
                                    <p className="text-light mb-2"><strong>Недостатки:</strong> {review.cons_text.replace(/^Комментарий:/i, '').trim()}</p>
                                )}
                                {review.main_text && (
                                    <p className="text-light mb-2"><strong>Комментарий:</strong> {review.main_text.replace(/^Комментарий:/i, '').trim()}</p>
                                )}

                                <p className="text-light mb-2">
                                    <strong>Дата:</strong> {formatDate(review.created_at)}
                                </p>

                                {review.photos && review.photos.length > 0 && (
                                    <div className="mb-2">
                                        <strong className="text-light">Фото:</strong>
                                        <div className="d-flex gap-2 mt-1">
                                            {review.photos.map((photo, index) => (
                                                <img
                                                    key={index}
                                                    src={photo}
                                                    alt={`Фото ${index + 1}`}
                                                    style={{ width: '60px', height: '60px', objectFit: 'cover' }}
                                                    className="rounded"
                                                />
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </Col>

                            <Col md={4}>
                                <div className="text-end">
                                    <Badge bg="info" className="mb-2 d-block">
                                        ID: {review.id}
                                    </Badge>
                                    {typeof review.is_deleted !== 'undefined' && (
                                        <Badge bg={review.is_deleted ? "danger" : "secondary"} className="mb-2 d-block">
                                            {review.is_deleted ? "Удален" : "Не удален"}
                                        </Badge>
                                    )}
                                    <Badge bg="warning" text="dark" className="mb-2 d-block">
                                        AI статус в работе
                                    </Badge>
                                </div>
                            </Col>
                        </Row>
                    </Card.Body>
                </Card>
            ))}

            {reviews.length === 0 && !loading && (
                <Alert variant="info" className="text-center">
                    Отзывы не найдены
                </Alert>
            )}

            {pagination.total > pagination.perPage && (
                <div className="d-flex justify-content-center mt-4">
                    <Pagination>
                        <Pagination.First
                            onClick={() => handlePageChange(1)}
                            disabled={pagination.page === 1}
                        />
                        <Pagination.Prev
                            onClick={() => handlePageChange(pagination.page - 1)}
                            disabled={pagination.page === 1}
                        />

                        {Array.from({ length: Math.ceil(pagination.total / pagination.perPage) }, (_, i) => i + 1)
                            .filter(page => Math.abs(page - pagination.page) <= 4 || page === 1 || page === Math.ceil(pagination.total / pagination.perPage))
                            .reduce((acc, page, idx, arr) => {
                                if (idx > 0 && page - arr[idx - 1] > 1) {
                                    acc.push('ellipsis-' + page);
                                }
                                acc.push(page);
                                return acc;
                            }, [])
                            .map((page, idx) =>
                                typeof page === 'string' ? (
                                    <Pagination.Ellipsis key={page} disabled />
                                ) : (
                                    <Pagination.Item
                                        key={page}
                                        active={page === pagination.page}
                                        onClick={() => handlePageChange(page)}
                                    >
                                        {page}
                                    </Pagination.Item>
                                )
                            )}

                        <Pagination.Next
                            onClick={() => handlePageChange(pagination.page + 1)}
                            disabled={pagination.page >= Math.ceil(pagination.total / pagination.perPage)}
                        />
                        <Pagination.Last
                            onClick={() => handlePageChange(Math.ceil(pagination.total / pagination.perPage))}
                            disabled={pagination.page >= Math.ceil(pagination.total / pagination.perPage)}
                        />
                    </Pagination>
                </div>
            )}
        </Container>
    );
};

export default ReviewAnalyzerPage; 