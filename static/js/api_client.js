/**
 * Thin fetch wrapper for the QEC decoder API.
 */
async function postAPI(endpoint, data = {}) {
    const resp = await fetch(`/api/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    return resp.json();
}
