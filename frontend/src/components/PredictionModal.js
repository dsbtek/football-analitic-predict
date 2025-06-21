import React, { useState } from 'react';
import './PredictionModal.css';

const PredictionModal = ({ match, onClose, onPredict }) => {
    const [prediction, setPrediction] = useState(null);
    const [loading, setLoading] = useState(false);
    const [additionalFactors, setAdditionalFactors] = useState({
        home_form: 5,
        away_form: 5,
        injuries: 0
    });

    const handlePredict = async () => {
        setLoading(true);
        try {
            const response = await fetch('http://localhost:8000/predict/match', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    home_team: match.home,
                    away_team: match.away,
                    additional_factors: additionalFactors
                }),
            });

            if (response.ok) {
                const data = await response.json();
                setPrediction(data.prediction);
                if (onPredict) {
                    onPredict(data.prediction);
                }
            } else {
                console.error('Prediction failed');
            }
        } catch (error) {
            console.error('Error getting prediction:', error);
        } finally {
            setLoading(false);
        }
    };

    const getRiskColor = (riskLevel) => {
        switch (riskLevel) {
            case 'low': return '#4CAF50';
            case 'medium': return '#FF9800';
            case 'high': return '#f44336';
            default: return '#666';
        }
    };

    const getOutcomeIcon = (outcome) => {
        switch (outcome) {
            case 'home': return '🏠';
            case 'draw': return '🤝';
            case 'away': return '✈️';
            default: return '❓';
        }
    };

    return (
        <div className="prediction-modal">
            <div className="prediction-modal-content">
                <div className="prediction-header">
                    <h3>🔮 Match Prediction</h3>
                    <button onClick={onClose} className="close-btn">✕</button>
                </div>

                <div className="match-info">
                    <h4>{match.home} vs {match.away}</h4>
                    <p className="bookmaker">📊 {match.bookmaker}</p>
                </div>

                {!prediction && (
                    <div className="prediction-form">
                        <h5>Additional Factors (Optional)</h5>
                        
                        <div className="factor-group">
                            <label>Home Team Form (1-10):</label>
                            <input
                                type="range"
                                min="1"
                                max="10"
                                value={additionalFactors.home_form}
                                onChange={(e) => setAdditionalFactors({
                                    ...additionalFactors,
                                    home_form: parseInt(e.target.value)
                                })}
                            />
                            <span className="factor-value">{additionalFactors.home_form}</span>
                        </div>

                        <div className="factor-group">
                            <label>Away Team Form (1-10):</label>
                            <input
                                type="range"
                                min="1"
                                max="10"
                                value={additionalFactors.away_form}
                                onChange={(e) => setAdditionalFactors({
                                    ...additionalFactors,
                                    away_form: parseInt(e.target.value)
                                })}
                            />
                            <span className="factor-value">{additionalFactors.away_form}</span>
                        </div>

                        <div className="factor-group">
                            <label>Injury Impact (0-10):</label>
                            <input
                                type="range"
                                min="0"
                                max="10"
                                value={additionalFactors.injuries}
                                onChange={(e) => setAdditionalFactors({
                                    ...additionalFactors,
                                    injuries: parseInt(e.target.value)
                                })}
                            />
                            <span className="factor-value">{additionalFactors.injuries}</span>
                        </div>

                        <button
                            onClick={handlePredict}
                            disabled={loading}
                            className="predict-btn"
                        >
                            {loading ? '🔄 Analyzing...' : '🎯 Get Prediction'}
                        </button>
                    </div>
                )}

                {prediction && (
                    <div className="prediction-result">
                        <div className="prediction-outcome">
                            <div className="outcome-header">
                                <span className="outcome-icon">
                                    {getOutcomeIcon(prediction.predicted_outcome)}
                                </span>
                                <h4>
                                    Predicted: {prediction.predicted_outcome.charAt(0).toUpperCase() + prediction.predicted_outcome.slice(1)}
                                </h4>
                            </div>
                            
                            <div className="confidence-meter">
                                <div className="confidence-label">
                                    Confidence: {prediction.confidence}%
                                </div>
                                <div className="confidence-bar">
                                    <div 
                                        className="confidence-fill"
                                        style={{ 
                                            width: `${prediction.confidence}%`,
                                            backgroundColor: prediction.confidence > 70 ? '#4CAF50' : 
                                                           prediction.confidence > 50 ? '#FF9800' : '#f44336'
                                        }}
                                    ></div>
                                </div>
                            </div>
                        </div>

                        <div className="probabilities">
                            <h5>Outcome Probabilities</h5>
                            <div className="prob-grid">
                                <div className="prob-item">
                                    <span className="prob-label">🏠 Home Win</span>
                                    <span className="prob-value">{prediction.probabilities.home}%</span>
                                </div>
                                <div className="prob-item">
                                    <span className="prob-label">🤝 Draw</span>
                                    <span className="prob-value">{prediction.probabilities.draw}%</span>
                                </div>
                                <div className="prob-item">
                                    <span className="prob-label">✈️ Away Win</span>
                                    <span className="prob-value">{prediction.probabilities.away}%</span>
                                </div>
                            </div>
                        </div>

                        <div className="prediction-details">
                            <div className="risk-level">
                                <span>Risk Level: </span>
                                <span 
                                    className="risk-badge"
                                    style={{ backgroundColor: getRiskColor(prediction.risk_level) }}
                                >
                                    {prediction.risk_level.toUpperCase()}
                                </span>
                            </div>

                            <div className="expected-value">
                                <span>Expected Value: </span>
                                <span className={prediction.expected_value > 0 ? 'positive' : 'negative'}>
                                    {prediction.expected_value > 0 ? '+' : ''}{prediction.expected_value}%
                                </span>
                            </div>
                        </div>

                        <div className="reasoning">
                            <h5>Analysis</h5>
                            <p>{prediction.reasoning}</p>
                        </div>

                        <div className="prediction-actions">
                            <button onClick={() => setPrediction(null)} className="new-prediction-btn">
                                🔄 New Prediction
                            </button>
                            <button onClick={onClose} className="close-prediction-btn">
                                ✅ Done
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default PredictionModal;
