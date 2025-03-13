### **Run Locally**

To run the project locally, follow these steps:

1. **Clone the repository**:
    
    ```bash
    git clone https://github.com/Grace0413/tech_assessment.git
    cd tech_assessment
    
    ```
    
2. **Create a virtual environment and activate it**:
    
    ```bash
    python -m venv venv
    source venv/bin/activate  # On macOS/Linux
    venv\Scripts\activate  # On Windows
    
    ```
    
3. **Install dependencies**:
    
    ```bash
    pip install -r requirements.txt
    
    ```
    
4. **Add your OpenAI API key**:
    - Create a `.env` file in the root directory.
    - Add the following line:
        
        ```
        OPENAI_API_KEY=your_openai_api_key_here
        
        ```
5. **Open app.py and update the API_URL variable**:
    ```
    # Change this line in app.py
    API_URL = "http://127.0.0.1:8000"  # Use local FastAPI server
    
    ```
        
5. **Run the FastAPI backend**:
    
    ```bash
    uvicorn main:app --reload
    
    ```
    
6. **Start the Streamlit frontend**:
    ```bash
    streamlit run app.py
    
    ```
