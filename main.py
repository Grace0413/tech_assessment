from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import requests
from bs4 import BeautifulSoup
import re
from openai import OpenAI
import os
import time

from dotenv import load_dotenv

# Load .env file
# load_dotenv()
# api_key = os.getenv("OPENAI_API_KEY")

import streamlit as st
api_key = st.secrets["OPENAI_API_KEY"]

if not api_key:
    raise ValueError("❌ OpenAI API Key not found, please check the .env file!")

client = OpenAI()

# Initialize FastAPI
app = FastAPI()

# Connect to SQLite database
DB_FILE = "links.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            type TEXT,
            relevance_score REAL,
            keywords TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()  # Initialize database

# Pydantic models
class ScrapeRequest(BaseModel):
    url: str
    use_gpt: bool = False  # Whether to use GPT
    keywords: List[str]  # List of keywords

class LinkResponse(BaseModel):
    url: str
    type: str
    relevance_score: float
    keywords: List[str]

def save_links(links):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for url, link_type, relevance_score, keywords in links:
        cursor.execute("""
            INSERT INTO links (url, type, relevance_score, keywords)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                type = excluded.type,
                relevance_score = excluded.relevance_score,
                keywords = excluded.keywords
        """, (url, link_type, relevance_score, keywords))
    conn.commit()
    conn.close()

def scrape_webpage(url):
    """Fetches and extracts readable text from a webpage."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}  # Avoid getting blocked
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()  # Raise error for bad status codes

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove unnecessary tags (script, style)
        for tag in soup(["script", "style"]):
            tag.extract()

        # Extract and clean text
        text = soup.get_text(separator=" ", strip=True)
        return text[:5000]  # Limit to 5000 chars (to avoid GPT token limits)

    except Exception as e:
        print(f"⚠️ Webpage scraping failed for {url}: {e}")
        return None  # Return None if scraping fails

def analyze_with_gpt(url, keyword):
    """Analyzes a URL's relevance to a keyword using GPT, with optional webpage content."""
    webpage_text = scrape_webpage(url)

    prompt = f"""Analyze the relevance of the following webpage to the keyword: "{keyword}". 

If webpage content is available, use it to determine the main topic and its connection to the keyword. Otherwise, base the relevance on the URL structure.

Scoring guidelines:
- 0.0: Completely unrelated
- 0.2: Slightly related (keyword appears but seems incidental)
- 0.5: Somewhat relevant (keyword appears, but topic is broader)
- 0.8: Highly relevant (webpage strongly focuses on keyword)
- 1.0: Directly relevant (keyword is the main subject)

Return **only a single floating-point number** between 0 and 1. No explanations.

URL: {url}
"""

    if webpage_text:
        print(f"📄 Webpage Content: {webpage_text[:100]}...")
        prompt += f"\nWebpage Content:\n{webpage_text}"

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message.content.strip()
        print(f"📝 GPT Output: {answer}\n")

        # Ensure GPT returns a valid score
        try:
            score = float(answer)
            if 0.0 <= score <= 1.0:
                return score
            else:
                print(f"⚠️ Invalid GPT output (out of range): {answer}")
        except ValueError:
            print(f"⚠️ Invalid GPT output (not a number): {answer}")

        return 0.3  # Default fallback score

    except Exception as e:
        print(f"❌ GPT processing failed: {e}")
        return 0.3  # Return fallback score if GPT call fails
    
    
def scrape_links(url, use_gpt, keywords):
    print("Keywords:", keywords)
    """ Scrape all links from a webpage and filter high-value links """
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")

    soup = BeautifulSoup(response.text, "html.parser")
    links = soup.find_all("a", href=True)

    extracted_links = []
    total_links = len(links)
    for i, link in enumerate(links):
        href = link["href"]
        full_url = requests.compat.urljoin(url, href)
        
        # Match user-provided keywords
        keywords_found = [kw for kw in keywords if kw.lower() in href.lower()]

        relevance_score = 1.0 if keywords_found else 0.3

        # Identify type
        link_type = "document" if href.endswith((".pdf", ".xls", ".xlsx", ".doc", ".docx")) else "webpage"

        extracted_links.append((full_url, link_type, relevance_score, ",".join(keywords_found)))

        print(f"✅ Processed {i+1}/{total_links} links", ",".join(keywords_found), "score: ", relevance_score)
    
    return extracted_links

@app.post("/scrape")
def scrape(request: ScrapeRequest):
    links = scrape_links(request.url, request.use_gpt, request.keywords)
    save_links(links)
    return {"message": "Scraping completed", "scraped_links": len(links)}

@app.get("/links", response_model=List[LinkResponse])
def get_links(
    keyword: Optional[str] = Query(None),
    min_score: float = Query(0.0),
    use_gpt: bool = Query(False)
):
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    query = "SELECT url, type, relevance_score, keywords FROM links WHERE relevance_score >= ?"
    params = [min_score]

    if keyword:
        query += " AND keywords LIKE ?"
        params.append(f"%{keyword}%")

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    filtered_results = []
    for row in results:
        url, link_type, score, stored_keywords = row
        if not use_gpt: 
            filtered_results.append({
                "url": url,
                "type": link_type,
                "relevance_score": score,
                "keywords": stored_keywords.split(",")
            })
        else:
            gpt_score = analyze_with_gpt(url, keyword)
            filtered_results.append({
                "url": url,
                "type": link_type,
                "relevance_score": gpt_score,
                "keywords": stored_keywords.split(",")
            })

    return filtered_results
