import React, { useState, useEffect, useMemo } from 'react';
import { FaTrash, FaDownload, FaPlay, FaFilm, FaTimes } from 'react-icons/fa';
import { io } from 'socket.io-client';
import { API_BASE_URL } from '../config';

// Clip timestamps come from the backend as "YYYY-MM-DD HH-MM-SS"
function parseTimestamp(timestamp) {
    const [date = '', time = ''] = timestamp.split(' ');
    return { date, time: time.replace(/-/g, ':') };
}

function formatDateHeading(dateStr) {
    const [y, m, d] = dateStr.split('-').map(Number);
    if (!y || !m || !d) return dateStr;
    const date = new Date(y, m - 1, d);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diffDays = Math.round((today - date) / 86400000);
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    return date.toLocaleDateString(undefined, {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: date.getFullYear() === today.getFullYear() ? undefined : 'numeric'
    });
}

// Group clips by date (newest date first), clips within a date newest first
function groupByDate(clips) {
    const groups = {};
    clips.forEach((clip) => {
        const { date, time } = parseTimestamp(clip.timestamp);
        (groups[date] = groups[date] || []).push({ ...clip, time });
    });
    return Object.entries(groups)
        .sort(([a], [b]) => b.localeCompare(a))
        .map(([date, items]) => [date, items.sort((a, b) => b.time.localeCompare(a.time))]);
}

function Modal({ onClose, className = '', children }) {
    useEffect(() => {
        const onKey = (e) => e.key === 'Escape' && onClose();
        document.addEventListener('keydown', onKey);
        const prevOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        return () => {
            document.removeEventListener('keydown', onKey);
            document.body.style.overflow = prevOverflow;
        };
    }, [onClose]);

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div
                className={`modal ${className}`}
                role="dialog"
                aria-modal="true"
                onClick={(e) => e.stopPropagation()}
            >
                {children}
            </div>
        </div>
    );
}

export default function ClipsList({ notify = () => {} }) {
    const [clips, setClips] = useState([]);
    const [loading, setLoading] = useState(true);
    const [playing, setPlaying] = useState(null);   // clip being played
    const [confirming, setConfirming] = useState(null); // clip pending deletion

    useEffect(() => {
        fetch(`${API_BASE_URL}/api/clips`)
            .then((res) => res.json())
            .then(setClips)
            .catch((error) => {
                console.error('Error fetching clips:', error);
                notify('Could not load recorded clips', 'error');
            })
            .finally(() => setLoading(false));

        // Real-time updates when a new clip is recorded
        const socket = io(API_BASE_URL || undefined); // undefined = same origin
        socket.on('new_clip', (newClip) => {
            setClips((prev) =>
                prev.some((c) => c.video_filename === newClip.video_filename) ? prev : [newClip, ...prev]
            );
        });
        return () => socket.disconnect();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const grouped = useMemo(() => groupByDate(clips), [clips]);

    const handleDelete = async (clip) => {
        setConfirming(null);
        try {
            const res = await fetch(`${API_BASE_URL}/api/delete_clip/${clip.video_filename}`, { method: 'DELETE' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            setClips((prev) => prev.filter((c) => c.video_filename !== clip.video_filename));
            if (playing && playing.video_filename === clip.video_filename) setPlaying(null);
            notify('Clip deleted');
        } catch (err) {
            notify('Failed to delete clip', 'error');
        }
    };

    const downloadUrl = (clip) => `${API_BASE_URL}/api/download_clip/${clip.video_filename}`;

    return (
        <section className="card">
            <div className="card-header">
                <h2>Recorded clips</h2>
                {clips.length > 0 && <span className="clip-count">{clips.length}</span>}
            </div>

            <div className="card-body">
                {loading && <div className="empty"><div className="spinner" style={{ margin: '0 auto' }} /></div>}

                {!loading && grouped.length === 0 && (
                    <div className="empty">
                        <FaFilm />
                        <div>No clips recorded yet</div>
                        <div className="muted">Arm the camera to record when motion is detected.</div>
                    </div>
                )}

                {grouped.map(([date, items]) => (
                    <div key={date} className="date-group">
                        <h3 className="date-header">
                            <span>{formatDateHeading(date)}</span>
                            <span>{items.length}</span>
                        </h3>
                        <div className="clip-grid">
                            {items.map((clip) => (
                                <div key={clip.video_filename} className="clip">
                                    <button
                                        className="clip-thumb"
                                        onClick={() => setPlaying(clip)}
                                        aria-label={`Play clip from ${clip.time}`}
                                    >
                                        <img
                                            src={`${API_BASE_URL}/api/image/${clip.image_filename}`}
                                            alt=""
                                            loading="lazy"
                                        />
                                        <span className="play"><FaPlay /></span>
                                    </button>
                                    <div className="clip-meta">
                                        <span className="clip-time">{clip.time}</span>
                                        <div className="clip-actions">
                                            <a
                                                className="icon-btn"
                                                href={downloadUrl(clip)}
                                                download={clip.video_filename}
                                                title="Download"
                                                aria-label="Download clip"
                                            >
                                                <FaDownload size={14} />
                                            </a>
                                            <button
                                                className="icon-btn danger"
                                                onClick={() => setConfirming(clip)}
                                                title="Delete"
                                                aria-label="Delete clip"
                                            >
                                                <FaTrash size={13} />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>

            {playing && (
                <Modal onClose={() => setPlaying(null)}>
                    <div className="card-header">
                        <h2>{formatDateHeading(parseTimestamp(playing.timestamp).date)} · {playing.time}</h2>
                        <button className="icon-btn" onClick={() => setPlaying(null)} aria-label="Close">
                            <FaTimes />
                        </button>
                    </div>
                    <video
                        key={playing.video_filename}
                        controls
                        autoPlay
                        playsInline
                        poster={`${API_BASE_URL}/api/image/${playing.image_filename}`}
                        src={`${API_BASE_URL}/api/video/${playing.video_filename}`}
                    >
                        Your browser does not support the video tag.
                    </video>
                    <div className="modal-footer">
                        <a className="btn btn-ghost" href={downloadUrl(playing)} download={playing.video_filename}>
                            <FaDownload size={14} /> Download
                        </a>
                        <button className="btn btn-ghost" onClick={() => { setConfirming(playing); setPlaying(null); }}>
                            <FaTrash size={13} /> Delete
                        </button>
                    </div>
                </Modal>
            )}

            {confirming && (
                <Modal className="small" onClose={() => setConfirming(null)}>
                    <div className="modal-text">
                        <h3>Delete this clip?</h3>
                        <p>
                            {formatDateHeading(parseTimestamp(confirming.timestamp).date)} at{' '}
                            {parseTimestamp(confirming.timestamp).time}. This can't be undone.
                        </p>
                    </div>
                    <div className="modal-footer">
                        <button className="btn btn-ghost" onClick={() => setConfirming(null)}>Cancel</button>
                        <button className="btn btn-danger" onClick={() => handleDelete(confirming)}>Delete</button>
                    </div>
                </Modal>
            )}
        </section>
    );
}
