import React, { useState, useEffect } from 'react';
import './FeedbackCard.css';

const FeedbackCard = () => {
    const [isVisible, setIsVisible] = useState(true);
    const [isExpanded, setIsExpanded] = useState(false);
    const [currentStep, setCurrentStep] = useState(0);
    const [feedback, setFeedback] = useState({
        rating: 0,
        category: '',
        message: '',
        email: '',
        anonymous: false
    });
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isSubmitted, setIsSubmitted] = useState(false);

    const feedbackSteps = [
        {
            title: "Rate Your Experience",
            icon: "⭐",
            component: "rating"
        },
        {
            title: "What's This About?",
            icon: "📝",
            component: "category"
        },
        {
            title: "Tell Us More",
            icon: "💬",
            component: "message"
        },
        {
            title: "Contact Info (Optional)",
            icon: "📧",
            component: "contact"
        }
    ];

    const categories = [
        { id: 'bug', label: '🐛 Bug Report', description: 'Something isn\'t working' },
        { id: 'feature', label: '💡 Feature Request', description: 'Suggest a new feature' },
        { id: 'ui', label: '🎨 UI/UX Feedback', description: 'Design or usability feedback' },
        { id: 'performance', label: '⚡ Performance', description: 'Speed or loading issues' },
        { id: 'prediction', label: '🔮 Prediction Accuracy', description: 'AI prediction feedback' },
        { id: 'general', label: '💭 General Feedback', description: 'Other thoughts or suggestions' }
    ];

    useEffect(() => {
        // Auto-show feedback card after user has been on the page for 30 seconds
        const timer = setTimeout(() => {
            if (!localStorage.getItem('feedback_shown_today')) {
                setIsVisible(true);
                localStorage.setItem('feedback_shown_today', new Date().toDateString());
            }
        }, 30000);

        return () => clearTimeout(timer);
    }, []);

    const handleRatingClick = (rating) => {
        setFeedback(prev => ({ ...prev, rating }));
        if (rating > 0) {
            setTimeout(() => setCurrentStep(1), 500);
        }
    };

    const handleCategorySelect = (categoryId) => {
        setFeedback(prev => ({ ...prev, category: categoryId }));
        setTimeout(() => setCurrentStep(2), 300);
    };

    const handleNext = () => {
        if (currentStep < feedbackSteps.length - 1) {
            setCurrentStep(currentStep + 1);
        }
    };

    const handlePrevious = () => {
        if (currentStep > 0) {
            setCurrentStep(currentStep - 1);
        }
    };

    const handleSubmit = async () => {
        setIsSubmitting(true);
        
        try {
            const response = await fetch('http://localhost:8000/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ...feedback,
                    timestamp: new Date().toISOString(),
                    user_agent: navigator.userAgent,
                    page_url: window.location.href
                })
            });

            if (response.ok) {
                setIsSubmitted(true);
                setTimeout(() => {
                    setIsVisible(false);
                    resetFeedback();
                }, 3000);
            } else {
                throw new Error('Failed to submit feedback');
            }
        } catch (error) {
            console.error('Error submitting feedback:', error);
            alert('Failed to submit feedback. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    const resetFeedback = () => {
        setFeedback({
            rating: 0,
            category: '',
            message: '',
            email: '',
            anonymous: false
        });
        setCurrentStep(0);
        setIsExpanded(false);
        setIsSubmitted(false);
    };

    const closeFeedback = () => {
        setIsVisible(false);
        resetFeedback();
    };

    const toggleExpanded = () => {
        setIsExpanded(!isExpanded);
        if (!isExpanded) {
            setCurrentStep(0);
        }
    };

    if (!isVisible) {
        return null;
    }

    const renderStepContent = () => {
        const step = feedbackSteps[currentStep];
        
        switch (step.component) {
            case 'rating':
                return (
                    <div className="rating-step">
                        <p>How would you rate your experience?</p>
                        <div className="rating-stars">
                            {[1, 2, 3, 4, 5].map(star => (
                                <button
                                    key={star}
                                    onClick={() => handleRatingClick(star)}
                                    className={`star ${feedback.rating >= star ? 'active' : ''}`}
                                >
                                    ⭐
                                </button>
                            ))}
                        </div>
                        <div className="rating-labels">
                            <span>Poor</span>
                            <span>Excellent</span>
                        </div>
                    </div>
                );

            case 'category':
                return (
                    <div className="category-step">
                        <p>What would you like to share?</p>
                        <div className="category-grid">
                            {categories.map(cat => (
                                <button
                                    key={cat.id}
                                    onClick={() => handleCategorySelect(cat.id)}
                                    className={`category-btn ${feedback.category === cat.id ? 'selected' : ''}`}
                                >
                                    <div className="category-label">{cat.label}</div>
                                    <div className="category-desc">{cat.description}</div>
                                </button>
                            ))}
                        </div>
                    </div>
                );

            case 'message':
                return (
                    <div className="message-step">
                        <p>Please share your thoughts:</p>
                        <textarea
                            value={feedback.message}
                            onChange={(e) => setFeedback(prev => ({ ...prev, message: e.target.value }))}
                            placeholder="Tell us more about your experience, suggestions, or issues..."
                            rows={4}
                            className="feedback-textarea"
                        />
                        <div className="step-navigation">
                            <button onClick={handlePrevious} className="nav-btn secondary">
                                ← Back
                            </button>
                            <button 
                                onClick={handleNext} 
                                className="nav-btn primary"
                                disabled={!feedback.message.trim()}
                            >
                                Next →
                            </button>
                        </div>
                    </div>
                );

            case 'contact':
                return (
                    <div className="contact-step">
                        <p>Contact info (optional):</p>
                        <input
                            type="email"
                            value={feedback.email}
                            onChange={(e) => setFeedback(prev => ({ ...prev, email: e.target.value }))}
                            placeholder="your.email@example.com"
                            className="feedback-input"
                        />
                        <label className="checkbox-label">
                            <input
                                type="checkbox"
                                checked={feedback.anonymous}
                                onChange={(e) => setFeedback(prev => ({ ...prev, anonymous: e.target.checked }))}
                            />
                            Submit anonymously
                        </label>
                        <div className="step-navigation">
                            <button onClick={handlePrevious} className="nav-btn secondary">
                                ← Back
                            </button>
                            <button 
                                onClick={handleSubmit} 
                                className="nav-btn primary submit-btn"
                                disabled={isSubmitting}
                            >
                                {isSubmitting ? '⏳ Submitting...' : '🚀 Submit Feedback'}
                            </button>
                        </div>
                    </div>
                );

            default:
                return null;
        }
    };

    if (isSubmitted) {
        return (
            <div className="feedback-card submitted">
                <div className="success-message">
                    <div className="success-icon">✅</div>
                    <h3>Thank You!</h3>
                    <p>Your feedback has been submitted successfully.</p>
                    <p>We appreciate your input!</p>
                </div>
            </div>
        );
    }

    return (
        <div className={`feedback-card ${isExpanded ? 'expanded' : 'collapsed'}`}>
            {!isExpanded ? (
                <div className="feedback-trigger" onClick={toggleExpanded}>
                    <div className="trigger-icon">💬</div>
                    <div className="trigger-text">
                        <span>Feedback</span>
                        <small>Share your thoughts</small>
                    </div>
                </div>
            ) : (
                <div className="feedback-content">
                    <div className="feedback-header">
                        <div className="step-indicator">
                            <span className="step-icon">{feedbackSteps[currentStep].icon}</span>
                            <span className="step-title">{feedbackSteps[currentStep].title}</span>
                        </div>
                        <button onClick={closeFeedback} className="close-btn">✕</button>
                    </div>

                    <div className="progress-bar">
                        <div 
                            className="progress-fill" 
                            style={{ width: `${((currentStep + 1) / feedbackSteps.length) * 100}%` }}
                        />
                    </div>

                    <div className="step-content">
                        {renderStepContent()}
                    </div>

                    <div className="feedback-footer">
                        <div className="step-dots">
                            {feedbackSteps.map((_, index) => (
                                <div 
                                    key={index}
                                    className={`dot ${index <= currentStep ? 'active' : ''}`}
                                />
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default FeedbackCard;
