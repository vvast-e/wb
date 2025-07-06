import React, { useState, useEffect } from 'react';
import { Alert, Card } from 'react-bootstrap';

const MediaUploader = ({ nmId, currentPhotoCount, onFileAdded, hasVideo }) => {
    const [photoNumber, setPhotoNumber] = useState(currentPhotoCount + 1);
    const [error, setError] = useState(null);
    const [preview, setPreview] = useState(null);
    const [mediaType, setMediaType] = useState('image');

    useEffect(() => {
        // Если уже есть видео, сбрасываем тип на изображение
        if (hasVideo) {
            setMediaType('image');
        }
    }, [hasVideo]);

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Валидация
        const validImageTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp', 'image/gif'];
        const validVideoTypes = ['video/mp4', 'video/quicktime'];
        const maxSize = 32 * 1024 * 1024; // 32MB

        if (mediaType === 'image' && !validImageTypes.includes(file.type)) {
            setError('Допустимые форматы изображений: JPG, PNG, BMP, GIF, WebP');
            return;
        }

        if (mediaType === 'video' && !validVideoTypes.includes(file.type)) {
            setError('Допустимые форматы видео: MP4, MOV');
            return;
        }

        if (file.size > maxSize) {
            setError('Максимальный размер файла: 32 МБ');
            return;
        }


        setError(null);

        // Создаем превью
        const reader = new FileReader();
        reader.onload = (e) => {
            setPreview(e.target.result);
            onFileAdded({
                file,
                photoNumber: mediaType === 'video' ? 1 : photoNumber,
                previewUrl: e.target.result,
                mediaType
            });
        };
        reader.readAsDataURL(file);
    };

    return (
        <Card className="bg-dark text-light border-success mb-3">
            <Card.Body>
                <h5 className="text-success mb-3">Добавить медиа</h5>

                <div className="mb-3">
                    <label className="form-label">Тип медиа</label>
                    <select
                        className="form-select bg-secondary border-success text-light"
                        value={mediaType}
                        onChange={(e) => setMediaType(e.target.value)}
                        disabled={hasVideo}
                    >
                        <option value="image">Изображение</option>
                        <option value="video" disabled={hasVideo}>
                            Видео {hasVideo ? '(уже добавлено)' : ''}
                        </option>
                    </select>
                </div>

                <div className="mb-3">
                    <label className="form-label">Позиция (1-30)</label>
                    <input
                        type="number"
                        min="1"
                        max="30"
                        value={mediaType === 'video' ? 1 : photoNumber}
                        onChange={(e) => setPhotoNumber(Number(e.target.value))}
                        className="form-control bg-secondary border-success text-light"
                        disabled={mediaType === 'video'}
                    />
                </div>

                <div className="mb-3">
                    <label className="form-label">Выберите файл</label>
                    <input
                        type="file"
                        onChange={handleFileChange}
                        accept={mediaType === 'image' ? 'image/*' : 'video/*'}
                        className="form-control bg-secondary border-success text-light"
                    />
                </div>

                {preview && (
                    <div className="mt-3">
                        <div className="ratio ratio-16x9 bg-secondary rounded overflow-hidden">
                            {mediaType === 'image' ? (
                                <img src={preview} alt="Превью" className="img-fluid object-fit-cover" />
                            ) : (
                                <video controls className="w-100 h-100">
                                    <source src={preview} type="video/mp4" />
                                    Ваш браузер не поддерживает видео.
                                </video>
                            )}
                        </div>
                    </div>
                )}

                {error && <Alert variant="danger" className="mt-3">{error}</Alert>}
            </Card.Body>
        </Card>
    );
};

export default MediaUploader;