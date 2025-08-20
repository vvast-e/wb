import React, { useState } from 'react';
import { Form, Button, Row, Col } from 'react-bootstrap';

const DateRangePicker = ({ onDateChange, initialStartDate, initialEndDate }) => {
    const [startDate, setStartDate] = useState(initialStartDate || '');
    const [endDate, setEndDate] = useState(initialEndDate || '');
    const [lastNDays, setLastNDays] = useState('');

    const handleReset = () => {
        setStartDate('');
        setEndDate('');
        setLastNDays('');
        onDateChange('', '');
    };

    // Сброс при ручном вводе дат
    const handleStartDateChange = (e) => {
        const newStart = e.target.value;
        setStartDate(newStart);
        setLastNDays('');

        if (newStart) {
            if (endDate) {
                // Если конечная дата уже выбрана, применяем диапазон
                onDateChange(newStart, endDate);
            } else {
                // Если конечная не выбрана, применяем от начальной до сегодня
                const today = new Date().toISOString().split('T')[0];
                onDateChange(newStart, today);
            }
        }
    };

    const handleEndDateChange = (e) => {
        const newEnd = e.target.value;
        setEndDate(newEnd);
        setLastNDays('');

        if (newEnd) {
            if (startDate) {
                // Если начальная дата уже выбрана, применяем диапазон
                onDateChange(startDate, newEnd);
            } else {
                // Если начальная не выбрана, применяем от самого начала до конечной
                const earliestDate = '2020-01-01'; // Можно изменить на более подходящую дату
                onDateChange(earliestDate, newEnd);
            }
        }
    };

    // При изменении lastNDays сбрасываем ручные даты
    const handleLastNDaysChange = (e) => {
        const value = e.target.value;
        setLastNDays(value);
        setStartDate('');
        setEndDate('');
        if (value && Number(value) > 0) {
            const end = new Date();
            const start = new Date();
            start.setDate(start.getDate() - Number(value));
            const formatDate = (date) => date.toISOString().split('T')[0];
            onDateChange(formatDate(start), formatDate(end));
        } else {
            onDateChange('', '');
        }
    };

    return (
        <div className="bg-dark p-3 rounded mb-4 border border-success" style={{ borderWidth: '2px' }}>
            <h5 className="text-light mb-3">Период</h5>
            <Row className="g-3 align-items-end">
                <Col md={3}>
                    <Form.Label className="text-light">С</Form.Label>
                    <Form.Control
                        type="date"
                        value={startDate}
                        onChange={handleStartDateChange}
                        className="bg-dark border-success text-light"
                    />
                </Col>
                <Col md={3}>
                    <Form.Label className="text-light">По</Form.Label>
                    <Form.Control
                        type="date"
                        value={endDate}
                        onChange={handleEndDateChange}
                        className="bg-dark border-success text-light"
                    />
                </Col>
                <Col md={3}>
                    <Form.Label className="text-light">Последние N дней</Form.Label>
                    <Form.Control
                        type="number"
                        min="1"
                        placeholder="Например, 7"
                        value={lastNDays}
                        onChange={handleLastNDaysChange}
                        className="bg-dark border-success text-light"
                    />
                </Col>
            </Row>
            <Row className="mt-3">
                <Col md={6} className="d-flex gap-2">
                    <Button
                        type="button"
                        variant="outline-danger"
                        size="sm"
                        onClick={handleReset}
                    >
                        Сбросить
                    </Button>
                </Col>
            </Row>
        </div>
    );
};

export default DateRangePicker; 