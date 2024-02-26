## How to use this repo

1. Install Chainlit, Langchain, openai

   ```bash
   pip install chainlit
   pip install langchain
   pip install openai
   ```

2. Clone the repo, then add a `.env` file that includes

   ```bash
   OPENAI_API_KEY=
   CHAINLIT_AUTH_SECRET=
   ```

   You can generate `CHAINLIT_AUTH_SECRET` using `chainlit create-secret`.

3. Run the application in its directory (contains `app.py`)

   ```bash
   chainlit run app.py -w
   ```

   Your chatbot should now be accessible at [http://localhost:8000](http://localhost:8000/).
