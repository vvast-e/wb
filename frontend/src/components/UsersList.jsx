import { useEffect, useState } from 'react';
import api from '../api';
import { Table, Button, Spinner, Alert, Card } from 'react-bootstrap';
import { BiUserPlus } from 'react-icons/bi';
import { useNavigate } from 'react-router-dom';

export default function UsersList() {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchUsers = async () => {
            try {
                setLoading(true);
                setError(null);
                const token = localStorage.getItem('token');
                const response = await api.get(
                    `${import.meta.env.VITE_API_URL}/admin/users`,
                    {
                        headers: { 'Authorization': `Bearer ${token}` }
                    }
                );

                if (response.data && Array.isArray(response.data)) {
                    setUsers(response.data);
                } else if (response.data && typeof response.data === 'object') {
                    setUsers(Object.values(response.data));
                } else {
                    setUsers([]);
                }
            } catch (err) {
                let errorMsg = 'Ошибка загрузки пользователей';
                if (err.response?.status === 404) {
                    errorMsg = 'Пользователи не найдены';
                } else {
                    errorMsg = err.response?.data?.detail ||
                        err.response?.data?.message ||
                        'Ошибка загрузки пользователей';
                }
                setError(errorMsg);
                setUsers([]);
            } finally {
                setLoading(false);
            }
        };
        fetchUsers();
    }, []);

    const handleDeleteUser = async (id) => {
        if (!window.confirm("Вы уверены, что хотите удалить этого пользователя?")) return;

        try {
            const token = localStorage.getItem('token');
            await api.delete(`${import.meta.env.VITE_API_URL}/admin/users/${id}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            setUsers(users.filter(user => user.id !== id));
        } catch (err) {
            setError("Не удалось удалить пользователя");
        }
    };

    const handleChangeStatus = async (id, currentStatus) => {
        const newStatus = currentStatus === 'admin' ? 'user' : 'admin';
        try {
            const token = localStorage.getItem('token');
            const response = await api.patch(
                `${import.meta.env.VITE_API_URL}/admin/users/${id}/status?new_status=${newStatus}`,
                {},
                {
                    headers: { 'Authorization': `Bearer ${token}` }
                }
            );
            setUsers(users.map(u => u.id === id ? response.data : u));
        } catch (err) {
            setError("Не удалось изменить статус пользователя");
        }
    };

    if (loading) return (
        <div className="text-center py-5">
            <Spinner animation="border" variant="light" />
        </div>
    );

    if (error) return (
        <Alert variant="danger" className="mt-4">
            <Alert.Heading>Ошибка</Alert.Heading>
            <p>{error}</p>
        </Alert>
    );

    return (
        <Card className="bg-dark text-light border-secondary">
            <Card.Body>
                {users.length === 0 ? (
                    <div className="text-center py-4">
                        <h5>Нет зарегистрированных сотрудников</h5>
                        <p className="text-muted mb-3">Вы можете зарегистрировать нового сотрудника</p>
                        <Button
                            variant="success"
                            onClick={() => navigate('/admin?tab=register')}
                            className="d-flex align-items-center mx-auto"
                        >
                            <BiUserPlus className="me-2" size={18} />
                            Зарегистрировать сотрудника
                        </Button>
                    </div>
                ) : (
                    <>
                        <Table striped bordered hover variant="dark">
                            <thead>
                                <tr>
                                    <th>Email</th>
                                    <th>Магазин</th>
                                    <th>Статус</th>
                                    <th>Действия</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map(user => (
                                    <tr key={user.id}>
                                        <td>{user.email}</td>
                                        <td>{user.wb_api_key ? Object.keys(user.wb_api_key).join(', ') : '-'}</td>
                                        <td>{user.status}</td>
                                        <td>
                                            <Button
                                                variant={user.status === 'admin' ? 'warning' : 'secondary'}
                                                size="sm"
                                                className="me-2"
                                                onClick={() => handleChangeStatus(user.id, user.status)}
                                            >
                                                {user.status === 'admin' ? 'Сделать user' : 'Сделать admin'}
                                            </Button>
                                            <Button
                                                variant="danger"
                                                size="sm"
                                                onClick={() => handleDeleteUser(user.id)}
                                            >
                                                Удалить
                                            </Button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </Table>
                        <div className="d-flex justify-content-end mt-3">
                            <Button
                                variant="success"
                                onClick={() => navigate('/admin?tab=register')}
                            >
                                <BiUserPlus className="me-2" />
                                Добавить сотрудника
                            </Button>
                        </div>
                    </>
                )}
            </Card.Body>
        </Card>
    );
}
