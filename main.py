# main.py (一時的なデバッグ用 - GCSアクセスと3Dモデル生成はコメントアウト)
import functions_framework
import json
# import numpy as np # 不要なのでコメントアウト
# from pygltflib import GLTF2, Buffer, BufferView, Accessor, Mesh, Primitive, Node, Scene, Asset # 不要なのでコメントアウト
# from google.cloud import storage # 不要なのでコメントアウト
# import os # 不要なのでコメントアウト

# storage_client = storage.Client() # 初期化もコメントアウト
# GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "your-gcs-bucket-name-if-not-set")

@functions_framework.http
def model_generate_v2(request):
    """
    HTTP リクエストを受け取り、シンプルな文字列を返す Cloud Function (デバッグ用)。
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

    # CORS ヘッダー
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json' # JSON形式で返すことを示すMIMEタイプに変更
    }

    request_json = request.get_json(silent=True)
    received_task_id = None
    if request_json and 'taskId' in request_json:
        received_task_id = request_json['taskId']
        print(f"Cloud Functions: Received Task ID: {received_task_id}")
    else:
        print("Cloud Functions: No 'taskId' found in request body.")

    try:
        # ★★★ Cloud Functions からのシンプルなJSONレスポンス ★★★
        response_data = {
            "status": "success",
            "message": "Hello from Cloud Functions!",
            "received_task_id": received_task_id,
            "timestamp": f"{Date.now()}"
        }
        print(f"Cloud Functions: Responding with: {response_data}")
        return (json.dumps(response_data), 200, response_headers)

    except Exception as e:
        error_message = f"Cloud Functions internal error (debug mode): {str(e)}"
        print(f"Error: {error_message}")
        return (json.dumps({'error': error_message}), 500, response_headers)