import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Form, Button, Alert, Card, Spinner } from 'react-bootstrap';

export default function AuthForm({ setIsAuth }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const [checkingAdmin, setCheckingAdmin] = useState(false);
    const navigate = useNavigate();

    const checkAdminStatus = async (token) => {
        try {
            setCheckingAdmin(true);
            const response = await axios.get(`${import.meta.env.VITE_API_URL}/admin/check-admin`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            return response.data?.is_admin || false;
        } catch (err) {
            console.error("Ошибка при проверке прав администратора:", err);
            return false;
        } finally {
            setCheckingAdmin(false);
        }
    };

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const formData = new FormData();
            formData.append('username', email);
            formData.append('password', password);

            // Получаем токен
            const authResponse = await axios.post(
                `${import.meta.env.VITE_API_URL}/auth/token`,
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } }
            );

            const token = authResponse.data.access_token;
            localStorage.setItem('token', token);
            setIsAuth(true);

            // Проверяем права администратора
            const isAdmin = await checkAdminStatus(token);

            // Переходим на главную страницу с навигацией после успешного входа
            navigate('/home');

        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка авторизации');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '100vh' }}>
            <Card className="w-100" style={{ maxWidth: '400px' }} bg="dark" text="light">
                <Card.Body>
                    <h2 className="text-center text-success mb-4">Авторизация</h2>

                    {error && <Alert variant="danger">{error}</Alert>}

                    <Form onSubmit={handleLogin}>
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

                        <Form.Group className="mb-4">
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

                        <Button
                            type="submit"
                            variant="success"
                            className="w-100 mb-3"
                            disabled={loading || checkingAdmin}
                        >
                            {loading || checkingAdmin ? (
                                <>
                                    <Spinner animation="border" size="sm" className="me-2" />
                                    {checkingAdmin ? 'Проверка прав...' : 'Вход...'}
                                </>
                            ) : 'Войти'}
                        </Button>
                        <div className="text-center mt-3">
                            <Button
                                variant="outline-success"
                                onClick={() => navigate('/register')}
                                className="w-100"
                            >
                                Регистрация
                            </Button>
                        </div>
                    </Form>
                </Card.Body>
            </Card>
        </div>
    );
}