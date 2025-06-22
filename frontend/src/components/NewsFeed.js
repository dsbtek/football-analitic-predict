import React, { useState, useEffect, useRef } from 'react';
import CircularLinkedList from '../utils/CircularLinkedList';
import './NewsFeed.css';

const NewsFeed = () => {
    const [news, setNews] = useState([]);
    const [currentNews, setCurrentNews] = useState(null);
    const [loading, setLoading] = useState(true);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(true);
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
            
            // Start auto-advance if playing
            if (isPlaying) {
                startAutoAdvance();
            }
        }
        
        return () => {
            if (autoAdvanceRef.current) {
                clearInterval(autoAdvanceRef.current);
            }
        };
    }, [news, isPlaying]);

    const fetchNews = async () => {
        try {
            const response = await fetch('http://localhost:8000/news/latest?limit=10');
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
        }, 8000); // Change news every 8 seconds
    };

    const stopAutoAdvance = () => {
        if (autoAdvanceRef.current) {
            clearInterval(autoAdvanceRef.current);
            autoAdvanceRef.current = null;
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
        
        // Restart auto-advance after manual navigation if playing
        if (isPlaying) {
            setTimeout(startAutoAdvance, 3000);
        }
    };

    const jumpToNews = (index) => {
        stopAutoAdvance();
        
        const news = newsListRef.current.jumpTo(index);
        if (news) {
            setCurrentNews(news);
            setCurrentIndex(index);
        }
        
        // Restart auto-advance after manual navigation if playing
        if (isPlaying) {
            setTimeout(startAutoAdvance, 3000);
        }
    };

    const togglePlayPause = () => {
        setIsPlaying(!isPlaying);
        if (!isPlaying) {
            startAutoAdvance();
        } else {
            stopAutoAdvance();
        }
    };

    const formatTimeAgo = (dateString) => {
        const now = new Date();
        const newsDate = new Date(dateString);
        const diffInMinutes = Math.floor((now - newsDate) / (1000 * 60));
        
        if (diffInMinutes < 1) return 'Just now';
        if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
        
        const diffInHours = Math.floor(diffInMinutes / 60);
        if (diffInHours < 24) return `${diffInHours}h ago`;
        
        const diffInDays = Math.floor(diffInHours / 24);
        return `${diffInDays}d ago`;
    };

    if (loading) {
        return (
            <div className="news-feed">
                <div className="news-feed-header">
                    <h3>📰 Football News</h3>
                </div>
                <div className="news-loading">
                    <div className="news-spinner"></div>
                    <p>Loading news...</p>
                </div>
            </div>
        );
    }

    if (!currentNews || news.length === 0) {
        return (
            <div className="news-feed">
                <div className="news-feed-header">
                    <h3>📰 Football News</h3>
                </div>
                <div className="no-news">
                    <p>No news available</p>
                </div>
            </div>
        );
    }

    return (
        <div className="news-feed">
            <div className="news-feed-header">
                <h3>📰 Football News</h3>
                <div className="news-controls">
                    <button 
                        onClick={togglePlayPause}
                        className="play-pause-btn"
                        title={isPlaying ? 'Pause auto-advance' : 'Resume auto-advance'}
                    >
                        {isPlaying ? '⏸️' : '▶️'}
                    </button>
                    <span className="news-counter">
                        {currentIndex + 1} / {news.length}
                    </span>
                </div>
            </div>

            <div className="news-content">
                <div className="current-news">
                    {currentNews.image && (
                        <div className="news-image">
                            <img src={currentNews.image} alt={currentNews.title} />
                        </div>
                    )}
                    
                    <div className="news-details">
                        <h4 className="news-title">{currentNews.title}</h4>
                        <p className="news-summary">{currentNews.summary}</p>
                        
                        <div className="news-meta">
                            <span className="news-source">{currentNews.source}</span>
                            <span className="news-time">
                                {formatTimeAgo(currentNews.published_at)}
                            </span>
                        </div>
                        
                        {currentNews.url && (
                            <a 
                                href={currentNews.url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="read-more-btn"
                            >
                                Read More →
                            </a>
                        )}
                    </div>
                </div>

                <div className="news-navigation">
                    <button 
                        onClick={() => handleNewsNavigation('prev')}
                        className="nav-btn prev-btn"
                        title="Previous news"
                    >
                        ←
                    </button>
                    <button 
                        onClick={() => handleNewsNavigation('next')}
                        className="nav-btn next-btn"
                        title="Next news"
                    >
                        →
                    </button>
                </div>

                <div className="news-indicators">
                    {news.slice(0, 5).map((_, index) => (
                        <button
                            key={index}
                            onClick={() => jumpToNews(index)}
                            className={`indicator ${index === currentIndex ? 'active' : ''}`}
                            title={`Jump to news ${index + 1}`}
                        />
                    ))}
                    {news.length > 5 && (
                        <span className="more-indicator">+{news.length - 5}</span>
                    )}
                </div>
            </div>

            <div className="news-preview">
                <h5>Upcoming News</h5>
                <div className="preview-list">
                    {newsListRef.current.getUpcoming(3).map((item, index) => (
                        <div key={index} className="preview-item">
                            <span className="preview-title">{item.title}</span>
                            <span className="preview-time">
                                {formatTimeAgo(item.published_at)}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default NewsFeed;
