import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Container, Row, Col, Card, Form, Button, Spinner, Alert, Carousel } from 'react-bootstrap';
import Hls from 'hls.js';
import { BiArrowBack } from 'react-icons/bi';
import MediaUploader from "./MediaUploader.jsx";

export default function ProductEdit() {
    const { nm_id } = useParams();
    const navigate = useNavigate();

    const [card, setCard] = useState({});
    const [formData, setFormData] = useState({});
    const [photoGroups, setPhotoGroups] = useState([]);
    const [characteristics, setCharacteristics] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Новые фото для загрузки через MediaUploader (с ПК)
    const [pendingFiles, setPendingFiles] = useState([]);
    // Замены фото в карусели - ключ: индекс, значение: новая ссылка на фото
    const [replacedPhotos, setReplacedPhotos] = useState({});
    // Статус изменений
    const [changes, setChanges] = useState({
        content: false,
        characteristics: false,
        mediaFiles: false,
        mediaLinks: false,
    });

    const [searchParams] = useSearchParams();
    const brand = searchParams.get('brand');
    const vendorCode = searchParams.get('vendorCode');

    const videoRef = useRef(null);

    const formatDateTimeLocal = (date) => {
        const pad = (num) => num.toString().padStart(2, '0');
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
    };

    // Добавляем функцию проверки видео
    const isVideoUrl = url => url && (url.endsWith('.mp4') || url.endsWith('.m3u8') || url.endsWith('.webm'));

    useEffect(() => {
        const fetchData = async () => {
            try {
                const token = localStorage.getItem('token');
                const res = await axios.get(
                    `${import.meta.env.VITE_API_URL}/items/${nm_id}?brand=${encodeURIComponent(brand)}`,
                    { headers: { Authorization: `Bearer ${token}` } }
                );
                if (!res.data.success) throw new Error('Не удалось загрузить товар');
                const data = res.data.data;
                setCard(data);
                setFormData({
                    title: data.title || '',
                    brand: data.brand || '',
                    description: data.description || '',
                    length: data.dimensions?.length || 0,
                    width: data.dimensions?.width || 0,
                    height: data.dimensions?.height || 0,
                    weightBrutto: data.dimensions?.weightBrutto || 0,
                    scheduledAt: formatDateTimeLocal(new Date())
                });
                setCharacteristics(data.characteristics || []);
                setPhotoGroups(data.photos || []);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [nm_id, brand]);

    useEffect(() => {
        if (!card.video || !videoRef.current) return;
        const video = videoRef.current;
        let hls = null;
        const handleError = () => console.error('Ошибка воспроизведения видео');
        video.addEventListener('error', handleError);
        if (video.canPlayType('application/vnd.apple.mpegurl')) {
            video.src = card.video;
            video.muted = true;
            video.play().catch(() => { });
        } else if (Hls.isSupported()) {
            hls = new Hls();
            hls.on(Hls.Events.ERROR, handleError);
            hls.loadSource(card.video);
            hls.attachMedia(video);
            hls.on(Hls.Events.MANIFEST_PARSED, () => {
                video.muted = true;
                video.play().catch(() => { });
            });
        }
        return () => {
            video.removeEventListener('error', handleError);
            if (hls) {
                hls.off(Hls.Events.ERROR, handleError);
                hls.destroy();
            }
        };
    }, [card.video]);

    const handleFileAdded = (fileData) => {
        setPendingFiles(prev => [...prev, fileData]);
        setChanges(prev => ({ ...prev, mediaFiles: true }));
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => {
            if (prev[name] === value) return prev;
            setChanges(prev => ({ ...prev, content: true }));
            return { ...prev, [name]: value };
        });
    };

    const updateCharacteristic = (id, value) => {
        setCharacteristics(prev => {
            const updated = prev.map(c => c.id === id ? { ...c, value: value.split(',').map(v => v.trim()) } : c);
            setChanges(prev => ({ ...prev, characteristics: true }));
            return updated;
        });
    };

    // Обработчик выбора файла для замены фото в карусели
    const handleReplaceFile = async (index, file) => {
        if (!file) return;

        if (file.size > 32 * 1024 * 1024) {
            alert('Размер файла превышает 32 МБ');
            return;
        }

        try {
            const token = localStorage.getItem('token');
            const formDataUpload = new FormData();
            formDataUpload.append('file', file);

            const uploadRes = await axios.post(
                `${import.meta.env.VITE_API_URL}/items/${nm_id}/upload-imgbb?brand=${encodeURIComponent(brand)}`,
                formDataUpload,
                { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'multipart/form-data' } }
            );

            const newUrl = uploadRes.data.data.url;
            setReplacedPhotos(prev => ({ ...prev, [index]: newUrl }));
            setChanges(prev => ({ ...prev, mediaLinks: true }));
        } catch (err) {
            alert('Ошибка загрузки файла: ' + (err.response?.data?.detail || err.message));
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const token = localStorage.getItem('token');
            const headers = { Authorization: `Bearer ${token}` };
            const scheduled_at = `${formData.scheduledAt}:00+03:00`;

            // 1. Загрузка новых файлов (через MediaUploader)
            if (changes.mediaFiles && pendingFiles.length > 0) {
                for (const fileData of pendingFiles) {
                    const fileForm = new FormData();
                    fileForm.append('file', fileData.file);
                    fileForm.append('photo_number', fileData.photoNumber.toString());
                    fileForm.append('media_type', fileData.mediaType || 'image');
                    fileForm.append('scheduled_at', scheduled_at);
                    await axios.post(
                        `${import.meta.env.VITE_API_URL}/items/${nm_id}/upload-media-file?brand=${encodeURIComponent(brand)}`,
                        fileForm,
                        { headers: { ...headers, 'Content-Type': 'multipart/form-data' } }
                    );
                }
                setChanges({ mediaFiles: false, mediaLinks: false, content: false, characteristics: false });
                return navigate('/home');
            }

            const requests = [];

            // 2. Обновление заменённых фото (пары old/new)
            if (changes.mediaLinks && Object.keys(replacedPhotos).length > 0) {
                const updatedPhotos = photoGroups.map((group, idx) => {
                    if (replacedPhotos[idx]) {
                        return replacedPhotos[idx];  // новая ссылка
                    }
                    // старое фото (big, или любой другой доступный вариант)
                    return group.big || group.c246x328 || Object.values(group)[0];
                }).filter(Boolean);  // убираем пустые

                // проверка: максимум 30 фото
                if (updatedPhotos.length === 0 || updatedPhotos.length > 30) {
                    alert('Количество фото должно быть от 1 до 30');
                    return;
                }
                const index = parseInt(Object.keys(replacedPhotos)[0], 10);

                requests.push(
                    axios.post(
                        `${import.meta.env.VITE_API_URL}/items/${nm_id}/media?brand=${encodeURIComponent(brand)}`,
                        { nmId: parseInt(nm_id), media: updatedPhotos, index, scheduled_at },
                        { headers }
                    )
                );

                await Promise.all(requests);
                setChanges({ mediaFiles: false, mediaLinks: false, content: false, characteristics: false });
                return navigate('/home');
            }


            // 3. Обновление контента и характеристик
            if (changes.content || changes.characteristics) {
                requests.push(
                    axios.post(
                        `${import.meta.env.VITE_API_URL}/items/${nm_id}/schedule?brand=${encodeURIComponent(brand)}`,
                        {
                            content: {
                                title: formData.title,
                                brand: formData.brand,
                                description: formData.description,
                                dimensions: {
                                    length: parseInt(formData.length),
                                    width: parseInt(formData.width),
                                    height: parseInt(formData.height),
                                    weightBrutto: parseFloat(formData.weightBrutto)
                                },
                                characteristics: characteristics.map(c => ({
                                    id: c.id,
                                    name: c.name,
                                    value: Array.isArray(c.value) ? c.value : [c.value]
                                }))
                            },
                            scheduled_at
                        },
                        { headers }
                    )
                );
            }

            if (requests.length) await Promise.all(requests);

            setChanges({ mediaFiles: false, mediaLinks: false, content: false, characteristics: false });
            navigate('/home');
        } catch (err) {
            console.error('Ошибка сохранения:', err);
            setError(err.response?.data?.message || 'Ошибка при сохранении');
        }
    };

    if (loading) return <Container className="py-5 text-center"><Spinner animation="border" /></Container>;
    if (error) return <Container className="py-5"><Alert variant="danger">{error}</Alert></Container>;

    const hasVideo = card.video && isVideoUrl(card.video);

    return (
        <Container className="py-4">
            <div className="d-flex justify-content-between align-items-center mb-4">
                <h2 className="text-success mb-0">
                    Редактирование товара (артикул: {vendorCode || nm_id || 'не указан'})
                </h2>
            </div>

            <Form onSubmit={handleSubmit}>
                <Row>
                    <Col lg={4} className="mb-4">
                        <Card className="bg-dark text-light border-success">
                            <Card.Body className="d-flex flex-column gap-3">
                                <h5 className="text-center mb-2">Медиа</h5>
                                {(hasVideo || photoGroups.length) ? (
                                    <Carousel variant="dark" interval={null} className="rounded-3 overflow-hidden">
                                        {hasVideo && (
                                            <Carousel.Item key="video">
                                                <div
                                                    className="ratio ratio-16x9 bg-secondary rounded-3 overflow-hidden mb-2">
                                                    <video ref={videoRef} controls className="w-100 h-100">
                                                        <source src={card.video} type="application/x-mpegURL" />
                                                        Ваш браузер не поддерживает видео.
                                                    </video>
                                                </div>
                                            </Carousel.Item>
                                        )}
                                        {photoGroups.map((group, idx) => {
                                            const currentPhotoUrl = replacedPhotos[idx] || group.c246x328 || Object.values(group)[0];
                                            return (
                                                <Carousel.Item key={idx} className="pb-4">
                                                    <div className="ratio ratio-1x1 bg-secondary rounded-3 overflow-hidden mb-2">
                                                        <img
                                                            src={`${currentPhotoUrl}?v=${Date.now()}`}
                                                            alt={`Фото ${idx + 1}`}
                                                            className="img-fluid object-fit-cover"
                                                        />
                                                    </div>
                                                    <Form.Group controlId={`replace-photo-${idx}`} className="mb-2">
                                                        <Form.Label>Заменить фото #{idx + 1}</Form.Label>
                                                        <Form.Control
                                                            type="file"
                                                            accept="image/jpeg,image/png,image/bmp,image/gif,image/webp"
                                                            onChange={async (e) => {
                                                                const file = e.target.files?.[0];
                                                                if (!file) return;
                                                                await handleReplaceFile(idx, file);
                                                            }}
                                                        />
                                                    </Form.Group>
                                                </Carousel.Item>
                                            );
                                        })}
                                    </Carousel>
                                ) : (
                                    <p className="text-center text-muted mb-3">Нет медиа</p>
                                )}
                                {/* Компонент загрузки новых файлов */}
                                <MediaUploader nmId={nm_id} currentPhotoCount={photoGroups.length} onFileAdded={handleFileAdded} />
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col lg={8}>
                        <Card className="bg-dark text-light border-success">
                            <Card.Body>
                                <Form.Group className="mb-3">
                                    <Form.Label>Название</Form.Label>
                                    <Form.Control
                                        name="title"
                                        value={formData.title}
                                        onChange={handleChange}
                                        className="bg-secondary border-success text-light"
                                    />
                                </Form.Group>
                                <Form.Group className="mb-3">
                                    <Form.Label>Бренд</Form.Label>
                                    <Form.Control
                                        name="brand"
                                        value={formData.brand}
                                        onChange={handleChange}
                                        className="bg-secondary border-success text-light"
                                    />
                                </Form.Group>
                                <Form.Group className="mb-3">
                                    <Form.Label>Описание</Form.Label>
                                    <Form.Control
                                        as="textarea"
                                        rows={3}
                                        name="description"
                                        value={formData.description}
                                        onChange={handleChange}
                                        className="bg-secondary border-success text-light"
                                    />
                                </Form.Group>
                                <Row className="mb-3">
                                    <Col md={6}>
                                        <Form.Label>Длина</Form.Label>
                                        <Form.Control
                                            type="number"
                                            name="length"
                                            value={formData.length}
                                            onChange={handleChange}
                                            className="bg-secondary border-success text-light"
                                        />
                                    </Col>
                                    <Col md={6}>
                                        <Form.Label>Ширина</Form.Label>
                                        <Form.Control
                                            type="number"
                                            name="width"
                                            value={formData.width}
                                            onChange={handleChange}
                                            className="bg-secondary border-success text-light"
                                        />
                                    </Col>
                                    <Col md={6}>
                                        <Form.Label>Высота</Form.Label>
                                        <Form.Control
                                            type="number"
                                            name="height"
                                            value={formData.height}
                                            onChange={handleChange}
                                            className="bg-secondary border-success text-light"
                                        />
                                    </Col>
                                    <Col md={6}>
                                        <Form.Label>Вес (кг)</Form.Label>
                                        <Form.Control
                                            type="number"
                                            step="0.01"
                                            name="weightBrutto"
                                            value={formData.weightBrutto}
                                            onChange={handleChange}
                                            className="bg-secondary border-success text-light"
                                        />
                                    </Col>
                                </Row>
                                <Form.Group className="mb-4">
                                    <Form.Label>Характеристики</Form.Label>
                                    {characteristics.map((char) => (
                                        <Form.Group key={char.id} className="mb-2">
                                            <Form.Label>{char.name}</Form.Label>
                                            <Form.Control
                                                type="text"
                                                value={Array.isArray(char.value) ? char.value.join(', ') : char.value}
                                                onChange={(e) => updateCharacteristic(char.id, e.target.value)}
                                                className="bg-secondary border-success text-light"
                                            />
                                        </Form.Group>
                                    ))}
                                </Form.Group>
                                <Form.Group className="mb-3">
                                    <Form.Label>Время обновления</Form.Label>
                                    <Form.Control
                                        type="datetime-local"
                                        name="scheduledAt"
                                        value={formData.scheduledAt}
                                        onChange={handleChange}
                                        className="bg-secondary border-success text-light"
                                    />
                                </Form.Group>
                                <div className="d-flex gap-2">
                                    <Button type="submit" variant="success">Сохранить</Button>
                                </div>
                            </Card.Body>
                        </Card>
                    </Col>
                </Row>
            </Form>
        </Container>
    );
}
