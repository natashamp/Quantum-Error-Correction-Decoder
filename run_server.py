"""Launch the QEC decoder visualization server."""

import webbrowser
from server.app import app

if __name__ == "__main__":
    url = "http://localhost:5000"
    print(f"Starting QEC Decoder Visualization at {url}")
    webbrowser.open(url)
    app.run(host="localhost", port=5000, debug=False)
