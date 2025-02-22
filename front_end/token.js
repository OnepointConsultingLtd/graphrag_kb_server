export default function getToken() {
    const main = document.querySelector('[x-ref="main"]');
    if (main) {
        return Alpine.$data(main).token;
    }
    return null;
}

export function setToken(token) {
    const main = document.querySelector('[x-ref="main"]');
    if(main && token) {
        Alpine.$data(main).token = token
    }
}