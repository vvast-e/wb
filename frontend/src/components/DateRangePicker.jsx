import React, { useState } from 'react';
import { Form, Button, Row, Col } from 'react-bootstrap';

const DateRangePicker = ({ onDateChange, initialStartDate, initialEndDate }) => {
    const [startDate, setStartDate] = useState(initialStartDate || '');
    const [endDate, setEndDate] = useState(initialEndDate || '');
    const [activePreset, setActivePreset] = useState(null); // 7, 30, 90 или null

    const handleSubmit = (e) => {
        e.preventDefault();
        if (startDate && endDate) {
            onDateChange(startDate, endDate);
        }
    };

    const handleQuickSelect = (days) => {
        const end = new Date();
        const start = new Date();
        start.setDate(start.getDate() - days);

        const formatDate = (date) => date.toISOString().split('T')[0];

        setStartDate(formatDate(start));
        setEndDate(formatDate(end));
        setActivePreset(days);
        onDateChange(formatDate(start), formatDate(end));
    };

    const handleReset = () => {
        setStartDate('');
        setEndDate('');
        setActivePreset(null);
        onDateChange('', '');
    };

    // Сброс активного пресета при ручном вводе дат
    const handleStartDateChange = (e) => {
        setStartDate(e.target.value);
        setActivePreset(null);
    };
    const handleEndDateChange = (e) => {
        setEndDate(e.target.value);
        setActivePreset(null);
    };

    return (
        <div className="bg-dark p-3 rounded mb-4 border border-success" style={{ borderWidth: '2px' }}>
            <h5 className="text-light mb-3">Выбор периода</h5>
            <Form onSubmit={handleSubmit}>
                <Row className="g-3">
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
                    <Col md={6} className="d-flex align-items-end">
                        <div className="d-flex gap-2 flex-wrap">
                            <Button
                                variant={activePreset === 7 ? "success" : "outline-success"}
                                size="sm"
                                onClick={() => handleQuickSelect(7)}
                                active={activePreset === 7}
                            >
                                7 дней
                            </Button>
                            <Button
                                variant={activePreset === 30 ? "success" : "outline-success"}
                                size="sm"
                                onClick={() => handleQuickSelect(30)}
                                active={activePreset === 30}
                            >
                                30 дней
                            </Button>
                            <Button
                                variant={activePreset === 90 ? "success" : "outline-success"}
                                size="sm"
                                onClick={() => handleQuickSelect(90)}
                                active={activePreset === 90}
                            >
                                90 дней
                            </Button>
                            <Button
                                type="submit"
                                variant="success"
                                size="sm"
                                disabled={!startDate || !endDate}
                            >
                                Применить
                            </Button>
                            <Button
                                type="button"
                                variant="outline-danger"
                                size="sm"
                                onClick={handleReset}
                            >
                                Сбросить
                            </Button>
                        </div>
                    </Col>
                </Row>
            </Form>
        </div>
    );
};

export default DateRangePicker; 