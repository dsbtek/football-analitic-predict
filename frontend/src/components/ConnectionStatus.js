import React from 'react';
import './Auth.css';

const ConnectionStatus = ({ status, lastUpdate }) => {
    const getStatusText = () => {
        switch (status) {
            case 'connected':
                return 'Live Updates Active';
            case 'connecting':
                return 'Connecting...';
            case 'disconnected':
                return 'Offline';
            default:
                return 'Unknown';
        }
    };

    const getStatusClass = () => {
        switch (status) {
            case 'connected':
                return 'connected';
            case 'connecting':
                return 'connecting';
            case 'disconnected':
                return 'disconnected';
            default:
                return 'disconnected';
        }
    };

    const formatLastUpdate = () => {
        if (!lastUpdate) return '';
        
        const now = new Date();
        const updateTime = new Date(lastUpdate);
        const diffMs = now - updateTime;
        const diffSeconds = Math.floor(diffMs / 1000);
        const diffMinutes = Math.floor(diffSeconds / 60);
        
        if (diffSeconds < 60) {
            return `Updated ${diffSeconds}s ago`;
        } else if (diffMinutes < 60) {
            return `Updated ${diffMinutes}m ago`;
        } else {
            return `Updated ${updateTime.toLocaleTimeString()}`;
        }
    };

    return (
        <div className="connection-status">
            <div className={`connection-indicator ${getStatusClass()}`}></div>
            <span className="connection-text">
                {getStatusText()}
                {status === 'connected' && lastUpdate && (
                    <span className="last-update"> • {formatLastUpdate()}</span>
                )}
            </span>
        </div>
    );
};

export default ConnectionStatus;
