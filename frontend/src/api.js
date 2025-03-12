const API = {
    login: (credentials) =>
        fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(credentials),
        }).then(res => res.json()),

    getClips: () =>
        fetch('/api/clips').then(res => res.json()),
};

export default API;
