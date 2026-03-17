import webbrowser

def open_url(url: str) -> dict:
    webbrowser.open(url)
    return {
        "success": True,
        "message": f"Opened URL: {url}",
    }