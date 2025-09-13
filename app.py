# 引入所有必要的函式庫
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
# 【重要】完全遵循您指定的導入方式
from google import genai
from PIL import Image
from io import BytesIO
import os
import logging

# --- 設定基礎日誌，方便除錯 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 初始化 Flask 應用 ---
app = Flask(__name__)
CORS(app)

# --- 步驟 1: 設定 API 金鑰和模型 (雙模式) ---

# 【核心機制】
# 1. 先嘗試從 Render 的環境變數讀取金鑰 (部署時使用)
API_KEY = os.environ.get("GOOGLE_API_KEY")

# 2. 如果找不到環境變數 (代表我們在本地電腦上)，則使用下面寫死的金鑰
if not API_KEY:
    logging.warning("[本地測試模式] 未找到 GOOGLE_API_KEY 環境變數。")
    logging.warning("              將使用程式碼中指定的 API 金鑰進行測試。")
    # 【本地測試金鑰】請將您的金鑰放在這裡
    API_KEY = "AIzaSyC_2KYmB0OilTnxmTZVg3zhJAbwnMPVaSw" 
else:
    logging.info("[部署模式] 成功從環境變數讀取 GOOGLE_API_KEY。")

# 初始化 Client 的變數
client = None

# 檢查 API_KEY 是否有效，如果兩種方式都拿不到，就直接報錯
if not API_KEY:
    logging.error("致命錯誤：API 金鑰遺失。請設定環境變數或在程式碼中提供。")
else:
    try:
        # 【重要】使用您指定的 genai.Client() 進行初始化
        client = genai.Client(api_key=API_KEY)
        logging.info("Google AI Client 初始化成功。")
    except Exception as e:
        logging.error(f"初始化 Google AI Client 時發生致命錯誤: {e}", exc_info=True)

# 【重要】使用您指定的模型名稱
MODEL_NAME = "gemini-2.5-flash-image-preview"
logging.info(f"將使用模型: '{MODEL_NAME}'")


# --- 步驟 2: 建立您的「產品庫」和「風格標籤庫」 ---
CASES = {
    "white_case": {
        "name_for_prompt": "a modern white PC case with a glass side panel",
        "image_path": "static/AP202_PBA_WHITE.png" 
    },
    "black_case": {
        "name_for_prompt": "a minimalist black PC case with a vertical slatted front panel",
        "image_path": "static/pa401.png"
    }
}

TAG_FRAGMENTS = {
    # ... (此處省略標籤庫的詳細內容，請確保您的檔案中包含完整的 TAG_FRAGMENTS 字典) ...
    "scene_futuristic": "Place it in a futuristic, all-white room where the walls are covered with 3D geometric, crystalline panels. ",
    "scene_cyberpunk": "Place it on a wet, reflective desk in a dark, cyberpunk city alley at night. ",
    "scene_cozy": "Place it on a warm, natural oak wood desk. ",
    "color_icy_blue": "The entire scene is illuminated by soft, cool-toned icy blue backlighting from hidden LED strips. ",
    "color_neon": "The main light source is the vibrant neon pink and cyan glow from the PC itself and nearby holographic signs. ",
    "color_sunset": "Soft, warm sunlight streams in from a blurred window in the background, creating a cozy and inviting atmosphere. ",
    "item_plants": "Shelves with small green potted plants are subtly visible in the out-of-focus background. ",
    "item_cat": "A cute cat is sleeping peacefully next to the PC case. ",
    "item_figures": "Shelves in the background are filled with detailed anime figures and gaming collectibles. "
}

def build_prompt_from_tags(tags, case_name_for_prompt):
    prompt = f"A photorealistic, ultra-detailed, hero shot of {case_name_for_prompt}. CRITICAL: Do not alter, modify, or change the design of the provided PC case in any way. Keep the original product design intact. "
    for tag in tags:
        prompt += TAG_FRAGMENTS.get(tag, "")
    prompt += "The background should be soft-focused. Product photography, shallow depth of field, bokeh background, 8K."
    return prompt

# --- 步驟 3: 建立路由 ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_image_endpoint():
    if client is None:
        return jsonify({"error": "伺服器 AI Client 初始化失敗，請檢查後端日誌。"}), 500
    try:
        data = request.get_json()
        case_id = data.get('case_id')
        tags = data.get('tags', [])
        selected_case = CASES.get(case_id)
        if not selected_case:
            return jsonify({"error": f"伺服器找不到對應的機殼圖片: {case_id}"}), 404
        
        input_image = Image.open(selected_case["image_path"])
        prompt = build_prompt_from_tags(tags, selected_case["name_for_prompt"])
        
        logging.info("======> 準備呼叫 Gemini API... <======")
        # 【重要】使用您指定的 client.models.generate_content() 進行 API 呼叫
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt, input_image]
        )
        logging.info("======> 成功收到 Gemini API 回應！ <======")

        if not response.candidates:
            raise ValueError(f"Gemini API 沒有回傳任何有效的候選內容. 原因: {response.prompt_feedback}")

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                return send_file(BytesIO(part.inline_data.data), mimetype='image/png')
        
        raise ValueError("模型回傳了內容，但在其中找不到圖片資料。")
    except Exception as e:
        logging.error(f"[!!!] 請求處理時發生錯誤.", exc_info=True)
        return jsonify({"error": str(e)}), 500

# --- 讓程式可以被執行 ---
if __name__ == '__main__':
    # 這段程式碼讓您可以在本地用 'python app.py' 啟動
    # Render 在部署時會忽略這一段，直接使用 Gunicorn
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

