import { Link } from 'react-router-dom';
import { Card } from 'react-bootstrap';

// SVG data URI placeholder (серый квадрат 300x300)
const placeholderImg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><rect width='300' height='300' fill='%23cccccc'/><text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle' font-size='24' fill='%23777'>Нет фото</text></svg>";

const ProductCard = ({ product, brand }) => {
    const getPhotoUrl = () => {
        if (product.photos?.length > 0) {
            return product.photos[0].c246x328 ||
                product.photos[0].square ||
                product.photos[0].big ||
                placeholderImg;
        }
        return placeholderImg;
    };

    return (
        <Link
            to={`/edit/${product.nmID}?brand=${encodeURIComponent(brand)}&vendorCode=${encodeURIComponent(product.vendorCode || product.nmID)}`}
            className="text-decoration-none"
        >
            <Card
                className="h-100 bg-dark text-light border-success hover-shadow"
                style={{ maxWidth: '300px' }}
            >
                <div className="ratio ratio-1x1">
                    <Card.Img
                        variant="top"
                        src={`${getPhotoUrl()}?v=${product.updated_at || Date.now()}`}
                        alt={product.title}
                        onError={(e) => e.target.src = placeholderImg}
                        className="object-fit-cover"
                    />
                </div>

                <Card.Body>
                    <Card.Title className="text-truncate">{product.title}</Card.Title>
                    <Card.Text className="text small">
                        Артикул продавца: {product.vendorCode || product.nmID}
                    </Card.Text>

                </Card.Body>
            </Card>
        </Link>
    );
};

export default ProductCard;