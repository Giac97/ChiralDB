import requests

def get_metadata_from_doi(doi_url):
    # Remove the 'https://doi.org/' prefix if it exists
    doi = doi_url.replace("https://doi.org/", "").strip()
    url = f"https://api.crossref.org/works/{doi}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Extract relevant fields
            title = data["message"].get("title", ["Unknown Title"])[0]
            authors = [
                f"{author.get('given', '')} {author.get('family', '')}"
                for author in data["message"].get("author", [])
            ]
            publication_year = data["message"].get("published-print", {}).get("date-parts", [[None]])[0][0]
            return {"title": title, "authors": authors, "year": publication_year}
        else:
            return {"title": "Unknown Title", "authors": [], "year": "Unknown Year"}
    except Exception as e:
        return {"title": "Error Fetching Data", "authors": [], "year": "N/A"}
    
def get_bibtex_from_doi(doi):
    url = f"https://doi.org/{doi}"
    headers = {"Accept": "application/x-bibtex"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching BibTeX for DOI {doi}: {e}")
        return None