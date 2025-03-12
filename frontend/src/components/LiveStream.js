import React from 'react';

export default function LiveStream() {
    return (
        <div style={styles.container}>
            {/*<h3>Live Video Stream</h3>*/}
            <img
                src={`${process.env.REACT_APP_API_BASE_URL}/api/video_stream`}
                alt="Live Stream"
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