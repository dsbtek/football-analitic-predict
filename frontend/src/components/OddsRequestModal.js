import React, { useState } from 'react';
import './OddsRequestModal.css';

const OddsRequestModal = ({ onClose, addToCart, onAnalyze }) => {
    const [request, setRequest] = useState({
        target_odds: 3.0,
        max_matches: 2,
        risk_tolerance: 'moderate',
        preferred_outcomes: ['home', 'away'],
    });
    const [combinations, setCombinations] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searched, setSearched] = useState(false);

    const handleInputChange = (field, value) => {
        setRequest((prev) => ({
            ...prev,
            [field]: value,
        }));
    };

    const handleOutcomeToggle = (outcome) => {
        setRequest((prev) => ({
            ...prev,
            preferred_outcomes: prev.preferred_outcomes.includes(outcome)
                ? prev.preferred_outcomes.filter((o) => o !== outcome)
                : [...prev.preferred_outcomes, outcome],
        }));
    };

    const searchCombinations = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                target_odds: request.target_odds,
                max_matches: request.max_matches,
                risk_tolerance: request.risk_tolerance,
                preferred_outcomes: request.preferred_outcomes.join(','),
            });

            const response = await fetch(
                `http://localhost:8000/odds/request?${params}`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                },
            );

            if (response.ok) {
                const data = await response.json();
                setCombinations(data.combinations);
                setSearched(true);
            } else {
                console.error('Odds request failed');
            }
        } catch (error) {
            console.error('Error requesting odds:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleAddToCart = async (combo) => {
        try {
            if (combo.type === 'single' && combo.matches.length > 0) {
                // For single bets, add the specific match and outcome
                const match = combo.matches[0];
                const outcome = combo.outcomes[0];

                if (addToCart && match.id) {
                    await addToCart(match.id, outcome);
                } else {
                    alert('Unable to add to cart: Missing match information');
                }
            } else {
                // For combination bets, we need to add each match separately
                // or implement a combination cart feature
                alert(
                    'Combination bets not yet supported in cart. Please add individual matches.',
                );
            }
        } catch (error) {
            console.error('Error adding combination to cart:', error);
            alert('Failed to add to cart');
        }
    };

    const handleAnalyze = (combo) => {
        if (onAnalyze) {
            onAnalyze(combo);
        } else {
            // Default analysis display
            const analysisText = `
Analysis for ${combo.description}:
- Combined Odds: ${combo.combined_odds}
- Risk Level: ${combo.risk_level}
- Confidence: ${combo.prediction_confidence}%
- Type: ${combo.type.toUpperCase()}

Reasoning: ${combo.reasoning}
            `.trim();

            alert(analysisText);
        }
    };

    const getRiskColor = (riskLevel) => {
        switch (riskLevel) {
            case 'low':
                return '#4CAF50';
            case 'medium':
                return '#FF9800';
            case 'high':
                return '#f44336';
            default:
                return '#666';
        }
    };

    const getCombinationIcon = (type) => {
        switch (type) {
            case 'single':
                return '🎯';
            case 'double':
                return '🎲';
            case 'triple':
                return '🎰';
            default:
                return '📊';
        }
    };

    return (
        <div className="odds-request-modal">
            <div className="odds-request-modal-content">
                <div className="odds-request-header">
                    <h3>🎯 Custom Odds Request</h3>
                    <button onClick={onClose} className="close-btn">
                        ✕
                    </button>
                </div>

                <div className="odds-request-form">
                    <div className="form-section">
                        <h4>Target Odds</h4>
                        <div className="odds-input-group">
                            <input
                                type="number"
                                min="1.1"
                                max="50"
                                step="0.1"
                                value={request.target_odds}
                                onChange={(e) =>
                                    handleInputChange(
                                        'target_odds',
                                        parseFloat(e.target.value),
                                    )
                                }
                                className="odds-input"
                            />
                            <span className="odds-label">Target Odds</span>
                        </div>
                    </div>

                    <div className="form-section">
                        <h4>Maximum Matches</h4>
                        <div className="max-matches-group">
                            {[1, 2, 3, 4, 5].map((num) => (
                                <button
                                    key={num}
                                    className={`match-count-btn ${
                                        request.max_matches === num
                                            ? 'active'
                                            : ''
                                    }`}
                                    onClick={() =>
                                        handleInputChange('max_matches', num)
                                    }
                                >
                                    {num}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="form-section">
                        <h4>Risk Tolerance</h4>
                        <div className="risk-tolerance-group">
                            {[
                                {
                                    value: 'conservative',
                                    label: '🛡️ Conservative',
                                    desc: 'Safer bets',
                                },
                                {
                                    value: 'moderate',
                                    label: '⚖️ Moderate',
                                    desc: 'Balanced approach',
                                },
                                {
                                    value: 'aggressive',
                                    label: '🚀 Aggressive',
                                    desc: 'Higher risk/reward',
                                },
                            ].map((option) => (
                                <button
                                    key={option.value}
                                    className={`risk-btn ${
                                        request.risk_tolerance === option.value
                                            ? 'active'
                                            : ''
                                    }`}
                                    onClick={() =>
                                        handleInputChange(
                                            'risk_tolerance',
                                            option.value,
                                        )
                                    }
                                >
                                    <span className="risk-label">
                                        {option.label}
                                    </span>
                                    <span className="risk-desc">
                                        {option.desc}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="form-section">
                        <h4>Preferred Outcomes</h4>
                        <div className="outcomes-group">
                            {[
                                {
                                    value: 'home',
                                    label: '🏠 Home Win',
                                    color: '#4CAF50',
                                },
                                {
                                    value: 'draw',
                                    label: '🤝 Draw',
                                    color: '#FF9800',
                                },
                                {
                                    value: 'away',
                                    label: '✈️ Away Win',
                                    color: '#2196F3',
                                },
                            ].map((outcome) => (
                                <button
                                    key={outcome.value}
                                    className={`outcome-btn ${
                                        request.preferred_outcomes.includes(
                                            outcome.value,
                                        )
                                            ? 'active'
                                            : ''
                                    }`}
                                    onClick={() =>
                                        handleOutcomeToggle(outcome.value)
                                    }
                                    style={{
                                        borderColor:
                                            request.preferred_outcomes.includes(
                                                outcome.value,
                                            )
                                                ? outcome.color
                                                : '#ddd',
                                        backgroundColor:
                                            request.preferred_outcomes.includes(
                                                outcome.value,
                                            )
                                                ? outcome.color + '20'
                                                : 'white',
                                    }}
                                >
                                    {outcome.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    <button
                        onClick={searchCombinations}
                        disabled={
                            loading || request.preferred_outcomes.length === 0
                        }
                        className="search-btn"
                    >
                        {loading ? '🔍 Searching...' : '🎯 Find Combinations'}
                    </button>
                </div>

                {searched && (
                    <div className="combinations-results">
                        <div className="results-header">
                            <h4>Found {combinations.length} Combinations</h4>
                            <p>
                                Target: {request.target_odds} odds • Max{' '}
                                {request.max_matches} matches
                            </p>
                        </div>

                        {combinations.length === 0 ? (
                            <div className="no-combinations">
                                <p>
                                    😔 No combinations found matching your
                                    criteria.
                                </p>
                                <p>
                                    Try adjusting your target odds or risk
                                    tolerance.
                                </p>
                            </div>
                        ) : (
                            <div className="combinations-list">
                                {combinations.map((combo, index) => (
                                    <div
                                        key={index}
                                        className="combination-card"
                                    >
                                        <div className="combo-header">
                                            <div className="combo-type">
                                                <span className="combo-icon">
                                                    {getCombinationIcon(
                                                        combo.type,
                                                    )}
                                                </span>
                                                <span className="combo-label">
                                                    {combo.type.toUpperCase()}
                                                </span>
                                            </div>
                                            <div className="combo-odds">
                                                <span className="odds-value">
                                                    {combo.combined_odds}
                                                </span>
                                                <span className="odds-label">
                                                    odds
                                                </span>
                                            </div>
                                        </div>

                                        <div className="combo-description">
                                            {combo.description}
                                        </div>

                                        <div className="combo-details">
                                            <div className="combo-matches">
                                                {combo.matches.map(
                                                    (match, matchIndex) => (
                                                        <div
                                                            key={matchIndex}
                                                            className="combo-match"
                                                        >
                                                            <span className="match-teams">
                                                                {match.home} vs{' '}
                                                                {match.away}
                                                            </span>
                                                            <span className="match-outcome">
                                                                {combo.outcomes[
                                                                    matchIndex
                                                                ].toUpperCase()}
                                                            </span>
                                                        </div>
                                                    ),
                                                )}
                                            </div>

                                            <div className="combo-stats">
                                                <div className="stat-item">
                                                    <span className="stat-label">
                                                        Confidence:
                                                    </span>
                                                    <span className="stat-value">
                                                        {
                                                            combo.prediction_confidence
                                                        }
                                                        %
                                                    </span>
                                                </div>
                                                <div className="stat-item">
                                                    <span className="stat-label">
                                                        Risk:
                                                    </span>
                                                    <span
                                                        className="risk-badge"
                                                        style={{
                                                            backgroundColor:
                                                                getRiskColor(
                                                                    combo.risk_level,
                                                                ),
                                                        }}
                                                    >
                                                        {combo.risk_level.toUpperCase()}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="combo-reasoning">
                                            <small>{combo.reasoning}</small>
                                        </div>

                                        <div className="combo-actions">
                                            <button
                                                className="add-to-cart-combo-btn"
                                                onClick={() =>
                                                    handleAddToCart(combo)
                                                }
                                            >
                                                🛒 Add to Cart
                                            </button>
                                            <button
                                                className="analyze-combo-btn"
                                                onClick={() =>
                                                    handleAnalyze(combo)
                                                }
                                            >
                                                📊 Analyze
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default OddsRequestModal;
