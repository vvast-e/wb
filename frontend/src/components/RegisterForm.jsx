import { useState, useEffect } from 'react';
import api from '../api';
import { useNavigate } from 'react-router-dom';
import { Form, Button, Alert, Card, Spinner, Row, Col } from 'react-bootstrap';

export default function RegisterForm({ isAdminCreating = false, onSuccess }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [status, setStatus] = useState('user');
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [loading, setLoading] = useState(false);
    const [brands, setBrands] = useState({});
    const [loadingBrands, setLoadingBrands] = useState(false);
    const [userBrands, setUserBrands] = useState([{ brand: '' }]);
    const [ownerAdmin, setOwnerAdmin] = useState('');
    const [imagebbKey, setImagebbKey] = useState('');

    useEffect(() => {
        if (isAdminCreating) {
            const token = localStorage.getItem('token');
            if (token) {
                const adminEmail = JSON.parse(atob(token.split('.')[1])).email;
                setOwnerAdmin(adminEmail);
            }
        }
    }, [isAdminCreating]);

    useEffect(() => {
        const fetchBrands = async () => {
            try {
                setLoadingBrands(true);
                const token = localStorage.getItem('token');
                const response = await api.get(
                    `${import.meta.env.VITE_API_URL}/admin/brands`,
                    {
                        headers: { 'Authorization': `Bearer ${token}` }
                    }
                );
                if (response.data && typeof response.data === 'object' && !Array.isArray(response.data)) {
                    setBrands(response.data);
                } else {
                    console.error('Ожидался объект с магазинами, получено:', response.data);
                    setBrands({});
                }
            } catch (err) {
                console.error('Ошибка загрузки магазинов:', err);
                if (err.response?.status !== 404) {
                    setError('Не удалось загрузить список магазинов');
                }
                setBrands({});
            } finally {
                setLoadingBrands(false);
            }
        };
        fetchBrands();
    }, []);

    const handleAddBrand = () => {
        setUserBrands([...userBrands, { brand: '' }]);
    };

    const handleRemoveBrand = (index) => {
        if (userBrands.length <= 1) return;
        const newBrands = [...userBrands];
        newBrands.splice(index, 1);
        setUserBrands(newBrands);
    };

    const handleBrandChange = (index, value) => {
        const newBrands = [...userBrands];
        newBrands[index].brand = value;
        setUserBrands(newBrands);
    };

    const handleRegister = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            const wbApiKeys = {};
            userBrands.forEach(item => {
                if (item.brand && brands[item.brand]) {
                    wbApiKeys[item.brand] = brands[item.brand].api_key;
                }
            });

            const payload = {
                email,
                password,
                status,
                wb_api_key: wbApiKeys,
                imagebb_key: imagebbKey || '', // Добавлено поле imagebb_key
                ...(isAdminCreating && { owner_admin: ownerAdmin })
            };

            await api.post(
                `${import.meta.env.VITE_API_URL}/admin/register`,
                payload,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                }
            );

            setSuccess(
                status === 'admin'
                    ? 'Администратор успешно зарегистрирован!'
                    : 'Пользователь успешно зарегистрирован!'
            );
            setError(null);
            if (onSuccess) onSuccess();
        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка регистрации');
            setSuccess(null);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '100vh' }}>
            <Card className="w-100" style={{ maxWidth: '800px' }} bg="dark" text="light">
                <Card.Body>
                    <h2 className="text-center text-success mb-4">Добавить сотрудника</h2>
                    {error && <Alert variant="danger">{error}</Alert>}
                    {success && <Alert variant="success">{success}</Alert>}
                    <Form onSubmit={handleRegister}>
                        <Form.Group className="mb-3">
                            <Form.Label>Email</Form.Label>
                            <Form.Control
                                type="email"
                                placeholder="Введите email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                className="bg-secondary border-success text-light"
                            />
                        </Form.Group>
                        <Form.Group className="mb-3">
                            <Form.Label>Пароль</Form.Label>
                            <Form.Control
                                type="password"
                                placeholder="Введите пароль"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                className="bg-secondary border-success text-light"
                            />
                        </Form.Group>
                        <Form.Group className="mb-3">
                            <Form.Label>Роль</Form.Label>
                            <Form.Select
                                value={status}
                                onChange={(e) => setStatus(e.target.value)}
                                className="bg-secondary border-success text-light"
                            >
                                <option value="user">Пользователь</option>
                                <option value="admin">Администратор</option>
                            </Form.Select>
                        </Form.Group>

                        {/* Поле для ImageBB Key */}
                        <Form.Group className="mb-3">
                            <Form.Label>ImageBB API Key</Form.Label>
                            <Form.Control
                                type="text"
                                placeholder="Введите ImageBB API ключ"
                                value={imagebbKey}
                                onChange={(e) => setImagebbKey(e.target.value)}
                                className="bg-secondary border-success text-light"
                            />
                        </Form.Group>

                        <Form.Group className="mb-4">
                            <Form.Label>Открыть магазин</Form.Label>
                            {userBrands.map((brandItem, index) => (
                                <div key={index} className="mb-3 p-3 border border-success rounded">
                                    <Row className="mb-2">
                                        <Col md={11}>
                                            <Form.Label>Магазин</Form.Label>
                                            {loadingBrands ? (
                                                <Spinner animation="border" size="sm" variant="success" />
                                            ) : (
                                                <Form.Select
                                                    value={brandItem.brand}
                                                    onChange={(e) => handleBrandChange(index, e.target.value)}
                                                    className="bg-secondary border-success text-light"
                                                    required
                                                >
                                                    <option value="">Выберите магазин</option>
                                                    {Object.keys(brands).map((brandName) => (
                                                        <option key={brandName} value={brandName}>
                                                            {brandName}
                                                        </option>
                                                    ))}
                                                </Form.Select>
                                            )}
                                        </Col>
                                        <Col md={1} className="d-flex align-items-end">
                                            <Button
                                                variant="outline-danger"
                                                onClick={() => handleRemoveBrand(index)}
                                                disabled={userBrands.length <= 1}
                                                className="w-100"
                                            >
                                                ×
                                            </Button>
                                        </Col>
                                    </Row>
                                </div>
                            ))}
                            <Button
                                variant="outline-success"
                                onClick={handleAddBrand}
                                className="w-100"
                            >
                                + Добавить магазин
                            </Button>
                        </Form.Group>

                        <Button
                            type="submit"
                            variant="success"
                            className="w-100 mb-3"
                            disabled={loading}
                        >
                            {loading ? (
                                <Spinner animation="border" size="sm" />
                            ) : 'Зарегистрировать'}
                        </Button>
                    </Form>
                </Card.Body>
            </Card>
        </div>
    );
}