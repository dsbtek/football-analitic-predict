import React, { useState, useEffect } from 'react';
import './App.css';
import Login from './components/Login';
import Register from './components/Register';
import UserProfile from './components/UserProfile';
import ConnectionStatus from './components/ConnectionStatus';
import PredictionModal from './components/PredictionModal';
import OddsRequestModal from './components/OddsRequestModal';
import FloatingNews from './components/FloatingNews';
import useWebSocket from './hooks/useWebSocket';

const API_BASE_URL = 'http://localhost:8000';

function App() {
    const [matches, setMatches] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [filter, setFilter] = useState('all');

    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(10);
    const [pagination, setPagination] = useState(null);

    // Cart state
    const [cart, setCart] = useState([]);
    const [cartVisible, setCartVisible] = useState(false);
    const [sessionId] = useState('default'); // In production, generate unique session ID

    // Authentication state
    const [user, setUser] = useState(null);
    const [authModalVisible, setAuthModalVisible] = useState(false);
    const [authMode, setAuthMode] = useState('login'); // 'login' or 'register'

    // WebSocket state
    const token = localStorage.getItem('access_token');
    const { connectionStatus, lastMessage, sendMessage } = useWebSocket(
        'ws://localhost:8000/ws',
        token,
    );
    const [lastUpdateTime, setLastUpdateTime] = useState(null);

    // New modal states
    const [predictionModalVisible, setPredictionModalVisible] = useState(false);
    const [selectedMatchForPrediction, setSelectedMatchForPrediction] =
        useState(null);
    const [oddsRequestModalVisible, setOddsRequestModalVisible] =
        useState(false);

    // Fetch matches from API with pagination
    const fetchMatches = async (page = currentPage, size = pageSize) => {
        try {
            setError(null);
            const response = await fetch(
                `${API_BASE_URL}/matches/?page=${page}&page_size=${size}`,
            );
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            setMatches(data.matches);
            setPagination(data.pagination);
        } catch (err) {
            setError(`Failed to fetch matches: ${err.message}`);
            console.error('Error fetching matches:', err);
        } finally {
            setLoading(false);
        }
    };

    // Fetch cart from API
    const fetchCart = async () => {
        try {
            const response = await fetch(
                `${API_BASE_URL}/cart/?session_id=${sessionId}`,
            );
            if (response.ok) {
                const data = await response.json();
                setCart(data.items);
            }
        } catch (err) {
            console.error('Error fetching cart:', err);
        }
    };

    // Refresh odds data
    const refreshOdds = async () => {
        try {
            setRefreshing(true);
            setError(null);
            const response = await fetch(`${API_BASE_URL}/matches/refresh`, {
                method: 'POST',
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const result = await response.json();
            console.log('Refresh started:', result);

            // Wait a bit then refresh the matches
            setTimeout(() => {
                fetchMatches();
            }, 3000);
        } catch (err) {
            setError(`Failed to refresh odds: ${err.message}`);
            console.error('Error refreshing odds:', err);
        } finally {
            setRefreshing(false);
        }
    };

    // Add bet to cart
    const addToCart = async (matchId, betType) => {
        try {
            const response = await fetch(
                `${API_BASE_URL}/cart/add?session_id=${sessionId}`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        match_id: matchId,
                        bet_type: betType,
                    }),
                },
            );

            if (response.ok) {
                const data = await response.json();
                setCart(data.items);
                alert('Added to cart successfully!');
            } else {
                const error = await response.json();
                alert(error.detail || 'Failed to add to cart');
            }
        } catch (err) {
            console.error('Error adding to cart:', err);
            alert('Failed to add to cart');
        }
    };

    // Remove bet from cart
    const removeFromCart = async (matchId, betType) => {
        try {
            const response = await fetch(
                `${API_BASE_URL}/cart/remove/${matchId}/${betType}?session_id=${sessionId}`,
                { method: 'DELETE' },
            );

            if (response.ok) {
                const data = await response.json();
                setCart(data.items);
            }
        } catch (err) {
            console.error('Error removing from cart:', err);
        }
    };

    // Clear entire cart
    const clearCart = async () => {
        try {
            const response = await fetch(
                `${API_BASE_URL}/cart/clear?session_id=${sessionId}`,
                { method: 'DELETE' },
            );

            if (response.ok) {
                setCart([]);
            }
        } catch (err) {
            console.error('Error clearing cart:', err);
        }
    };

    // Print cart
    const printCart = async () => {
        try {
            const response = await fetch(
                `${API_BASE_URL}/cart/print?session_id=${sessionId}`,
            );

            if (response.ok) {
                const data = await response.json();

                // Create a new window for printing
                const printWindow = window.open('', '_blank');
                printWindow.document.write(`
                    <html>
                        <head>
                            <title>${data.title}</title>
                            <style>
                                body { font-family: Arial, sans-serif; margin: 20px; }
                                h1 { color: #333; }
                                .header { border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
                                .item { margin-bottom: 15px; padding: 10px; border: 1px solid #ddd; }
                                .disclaimer { margin-top: 30px; font-style: italic; color: #666; }
                                @media print { .no-print { display: none; } }
                            </style>
                        </head>
                        <body>
                            <div class="header">
                                <h1>${data.title}</h1>
                                <p>Generated: ${data.generated_at}</p>
                                <p>Total Selections: ${
                                    data.total_selections
                                } | Average Value: ${data.average_value}</p>
                            </div>
                            ${data.items
                                .map(
                                    (item) => `
                                <div class="item">
                                    <strong>${item.match}</strong><br>
                                    Bookmaker: ${item.bookmaker}<br>
                                    Bet: ${item.bet}<br>
                                    Odds: ${item.odds} | Value: ${item.value}<br>
                                    Potential Return: ${item.potential_return}
                                </div>
                            `,
                                )
                                .join('')}
                            <div class="disclaimer">
                                <p>${data.disclaimer}</p>
                            </div>
                            <div class="no-print" style="margin-top: 20px;">
                                <button onclick="window.print()">Print</button>
                                <button onclick="window.close()">Close</button>
                            </div>
                        </body>
                    </html>
                `);
                printWindow.document.close();
            }
        } catch (err) {
            console.error('Error printing cart:', err);
            alert('Failed to generate print view');
        }
    };

    // Pagination functions
    const goToPage = (page) => {
        setCurrentPage(page);
        fetchMatches(page, pageSize);
    };

    const changePageSize = (newSize) => {
        setPageSize(newSize);
        setCurrentPage(1);
        fetchMatches(1, newSize);
    };

    // Filter matches based on selected filter
    const filteredMatches = matches.filter((match) => {
        if (filter === 'all') return true;
        if (filter === 'home') return match.value_home > 0;
        if (filter === 'draw') return match.value_draw > 0;
        if (filter === 'away') return match.value_away > 0;
        return true;
    });

    // Get the best value bet for a match
    const getBestBet = (match) => {
        const bets = [
            {
                type: 'Home Win',
                value: match.value_home,
                odds: match.home_odds,
            },
            { type: 'Draw', value: match.value_draw, odds: match.draw_odds },
            {
                type: 'Away Win',
                value: match.value_away,
                odds: match.away_odds,
            },
        ];
        return bets.reduce((best, current) =>
            current.value > best.value ? current : best,
        );
    };

    // Format date/time
    const formatDateTime = (isoString) => {
        if (!isoString) return 'TBD';
        const date = new Date(isoString);
        return date.toLocaleString();
    };

    // Authentication functions
    const handleLogin = async (loginData) => {
        try {
            // Fetch user info
            const response = await fetch(`${API_BASE_URL}/auth/me`, {
                headers: {
                    Authorization: `Bearer ${loginData.access_token}`,
                },
            });

            if (response.ok) {
                const userData = await response.json();
                setUser(userData);
            }
        } catch (err) {
            console.error('Error fetching user data:', err);
        }
    };

    const handleLogout = () => {
        setUser(null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    };

    // WebSocket message handling
    useEffect(() => {
        if (lastMessage) {
            const message = lastMessage;

            switch (message.type) {
                case 'matches_update':
                    setMatches(message.data);
                    setLastUpdateTime(message.timestamp);
                    break;

                case 'odds_refresh_started':
                    setRefreshing(true);
                    break;

                case 'odds_refresh_complete':
                    setRefreshing(false);
                    // Optionally show notification
                    if (message.new_matches_count > 0) {
                        alert(
                            `Odds updated! ${message.new_matches_count} value bets found.`,
                        );
                    }
                    break;

                case 'system_notification':
                    // Show system notifications
                    if (message.level === 'error') {
                        setError(message.message);
                    } else {
                        console.log('System notification:', message.message);
                    }
                    break;

                case 'cart_update':
                    setCart(message.data.items);
                    break;

                default:
                    console.log('Unhandled WebSocket message:', message);
            }
        }
    }, [lastMessage]);

    // Check authentication on mount
    useEffect(() => {
        const token = localStorage.getItem('access_token');
        if (token) {
            // Verify token and get user data
            fetch(`${API_BASE_URL}/auth/me`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            })
                .then((response) => {
                    if (response.ok) {
                        return response.json();
                    } else {
                        // Token is invalid, remove it
                        localStorage.removeItem('access_token');
                        localStorage.removeItem('refresh_token');
                        throw new Error('Invalid token');
                    }
                })
                .then((userData) => {
                    setUser(userData);
                })
                .catch((err) => {
                    console.error('Token verification failed:', err);
                });
        }
    }, []);

    // New feature functions
    const openPredictionModal = (match) => {
        setSelectedMatchForPrediction(match);
        setPredictionModalVisible(true);
    };

    const closePredictionModal = () => {
        setPredictionModalVisible(false);
        setSelectedMatchForPrediction(null);
    };

    const openOddsRequestModal = () => {
        setOddsRequestModalVisible(true);
    };

    const closeOddsRequestModal = () => {
        setOddsRequestModalVisible(false);
    };

    // Check if bet is in cart
    const isBetInCart = (matchId, betType) => {
        return cart.some(
            (item) => item.match_id === matchId && item.bet_type === betType,
        );
    };

    useEffect(() => {
        fetchMatches();
        fetchCart();
    }, []);

    return (
        <div className="App">
            <header className="app-header">
                <div className="header-content">
                    <div className="header-left">
                        <h1>⚽ Football Analytics Predictor</h1>
                        <p>EPL Value Betting System using Elo Ratings</p>
                    </div>
                    <div className="header-right">
                        <ConnectionStatus
                            status={connectionStatus}
                            lastUpdate={lastUpdateTime}
                        />
                        {user ? (
                            <UserProfile user={user} onLogout={handleLogout} />
                        ) : (
                            <button
                                onClick={() => setAuthModalVisible(true)}
                                className="auth-trigger-btn"
                            >
                                🔐 Login / Register
                            </button>
                        )}
                    </div>
                </div>
            </header>

            {/* Authentication Modal */}
            {authModalVisible && (
                <div className="auth-modal">
                    <div className="auth-modal-content">
                        <button
                            className="auth-close-button"
                            onClick={() => setAuthModalVisible(false)}
                        >
                            ✕
                        </button>

                        {authMode === 'login' ? (
                            <Login
                                onLogin={handleLogin}
                                onSwitchToRegister={() =>
                                    setAuthMode('register')
                                }
                                onClose={() => setAuthModalVisible(false)}
                            />
                        ) : (
                            <Register
                                onRegister={() => {}}
                                onSwitchToLogin={() => setAuthMode('login')}
                                onClose={() => setAuthModalVisible(false)}
                            />
                        )}
                    </div>
                </div>
            )}

            <main className="main-content">
                <div className="controls">
                    <button
                        onClick={refreshOdds}
                        disabled={refreshing}
                        className="refresh-btn"
                    >
                        {refreshing ? '🔄 Refreshing...' : '🔄 Refresh Odds'}
                    </button>

                    <select
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        className="filter-select"
                    >
                        <option value="all">All Value Bets</option>
                        <option value="home">Home Win Values</option>
                        <option value="draw">Draw Values</option>
                        <option value="away">Away Win Values</option>
                    </select>

                    <select
                        value={pageSize}
                        onChange={(e) =>
                            changePageSize(parseInt(e.target.value))
                        }
                        className="filter-select"
                    >
                        <option value="5">5 per page</option>
                        <option value="10">10 per page</option>
                        <option value="20">20 per page</option>
                        <option value="50">50 per page</option>
                    </select>

                    <button
                        onClick={() => setCartVisible(!cartVisible)}
                        className="cart-btn"
                    >
                        🛒 Cart ({cart.length})
                    </button>

                    <button
                        onClick={openOddsRequestModal}
                        className="odds-request-btn"
                    >
                        🎯 Custom Odds
                    </button>
                </div>

                {/* Cart Modal */}
                {cartVisible && (
                    <div className="cart-modal">
                        <div className="cart-content">
                            <div className="cart-header">
                                <h3>🛒 Your Value Bets</h3>
                                <button
                                    onClick={() => setCartVisible(false)}
                                    className="close-btn"
                                >
                                    ✕
                                </button>
                            </div>

                            {cart.length === 0 ? (
                                <p>Your cart is empty</p>
                            ) : (
                                <>
                                    <div className="cart-items">
                                        {cart.map((item, index) => (
                                            <div
                                                key={index}
                                                className="cart-item"
                                            >
                                                <div className="cart-item-info">
                                                    <strong>
                                                        {item.home} vs{' '}
                                                        {item.away}
                                                    </strong>
                                                    <div>{item.bookmaker}</div>
                                                    <div>
                                                        {item.bet_type.toUpperCase()}{' '}
                                                        - Odds: {item.odds} -
                                                        Value: +{item.value}%
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={() =>
                                                        removeFromCart(
                                                            item.match_id,
                                                            item.bet_type,
                                                        )
                                                    }
                                                    className="remove-btn"
                                                >
                                                    Remove
                                                </button>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="cart-actions">
                                        <button
                                            onClick={printCart}
                                            className="print-btn"
                                        >
                                            🖨️ Print Selections
                                        </button>
                                        <button
                                            onClick={clearCart}
                                            className="clear-btn"
                                        >
                                            🗑️ Clear Cart
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                )}

                {error && <div className="error-message">⚠️ {error}</div>}

                {loading ? (
                    <div className="loading">
                        <div className="spinner"></div>
                        <p>Loading value bets...</p>
                    </div>
                ) : (
                    <div className="matches-container">
                        {filteredMatches.length === 0 ? (
                            <div className="no-matches">
                                <h3>No value bets found</h3>
                                <p>
                                    Try refreshing the odds or check back later
                                    for new opportunities.
                                </p>
                            </div>
                        ) : (
                            <div className="matches-grid">
                                {filteredMatches.map((match) => {
                                    const bestBet = getBestBet(match);
                                    return (
                                        <div
                                            key={match.id}
                                            className="match-card"
                                        >
                                            <div className="match-header">
                                                <div className="match-title-section">
                                                    <h3>
                                                        {match.home} vs{' '}
                                                        {match.away}
                                                    </h3>
                                                    <span className="bookmaker">
                                                        {match.bookmaker}
                                                    </span>
                                                </div>
                                                <button
                                                    onClick={() =>
                                                        openPredictionModal(
                                                            match,
                                                        )
                                                    }
                                                    className="predict-match-btn"
                                                    title="Get AI Prediction"
                                                >
                                                    🔮
                                                </button>
                                            </div>

                                            <div className="match-time">
                                                📅{' '}
                                                {formatDateTime(
                                                    match.start_time,
                                                )}
                                            </div>

                                            <div className="best-value">
                                                <div className="best-bet">
                                                    <span className="bet-type">
                                                        Best Value:{' '}
                                                        {bestBet.type}
                                                    </span>
                                                    <span className="value-percentage">
                                                        +
                                                        {bestBet.value.toFixed(
                                                            1,
                                                        )}
                                                        %
                                                    </span>
                                                </div>
                                                <div className="odds">
                                                    Odds: {bestBet.odds}
                                                </div>
                                            </div>

                                            <div className="all-values">
                                                <div className="value-row">
                                                    <span>Home Win:</span>
                                                    <span
                                                        className={
                                                            match.value_home > 0
                                                                ? 'positive'
                                                                : 'neutral'
                                                        }
                                                    >
                                                        {match.value_home > 0
                                                            ? `+${match.value_home}%`
                                                            : '-'}
                                                    </span>
                                                    <span className="odds-small">
                                                        ({match.home_odds})
                                                    </span>
                                                    {match.value_home > 0 && (
                                                        <button
                                                            onClick={() =>
                                                                addToCart(
                                                                    match.id,
                                                                    'home',
                                                                )
                                                            }
                                                            disabled={isBetInCart(
                                                                match.id,
                                                                'home',
                                                            )}
                                                            className="add-to-cart-btn"
                                                        >
                                                            {isBetInCart(
                                                                match.id,
                                                                'home',
                                                            )
                                                                ? '✓'
                                                                : '+'}
                                                        </button>
                                                    )}
                                                </div>
                                                <div className="value-row">
                                                    <span>Draw:</span>
                                                    <span
                                                        className={
                                                            match.value_draw > 0
                                                                ? 'positive'
                                                                : 'neutral'
                                                        }
                                                    >
                                                        {match.value_draw > 0
                                                            ? `+${match.value_draw}%`
                                                            : '-'}
                                                    </span>
                                                    <span className="odds-small">
                                                        ({match.draw_odds})
                                                    </span>
                                                    {match.value_draw > 0 && (
                                                        <button
                                                            onClick={() =>
                                                                addToCart(
                                                                    match.id,
                                                                    'draw',
                                                                )
                                                            }
                                                            disabled={isBetInCart(
                                                                match.id,
                                                                'draw',
                                                            )}
                                                            className="add-to-cart-btn"
                                                        >
                                                            {isBetInCart(
                                                                match.id,
                                                                'draw',
                                                            )
                                                                ? '✓'
                                                                : '+'}
                                                        </button>
                                                    )}
                                                </div>
                                                <div className="value-row">
                                                    <span>Away Win:</span>
                                                    <span
                                                        className={
                                                            match.value_away > 0
                                                                ? 'positive'
                                                                : 'neutral'
                                                        }
                                                    >
                                                        {match.value_away > 0
                                                            ? `+${match.value_away}%`
                                                            : '-'}
                                                    </span>
                                                    <span className="odds-small">
                                                        ({match.away_odds})
                                                    </span>
                                                    {match.value_away > 0 && (
                                                        <button
                                                            onClick={() =>
                                                                addToCart(
                                                                    match.id,
                                                                    'away',
                                                                )
                                                            }
                                                            disabled={isBetInCart(
                                                                match.id,
                                                                'away',
                                                            )}
                                                            className="add-to-cart-btn"
                                                        >
                                                            {isBetInCart(
                                                                match.id,
                                                                'away',
                                                            )
                                                                ? '✓'
                                                                : '+'}
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                )}

                {/* Pagination Controls */}
                {pagination && pagination.total_pages > 1 && (
                    <div className="pagination">
                        <button
                            onClick={() => goToPage(currentPage - 1)}
                            disabled={!pagination.has_previous}
                            className="pagination-btn"
                        >
                            ← Previous
                        </button>

                        <span className="pagination-info">
                            Page {pagination.page} of {pagination.total_pages}(
                            {pagination.total_items} total items)
                        </span>

                        <button
                            onClick={() => goToPage(currentPage + 1)}
                            disabled={!pagination.has_next}
                            className="pagination-btn"
                        >
                            Next →
                        </button>
                    </div>
                )}
            </main>

            <footer className="app-footer">
                <p>
                    Built with ❤️ by Muhammad - Betting like a data scientist 📊
                </p>
            </footer>

            {/* Prediction Modal */}
            {predictionModalVisible && selectedMatchForPrediction && (
                <PredictionModal
                    match={selectedMatchForPrediction}
                    onClose={closePredictionModal}
                    onPredict={(prediction) => {
                        console.log('Prediction received:', prediction);
                    }}
                />
            )}

            {/* Odds Request Modal */}
            {oddsRequestModalVisible && (
                <OddsRequestModal onClose={closeOddsRequestModal} />
            )}

            {/* Floating News */}
            <FloatingNews />
        </div>
    );
}

export default App;
