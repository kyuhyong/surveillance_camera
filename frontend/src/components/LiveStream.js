import React, { useCallback, useEffect, useRef, useState } from 'react';
import { FaExpand, FaRedo } from 'react-icons/fa';
import { API_BASE_URL } from '../config';

// Reconnect the MJPEG stream periodically and on errors, so a dropped
// connection (Wi-Fi blip, server restart, sleeping tab) doesn't leave the
// live view frozen forever.
const RECONNECT_DELAY_MS = 3000;
const REFRESH_INTERVAL_MS = 30 * 60 * 1000; // force a fresh connection every 30 min

const canFullscreen = typeof document !== 'undefined' &&
    !!(document.fullscreenEnabled || document.webkitFullscreenEnabled);

export default function LiveStream() {
    const [streamKey, setStreamKey] = useState(() => Date.now());
    const [offline, setOffline] = useState(false);
    const retryTimer = useRef(null);
    const containerRef = useRef(null);

    const reconnect = useCallback(() => {
        clearTimeout(retryTimer.current);
        setStreamKey(Date.now());
    }, []);

    const handleError = () => {
        setOffline(true);
        clearTimeout(retryTimer.current);
        retryTimer.current = setTimeout(reconnect, RECONNECT_DELAY_MS);
    };

    const toggleFullscreen = () => {
        const el = containerRef.current;
        if (!el) return;
        if (document.fullscreenElement || document.webkitFullscreenElement) {
            (document.exitFullscreen || document.webkitExitFullscreen).call(document);
        } else {
            (el.requestFullscreen || el.webkitRequestFullscreen).call(el);
        }
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
        <section className="card">
            <div className="stream" ref={containerRef}>
                <img
                    key={streamKey}
                    src={`${API_BASE_URL}/api/video_stream?t=${streamKey}`}
                    alt="Live camera stream"
                    onLoad={() => setOffline(false)}
                    onError={handleError}
                    style={offline ? { visibility: 'hidden' } : undefined}
                />

                {offline && (
                    <div className="stream-overlay">
                        <div className="spinner" />
                        Reconnecting to camera…
                    </div>
                )}

                <div className={`stream-badge ${offline ? 'offline' : ''}`}>
                    <span className="dot" />
                    {offline ? 'OFFLINE' : 'LIVE'}
                </div>

                <div className="stream-tools">
                    <button
                        className="icon-btn"
                        onClick={reconnect}
                        title="Reload stream"
                        aria-label="Reload stream"
                    >
                        <FaRedo size={14} />
                    </button>
                    {canFullscreen && (
                        <button
                            className="icon-btn"
                            onClick={toggleFullscreen}
                            title="Fullscreen"
                            aria-label="Fullscreen"
                        >
                            <FaExpand size={15} />
                        </button>
                    )}
                </div>
            </div>
        </section>
    );
}
