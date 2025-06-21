import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

function App() {
    const [matches, setMatches] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [filter, setFilter] = useState('all');

    // Fetch matches from API
    const fetchMatches = async () => {
        try {
            setError(null);
            const response = await fetch(`${API_BASE_URL}/matches/`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            setMatches(data);
        } catch (err) {
            setError(`Failed to fetch matches: ${err.message}`);
            console.error('Error fetching matches:', err);
        } finally {
            setLoading(false);
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

    useEffect(() => {
        fetchMatches();
    }, []);

    return (
        <div className="App">
            <header className="app-header">
                <h1>⚽ Football Analytics Predictor</h1>
                <p>EPL Value Betting System using Elo Ratings</p>
            </header>

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
                </div>

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
                                                <h3>
                                                    {match.home} vs {match.away}
                                                </h3>
                                                <span className="bookmaker">
                                                    {match.bookmaker}
                                                </span>
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
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                )}
            </main>

            <footer className="app-footer">
                <p>
                    Built with ❤️ by Muhammad - Betting like a data scientist 📊
                </p>
            </footer>
        </div>
    );
}

export default App;
