import React, { useState, useEffect } from 'react';
import { FaTrash } from 'react-icons/fa';  // Import trash icon
import { FaDownload } from 'react-icons/fa';  // Import download icon
import { io } from 'socket.io-client';

export default function ClipsList() {
    const [clips, setClips] = useState([]);
    const [selectedVideo, setSelectedVideo] = useState(null);  // Video selected for playback

    useEffect(() => {
        fetch(`${process.env.REACT_APP_API_BASE_URL}/api/clips`)
            .then(res => res.json())
            .then(setClips)
            .catch(error => console.error('Error fetching clips:', error));
        // Connect to WebSocket for real-time updates
        const socket = io(process.env.REACT_APP_API_BASE_URL);
        socket.on('new_clip', (newClip) => {
            setClips((prevClips) => [newClip, ...prevClips]); // Add new clips at the top
        });

        return () => socket.disconnect();
    }, []);

    const handleDelete = async (filename) => {
        await fetch(`${process.env.REACT_APP_API_BASE_URL}/api/delete_clip/${filename}`, { method: 'DELETE' });
        setClips(clips.filter(clip => clip.video_filename !== filename));
    };
    // Download Handler
    const handleDownload = (filename) => {
        const downloadUrl = `${process.env.REACT_APP_API_BASE_URL}/api/download_clip/${filename}`;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename; // Ensures the proper filename is set
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };
    const handleImageClick = (videoFilename) => {
        // Toggle video playback when image is clicked
        setSelectedVideo(selectedVideo === videoFilename ? null : videoFilename);
    };

    return (
        <div style={styles.clipsContainer}>
            <h2>Recorded Clips</h2>
            {clips.length === 0 && <p>No clips available</p>}

            {clips.map((clip, index) => (
                <div key={index} style={styles.clipContainer}>
                    {/* Timestamp Display */}
                    <div style={styles.infoContainer}>
                        <p style={styles.timestamp}>{clip.timestamp}</p>
                    </div>
                    {/* Thumbnail Image */}
                    <img
                        src={`${process.env.REACT_APP_API_BASE_URL}/api/image/${clip.image_filename}`}
                        alt="Captured Image"
                        style={styles.imagePreview}
                        onClick={() => handleImageClick(clip.video_filename)}
                        //onClick={() => setSelectedVideo(clip.video_filename)}  // Click image to play video
                    />
                    {/* Playable Video (if selected) */}
                    {selectedVideo === clip.video_filename && (
                        <video controls width="320" height="240" autoPlay>
                            <source
                                src={`${process.env.REACT_APP_API_BASE_URL}/api/video/${clip.video_filename}`}
                                type="video/mp4"
                            />
                            Your browser does not support the video tag.
                        </video>
                    )}
                    {/* Download Button with Icon */}
                    <button
                        style={styles.downloadButton}
                        onClick={() => handleDownload(clip.video_filename)}
                        title="Download this clip"
                    >
                        <FaDownload style={styles.icon} />
                    </button>

                    {/* Smaller Delete Button with Trash Icon */}
                    <button 
                        style={styles.deleteButton} 
                        onClick={() => handleDelete(clip.video_filename)}
                        title="Delete this clip"
                    >
                        <FaTrash />
                    </button>
                </div>
            ))}
        </div>
    );
}

// Inline CSS for improved layout
const styles = {
    clipsContainer: {
        maxHeight: '60vh',       // Limits the height of ClipsList to enable scrolling
        overflowY: 'auto',       // Enables scroll only for ClipsList
        padding: '10px'
    },
    clipContainer: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '10px',
        border: '1px solid #ccc',
        padding: '10px',
        borderRadius: '10px'
    },
    infoContainer: {
        display: 'flex',
        flexDirection: 'column',
        marginRight: '10px'
    },
    timestamp: {
        fontWeight: 'bold',
        color: '#4CAF50',
        marginBottom: '5px'
    },
    imagePreview: {
        width: '100px',
        height: 'auto',
        cursor: 'pointer',
        borderRadius: '5px'
    },
    deleteButton: {
        backgroundColor: '#c91414',
        color: '#fff',
        border: 'none',
        padding: '8px 10px',
        borderRadius: '30%',     // Circular rect button
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        width: '40px',           // Small size
        height: '40px',
        transition: 'background-color 0.2s ease'
    },
    deleteButtonHover: {
        backgroundColor: '#d32f2f' // Darker red on hover
    },
    downloadButton: {
        backgroundColor: '#4CAF50',
        color: '#fff',
        border: 'none',
        padding: '8px 10px',
        borderRadius: '30%',
        width: '40px',
        height: '40px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        transition: 'background-color 0.2s ease'
    },
    downloadButtonHover: {
        backgroundColor: '#45a049'
    },
    icon: {
        fontSize: '18px'
    }
};
