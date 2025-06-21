import React, { useState, useEffect, useRef } from 'react';
import CircularLinkedList from '../utils/CircularLinkedList';
import './FloatingNews.css';

const FloatingNews = () => {
    const [news, setNews] = useState([]);
    const [currentNews, setCurrentNews] = useState(null);
    const [isVisible, setIsVisible] = useState(true);
    const [isExpanded, setIsExpanded] = useState(false);
    const [loading, setLoading] = useState(true);
    const [currentIndex, setCurrentIndex] = useState(0);
    const newsListRef = useRef(new CircularLinkedList());
    const autoAdvanceRef = useRef(null);

    useEffect(() => {
        fetchNews();
        const interval = setInterval(fetchNews, 300000); // Refresh every 5 minutes
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        if (news.length > 0) {
            // Rebuild the circular linked list with new news
            newsListRef.current.rebuild(news);
            setCurrentNews(newsListRef.current.getCurrent());
            setCurrentIndex(0);

            // Start auto-advance
            startAutoAdvance();
        }

        return () => {
            if (autoAdvanceRef.current) {
                clearInterval(autoAdvanceRef.current);
            }
        };
    }, [news]);

    const startAutoAdvance = () => {
        if (autoAdvanceRef.current) {
            clearInterval(autoAdvanceRef.current);
        }

        autoAdvanceRef.current = setInterval(() => {
            if (!newsListRef.current.isEmpty()) {
                const nextNews = newsListRef.current.autoAdvance();
                setCurrentNews(nextNews);
                setCurrentIndex(newsListRef.current.getCurrentIndex());
            }
        }, 5000); // Change news every 5 seconds
    };

    const stopAutoAdvance = () => {
        if (autoAdvanceRef.current) {
            clearInterval(autoAdvanceRef.current);
            autoAdvanceRef.current = null;
        }
    };

    const fetchNews = async () => {
        try {
            const response = await fetch(
                'http://localhost:8000/news/latest?limit=10',
            );
            if (response.ok) {
                const data = await response.json();
                setNews(data.news);
            }
        } catch (error) {
            console.error('Error fetching news:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleNewsNavigation = (direction) => {
        stopAutoAdvance();

        let newNews;
        if (direction === 'next') {
            newNews = newsListRef.current.next();
        } else if (direction === 'prev') {
            newNews = newsListRef.current.previous();
        }

        if (newNews) {
            setCurrentNews(newNews);
            setCurrentIndex(newsListRef.current.getCurrentIndex());
        }

        // Restart auto-advance after manual navigation
        setTimeout(startAutoAdvance, 3000);
    };

    const jumpToNews = (index) => {
        stopAutoAdvance();

        const news = newsListRef.current.jumpTo(index);
        if (news) {
            setCurrentNews(news);
            setCurrentIndex(index);
        }

        // Restart auto-advance after manual navigation
        setTimeout(startAutoAdvance, 3000);
    };

    const getCategoryIcon = (category) => {
        switch (category) {
            case 'transfer':
                return '🔄';
            case 'match':
                return '⚽';
            case 'injury':
                return '🏥';
            case 'general':
                return '📰';
            default:
                return '📰';
        }
    };

    const getCategoryColor = (category) => {
        switch (category) {
            case 'transfer':
                return '#FF6B6B';
            case 'match':
                return '#4ECDC4';
            case 'injury':
                return '#FFE66D';
            case 'general':
                return '#A8E6CF';
            default:
                return '#A8E6CF';
        }
    };

    const formatTimeAgo = (timeAgo) => {
        return timeAgo || 'Just now';
    };

    const truncateText = (text, maxLength = 100) => {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    };

    if (!isVisible || loading || news.length === 0 || !currentNews) {
        return null;
    }

    return (
        <div className={`floating-news ${isExpanded ? 'expanded' : ''}`}>
            <div className="news-header">
                <div className="news-brand">
                    <span className="news-icon">📺</span>
                    <span className="news-title">Football News</span>
                </div>
                <div className="news-controls">
                    <button
                        className="expand-btn"
                        onClick={() => setIsExpanded(!isExpanded)}
                        title={isExpanded ? 'Collapse' : 'Expand'}
                    >
                        {isExpanded ? '📖' : '📰'}
                    </button>
                    <button
                        className="close-btn"
                        onClick={() => setIsVisible(false)}
                        title="Close news ticker"
                    >
                        ✕
                    </button>
                </div>
            </div>

            {!isExpanded ? (
                // Compact ticker mode
                <div className="news-ticker">
                    <div className="news-item-compact">
                        <div className="news-category-badge">
                            <span
                                className="category-icon"
                                style={{
                                    backgroundColor: getCategoryColor(
                                        currentNews.category,
                                    ),
                                }}
                            >
                                {getCategoryIcon(currentNews.category)}
                            </span>
                        </div>
                        <div className="news-content-compact">
                            <div className="news-title-compact">
                                {truncateText(currentNews.title, 80)}
                            </div>
                            <div className="news-meta-compact">
                                <span className="news-source">
                                    {currentNews.source}
                                </span>
                                <span className="news-time">
                                    {formatTimeAgo(currentNews.time_ago)}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div className="news-progress">
                        <div
                            className="progress-bar"
                            style={{
                                animation: 'progress 5s linear infinite',
                                backgroundColor: getCategoryColor(
                                    currentNews.category,
                                ),
                            }}
                        ></div>
                    </div>
                </div>
            ) : (
                // Expanded mode
                <div className="news-expanded">
                    <div className="current-news">
                        <div className="news-item-full">
                            <div className="news-category-full">
                                <span
                                    className="category-badge"
                                    style={{
                                        backgroundColor: getCategoryColor(
                                            currentNews.category,
                                        ),
                                    }}
                                >
                                    {getCategoryIcon(currentNews.category)}{' '}
                                    {currentNews.category.toUpperCase()}
                                </span>
                            </div>
                            <h4 className="news-title-full">
                                {currentNews.title}
                            </h4>
                            <p className="news-summary">
                                {currentNews.summary}
                            </p>
                            <div className="news-meta-full">
                                <span className="news-source-full">
                                    {currentNews.source}
                                </span>
                                <span className="news-time-full">
                                    {formatTimeAgo(currentNews.time_ago)}
                                </span>
                                {currentNews.teams_mentioned.length > 0 && (
                                    <div className="teams-mentioned">
                                        <span className="teams-label">
                                            Teams:
                                        </span>
                                        {currentNews.teams_mentioned.map(
                                            (team, index) => (
                                                <span
                                                    key={index}
                                                    className="team-tag"
                                                >
                                                    {team}
                                                </span>
                                            ),
                                        )}
                                    </div>
                                )}
                            </div>
                            <div className="news-actions">
                                <a
                                    href={currentNews.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="read-more-btn"
                                >
                                    📖 Read Full Article
                                </a>
                            </div>
                        </div>
                    </div>

                    <div className="news-list">
                        <div className="news-list-header">
                            <h5>Latest Headlines</h5>
                            <button
                                className="refresh-news-btn"
                                onClick={fetchNews}
                                title="Refresh news"
                            >
                                🔄
                            </button>
                        </div>
                        <div className="news-items-list">
                            {news.slice(0, 5).map((item, index) => (
                                <div
                                    key={index}
                                    className={`news-list-item ${
                                        index === currentIndex ? 'active' : ''
                                    }`}
                                    onClick={() => setCurrentIndex(index)}
                                >
                                    <div className="list-item-category">
                                        <span
                                            className="list-category-icon"
                                            style={{
                                                backgroundColor:
                                                    getCategoryColor(
                                                        item.category,
                                                    ),
                                            }}
                                        >
                                            {getCategoryIcon(item.category)}
                                        </span>
                                    </div>
                                    <div className="list-item-content">
                                        <div className="list-item-title">
                                            {truncateText(item.title, 60)}
                                        </div>
                                        <div className="list-item-meta">
                                            <span className="list-item-source">
                                                {item.source}
                                            </span>
                                            <span className="list-item-time">
                                                {formatTimeAgo(item.time_ago)}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* News indicator dots */}
            <div className="news-indicators">
                {news.slice(0, 5).map((_, index) => (
                    <button
                        key={index}
                        className={`indicator-dot ${
                            index === currentIndex ? 'active' : ''
                        }`}
                        onClick={() => setCurrentIndex(index)}
                        style={{
                            backgroundColor:
                                index === currentIndex
                                    ? getCategoryColor(
                                          news[currentIndex]?.category,
                                      )
                                    : '#ddd',
                        }}
                    />
                ))}
            </div>
        </div>
    );
};

export default FloatingNews;
