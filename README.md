# XBanka Backend

Backend service for **XBanka**. Built with [FastAPI](https://fastapi.tiangolo.com/) for performance and scalability.
<!-- a fintech application that enables users to manage accounts, transfer funds, and track transactions securely.   -->



## 🛠️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/xbanka-backend.git
cd xbanka-backend
```

### 2. Create & activate a virtual environment
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

### 3. Install dependencies
pip install -r requirements.txt

## ▶️ Running the Application

```bash
uvicorn app.main:app --reload
```
- API root → http://127.0.0.1:8000
- Swagger docs → http://127.0.0.1:8000/docs
- ReDoc → http://127.0.0.1:8000/redoc


## 🧪 Testing
Run tests with:

```bash
pytest
```