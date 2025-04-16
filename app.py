from flask import Flask, request, render_template, redirect, url_for, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote
app = Flask(__name__)
AHMIA_SEARCH_URL = "https://ahmia.fi/search/"

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect(url_for("index"))
    
    # Fetch first batch of results (page 0)
    results = []
    page = 0
    try:
        # Dynamically get the full URL of the deployed app
        base_url = request.host_url  # This will give us the correct base URL for the deployed app
        
        # Use the correct base URL for the API request
        res = requests.get(f"{base_url}api/search?q={query}&page={page}")
        data = res.json()
        results = data.get("results", [])
    except requests.RequestException as e:
        return render_template("results.html", query=query, error=str(e), results=[])

    return render_template("results.html", query=query, results=results, error=None)

@app.route("/api/search", methods=["GET"])
def api_search():
    query = request.args.get("q", "").strip()
    page = int(request.args.get("page", 0))
    results_per_page = 20
    start = page * results_per_page
    max_pages = 500  # Maximum number of pages that can be fetched
    
    if page >= max_pages:
        return jsonify({"results": [], "error": "No more results."})
    
    # Get the User-Agent from the incoming request (client's request)
    user_agent = request.headers.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')

    headers = {
        "User-Agent": user_agent  # Use the User-Agent from the client
    }
    
    try:
        res = requests.get(
            AHMIA_SEARCH_URL,
            params={"q": query, "start": start},
            headers=headers
        )
        res.raise_for_status()
    except requests.RequestException as e:
        return jsonify({"error": str(e), "results": []})
    
    soup = BeautifulSoup(res.text, "html.parser")
    result_elements = soup.select(".result")
    results = []
    
    for item in result_elements:
        title_tag = item.find("a")
        snippet_tag = item.find("p")

        if title_tag:
            raw_href = title_tag["href"]
            parsed_url = urlparse(raw_href)
            query_params = parse_qs(parsed_url.query)
            real_url = query_params.get("redirect_url", [None])[0]
    
            if real_url and real_url.endswith(".onion/") or ".onion/" in real_url:
                result = {
                    "title": title_tag.text.strip(),
                    "link": unquote(real_url),
                    "snippet": snippet_tag.text.strip() if snippet_tag else ""
                }
                results.append(result)
    
    return jsonify({"results": results, "error": None})

if __name__ == "__main__":
    app.run(debug=False)
