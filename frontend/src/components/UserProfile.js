import React, { useState, useRef, useEffect } from 'react';
import './Auth.css';

const UserProfile = ({ user, onLogout }) => {
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const dropdownRef = useRef(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setDropdownOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    const handleLogout = () => {
        // Clear tokens from localStorage
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        
        // Call parent logout handler
        onLogout();
        setDropdownOpen(false);
    };

    const getInitials = (name) => {
        return name
            .split(' ')
            .map(word => word.charAt(0))
            .join('')
            .toUpperCase()
            .slice(0, 2);
    };

    return (
        <div className="user-profile" ref={dropdownRef}>
            <button
                className="user-profile-button"
                onClick={() => setDropdownOpen(!dropdownOpen)}
            >
                <span className="user-avatar">
                    {getInitials(user.full_name)}
                </span>
                <span className="user-name">
                    {user.full_name.split(' ')[0]}
                </span>
                <span className="dropdown-arrow">
                    {dropdownOpen ? '▲' : '▼'}
                </span>
            </button>

            {dropdownOpen && (
                <div className="user-dropdown">
                    <div className="user-dropdown-item user-info">
                        <div>
                            <strong>{user.full_name}</strong>
                            <div style={{ fontSize: '0.8rem', color: '#666' }}>
                                {user.email}
                            </div>
                        </div>
                    </div>
                    
                    <button
                        className="user-dropdown-item"
                        onClick={() => {
                            setDropdownOpen(false);
                            // Add profile management functionality here
                            alert('Profile management coming soon!');
                        }}
                    >
                        👤 Manage Profile
                    </button>
                    
                    <button
                        className="user-dropdown-item"
                        onClick={() => {
                            setDropdownOpen(false);
                            // Add settings functionality here
                            alert('Settings coming soon!');
                        }}
                    >
                        ⚙️ Settings
                    </button>
                    
                    <button
                        className="user-dropdown-item"
                        onClick={handleLogout}
                    >
                        🚪 Logout
                    </button>
                </div>
            )}
        </div>
    );
};

export default UserProfile;
