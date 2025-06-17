from PIL import Image
import os
import requests
from io import BytesIO

SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')
MAX_FILE_SIZE_BYTES = 32 * 1024 * 1024  # 32 MB
MIN_RESOLUTION = (700, 900)


def get_file_extension(url_or_path):
    """Получает расширение файла из URL или локального пути"""
    if url_or_path.startswith(('http://', 'https://')):
        return os.path.splitext(url_or_path)[1].lower()
    else:
        return os.path.splitext(os.path.basename(url_or_path))[1].lower()


def is_valid_format(url_or_path):
    ext = get_file_extension(url_or_path)
    return ext in SUPPORTED_FORMATS


def download_image(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return Image.open(BytesIO(response.content))


def validate_resolution(image):
    width, height = image.size
    return width >= MIN_RESOLUTION[0] and height >= MIN_RESOLUTION[1]


def get_file_size(url_or_path):
    if url_or_path.startswith(('http://', 'https://')):
        response = requests.head(url_or_path, timeout=10)
        content_length = response.headers.get('Content-Length')
        return int(content_length) if content_length else None
    else:
        return os.path.getsize(url_or_path)


def check_jpeg_quality(image):
    """Пытается определить качество JPEG через PIL (приблизительно)"""
    if image.format != 'JPEG':
        return True  # Не JPEG — не проверяем качество

    # Сохраняем изображение с разным качеством и сравниваем размеры
    buffer_low = BytesIO()
    image.save(buffer_low, format='JPEG', quality=65)
    buffer_low.seek(0)
    low_size = len(buffer_low.getvalue())

    buffer_high = BytesIO()
    image.save(buffer_high, format='JPEG', quality=95)
    buffer_high.seek(0)
    high_size = len(buffer_high.getvalue())

    # Если оригинальное изображение меньше по размеру при высоком качестве — значит оно было сжато сильнее
    return low_size < high_size


def validate_images(url_or_path)->str:
    try:
        # Проверка формата
        if not is_valid_format(url_or_path):
            print("❌ Неверный формат изображения")
            return False

        # Проверка размера
        file_size = get_file_size(url_or_path)
        if file_size is None:
            print("⚠️ Не удалось получить размер файла")
        elif file_size > MAX_FILE_SIZE_BYTES:
            print(f"❌ Размер файла превышает {MAX_FILE_SIZE_BYTES / (1024 * 1024)} МБ")
            return False

        # Открытие изображения
        if url_or_path.startswith(('http://', 'https://')):
            image = download_image(url_or_path)
        else:
            image = Image.open(url_or_path)

        # Проверка разрешения
        if not validate_resolution(image):
            print(f"❌ Разрешение меньше {MIN_RESOLUTION[0]}x{MIN_RESOLUTION[1]} px")
            return False

        # Проверка качества для JPEG
        if image.format == 'JPEG' and not check_jpeg_quality(image):
            print("⚠️ Качество JPEG может быть ниже 65%. Рекомендуется пересохранить.")

        print("✅ Изображение соответствует требованиям Wildberries.")
        return url_or_path

    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")
        return False