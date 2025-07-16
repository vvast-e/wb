import { useEffect, useState } from 'react';
import api from '../api';
import { Container, Table, Spinner, Alert, Button, Pagination, Form, Row, Col } from 'react-bootstrap';
import { useLocation } from 'react-router-dom';
import { BiRefresh, BiChevronUp, BiChevronDown } from 'react-icons/bi';
import '../components/HistoryPage.css';

const actionMap = {
    update_media: 'Обновление медиа',
    update_content: 'Обновление контента',
    revert_media: 'Откат медиа',
    revert_content: 'Откат контента',
    delete: 'Удаление',
    create: 'Создание',
    revert: 'Откат',
    // ... другие действия
};

const statusMap = {
    pending: 'Ожидает',
    completed: 'Выполнено',
    error: 'Ошибка',
    // ... другие статусы
};

const changeKeyMap = {
    title: 'Название',
    brand: 'Бренд',
    description: 'Описание',
    dimensions: 'Габариты',
    characteristics: 'Характеристики',
    media: 'Медиа',
    revert: 'Откат'
};

const sortableColumns = [
    { key: "created_at", label: "Дата создания" },
    { key: "scheduled_at", label: "Дата выполнения" },
    { key: "vendor_code", label: "Артикул" },
    { key: "brand", label: "Бренд" },
    { key: "action", label: "Действие" },
    { key: "status", label: "Статус" },
    { key: "user_email", label: "Пользователь" }
];

