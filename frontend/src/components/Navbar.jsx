import React, { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import api from '../api';

const Navbar = ({ setIsAuth }) => {
    const navigate = useNavigate();
    const location = useLocation();
    const [userStatus, setUserStatus] = useState(null);
    const [userEmail, setUserEmail] = useState('');

    useEffect(() => {
        fetchUserData();
    }, []);

    const fetchUserData = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await api.get(`/admin/check-admin`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            setUserStatus(response.data.status);
            setUserEmail(response.data.email || '');
        } catch (err) {
            console.error("Ошибка при получении данных пользователя:", err);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem("token");
        setIsAuth(false);
        navigate("/");
    };

    const isActive = (path) => {
        return location.pathname === path;
    };

    return (
        <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
            <div className="container-fluid">
                <Link className="navbar-brand" to="/home">
                    <i className="fas fa-store me-2"></i>
                    WB Content Manager
                </Link>

                <button
                    className="navbar-toggler"
                    type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#navbarNav"
                    aria-controls="navbarNav"
                    aria-expanded="false"
                    aria-label="Toggle navigation"
                >
                    <span className="navbar-toggler-icon"></span>
                </button>

                <div className="collapse navbar-collapse" id="navbarNav">
                    <ul className="navbar-nav me-auto">
                        <li className="nav-item">
                            <Link
                                className={`nav-link ${isActive('/home') ? 'active' : ''}`}
                                to="/home"
                            >
                                <i className="fas fa-home me-1"></i>
                                Главная
                            </Link>
                        </li>
                        <li className="nav-item">
                            <Link
                                className={`nav-link ${isActive('/analytics') ? 'active' : ''}`}
                                to="/analytics"
                            >
                                <i className="fas fa-chart-bar me-1"></i>
                                Аналитика
                            </Link>
                        </li>
                        <li className="nav-item">
                            <Link
                                className={`nav-link ${isActive('/scheduled-tasks') ? 'active' : ''}`}
                                to="/scheduled-tasks"
                            >
                                <i className="fas fa-clock me-1"></i>
                                Задачи
                            </Link>
                        </li>
                        <li className="nav-item">
                            <Link
                                className={`nav-link ${isActive('/history') ? 'active' : ''}`}
                                to="/history"
                            >
                                <i className="fas fa-history me-1"></i>
                                История
                            </Link>
                        </li>
                        {userStatus === 'admin' && (
                            <li className="nav-item">
                                <Link
                                    className={`nav-link ${isActive('/Admin') ? 'active' : ''}`}
                                    to="/Admin"
                                >
                                    <i className="fas fa-cog me-1"></i>
                                    Панель управления
                                </Link>
                            </li>
                        )}
                    </ul>

                    <ul className="navbar-nav">
                        <li className="nav-item dropdown">
                            <a
                                className="nav-link dropdown-toggle"
                                href="#"
                                id="navbarDropdown"
                                role="button"
                                data-bs-toggle="dropdown"
                                aria-expanded="false"
                            >
                                <i className="fas fa-user me-1"></i>
                                {userEmail ? (
                                    <>
                                        <span>{userEmail}</span>
                                        {userStatus && (
                                            <span className="ms-2 badge bg-secondary text-uppercase">{userStatus}</span>
                                        )}
                                    </>
                                ) : 'Пользователь'}
                            </a>
                            <ul className="dropdown-menu dropdown-menu-dark" aria-labelledby="navbarDropdown">
                                <li>
                                    <a className="dropdown-item" href="#" onClick={handleLogout}>
                                        <i className="fas fa-sign-out-alt me-1"></i>
                                        Выход
                                    </a>
                                </li>
                            </ul>
                        </li>
                    </ul>
                </div>
            </div>
        </nav>
    );
};

export default Navbar;
