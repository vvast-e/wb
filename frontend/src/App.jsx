import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Home from './pages/Home';
import Login from './pages/Login';
import ProductEdit from "./components/ProductEdit";
import ScheduledTasks from './pages/ScheduledTasks';
import 'bootstrap/dist/css/bootstrap.min.css';
import './index.css';
import Register from "./pages/Register.jsx";
import AdminPanel from "./pages/AdminPanel.jsx";
import ProtectedRoute from './components/ProtectedRoute';
import HistoryPage from './pages/HistoryPage';
import Navbar from './components/Navbar';
import AnalyticsPage from './pages/AnalyticsPage';
import ReviewAnalyzerPage from './pages/ReviewAnalyzerPage';
import BrandShopsPage from './pages/BrandShopsPage';
import ReputationEfficiencyPage from './pages/ReputationEfficiencyPage';
import ShopsSummaryPage from './pages/ShopsSummaryPage';


function App() {
    const [isAuth, setIsAuth] = useState(() => {
        return localStorage.getItem('token') !== null;
    });

    // Компонент-обертка для защищенных страниц с навигацией
    const ProtectedPage = ({ children }) => (
        <div className="min-vh-100 bg-dark">
            <Navbar setIsAuth={setIsAuth} />
            {children}
        </div>
    );

    return (
        <BrowserRouter basename="/">
            <div className="app-container bg-dark text-light min-vh-100">
                <Routes>
                    <Route path="/" element={<Login setIsAuth={setIsAuth} />} />
                    <Route path="/register" element={<Register setIsAuth={setIsAuth} />} />

                    {/* Защищенные маршруты */}
                    <Route path="/home" element={
                        <ProtectedRoute isAuth={isAuth}>
                            <ProtectedPage>
                                <Home />
                            </ProtectedPage>
                        </ProtectedRoute>
                    } />
                    <Route path="/analytics" element={
                        <ProtectedRoute isAuth={isAuth}>
                            <ProtectedPage>
                                <AnalyticsPage />
                            </ProtectedPage>
                        </ProtectedRoute>
                    } />
                    <Route path="/edit/:nm_id" element={
                        <ProtectedRoute isAuth={isAuth}>
                            <ProtectedPage>
                                <ProductEdit />
                            </ProtectedPage>
                        </ProtectedRoute>
                    } />
                    <Route path="/scheduled-tasks" element={
                        <ProtectedRoute isAuth={isAuth}>
                            <ProtectedPage>
                                <ScheduledTasks />
                            </ProtectedPage>
                        </ProtectedRoute>
                    } />
                    <Route path="/Admin" element={
                        <ProtectedRoute isAuth={isAuth}>
                            <ProtectedPage>
                                <AdminPanel setIsAuth={setIsAuth} />
                            </ProtectedPage>
                        </ProtectedRoute>
                    } />
                    <Route path="/history" element={
                        <ProtectedRoute isAuth={isAuth}>
                            <ProtectedPage>
                                <HistoryPage />
                            </ProtectedPage>
                        </ProtectedRoute>
                    } />
                    <Route path="/analytics/review-analyzer" element={
                        <ProtectedRoute isAuth={isAuth}>
                            <ProtectedPage>
                                <ReviewAnalyzerPage />
                            </ProtectedPage>
                        </ProtectedRoute>
                    } />
                    <Route path="/analytics/brand-shops" element={
                        <ProtectedRoute isAuth={isAuth}>
                            <ProtectedPage>
                                <BrandShopsPage />
                            </ProtectedPage>
                        </ProtectedRoute>
                    } />
                    <Route path="/analytics/reputation-efficiency" element={
                        <ProtectedRoute isAuth={isAuth}>
                            <ProtectedPage>
                                <ReputationEfficiencyPage />
                            </ProtectedPage>
                        </ProtectedRoute>
                    } />
                    <Route path="/analytics/shops-summary" element={
                        <ProtectedRoute isAuth={isAuth}>
                            <ProtectedPage>
                                <ShopsSummaryPage />
                            </ProtectedPage>
                        </ProtectedRoute>
                    } />


                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </div>
        </BrowserRouter>
    );
}

export default App;