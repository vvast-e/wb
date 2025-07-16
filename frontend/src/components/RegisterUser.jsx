import { useState } from 'react';
import api from '../api';
import { useNavigate } from 'react-router-dom';
import { Form, Button, Alert, Card, Spinner } from 'react-bootstrap';

export default function RegisterUser({ setIsAuth }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleRegister = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await api.post(
                `${import.meta.env.VITE_API_URL}/auth/register`,
                { email, password }
            );

            setSuccess('Регистрация прошла успешно! Перенаправляем на страницу входа...');
            setError(null);

            setTimeout(() => {
                navigate('/'); // Или navigate('/'), если логин на главной
            }, 2000);

        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка регистрации');
            setSuccess(null);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '100vh' }}>
            <Card className="w-100" style={{ maxWidth: '600px' }} bg="dark" text="light">
                <Card.Body>
                    <h2 className="text-center text-success mb-4">Регистрация</h2>

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

                        <Button
                            type="submit"
                            variant="success"
                            className="w-100 mb-3"
                            disabled={loading}
                        >
                            {loading ? (
                                <Spinner animation="border" size="sm" />
                            ) : 'Зарегистрироваться'}
                        </Button>

                        <div className="text-center mt-3">
                            <Button
                                variant="outline-success"
                                onClick={() => navigate('/')}
                                className="w-100"
                            >
                                Уже есть аккаунт? Войти
                            </Button>
                        </div>
                    </Form>
                </Card.Body>
            </Card>
        </div>
    );
}