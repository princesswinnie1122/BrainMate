# BrainMate

<img src="./public/avatar.png" alt="drawing" width="300"/>

## About

[簡報連結](https://www.canva.com/design/DAF-GqnHNtE/s6xV3q02vMmpF5eYIRLlPQ/view?utm_content=DAF-GqnHNtE&utm_campaign=designshare&utm_medium=link&utm_source=editor)

1. **繁體中文辨識**：用戶可以直接拖曳上傳圖片，接著輸入問題，BrainMate可以非常迅速的辨識題目並回答，不論是辨識能力還是速度都優於ChatGPT 4。
2. **根據用戶需求調用知識**：BrainMate會根據用戶的選項，從資料庫調用相對應的知識，接著帶入提問搜尋最貼近的內容；而且只要有新教材都可以新增置資料庫。
3. **保留歷史對話**：用戶重新登入BrainMate並不會流失資料，過去的對話紀錄都會保留，還能根據記憶再次延續對話。
4. **PDF 閱讀器**：用戶拖曳上傳PDF檔案後，能展開彈性側邊欄，在閱讀PDF的同時向AI提問，提升學習效率。
5. **任務自動化**：其中一項功能是根據AI生成的列表在側邊欄設置任務清單，並自動化執行所有問答，一目瞭然。



## How to use this repo

1. Clone this repo

   ```bash
   git clone https://github.com/princesswinnie1122/BrainMate.git
   ```

2. Add an `.env` file that includes: 

   ```bash
   OPENAI_API_KEY=
   CHAINLIT_AUTH_SECRET=
   LITERAL_API_KEY=
   GOOGLE_APPLICATION_CREDENTIALS=/chainlit-gcp/vision.json
   ```

   - `OPENAI_API_KEY`：get an API key [here](https://platform.openai.com/docs/overview)
   - `CHAINLIT_AUTH_SECRET`：generate with `chainlit create-secret`
   - `LITERAL_API_KEY`：follow [this instruction](https://docs.chainlit.io/data-persistence/overview)

3. Modify the <names> in the below commands yourself.

### Run locally

1. Install dependencies

   ```bash
   pip install --no-cache-dir -r requirements.txt
   ```

2. Run the app in root directory (contains `app.py`)

   ```bash
   chainlit run app.py -w
   ```

   Your app should now be accessible at [http://localhost:8000](http://localhost:8000/).

### Run with Docker

1. Put all folders and files in another folder (container)

2. Build docker image (in the container)

   ```bash
   docker build -t brainmate .
   ```

3. Test running it locally

   ```bash
   docker run -p 8000:8000 `
     --env-file .env `
     --name chainlit-gcp-container `
     brainmate
   ```

   Your app should now be accessible at [http://localhost:8000](http://localhost:8000/).
