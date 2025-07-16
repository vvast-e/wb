import { useState, useEffect } from 'react';
import api from '../api';
import { Container, Table, Button, Spinner, Alert, Badge } from 'react-bootstrap';

const actionMap = {
    update_media: 'Обновление медиа',
    update_content: 'Обновление контента',
    delete: 'Удаление',
    create: 'Создание',
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
};

const ScheduledTasks = () => {
    const [tasks, setTasks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchTasks = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await api.get('/tasks');
            setTasks(response.data);
            setLoading(false);
        } catch (err) {
            setError(err.response?.data?.detail || err.message);
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTasks();
    }, []);

    const handleDelete = async (taskId) => {
        if (window.confirm('Вы уверены, что хотите удалить это запланированное изменение?')) {
            try {
                const token = localStorage.getItem('token');
                await api.delete(`/tasks/delete/${taskId}`);
                fetchTasks();
            } catch (err) {
                setError(err.response?.data?.detail || err.message);
            }
        }
    };

    const formatChanges = (changes, action) => {
        if (!changes || Object.keys(changes).length === 0) {
            return "Нет изменений";
        }

        if (typeof changes.media === 'string') {
            if (changes.media.includes("Добавлено фото")) {
                return <div>• Загрузка фото</div>;
            }
            if (changes.media.includes("Добавлено видео")) {
                return <div>• Загрузка видео</div>;
            }
            if (changes.media.includes("Медиа обновлены")) {
                return <div>• Редактирование фото</div>;
            }
        }

        // Обычные текстовые и характеристические изменения
        const formatted = [];

        Object.entries(changes).forEach(([key, value]) => {
            const label = changeKeyMap[key] || key;
            if (key === 'dimensions' && typeof value === 'object') {
                Object.entries(value).forEach(([dimKey, dimVal]) => {
                    if (dimVal) formatted.push(`${label} (${changeKeyMap[dimKey] || dimKey}): ${dimVal}`);
                });
            } else if (key === 'characteristics' && Array.isArray(value)) {
                value.forEach(char => {
                    formatted.push(`${label}: ${char.name} = ${Array.isArray(char.value) ? char.value.join(', ') : char.value}`);
                });
            } else if (typeof value === 'string' || typeof value === 'number') {
                formatted.push(`${label}: ${value}`);
            }
        });

        return formatted.length > 0
            ? formatted.map((change, i) => <div key={i}>• {change}</div>)
            : "Нет изменений";
    };

    if (loading) {
        return (
            <Container className="d-flex justify-content-center mt-5">
                <Spinner animation="border" variant="success" />
            </Container>
        );
    }

    if (error) {
        return (
            <Container className="mt-4">
                <Alert variant="danger">{error}</Alert>
            </Container>
        );
    }

    return (
        <Container className="py-4">
            <div className="d-flex justify-content-between align-items-center mb-4">
                <h1 className="text-success">Запланированные изменения</h1>
            </div>

            {tasks.length === 0 ? (
                <Alert variant="info">Нет запланированных изменений</Alert>
            ) : (
                <Table striped bordered hover variant="dark" className="border-success">
                    <thead>
                        <tr>
                            <th>ID товара</th>
                            <th>Действие</th>
                            <th>Запланировано на</th>
                            <th>Статус</th>
                            <th>Изменения</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tasks.map(task => (
                            <tr key={task.id}>
                                <td>
                                    <a
                                        href={`/edit/${task.nm_id}?brand=${encodeURIComponent(task.brand)}&vendorCode=${encodeURIComponent(task.payload?.vendorCode || task.nm_id)}`}
                                        className="text-success"
                                    >
                                        {task.nm_id}
                                    </a>
                                </td>
                                <td>{actionMap[task.action] || task.action}</td>
                                <td>{new Date(task.scheduled_at).toLocaleString()}</td>
                                <td>
                                    <Badge bg={task.status === 'pending' ? 'warning' : 'success'}>
                                        {statusMap[task.status] || task.status}
                                    </Badge>
                                </td>
                                <td style={{ maxWidth: '300px' }}>
                                    <div className="text-light small">
                                        {formatChanges(task.changes, task.originalData)}
                                    </div>
                                </td>
                                <td>
                                    {task.status === 'pending' && (
                                        <Button
                                            variant="danger"
                                            size="sm"
                                            onClick={() => handleDelete(task.id)}
                                        >
                                            Удалить
                                        </Button>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </Table>
            )}
        </Container>
    );
};

export default ScheduledTasks;
