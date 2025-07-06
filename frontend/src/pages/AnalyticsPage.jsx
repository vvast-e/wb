import React from 'react';
import { useNavigate } from 'react-router-dom';

const analyticsPages = [
    { label: 'База отзывов', path: '/analytics/review-analyzer' },
    { label: 'Магазины бренда', path: '/analytics/brand-shops' },
    { label: 'Эффективность отдела репутации', path: '/analytics/reputation-efficiency' },
    { label: 'Сводка по магазинам', path: '/analytics/shops-summary' },
];

const AnalyticsPage = () => {
    const navigate = useNavigate();
    return (
        <div className="min-vh-100 d-flex flex-column align-items-center justify-content-center bg-dark text-light p-4">
            <div className="w-100" style={{ maxWidth: 400 }}>
                {analyticsPages.map((item, idx) => (
                    <button
                        key={item.path}
                        className="btn btn-outline-success w-100 mb-3 d-flex justify-content-between align-items-center fs-5 shadow-sm"
                        style={{ borderRadius: 12, fontWeight: 500, letterSpacing: 0.5 }}
                        onClick={() => navigate(item.path)}
                    >
                        <span>{item.label}</span>
                        <span className="ms-2" style={{ fontSize: 18 }}>&#8594;</span>
                    </button>
                ))}
            </div>
        </div>
    );
};

export default AnalyticsPage; 