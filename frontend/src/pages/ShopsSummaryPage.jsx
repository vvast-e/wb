import React from 'react';
import { Container } from 'react-bootstrap';
import ShopSummaryWidget from '../components/ShopSummaryWidget';

const ShopsSummaryPage = () => {
    return (
        <Container className="py-4">
            <h2 className="text-light mb-4">Сводка по магазинам</h2>
            <ShopSummaryWidget shopType="wb" />
            <div className="my-4" />
            <ShopSummaryWidget shopType="ozon" />
        </Container>
    );
};

export default ShopsSummaryPage; 