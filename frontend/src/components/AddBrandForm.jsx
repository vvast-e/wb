import { useState, useEffect } from 'react';
import { Form, Button, Alert, Spinner, Card, Tabs, Tab, Toast, ToastContainer } from 'react-bootstrap';
import api from '../api';
import { BiPlusCircle, BiRefresh, BiTrash, BiImage } from 'react-icons/bi';

const AddBrandForm = ({ onSuccess }) => {
    const [mode, setMode] = useState('add');
    const [brands, setBrands] = useState({});
    const [formData, setFormData] = useState({
        platform: 'wb',  // По умолчанию WB
        api_key: '',
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [selectedBrand, setSelectedBrand] = useState('');
    const [imagebbKey, setImagebbKey] = useState('');
    const [toast, setToast] = useState({ show: false, message: '', variant: 'success' });

    // Загрузка брендов и текущего ImageBB ключа
    useEffect(() => {
        const fetchBrandsAndKeys = async () => {
            try {
                setLoading(true);
                setError(null);

                const token = localStorage.getItem('token');

                // Получаем бренды
                const brandsRes = await api.get('/admin/brands', {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (brandsRes.data && typeof brandsRes.data === 'object') {
                    setBrands(brandsRes.data);
                }

                // Получаем ImageBB ключ
                const imagebbRes = await api.get('/admin/imagebb-key', {
                    headers: { Authorization: `Bearer ${token}` }
                });

                setImagebbKey(imagebbRes.data.imagebb_key || '');

            } catch (err) {
                setError(err.response?.data?.detail || 'Не удалось загрузить данные');
            } finally {
                setLoading(false);
            }
        };

        fetchBrandsAndKeys();
    }, [success]);

    // Удаление бренда
    const handleDeleteBrand = async () => {
        if (!selectedBrand) {
            setError("Выберите магазин для удаления");
            return;
        }
        if (!window.confirm(`Вы уверены, что хотите удалить магазин "${selectedBrand}"?`)) {
            return;
        }
        try {
            setLoading(true);
            setError(null);
            const token = localStorage.getItem('token');
            await api.delete(
                `/admin/brands/${selectedBrand}`,
                {
                    headers: { Authorization: `Bearer ${token}` }
                }
            );
            setSuccess(`Магазин "${selectedBrand}" успешно удален`);
            setSelectedBrand('');
            if (onSuccess) onSuccess();
        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка при удалении магазина');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            const url = mode === 'add'
                ? `${import.meta.env.VITE_API_URL}/admin/brands`
                : `${import.meta.env.VITE_API_URL}/admin/brands/${selectedBrand}`;
            const method = mode === 'add' ? 'post' : 'put';

            const requestData = {
                platform: formData.platform,
                wb_name: formData.api_key,  // API ключ передаем в поле wb_name
            };

            const response = await api[method](url, requestData, {
                headers: { Authorization: `Bearer ${token}` }
            });

            // Получаем название магазина из ответа API
            let shopName = formData.platform; // fallback
            if (mode === 'add' && response.data) {
                // Вычисляем реально добавленный бренд по разнице ключей
                const beforeKeys = Object.keys(brands || {});
                const afterKeys = Object.keys(response.data || {});
                const diff = afterKeys.find((k) => !beforeKeys.includes(k));
                if (diff) {
                    shopName = diff;
                } else if (afterKeys.length > 0) {
                    // На всякий случай берем последний ключ (как наиболее вероятно новый)
                    shopName = afterKeys[afterKeys.length - 1];
                }
            }

            setSuccess(mode === 'add'
                ? 'Магазин успешно добавлен. Не забудьте добавить ImageBB ключ во вкладке "ImageBB Key" для работы с изображениями.'
                : 'API ключ успешно обновлен');
            setFormData({ platform: 'wb', api_key: '' });
            setSelectedBrand('');
            if (onSuccess) onSuccess();

            // Если добавлен новый магазин, запускаем парсер отзывов
            if (mode === 'add') {
                try {
                    setToast({ show: true, message: `Запуск парсера отзывов для магазина "${shopName}"...`, variant: 'info' });

                    const parseResponse = await api.post(
                        `${import.meta.env.VITE_API_URL}/analytics/shop/${shopName}/parse-feedbacks`,
                        {},
                        {
                            headers: { Authorization: `Bearer ${token}` }
                        }
                    );

                    // Проверяем статус парсинга
                    if (parseResponse.data && parseResponse.data.success) {
                        setToast({ show: true, message: `Парсер отзывов для магазина "${shopName}" успешно завершен! Обработано отзывов: ${parseResponse.data.processed_count || 0}`, variant: 'success' });
                    } else {
                        setToast({ show: true, message: `Парсер отзывов для магазина "${shopName}" запущен, но завершился с предупреждениями`, variant: 'warning' });
                    }
                } catch (err) {
                    setToast({ show: true, message: `Ошибка запуска парсера для "${shopName}": ${err.response?.data?.detail || err.message}`, variant: 'danger' });
                }
            }
        } catch (err) {
            setError(err.response?.data?.message || 'Ошибка операции');
        } finally {
            setLoading(false);
        }
    };

    // Выбор бренда для редактирования
    const handleBrandSelect = (brandName) => {
        setSelectedBrand(brandName);
        if (brandName && brands[brandName]) {
            setFormData({
                platform: brands[brandName].platform || 'wb',
                api_key: brands[brandName].api_key || '',
            });
        }
    };

    // Сохранение ImageBB ключа
    const handleImagebbSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            await api.post(
                `${import.meta.env.VITE_API_URL}/admin/imagebb-key`,
                { imagebb_key: formData.imagebb_key },
                {
                    headers: { Authorization: `Bearer ${token}` }
                }
            );
            setSuccess('ImageBB ключ успешно сохранен');
            setImagebbKey(formData.imagebb_key);
            setFormData({ ...formData, imagebb_key: '' });
        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка при сохранении ключа');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="bg-dark text-light border-success p-4">
            <Tabs
                activeKey={mode}
                onSelect={(k) => {
                    setMode(k);
                    setFormData({ platform: 'wb', api_key: '' });
                    setSelectedBrand('');
                    setError(null);
                    setSuccess(null);
                }}
                className="mb-3"
            >
                {/* Вкладка: Добавить магазин */}
                <Tab eventKey="add" title="Добавить магазин">
                    <BrandForm
                        formData={formData}
                        setFormData={setFormData}
                        loading={loading}
                        onSubmit={handleSubmit}
                        submitText="Добавить магазин"
                        showNameField
                        showImagebbField
                    />
                </Tab>

                {/* Вкладка: Обновить API ключ */}
                <Tab eventKey="update" title="Обновить API ключ">
                    {Object.keys(brands).length === 0 ? (
                        <div className="text-center py-4">
                            <h5>Нет доступных магазинов</h5>
                            <p className="text-muted mb-3">Сначала добавьте магазин во вкладке "Добавить магазин"</p>
                            <Button
                                variant="success"
                                onClick={() => setMode('add')}
                                className="d-flex align-items-center mx-auto"
                            >
                                <BiPlusCircle className="me-2" />
                                Добавить магазин
                            </Button>
                        </div>
                    ) : (
                        <>
                            <Form.Group className="mb-3">
                                <Form.Label>Выберите магазин</Form.Label>
                                <Form.Select
                                    value={selectedBrand}
                                    onChange={(e) => handleBrandSelect(e.target.value)}
                                    className="bg-dark border-success text-light"
                                >
                                    <option value="">Выберите магазин...</option>
                                    {Object.keys(brands).map((brandName) => (
                                        <option key={brandName} value={brandName}>
                                            {brandName}
                                        </option>
                                    ))}
                                </Form.Select>
                            </Form.Group>
                            {selectedBrand && (
                                <BrandForm
                                    formData={formData}
                                    setFormData={setFormData}
                                    loading={loading}
                                    onSubmit={handleSubmit}
                                    submitText="Обновить API ключ"
                                    showNameField={false}
                                    showImagebbField
                                />
                            )}
                        </>
                    )}
                </Tab>

                {/* Вкладка: Удалить магазин */}
                <Tab eventKey="delete" title="Удалить магазин">
                    {Object.keys(brands).length === 0 ? (
                        <div className="text-center py-4">
                            <h5>Нет доступных магазинов</h5>
                            <p className="text-muted mb-3">Нет магазинов для удаления</p>
                        </div>
                    ) : (
                        <>
                            <Form.Group className="mb-3">
                                <Form.Label>Выберите магазин для удаления</Form.Label>
                                <Form.Select
                                    value={selectedBrand}
                                    onChange={(e) => handleBrandSelect(e.target.value)}
                                    className="bg-dark border-success text-light"
                                >
                                    <option value="">Выберите магазин...</option>
                                    {Object.keys(brands).map((brandName) => (
                                        <option key={brandName} value={brandName}>
                                            {brandName}
                                        </option>
                                    ))}
                                </Form.Select>
                            </Form.Group>
                            {selectedBrand && (
                                <Button
                                    variant="success"
                                    onClick={handleDeleteBrand}
                                    disabled={loading}
                                    className="mt-3"
                                >
                                    {loading ? <Spinner size="sm" /> : (
                                        <>
                                            <BiTrash className="me-1" />
                                            Удалить магазин
                                        </>
                                    )}
                                </Button>
                            )}
                        </>
                    )}
                </Tab>

                {/* Вкладка: ImageBB Key */}
                <Tab eventKey="imagebb" title="ImageBB Key">
                    <Form onSubmit={handleImagebbSubmit}>
                        <Form.Group className="mb-3">
                            <Form.Label>Текущий ключ</Form.Label>
                            <Form.Control
                                type="text"
                                value={imagebbKey}
                                readOnly
                                className="bg-dark border-success text-light"
                            />
                        </Form.Group>

                        <Form.Group className="mb-3">
                            <Form.Label>Новый ImageBB API Key</Form.Label>
                            <Form.Control
                                name="imagebb_key"
                                value={formData.imagebb_key || ''}
                                onChange={(e) => setFormData({ ...formData, imagebb_key: e.target.value })}
                                required
                                className="bg-dark border-success text-light"
                            />
                        </Form.Group>

                        <Button variant="success" type="submit" disabled={loading}>
                            {loading ? <Spinner size="sm" /> : 'Сохранить ключ'}
                        </Button>
                    </Form>
                </Tab>

                {/* Новая вкладка: Принудительный парсинг */}
                <Tab eventKey="force-parse" title="Принудительный парсинг">
                    {Object.keys(brands).length === 0 ? (
                        <div className="text-center py-4">
                            <h5>Нет доступных магазинов</h5>
                            <p className="text-muted mb-3">Сначала добавьте магазин во вкладке "Добавить магазин"</p>
                        </div>
                    ) : (
                        <>
                            <Form.Group className="mb-3">
                                <Form.Label>Выберите магазин для парсинга</Form.Label>
                                <Form.Select
                                    value={selectedBrand}
                                    onChange={(e) => setSelectedBrand(e.target.value)}
                                    className="bg-dark border-success text-light"
                                >
                                    <option value="">Выберите магазин...</option>
                                    {Object.keys(brands).map((brandName) => (
                                        <option key={brandName} value={brandName}>
                                            {brandName}
                                        </option>
                                    ))}
                                </Form.Select>
                            </Form.Group>
                            {selectedBrand && (
                                <Button
                                    variant="success"
                                    disabled={!selectedBrand || loading}
                                    onClick={async () => {
                                        if (!selectedBrand) return;
                                        setLoading(true);
                                        try {
                                            const token = localStorage.getItem('token');
                                            setToast({ show: true, message: `Запуск парсера отзывов для магазина "${selectedBrand}"...`, variant: 'info' });

                                            const parseResponse = await api.post(
                                                `${import.meta.env.VITE_API_URL}/analytics/shop/${selectedBrand}/parse-feedbacks`,
                                                {},
                                                {
                                                    headers: { Authorization: `Bearer ${token}` },
                                                    params: {}
                                                }
                                            );

                                            // Проверяем статус парсинга
                                            if (parseResponse.data && parseResponse.data.success) {
                                                setToast({ show: true, message: `Парсер отзывов для магазина "${selectedBrand}" успешно завершен! Обработано отзывов: ${parseResponse.data.processed_count || 0}`, variant: 'success' });
                                            } else {
                                                setToast({ show: true, message: `Парсер отзывов для магазина "${selectedBrand}" запущен, но завершился с предупреждениями`, variant: 'warning' });
                                            }
                                        } catch (err) {
                                            setToast({ show: true, message: `Ошибка запуска парсера для "${selectedBrand}": ${err.response?.data?.detail || err.message}`, variant: 'danger' });
                                        } finally {
                                            setLoading(false);
                                        }
                                    }}
                                    className="mt-3"
                                >
                                    {loading ? <Spinner size="sm" /> : 'Запустить парсер'}
                                </Button>
                            )}
                        </>
                    )}
                </Tab>
            </Tabs>

            {/* Сообщения об ошибках и успехе */}
            {error && (
                <Alert variant="danger">
                    <Alert.Heading>Ошибка</Alert.Heading>
                    <p>{error}</p>
                    <Button
                        variant="outline-danger"
                        onClick={() => window.location.reload()}
                        size="sm"
                        className="mt-2"
                    >
                        <BiRefresh className="me-1" />
                        Обновить страницу
                    </Button>
                </Alert>
            )}
            {success && <Alert variant="success">{success}</Alert>}

            {/* Toast уведомление */}
            <ToastContainer position="bottom-end" className="p-3" style={{ zIndex: 9999 }}>
                <Toast
                    bg={toast.variant}
                    onClose={() => setToast({ ...toast, show: false })}
                    show={toast.show}
                    delay={toast.variant === 'info' ? 3000 : 8000}
                    autohide
                >
                    <Toast.Header closeButton>
                        <strong className="me-auto">
                            {toast.variant === 'success' ? '✅ Успех' :
                                toast.variant === 'danger' ? '❌ Ошибка' :
                                    toast.variant === 'warning' ? '⚠️ Предупреждение' :
                                        'ℹ️ Информация'}
                        </strong>
                    </Toast.Header>
                    <Toast.Body className="text-white">{toast.message}</Toast.Body>
                </Toast>
            </ToastContainer>
        </Card>
    );
};

// Компонент формы бренда
const BrandForm = ({
    formData,
    setFormData,
    loading,
    onSubmit,
    submitText,
    showNameField = true,
}) => {
    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    return (
        <Form onSubmit={onSubmit}>
            {showNameField && (
                <Form.Group className="mb-3">
                    <Form.Label>Платформа</Form.Label>
                    <Form.Select
                        name="platform"
                        value={formData.platform}
                        onChange={handleChange}
                        required
                        className="bg-dark border-success text-light"
                    >
                        <option value="wb">WB (Wildberries)</option>
                        <option value="ozon">Ozon</option>
                    </Form.Select>
                    <Form.Text className="text-muted">
                        {formData.platform === 'wb'
                            ? 'Название магазина будет получено автоматически через API WB'
                            : 'Для Ozon название магазина будет получено автоматически (пока заглушка)'
                        }
                    </Form.Text>
                </Form.Group>
            )}

            <Form.Group className="mb-3">
                <Form.Label>API Key</Form.Label>
                <Form.Control
                    name="api_key"
                    value={formData.api_key}
                    onChange={handleChange}
                    required
                    className="bg-dark border-success text-light"
                    placeholder={formData.platform === 'wb' ? 'WB API Key' : 'Ozon API Key'}
                />
            </Form.Group>

            <Button
                variant="success"
                type="submit"
                disabled={loading}
            >
                {loading ? <Spinner size="sm" /> : submitText}
            </Button>
        </Form>
    );
};

export default AddBrandForm;