// Base URL of the backend API.
// - Production build (served by Flask on :5000): '' -> same address the page was
//   loaded from, so it works from any device on the network.
// - `npm start` dev server on :3000: talk to the local Flask on :5000.
// - Set REACT_APP_API_BASE_URL in frontend/.env to override.
export const API_BASE_URL =
    process.env.REACT_APP_API_BASE_URL ||
    (process.env.NODE_ENV === 'development' ? 'http://localhost:5000' : '');
