# main.py

import functions_framework
import json
# 不要なインポートは削除
# import numpy as np 
# from pygltflib import GLTF2, Buffer, BufferView, Accessor, Mesh, Primitive, Node, Scene, Asset
# from google.cloud import storage 
# import os 
# import io 

# 不要な初期化は削除
# storage_client = storage.Client()
# GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "your-gcs-bucket-name-if-not-set")
# if GCS_BUCKET_NAME == "your-gcs-bucket-name-if-not-set": /* ... */

@functions_framework.http
def model_generate_v2(request):
    """
    HTTP リクエストを受け取り、"Hello world" という文字列をJSONで返すCloud Function。
    GCSからのファイル読み込みや3Dモデル生成は行いません。
    """
    # CORS プリフライトリクエストへの対応 (そのまま残す)
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

    # taskIdとfileExtensionの存在チェックは、受け取ったかどうかの確認のため残す
    if not received_task_id:
        error_message = "Missing 'taskId' in request body."
        print(f"Error: {error_message}")
        return (json.dumps({'error': error_message}), 400, response_headers)
    
    if not received_file_extension:
        error_message = "Missing 'fileExtension' in request body."
        print(f"Error: {error_message}")
        return (json.dumps({'error': error_message}), 400, response_headers)

    try:
        # --- GCSからのファイル読み込み、3Dモデル生成のロジックは一切行わない ---
        # print(f"Cloud Functions: Attempting to download from GCS path: gs://{GCS_BUCKET_NAME}/{gcs_file_path}")
        # bucket = storage_client.bucket(GCS_BUCKET_NAME); blob = bucket.blob(gcs_file_path); /* ... */

        # --- "Hello world" という文字列を含むJSONレスポンスを返す ---
        response_data = {
            "message": "Hello world from Cloud Functions!",
            "received_task_id": received_task_id,
            "received_file_extension": received_file_extension # 受信確認のために含める
        }
        print(f"Cloud Functions: Responding with: {response_data}")

        return (json.dumps(response_data), 200, response_headers)

    except Exception as e:
        # エラー発生時のログ出力とJSONエラーレスポンス
        error_message = f"Unexpected error in Cloud Functions (simple mode): {str(e)}"
        print(f"Error: {error_message}")
        return (json.dumps({'error': error_message}), 500, response_headers)