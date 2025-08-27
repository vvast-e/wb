import React, { useState, useEffect } from 'react';
import { Form, Row, Col, Button } from 'react-bootstrap';

const ReviewFilters = ({ onFiltersChange, shops = [], products = [], initialFilters = {} }) => {
    const [filters, setFilters] = useState({
        rating: '',
        shop: '',
        product: [],
        dateFrom: '',
        dateTo: '',
        lastNDays: '',
        negative: '',
        deleted: '',
        ...initialFilters
    });

    const [productSearchTerm, setProductSearchTerm] = useState('');

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
                newFilters.product = [];
            }

            // Вызываем onFiltersChange только при изменении пользователем
            setTimeout(() => onFiltersChange(newFilters), 0);

            return newFilters;
        });
    };

    const handleLastNDaysChange = (value) => {
        setFilters(prev => {
            const newFilters = {
                ...prev,
                lastNDays: value,
                dateFrom: '',
                dateTo: ''
            };
            setTimeout(() => onFiltersChange(newFilters), 0);
            return newFilters;
        });
    };

    const handleDateChange = (name, value) => {
        setFilters(prev => {
            const newFilters = {
                ...prev,
                [name]: value,
                lastNDays: ''
            };
            setTimeout(() => onFiltersChange(newFilters), 0);
            return newFilters;
        });
    };

    const handleReset = () => {
        const resetFilters = {
            rating: '',
            shop: '',
            product: '',
            dateFrom: '',
            dateTo: '',
            lastNDays: '',
            negative: '',
            deleted: ''
        };
        setFilters(resetFilters);
        onFiltersChange(resetFilters);
    };

    return (
        <div className="p-3 position-relative">
            <h5 className="text-light mb-3">Фильтры отзывов</h5>
            <Button
                variant="outline-warning"
                onClick={handleReset}
                className="position-absolute top-0 end-0"
            >
                Сбросить фильтры
            </Button>
            <Row className="g-3">
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
                <Col md={4}>
                    <Form.Label className="text-light">Выберите товары</Form.Label>
                    <div className="bg-dark border border-success rounded p-2">
                        {(!products || products.length === 0) ? (
                            <small className="text-muted">Загружаем товары...</small>
                        ) : (
                            <>
                                {/* Поиск */}
                                <div className="mb-2">
                                    <Form.Control
                                        type="text"
                                        placeholder="Поиск товаров..."
                                        className="bg-dark border-success text-light"
                                        onChange={(e) => setProductSearchTerm(e.target.value.toLowerCase())}
                                    />
                                </div>

                                {/* Статистика выбора и кнопки */}
                                <div className="d-flex justify-content-between align-items-center mb-2">
                                    <small className="text-muted">
                                        Выбрано: {filters.product.length} из {products.length}
                                    </small>
                                    <div>
                                        <button
                                            type="button"
                                            className="btn btn-sm btn-outline-success me-2"
                                            onClick={() => handleFilterChange('product', products.map(p => p.id))}
                                        >
                                            Выбрать все
                                        </button>
                                        <button
                                            type="button"
                                            className="btn btn-sm btn-outline-secondary"
                                            onClick={() => handleFilterChange('product', [])}
                                        >
                                            Сброс
                                        </button>
                                    </div>
                                </div>

                                {/* Список товаров с прокруткой, выбранные сверху */}
                                <div style={{ maxHeight: '150px', overflowY: 'auto' }}>
                                    {(() => {
                                        const term = productSearchTerm;
                                        const filtered = products.filter(p => !term || (p.id && p.id.toLowerCase().includes(term)));
                                        const selectedSet = new Set(filters.product);
                                        const selectedList = filtered.filter(p => selectedSet.has(p.id));
                                        const unselectedList = filtered.filter(p => !selectedSet.has(p.id));
                                        const visible = [...selectedList, ...unselectedList];
                                        return visible.map(p => (
                                            <div key={p.id} className="mb-1">
                                                <Form.Check
                                                    type="checkbox"
                                                    id={`product-${p.id}`}
                                                    label={p.id}
                                                    checked={filters.product.includes(p.id)}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            handleFilterChange('product', [...filters.product, p.id]);
                                                        } else {
                                                            handleFilterChange('product', filters.product.filter(id => id !== p.id));
                                                        }
                                                    }}
                                                    className="text-light"
                                                />
                                            </div>
                                        ));
                                    })()}
                                    {products.filter(p => !productSearchTerm || (p.id && p.id.toLowerCase().includes(productSearchTerm))).length === 0 && (
                                        <small className="text-muted">Товары не найдены</small>
                                    )}
                                </div>
                            </>
                        )}
                    </div>
                    <small className="text-muted">Ничего не выбрано — показываем все товары</small>
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
                <Col md={2}>
                    <Form.Label className="text-light">Удалён</Form.Label>
                    <Form.Select
                        value={filters.deleted}
                        onChange={(e) => handleFilterChange('deleted', e.target.value)}
                        className="bg-dark border-success text-light"
                    >
                        <option value="">Все</option>
                        <option value="false">Не удалённые</option>
                        <option value="true">Только удалённые</option>
                    </Form.Select>
                </Col>
            </Row>
            <Row className="g-3 mt-2 align-items-end">
                <Col md={3}>
                    <Form.Label className="text-light">Дата с</Form.Label>
                    <Form.Control
                        type="date"
                        value={filters.dateFrom}
                        onChange={(e) => handleDateChange('dateFrom', e.target.value)}
                        className="bg-dark border-success text-light"
                    />
                </Col>
                <Col md={3}>
                    <Form.Label className="text-light">Дата по</Form.Label>
                    <Form.Control
                        type="date"
                        value={filters.dateTo}
                        onChange={(e) => handleDateChange('dateTo', e.target.value)}
                        className="bg-dark border-success text-light"
                    />
                </Col>
                <Col md={3}>
                    <Form.Label className="text-light">Последние N дней</Form.Label>
                    <Form.Control
                        type="number"
                        min="1"
                        placeholder="Например, 7"
                        value={filters.lastNDays}
                        onChange={(e) => handleLastNDaysChange(e.target.value)}
                        className="bg-dark border-success text-light"
                    />
                </Col>
            </Row>
        </div>
    );
};

export default ReviewFilters; 