import { Link } from 'react-router-dom';
import { Card } from 'react-bootstrap';

const ProductCard = ({ product, brand }) => {
    const getPhotoUrl = () => {
        if (product.photos?.length > 0) {
            return product.photos[0].c246x328 ||
                product.photos[0].square ||
                product.photos[0].big ||
                'https://via.placeholder.com/300';
        }
        return 'https://via.placeholder.com/300';
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
                        onError={(e) => e.target.src = 'https://via.placeholder.com/300'}
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