import React, { useCallback, useEffect, useRef, useState } from 'react';
import { API_BASE_URL } from '../config';

// Reconnect the MJPEG stream periodically and on errors, so a dropped
// connection (Wi-Fi blip, server restart, sleeping tab) doesn't leave the
// live view frozen forever.
const RECONNECT_DELAY_MS = 3000;
const REFRESH_INTERVAL_MS = 30 * 60 * 1000; // force a fresh connection every 30 min

export default function LiveStream() {
    const [streamKey, setStreamKey] = useState(() => Date.now());
    const retryTimer = useRef(null);

    const reconnect = useCallback(() => {
        clearTimeout(retryTimer.current);
        setStreamKey(Date.now());
    }, []);

    const handleError = () => {
        clearTimeout(retryTimer.current);
        retryTimer.current = setTimeout(reconnect, RECONNECT_DELAY_MS);
    };

    useEffect(() => {
        const onVisible = () => {
            if (document.visibilityState === 'visible') reconnect();
        };
        document.addEventListener('visibilitychange', onVisible);
        window.addEventListener('online', reconnect);
        const refresh = setInterval(reconnect, REFRESH_INTERVAL_MS);
        return () => {
            document.removeEventListener('visibilitychange', onVisible);
            window.removeEventListener('online', reconnect);
            clearInterval(refresh);
            clearTimeout(retryTimer.current);
        };
    }, [reconnect]);

    return (
        <div style={styles.container}>
            {/*<h3>Live Video Stream</h3>*/}
            <img
                key={streamKey}
                src={`${API_BASE_URL}/api/video_stream?t=${streamKey}`}
                alt="Live Stream"
                onError={handleError}
                style={{ width: '100%', height: 'auto', border: '2px solid #4CAF50' }}
            />
        </div>
    );
}
const styles = {
    container: {
        backgroundColor: '#d1d1d1', // Light grey background for the header
        padding: '1px',
        alignItems: 'center',
        margin: '1px 0'
    }
};
