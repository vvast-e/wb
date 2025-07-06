import { useState, useEffect } from 'react';
import { Tab, Tabs, Card } from 'react-bootstrap';
import RegisterForm from '../components/RegisterForm.jsx';
import AddBrandForm from '../components/AddBrandForm.jsx';
import UsersList from '../components/UsersList.jsx';
import { useLocation } from 'react-router-dom';

const AdminPanel = () => {
    const location = useLocation();
    const [refreshKey, setRefreshKey] = useState(0); // Добавляем ключ для принудительного обновления

    const queryParams = new URLSearchParams(location.search);
    const tabFromUrl = queryParams.get('tab') || 'brands';

    const [activeTab, setActiveTab] = useState(tabFromUrl);

    useEffect(() => {
        const tab = new URLSearchParams(location.search).get('tab') || 'brands';
        setActiveTab(tab);
    }, [location.search]);

    const handleTabSelect = (k) => {
        const selectedTab = k || "brands"; // Если k равно null/undefined, используем "brands"
        setActiveTab(selectedTab);
        window.history.replaceState(null, '', `/Admin?tab=${selectedTab}`);
    };

    // Функция для обновления данных
    const handleDataUpdated = () => {
        setRefreshKey(prev => prev + 1); // Изменяем ключ для принудительного обновления
    };

    return (
        <Card className="bg-dark text-light border-success">
            <Card.Body>
                <h2 className="text-success mb-4">Панель управления</h2>
                <Tabs activeKey={activeTab} onSelect={handleTabSelect} className="mb-3">
                    <Tab eventKey="register" title="Регистрация">
                        <RegisterForm isAdminCreating={true} onSuccess={handleDataUpdated} />
                    </Tab>
                    <Tab eventKey="users" title="Сотрудники">
                        <UsersList key={refreshKey} /> {/* Передаем ключ для обновления */}
                    </Tab>
                    <Tab eventKey="brands" title="Управление магазинами">
                        <AddBrandForm onSuccess={handleDataUpdated} />
                    </Tab>
                </Tabs>
            </Card.Body>
        </Card>
    );
};

export default AdminPanel;