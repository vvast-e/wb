import { useEffect, useState } from 'react';
import api from '../api';
import ProductCard from '../components/ProductCard';
import { Container, Row, Col, Spinner, Alert, Button, Form, InputGroup, ButtonGroup } from 'react-bootstrap';
import { BiKey, BiUserCircle, BiRefresh } from 'react-icons/bi';

const Home = () => {
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [userStatus, setUserStatus] = useState(null);
    const [brands, setBrands] = useState({});
    const [selectedBrand, setSelectedBrand] = useState('');
    const [brandsLoading, setBrandsLoading] = useState(false);
    const [vendorCode, setVendorCode] = useState('');
    const [searchResult, setSearchResult] = useState(null);
    const [searchLoading, setSearchLoading] = useState(false);
    const [searchError, setSearchError] = useState(null);

    useEffect(() => {
        fetchUserData();
        fetchBrands();
    }, []);

    useEffect(() => {
        if (selectedBrand) {
            fetchProducts(selectedBrand);
        }
    }, [selectedBrand]);

    const fetchBrands = async () => {
        try {
            setBrandsLoading(true);
            const token = localStorage.getItem('token');
            const response = await api.get(`/admin/brands`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const brandData = response.data;

            if (Object.keys(brandData).length > 0) {
                setBrands(brandData);
                setSelectedBrand(Object.keys(brandData)[0]);
            } else {
                setBrands({});
            }

        } catch (err) {
            if (err.response?.status === 404) {
                setBrands(null);  // 💡 нет брендов
            } else {
                console.error("Ошибка при получении брендов:", err);
                setBrands({});
            }
        } finally {
            setBrandsLoading(false);
        }
    };


    const fetchUserData = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await api.get(`/admin/check-admin`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            setUserStatus(response.data.status);
        } catch (err) {
            console.error("Ошибка при получении данных пользователя:", err);
        }
    };

    const fetchProducts = async (brand) => {
        try {
            setLoading(true);
            setError(null);
            const token = localStorage.getItem('token');
            const url = `${import.meta.env.VITE_API_URL}/items?brand=${encodeURIComponent(brand)}`;

            const response = await api.get(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.data?.success || !response.data?.data?.cards) {
                throw new Error(response.data?.error || "Ошибка при загрузке товаров");
            }

            setProducts(response.data.data.cards);
        } catch (err) {
            const errorMessage = err.response?.data?.detail ||
                err.response?.data?.message ||
                err.message ||
                "Неизвестная ошибка при загрузке товаров";

            setError(errorMessage);
            setProducts([]);
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = async () => {
        try {
            setSearchLoading(true);
            setSearchError(null);
            setSearchResult(null);

            const token = localStorage.getItem('token');

            if (!vendorCode.trim()) {
                await fetchProducts(selectedBrand);
            } else {
                // Если есть vendorCode - ищем конкретный товар
                const response = await api.get(
                    `${import.meta.env.VITE_API_URL}/items/search/${encodeURIComponent(vendorCode)}?brand=${encodeURIComponent(selectedBrand)}`,
                    {
                        headers: { 'Authorization': `Bearer ${token}` }
                    }
                );

                if (response.data?.success) {
                    setSearchResult(response.data.data);
                } else {
                    throw new Error(response.data?.error || "Товар не найден");
                }
            }
        } catch (err) {
            setSearchError(err.response?.data?.detail || err.message || "Ошибка поиска");
        } finally {
            setVendorCode(''); // Очищаем поле ввода в любом случае
            setSearchLoading(false);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
    };

    return (
        <Container className="py-5">
            <div className="d-flex justify-content-between align-items-center mb-4">
                <h1 className="text-success">Мои товары</h1>
            </div>

            {/* Переключатель брендов */}
            {!brandsLoading && brands && Object.keys(brands).length > 0 && (
                <div className="mb-4">
                    <h4 className="mb-3">Выберите магазин</h4>
                    <ButtonGroup className="flex-wrap">
                        {Object.keys(brands).map(brand => (
                            <Button
                                key={brand}
                                variant={selectedBrand === brand ? 'success' : 'outline-success'}
                                onClick={() => setSelectedBrand(brand)}
                                className="me-2 mb-2"
                            >
                                {brand}
                            </Button>
                        ))}
                    </ButtonGroup>
                </div>
            )}

            {brands === null && (
                <Alert variant="info" className="mt-4">
                    <Alert.Heading>У вас пока нет добавленных магазинов</Alert.Heading>
                    <p>Для начала работы с товарами необходимо добавить хотя бы один бренд и WB API ключ.</p>
                    <Button
                        variant="success"
                        onClick={() => window.location.href = '/Admin'}
                        className="d-flex align-items-center mt-2"
                    >
                        <BiUserCircle className="me-2" />
                        Перейти в панель админа
                    </Button>
                </Alert>
            )}

            {/* Поисковая форма */}
            <div className="mb-4">
                <h4 className="mb-3">Поиск по артикулу продавца</h4>
                <InputGroup>
                    <Form.Control
                        type="text"
                        placeholder="Введите артикул продавца"
                        value={vendorCode}
                        onChange={(e) => setVendorCode(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    />
                    <Button
                        variant="success"
                        onClick={handleSearch}
                        disabled={searchLoading}
                    >
                        {searchLoading ? (
                            <Spinner animation="border" size="sm" />
                        ) : 'Поиск'}
                    </Button>
                </InputGroup>

                {searchError && (
                    <Alert variant="danger" className="mt-2">
                        {searchError}
                        <Button
                            variant="outline-danger"
                            onClick={handleSearch}
                            size="sm"
                            className="mt-2 d-block"
                        >
                            <BiRefresh className="me-1" />
                            Попробовать снова
                        </Button>
                    </Alert>
                )}
            </div>

            {searchResult && (
                <div className="mb-5">
                    <h4 className="mb-3">Результат поиска</h4>
                    <Row xs={1} sm={2} md={3} lg={4} className="g-4">
                        <Col>
                            <ProductCard product={searchResult} brand={selectedBrand} />
                        </Col>
                    </Row>
                </div>
            )}

            <h4 className="mb-3">
                {selectedBrand ? `Товары магазина ${selectedBrand}` : 'Все товары'}
            </h4>

            {loading ? (
                <div className="text-center py-5">
                    <Spinner animation="border" variant="success" />
                </div>
            ) : error ? (
                <Alert variant="danger" className="mt-4">
                    {error.includes("WB API key not configured") ||
                        error.includes("WB API ключ не настроен") ? (
                        <>
                            <Alert.Heading className="d-flex align-items-center">
                                <BiKey className="me-2" size={20} />
                                Не настроен WB API ключ
                            </Alert.Heading>
                            <div className="d-flex align-items-center mt-2">
                                <p className="mb-0 me-2">Для работы с товарами необходимо добавить WB API ключ</p>
                                <Button
                                    variant="outline-success"
                                    onClick={() => window.location.href = '/Admin'}
                                    size="sm"
                                    className="d-flex align-items-center"
                                >
                                    <BiUserCircle className="me-1" />
                                    Перейти в панель админа
                                </Button>
                            </div>
                        </>
                    ) : (
                        <>
                            <Alert.Heading>Ошибка загрузки товаров</Alert.Heading>
                            <p>{error}</p>
                            <Button
                                variant="outline-secondary"
                                onClick={fetchProducts}
                                size="sm"
                                className="mt-2"
                            >
                                <BiRefresh className="me-1" />
                                Попробовать снова
                            </Button>
                        </>
                    )}
                </Alert>
            ) : products.length > 0 ? (
                <Row xs={1} sm={2} md={3} lg={4} className="g-4">
                    {products.map((product, index) => (
                        <Col key={index}>
                            <ProductCard product={product} brand={selectedBrand} />
                        </Col>
                    ))}
                </Row>
            ) : (
                <Alert variant="info">Карточки товаров не найдены</Alert>
            )}
        </Container>
    );

};

export default Home;
