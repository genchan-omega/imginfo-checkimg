# main.py

import functions_framework
import json
from google.cloud import storage 
import os 

# Cloud Storage クライアントの初期化 (画像保存のために必要)
storage_client = storage.Client()

# Cloud Storage バケット名 (画像保存のために必要)
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "your-gcs-bucket-name-if-not-set")
if GCS_BUCKET_NAME == "your-gcs-bucket-name-if-not-set":
    print("WARNING: GCS_BUCKET_NAME environment variable is not set in Cloud Functions. Using placeholder. Please set it in Cloud Build or function configuration.")

@functions_framework.http
def model_generate_v2(request):
    """
    HTTP リクエストを受け取り、Cloud Storageから画像を読み込み、/tmpに保存し、
    その後 "Hello world" という文字列をJSONで返すCloud Function。
    """
    # CORS プリフライトリクエストへの対応
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # レスポンスヘッダーの設定 (JSONを返すためContent-Typeをapplication/jsonにする)
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json' # JSONを返すことを明確にする
    }

    request_json = request.get_json(silent=True)
    received_task_id = None
    received_file_extension = None 

    if request_json:
        received_task_id = request_json.get('taskId')
        received_file_extension = request_json.get('fileExtension')
        print(f"Cloud Functions: Received JSON - taskId: {received_task_id}, fileExtension: {received_file_extension}")
    else:
        error_message = "No JSON data found in request body."
        print(f"Error: {error_message}")
        return (json.dumps({'error': error_message}), 400, response_headers)

    # taskIdとfileExtensionの存在チェック
    if not received_task_id:
        error_message = "Missing 'taskId' in request body."
        print(f"Error: {error_message}")
        return (json.dumps({'error': error_message}), 400, response_headers)
    
    if not received_file_extension:
        error_message = "Missing 'fileExtension' in request body."
        print(f"Error: {error_message}")
        return (json.dumps({'error': error_message}), 400, response_headers)

    try:
        # --- 画像の保存操作を追加 (Cloud Storageからの読み込みと/tmpへの書き込み) ---
        # 1. GCSからファイルを読み込む
        gcs_file_path = f"uploads/{received_task_id}.{received_file_extension}" 
        print(f"Cloud Functions: Attempting to download from GCS path: gs://{GCS_BUCKET_NAME}/{gcs_file_path}")
        gcs_file_path = f"uploads/Figure_1.png"

        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_file_path)

        if not blob.exists():
            error_message = f"File not found in GCS: gs://{GCS_BUCKET_NAME}/{gcs_file_path}. Please check filename or upload status."
            print(f"Error: {error_message}")
            response_headers['Content-Type'] = 'application/json'
            return (json.dumps({'error': error_message}), 404, response_headers) # 404 Not Foundとして返す

        file_contents = blob.download_as_bytes()
        print(f"File '{gcs_file_path}' downloaded from GCS. Size: {len(file_contents)} bytes")

        # 2. 読み込んだファイルを /tmp ディレクトリに保存
        # Cloud Functions の一時ファイルは /tmp に保存されます
        local_temp_file_path = os.path.join("/tmp", f"{received_task_id}.{received_file_extension}")
        with open(local_temp_file_path, "wb") as f:
            f.write(file_contents)
        print(f"File successfully saved to local /tmp: {local_temp_file_path}")

        # --- "Hello world" という文字列を含むJSONレスポンスを返す (変更なし) ---
        response_data = {
            "message": "Hello world from Cloud Functions!",
            "received_task_id": received_task_id,
            "received_file_extension": received_file_extension 
        }
        print(f"Cloud Functions: Responding with: {response_data}")

        return (json.dumps(response_data), 200, response_headers)

    except Exception as e:
        # エラー発生時のログ出力とJSONエラーレスポンス
        error_message = f"Unexpected error in Cloud Functions (image save mode): {str(e)}"
        print(f"Error: {error_message}")
        response_headers['Content-Type'] = 'application/json' 
        # GCSからファイルが見つからなかった場合は404 Not Foundとして返す
        if "File not found in GCS" in str(e) or ("Access denied" in str(e) and "storage.googleapis.com" in str(e)): # 403 Access Deniedもここで捕捉
            return (json.dumps({'error': error_message}), 404, response_headers)
        else:
            return (json.dumps({'error': error_message}), 500, response_headers)