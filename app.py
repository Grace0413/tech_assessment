import streamlit as st
import requests
import pandas as pd
import time

# API_URL = "http://127.0.0.1:8000"  # FastAPI server address
API_URL = "https://tech-assessment-1emd.onrender.com" 


st.title("📊 High-Value Link Scraper")
st.write("Enter a webpage URL to scrape high-value links!")

# User input for the website URL
url = st.text_input("🔗 Enter URL:", "https://www.a2gov.org/")

# Initialize session state for keyword management
if "all_keywords" not in st.session_state:
    st.session_state.all_keywords = ["budget", "finance", "ACFR", "financial report", "contact"]

if "selected_keywords" not in st.session_state:
    st.session_state.selected_keywords = st.session_state.all_keywords[:]


# Allow users to select keywords
selected_keywords = st.multiselect(
    "📌 Select keywords for filtering (you can add new ones):",
    options=st.session_state.all_keywords,  
    default=st.session_state.selected_keywords
)

# Allow users to add new keywords
new_keyword = st.text_input("➕ Add new keyword (press Enter to add):")

if new_keyword:
    if new_keyword not in st.session_state.all_keywords:
        st.session_state.all_keywords.append(new_keyword)
        st.session_state.selected_keywords.append(new_keyword)
        st.rerun()  # Refresh UI immediately

# Detect removed keywords and trigger UI update
removed_keywords = set(st.session_state.selected_keywords) - set(selected_keywords)

if removed_keywords:
    st.session_state.all_keywords = selected_keywords[:]  # Sync keyword list
    st.session_state.selected_keywords = selected_keywords
    st.rerun()  # Refresh UI to reflect deletion immediately

# st.write("All Keywords:", st.session_state.all_keywords)
# st.write("Selected Keywords:", st.session_state.selected_keywords)

# Scrape button to trigger web scraping
if st.button("🚀 Start Scraping"):
    if url:
        payload = {
            "url": url,
            "use_gpt": False,
            "keywords": st.session_state.selected_keywords  # Ensure keywords are up to date
        }
        response = requests.post(f"{API_URL}/scrape", json=payload)
        if response.status_code == 200:
            st.success(f"✅ Scraping completed! {response.json()['scraped_links']} links found")
        else:
            st.error("❌ Scraping failed. Please check if the URL is valid!")

# Section to query stored high-value links
st.subheader("🔎 Search Stored High-Value Links")
keyword = st.text_input("📌 Filter out the link only with the keyword (optional)")
# Option to use GPT for intelligent filtering
use_gpt = st.checkbox("✨ Use GPT for intelligent scoring", value=True)
min_score = st.slider("💯 Minimum relevance score", 0.0, 1.0, 0.5)

if st.button("🔍 Search Data"):
    params = {"min_score": min_score, "use_gpt": use_gpt}
    if keyword:
        params["keyword"] = keyword

    response = requests.get(f"{API_URL}/links", params=params)
    
    if response.status_code == 200:
        links_data = response.json()

        if len(links_data) > 0:
            
            result_container = st.empty()  # Placeholder for updating UI dynamically

            total = len(links_data)
            processed_links = []

            for i, link in enumerate(links_data):
                # Simulate real-time processing of each link
                # Instead of sleeping, we could actually call GPT processing API here
                processed_links.append(link)  # Append processed link
                df = pd.DataFrame(processed_links)  # Update dataframe dynamically

                result_container.dataframe(df)  # Show updated table
                

        if links_data:
            st.success(f"✅ Found {len(links_data)} links!")
        else:
            st.warning("⚠️ No matching links found!")

    else:
        st.error("❌ Query failed!")
