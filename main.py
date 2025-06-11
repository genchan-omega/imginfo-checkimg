# main.py

import functions_framework
import json
from google.cloud import storage 
import os 

# Cloud Storage クライアントの初期化
storage_client = storage.Client()

# Cloud Storage バケット名
# ここは、GCSコンソールでFigure_1.pngを配置したバケット名に合わせます。
# 通常は環境変数から取得しますが、今回は決め打ちの検証のため、直接記述します。
# 実際のバケット名 "model-raw-img" をここに記述
GCS_BUCKET_NAME = "model-raw-img" 

# 環境変数が設定されていない場合の警告は、今回決め打ちなので不要です
# if GCS_BUCKET_NAME == "your-gcs-bucket-name-if-not-set":
#     print("WARNING: GCS_BUCKET_NAME environment variable is not set in Cloud Functions. Using placeholder. Please set it in Cloud Build or function configuration.")

@functions_framework.http
def model_generate_v2(request):
    """
    HTTP リクエストを受け取り、Cloud Storageから決め打ちの "uploads/Figure_1.png" を読み込み、
    /tmpに保存し、その後 "Hello world" という文字列をJSONで返すCloud Function。
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
        'Content-Type': 'application/json' # JSONを明確にする
    }

    # taskIdとfileExtensionは今回は使用しないが、リクエストボディの構造は維持
    request_json = request.get_json(silent=True)
    received_task_id = request_json.get('taskId', 'DEBUG_TASK_ID') # デバッグ用のデフォルト値
    received_file_extension = request_json.get('fileExtension', 'png') # デバッグ用のデフォルト値
    print(f"Cloud Functions: (Debug Mode) Received JSON - taskId: {received_task_id}, fileExtension: {received_file_extension}")
    
    # 受け取ったtaskId/fileExtensionの存在チェックは、今回は決め打ちの検証なので不要
    # if not received_task_id: ...
    # if not received_file_extension: ...

    try:
        # --- GCSからの決め打ちパスの画像を読み込む ---
        # ★★★ ここを修正！決め打ちのパスを指定 ★★★
        gcs_file_path = "uploads/Figure_1.png" 
        print(f"Cloud Functions: Attempting to download FIXED file from GCS path: gs://{GCS_BUCKET_NAME}/{gcs_file_path}")

        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_file_path)

        if not blob.exists():
            error_message = f"FIXED File 'uploads/Figure_1.png' not found in GCS: gs://{GCS_BUCKET_NAME}/{gcs_file_path}. Please ensure it is placed there manually."
            print(f"Error: {error_message}")
            response_headers['Content-Type'] = 'application/json'
            return (json.dumps({'error': error_message}), 404, response_headers) # 404 Not Foundとして返す

        file_contents = blob.download_as_bytes()
        print(f"FIXED File '{gcs_file_path}' downloaded from GCS. Size: {len(file_contents)} bytes")

        # 2. 読み込んだファイルを /tmp ディレクトリに保存 (確認のため)
        # 決め打ちなので、ファイル名もFigure_1.pngで保存
        local_temp_file_path = os.path.join("/tmp", "Figure_1.png")
        with open(local_temp_file_path, "wb") as f:
            f.write(file_contents)
        print(f"FIXED File successfully saved to local /tmp: {local_temp_file_path}")

        # --- "Hello world" という文字列を含むJSONレスポンスを返す ---
        response_data = {
            "message": "Hello world from Cloud Functions! (FIXED FILE TEST SUCCESS)",
            "read_file_path": gcs_file_path,
            "read_file_size": len(file_contents)
        }
        print(f"Cloud Functions: Responding with: {response_data}")

        return (json.dumps(response_data), 200, response_headers)

    except Exception as e:
        # エラー発生時のログ出力とJSONエラーレスポンス
        error_message = f"Unexpected error in Cloud Functions (FIXED FILE TEST): {str(e)}"
        print(f"Error: {error_message}")
        response_headers['Content-Type'] = 'application/json' 
        if "File not found in GCS" in str(e) or ("Access denied" in str(e) and "storage.googleapis.com" in str(e)): 
            return (json.dumps({'error': error_message}), 404, response_headers)
        else:
            return (json.dumps({'error': error_message}), 500, response_headers)