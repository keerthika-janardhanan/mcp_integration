# Execute Following Command in terminal
python -m venv .venv
# On Windows use
.venv\Scripts\activate
pip install -r requirements.txt
# In root folder's terminal run:
npm install
npm install @playwright/test
npx playwright install
 
# In frontend folder's terminal run:
npm install
 
# To run the application
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8001 --reload

# in a separate terminal
python -m venv .venv
cd frontend
npm run dev