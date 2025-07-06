import React, { useState, useEffect } from 'react';
import { Form, Row, Col, Button } from 'react-bootstrap';

const ReviewFilters = ({ onFiltersChange, shops = [], products = [], initialFilters = {} }) => {
    const [filters, setFilters] = useState({
        search: '',
        rating: '',
        shop: '',
        product: '',
        dateFrom: '',
        dateTo: '',
        negative: '',
        ...initialFilters
    });

    // Синхронизируем с initialFilters при их изменении
    useEffect(() => {
        if (initialFilters) {
            setFilters(prev => ({
                ...prev,
                ...initialFilters
            }));
        }
    }, [initialFilters]);

    // Убираем автоматический вызов onFiltersChange, чтобы избежать конфликтов
    // useEffect(() => {
    //     onFiltersChange(filters);
    // }, [filters, onFiltersChange]);

    const handleFilterChange = (name, value) => {
        setFilters(prev => {
            const newFilters = {
                ...prev,
                [name]: value
            };

            // Если изменился магазин, сбрасываем фильтр по товару
            if (name === 'shop') {
                newFilters.product = '';
            }

            // Вызываем onFiltersChange только при изменении пользователем
            setTimeout(() => onFiltersChange(newFilters), 0);

            return newFilters;
        });
    };

    const handleReset = () => {
        const resetFilters = {
            search: '',
            rating: '',
            shop: '',
            product: '',
            dateFrom: '',
            dateTo: '',
            negative: ''
        };
        setFilters(resetFilters);
        onFiltersChange(resetFilters);
    };

    return (
        <div className="p-3">
            <h5 className="text-light mb-3">Фильтры отзывов</h5>
            <Row className="g-3">
                <Col md={3}>
                    <Form.Label className="text-light">Поиск</Form.Label>
                    <Form.Control
                        type="text"
                        placeholder="Поиск по тексту..."
                        value={filters.search}
                        onChange={(e) => handleFilterChange('search', e.target.value)}
                        className="bg-dark border-success text-light"
                    />
                </Col>
                <Col md={2}>
                    <Form.Label className="text-light">Рейтинг</Form.Label>
                    <Form.Select
                        value={filters.rating}
                        onChange={(e) => handleFilterChange('rating', e.target.value)}
                        className="bg-dark border-success text-light"
                    >
                        <option value="">Все</option>
                        <option value="1">1 звезда</option>
                        <option value="2">2 звезды</option>
                        <option value="3">3 звезды</option>
                        <option value="4">4 звезды</option>
                        <option value="5">5 звезд</option>
                    </Form.Select>
                </Col>
                <Col md={2}>
                    <Form.Label className="text-light">Магазин</Form.Label>
                    <Form.Select
                        value={filters.shop}
                        onChange={(e) => handleFilterChange('shop', e.target.value)}
                        className="bg-dark border-success text-light"
                    >
                        <option value="">Все магазины</option>
                        {shops.map(shop => (
                            <option key={shop.id} value={shop.id}>
                                {shop.name}
                            </option>
                        ))}
                    </Form.Select>
                </Col>
                <Col md={2}>
                    <Form.Label className="text-light">Товар</Form.Label>
                    <Form.Select
                        value={filters.product}
                        onChange={(e) => handleFilterChange('product', e.target.value)}
                        className="bg-dark border-success text-light"
                        disabled={!products || products.length === 0}
                    >
                        <option value="">Все товары</option>
                        {products && products.map(product => (
                            <option key={product.id} value={product.id}>{product.name}</option>
                        ))}
                    </Form.Select>
                </Col>
                <Col md={2}>
                    <Form.Label className="text-light">Негативность</Form.Label>
                    <Form.Select
                        value={filters.negative}
                        onChange={(e) => handleFilterChange('negative', e.target.value)}
                        className="bg-dark border-success text-light"
                    >
                        <option value="">Все</option>
                        <option value="true">Только негативные</option>
                        <option value="false">Только позитивные</option>
                    </Form.Select>
                </Col>
                <Col md={3} className="d-flex align-items-end">
                    <Button
                        variant="outline-warning"
                        onClick={handleReset}
                        className="w-100"
                    >
                        Сбросить фильтры
                    </Button>
                </Col>
            </Row>
            <Row className="g-3 mt-2">
                <Col md={3}>
                    <Form.Label className="text-light">Дата с</Form.Label>
                    <Form.Control
                        type="date"
                        value={filters.dateFrom}
                        onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
                        className="bg-dark border-success text-light"
                    />
                </Col>
                <Col md={3}>
                    <Form.Label className="text-light">Дата по</Form.Label>
                    <Form.Control
                        type="date"
                        value={filters.dateTo}
                        onChange={(e) => handleFilterChange('dateTo', e.target.value)}
                        className="bg-dark border-success text-light"
                    />
                </Col>
            </Row>
        </div>
    );
};

export default ReviewFilters; 