const HistoryPage = () => {
    const location = useLocation();
    const params = new URLSearchParams(location.search);
    const brand = params.get('brand') || '';
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedHistory, setSelectedHistory] = useState(null);

    const [pagination, setPagination] = useState({
        page: 1,
        perPage: 20,
        total: 0,
        totalPages: 1
    });

    const [orderBy, setOrderBy] = useState("created_at");
    const [orderDir, setOrderDir] = useState("desc");

    const [filters, setFilters] = useState({
        email: '',
        brand: '',
        vendor_code: '',
        date_from: '',
        date_to: ''
    });

    const [brands, setBrands] = useState([]);
    const [selectedBrand, setSelectedBrand] = useState('');
    const [brandsLoading, setBrandsLoading] = useState(false);
    const [brandsError, setBrandsError] = useState(null);

    // Получение брендов при монтировании
    useEffect(() => {
        const fetchBrands = async () => {
            try {
                setBrandsLoading(true);
                setBrandsError(null);
                const token = localStorage.getItem('token');
                const response = await api.get('/admin/brands');
                const brandData = response.data;
                const brandNames = Object.keys(brandData);
                setBrands(brandNames);
                if (brandNames.length > 0) {
                    setSelectedBrand(brandNames[0]);
                }
            } catch (err) {
                setBrandsError('Не удалось загрузить бренды');
                setBrands([]);
            } finally {
                setBrandsLoading(false);
            }
        };
        fetchBrands();
    }, []);

    // Обновляем фильтр при смене бренда
    useEffect(() => {
        setFilters(prev => ({ ...prev, brand: selectedBrand }));
        setPagination(prev => ({ ...prev, page: 1 }));
    }, [selectedBrand]);

    useEffect(() => {
        fetchHistory();
    }, [pagination.page, pagination.perPage, orderBy, orderDir, filters]);

    const fetchHistory = async () => {
        if (!selectedBrand) {
            setHistory([]);
            setError('Выберите бренд для просмотра истории');
            setLoading(false);
            return;
        }
        try {
            setLoading(true);
            setError(null);
            const token = localStorage.getItem('token');
            const cleanedFilters = Object.fromEntries(
                Object.entries(filters).filter(([_, value]) => value !== '')
            );
            const response = await api.get('/history', {
                params: {
                    page: pagination.page,
                    per_page: pagination.perPage,
                    order_by: orderBy,
                    order_dir: orderDir,
                    ...cleanedFilters
                },
                headers: { 'Authorization': `Bearer ${token}` }
            });
            setHistory(response.data.items);
            setPagination(prev => ({
                ...prev,
                total: response.data.total,
                totalPages: response.data.total_pages
            }));
        } catch (err) {
            // Обработка ошибок FastAPI (422 и др.)
            const detail = err.response?.data?.detail;
            if (Array.isArray(detail)) {
                setError(detail.map(e => `${e.loc?.join('.')}: ${e.msg}`).join('; '));
            } else if (err.response?.status === 404) {
                setError('Никаких изменений не было');
            } else {
                setError(detail || err.message || 'Ошибка загрузки истории');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async (format) => {
        const token = localStorage.getItem('token');
        const cleanedFilters = Object.fromEntries(
            Object.entries(filters).filter(([_, value]) => value !== '')
        );

        const query = new URLSearchParams({
            format,
            ...cleanedFilters
        });

        const url = `${import.meta.env.VITE_API_URL}/history/export?${query.toString()}`;

        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) throw new Error(`Ошибка экспорта: ${response.statusText}`);

            const blob = await response.blob();
            const filename = format === 'excel' ? 'history_export.xlsx' : 'history_export.csv';

            const link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = filename;
            link.click();
            window.URL.revokeObjectURL(link.href);
        } catch (err) {
            alert(err.message);
        }
    };

    const handleSort = (col) => {
        if (orderBy === col) {
            setOrderDir(prev => (prev === "asc" ? "desc" : "asc"));
        } else {
            setOrderBy(col);
            setOrderDir("asc");
        }
        setPagination(prev => ({ ...prev, page: 1 }));
    };

    const handleFilterSubmit = (e) => {
        e.preventDefault();
        setPagination(prev => ({ ...prev, page: 1 }));
        fetchHistory();
    };

    const handleResetFilters = () => {
        setFilters({
            email: '',
            brand: '',
            vendor_code: '',
            date_from: '',
            date_to: ''
        });
        setPagination(prev => ({ ...prev, page: 1 }));
    };

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFilters(prev => ({ ...prev, [name]: value }));
    };

    const formatDate = (dateString) => new Date(dateString).toLocaleString('ru-RU');

    const formatChanges = (changes) => {
        if (!changes) return 'Нет данных';
        return Object.entries(changes).map(([key, value]) => (
            <div key={key}><strong>{changeKeyMap[key] || key}:</strong> {JSON.stringify(value)}</div>
        ));
    };

    const handlePageChange = (newPage) => {
        setPagination(prev => ({ ...prev, page: newPage }));
    };

    const handlePerPageChange = (e) => {
        setPagination(prev => ({
            ...prev,
            perPage: Number(e.target.value),
            page: 1
        }));
    };

    const renderSortIcon = (column) => {
        if (orderBy !== column) return null;
        return orderDir === 'asc' ? <BiChevronUp /> : <BiChevronDown />;
    };

    const renderPaginationItems = () => {
        const items = [];
        const maxVisiblePages = 5;
        let startPage, endPage;

        if (pagination.totalPages <= maxVisiblePages) {
            startPage = 1;
            endPage = pagination.totalPages;
        } else {
            const maxPagesBeforeCurrent = Math.floor(maxVisiblePages / 2);
            const maxPagesAfterCurrent = Math.ceil(maxVisiblePages / 2) - 1;

            if (pagination.page <= maxPagesBeforeCurrent) {
                startPage = 1;
                endPage = maxVisiblePages;
            } else if (pagination.page + maxPagesAfterCurrent >= pagination.totalPages) {
                startPage = pagination.totalPages - maxVisiblePages + 1;
                endPage = pagination.totalPages;
            } else {
                startPage = pagination.page - maxPagesBeforeCurrent;
                endPage = pagination.page + maxPagesAfterCurrent;
            }
        }

        if (startPage > 1) items.push(<Pagination.First key="first" onClick={() => handlePageChange(1)} />);
        items.push(<Pagination.Prev key="prev" onClick={() => handlePageChange(Math.max(1, pagination.page - 1))} disabled={pagination.page === 1} />);

        for (let number = startPage; number <= endPage; number++) {
            items.push(
                <Pagination.Item key={number} active={number === pagination.page} onClick={() => handlePageChange(number)}>
                    {number}
                </Pagination.Item>
            );
        }

        items.push(<Pagination.Next key="next" onClick={() => handlePageChange(Math.min(pagination.totalPages, pagination.page + 1))} disabled={pagination.page === pagination.totalPages} />);
        if (endPage < pagination.totalPages) items.push(<Pagination.Last key="last" onClick={() => handlePageChange(pagination.totalPages)} />);

        return items;
    };

    return (
        <Container className="py-5">
            <div className="d-flex justify-content-between align-items-center mb-4">
                <div className="d-flex align-items-center">
                    <h1 className="text-success mb-0">История изменений</h1>
                </div>
                <div className="d-flex align-items-center">
                    <Form.Select value={pagination.perPage} onChange={handlePerPageChange} style={{ width: '80px', marginRight: '15px' }} disabled={loading}>
                        <option value="10">10</option>
                        <option value="20">20</option>
                        <option value="50">50</option>
                        <option value="100">100</option>
                    </Form.Select>
                    <Button variant="outline-success" onClick={fetchHistory} disabled={loading}>
                        {loading ? <Spinner animation="border" size="sm" /> : <BiRefresh />}
                    </Button>
                </div>
            </div>

            {/* Выпадающий список брендов */}
            <div className="mb-4">
                <Form.Label>Магазин:</Form.Label>
                {brandsLoading ? (
                    <div className="text-muted">Загрузка брендов...</div>
                ) : brandsError ? (
                    <div className="text-danger small">{brandsError}</div>
                ) : brands.length === 0 ? (
                    <div className="text-muted">Нет доступных брендов</div>
                ) : (
                    <Form.Select
                        value={selectedBrand}
                        onChange={e => setSelectedBrand(e.target.value)}
                        style={{ maxWidth: 300 }}
                        className="mb-3"
                    >
                        {brands.map(brand => (
                            <option key={brand} value={brand}>{brand}</option>
                        ))}
                    </Form.Select>
                )}
            </div>

            <Form onSubmit={handleFilterSubmit} className="mb-4">
                <Row className="g-2">
                    <Col md><Form.Control name="email" placeholder="Email" value={filters.email} onChange={handleInputChange} /></Col>
                    <Col md><Form.Control name="vendor_code" placeholder="Артикул" value={filters.vendor_code} onChange={handleInputChange} /></Col>
                    <Col md><Form.Control name="date_from" type="datetime-local" value={filters.date_from} onChange={handleInputChange} /></Col>
                    <Col md><Form.Control name="date_to" type="datetime-local" value={filters.date_to} onChange={handleInputChange} /></Col>
                    <Col md="auto" className="d-flex gap-2">
                        <Button type="submit" variant="success">Поиск</Button>
                        <Button type="button" variant="outline-secondary" onClick={handleResetFilters}>Сброс</Button>
                        <Button type="button" variant="outline-success" onClick={() => handleExport('csv')}>Экспорт CSV</Button>
                        <Button type="button" variant="outline-success" onClick={() => handleExport('excel')}>Экспорт Excel</Button>
                    </Col>
                </Row>
            </Form>

            {loading ? (
                <div className="text-center py-5">
                    <Spinner animation="border" variant="success" />
                </div>
            ) : error ? (
                <Alert variant="danger">
                    <Alert.Heading>Ошибка загрузки истории</Alert.Heading>
                    <p>{error}</p>
                    <Button variant="outline-danger" onClick={fetchHistory} size="sm" className="mt-2">
                        <BiRefresh className="me-1" /> Попробовать снова
                    </Button>
                </Alert>
            ) : history.length > 0 ? (
                <>
                    <div className="table-responsive">
                        <Table striped bordered hover variant="dark" className="mt-4">
                            <thead>
                                <tr>
                                    {sortableColumns.map(col => (
                                        <th key={col.key} onClick={() => handleSort(col.key)} style={{ cursor: 'pointer' }}>
                                            {col.label} {renderSortIcon(col.key)}
                                        </th>
                                    ))}
                                    <th>Изменения</th>
                                </tr>
                            </thead>
                            <tbody>
                                {history.map((item, index) => (
                                    <tr
                                        key={index}
                                        onClick={() => setSelectedHistory(item)}
                                        className={selectedHistory?.id === item.id ? 'selected-history-row' : ''}
                                        style={{ cursor: 'pointer' }}
                                    >
                                        <td>{formatDate(item.created_at)}</td>
                                        <td>{item.scheduled_at ? formatDate(item.scheduled_at) : '-'}</td>
                                        <td>{item.vendor_code}</td>
                                        <td>{item.brand}</td>
                                        <td>{actionMap[item.action] || item.action}</td>
                                        <td>{statusMap[item.status] || item.status}</td>
                                        <td>{item.user?.email || '—'}</td>
                                        <td>{formatChanges(item.changes)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </Table>
                    </div>

                    <div className="d-flex justify-content-between align-items-center mt-4">
                        <div className="text-muted">
                            Показано {(pagination.page - 1) * pagination.perPage + 1}–
                            {Math.min(pagination.page * pagination.perPage, pagination.total)} из {pagination.total} записей
                        </div>
                        <Pagination className="mb-0">{renderPaginationItems()}</Pagination>
                    </div>

                    <div className="d-flex justify-content-end mt-3">
                        <Button
                            variant="danger"
                            disabled={!selectedHistory}
                            onClick={async () => {
                                const confirm = window.confirm("Вы уверены, что хотите откатить изменения?");
                                if (!confirm) return;

                                const token = localStorage.getItem('token');
                                const historyId = selectedHistory.id;
                                const action = selectedHistory.action;

                                let revertEndpoint;
                                if (action === 'update_media') {
                                    revertEndpoint = `/history/${historyId}/revert-media?brand=${encodeURIComponent(brand)}`;
                                } else {
                                    revertEndpoint = `/history/${historyId}/revert`;
                                }

                                try {
                                    await api.post(
                                        `${import.meta.env.VITE_API_URL}${revertEndpoint}`,
                                        {},
                                        { headers: { Authorization: `Bearer ${token}` } }
                                    );
                                    alert("Операция по откату изменений запланирована.");
                                    await fetchHistory();
                                    setSelectedHistory(null);
                                } catch (err) {
                                    alert("Ошибка при откате изменений: " + (err.response?.data?.detail || err.message));
                                }
                            }}
                        >
                            Сбросить изменения
                        </Button>
                    </div>
                </>
            ) : (
                <Alert variant="info">История изменений пуста</Alert>
            )}
        </Container>
    );
};

export default HistoryPage;
