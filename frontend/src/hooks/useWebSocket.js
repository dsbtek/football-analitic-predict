import { useState, useEffect, useRef, useCallback } from 'react';

const useWebSocket = (url, token = null) => {
    const [socket, setSocket] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState('disconnected');
    const [lastMessage, setLastMessage] = useState(null);
    const [error, setError] = useState(null);
    const reconnectTimeoutRef = useRef(null);
    const reconnectAttempts = useRef(0);
    const maxReconnectAttempts = 5;
    const reconnectInterval = 3000; // 3 seconds

    const connect = useCallback(() => {
        try {
            setConnectionStatus('connecting');
            setError(null);

            // Build WebSocket URL with token if provided
            const wsUrl = token ? `${url}?token=${token}` : url;
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('WebSocket connected');
                setConnectionStatus('connected');
                setSocket(ws);
                reconnectAttempts.current = 0;
                
                // Send ping to keep connection alive
                const pingInterval = setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ type: 'ping' }));
                    } else {
                        clearInterval(pingInterval);
                    }
                }, 30000); // Ping every 30 seconds
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    setLastMessage(message);
                } catch (err) {
                    console.error('Error parsing WebSocket message:', err);
                }
            };

            ws.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                setConnectionStatus('disconnected');
                setSocket(null);

                // Attempt to reconnect if not a manual close
                if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
                    reconnectAttempts.current += 1;
                    console.log(`Attempting to reconnect... (${reconnectAttempts.current}/${maxReconnectAttempts})`);
                    
                    reconnectTimeoutRef.current = setTimeout(() => {
                        connect();
                    }, reconnectInterval);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                setError('WebSocket connection error');
                setConnectionStatus('disconnected');
            };

        } catch (err) {
            console.error('Error creating WebSocket:', err);
            setError('Failed to create WebSocket connection');
            setConnectionStatus('disconnected');
        }
    }, [url, token]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        
        if (socket) {
            socket.close(1000, 'Manual disconnect');
        }
        
        setSocket(null);
        setConnectionStatus('disconnected');
        reconnectAttempts.current = 0;
    }, [socket]);

    const sendMessage = useCallback((message) => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(message));
            return true;
        } else {
            console.warn('WebSocket is not connected');
            return false;
        }
    }, [socket]);

    // Connect on mount and when dependencies change
    useEffect(() => {
        connect();
        
        return () => {
            disconnect();
        };
    }, [connect, disconnect]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
        };
    }, []);

    return {
        socket,
        connectionStatus,
        lastMessage,
        error,
        sendMessage,
        connect,
        disconnect
    };
};

export default useWebSocket;
