# main.py (修正案)
import functions_framework
import json
import numpy as np
from pygltflib import GLTF2, Buffer, BufferView, Accessor, Mesh, Primitive, Node, Scene, Asset
# Cloud Storage からファイルを読み込むために必要なライブラリ
from google.cloud import storage

# Cloud Storage クライアントの初期化 (Cloud Functions環境では認証情報が自動的に提供されます)
storage_client = storage.Client()
# Cloud Storage バケット名 (Next.js API Route と同じバケット名を指定)
# TODO: 環境変数から取得するのがベストプラクティス
GCS_BUCKET_NAME = "your-gcs-bucket-name" # 例: "my-model-upload-bucket"

@functions_framework.http
def model_generate_v2(request):
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
        'Content-Type': 'model/gltf-binary' # GLBファイルであることを示すMIMEタイプ
    }

    # --- Next.jsからのデータ取得と処理 ---
    request_json = request.get_json(silent=True)
    received_task_id = None
    if request_json and 'taskId' in request_json:
        received_task_id = request_json['taskId']
        print(f"Received Task ID: {received_task_id}")
    else:
        # taskId が提供されない場合はエラー
        error_message = "No 'taskId' found in request body."
        print(f"Error: {error_message}")
        return (json.dumps({'error': error_message}), 400, response_headers)

    try:
        # ★★★ Cloud Storage からファイルを読み込むロジック ★★★
        # Next.js API Route でファイルを `uploads/{taskId}.{拡張子}` の形式で保存していると仮定
        # 実際には、`taskId` に対応する正確なファイルパスや拡張子を知る必要があります
        # Cloud Storage に保存したファイル名を何らかの方法で渡すか、
        # taskId から推測できるように命名規則を決める必要があります。
        # 例: taskId が "12345-abcde" で、オリジナルファイルが "my_model.obj" なら、
        # GCSに "uploads/12345-abcde.obj" として保存されている、など。

        # 仮のファイル名 (Next.js API Routeで保存したファイル名を推測)
        # 実際のファイル拡張子はTaskIdを返す際に同時に返してもらうか、
        # データベースでTaskIdとファイル情報を紐付けるのがより堅牢です。
        # ここでは、簡単のため、taskIdがファイル名そのものだと仮定（もし拡張子が不明なら、汎用的な拡張子を試すなど）
        gcs_file_path = f"uploads/{received_task_id}.obj" # 例として.obj

        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_file_path)

        if not blob.exists():
            raise ValueError(f"File not found in GCS: gs://{GCS_BUCKET_NAME}/{gcs_file_path}")

        # ファイル内容をバイトデータとして読み込む
        file_contents = blob.download_as_bytes()
        print(f"File '{gcs_file_path}' downloaded from GCS. Size: {len(file_contents)} bytes")

        # TODO: ★★★ ここで、`file_contents` を解析し、3Dモデルを生成するロジックを実装 ★★★
        # 例: file_contents がOBJファイルの場合
        # from trimesh import Trimesh
        # import io
        # mesh = Trimesh(file_obj=io.BytesIO(file_contents), file_type='obj')
        # vertices_data = np.array(mesh.vertices, dtype=np.float32)
        # indices_data = np.array(mesh.faces.flatten(), dtype=np.uint16)
        # (以下、vertices, indices を使ってGLTF2オブジェクトを構築する既存のロジックに渡す)

        # --- 現在の立方体生成ロジック (ファイルデータに基づいて変更する部分) ---
        # ここは仮のデータ。上記TODOの「file_contentsを解析し3Dモデルを生成」に置き換える
        vertices = np.array([
            [-0.5, -0.5, -0.5], [ 0.5, -0.5, -0.5], [ 0.5,  0.5, -0.5], [-0.5,  0.5, -0.5],
            [-0.5, -0.5,  0.5], [ 0.5, -0.5,  0.5], [ 0.5,  0.5,  0.5], [-0.5,  0.5,  0.5],
        ], dtype=np.float32)

        indices = np.array([
            0, 1, 2,  0, 2, 3,  # Front face
            1, 5, 6,  1, 6, 2,  # Right face
            5, 4, 7,  5, 7, 6,  # Back face
            4, 0, 3,  4, 3, 7,  # Left face
            3, 2, 6,  3, 6, 7,  # Top face
            4, 5, 1,  4, 1, 0
        ], dtype=np.uint16)

        # --- GLBファイル構造の構築 (ここは既存のままでOK) ---
        gltf = GLTF2()
        # ... (中略: バッファ、バッファビュー、アクセサ、プリミティブ、メッシュ、ノード、シーン、アセットの構築) ...
        vertex_buffer_byte_offset = 0
        vertex_buffer_bytes = vertices.tobytes()
        index_buffer_byte_offset = len(vertex_buffer_bytes)
        index_buffer_bytes = indices.tobytes()

        buffer_data = vertex_buffer_bytes + index_buffer_bytes
        buffer = Buffer(byteLength=len(buffer_data))
        gltf.buffers.append(buffer)

        buffer_view_vertices = BufferView(buffer=0, byteOffset=vertex_buffer_byte_offset, byteLength=len(vertex_buffer_bytes), target=34962)
        gltf.bufferViews.append(buffer_view_vertices)
        buffer_view_indices = BufferView(buffer=0, byteOffset=index_buffer_byte_offset, byteLength=len(index_buffer_bytes), target=34963)
        gltf.bufferViews.append(buffer_view_indices)

        accessor_vertices = Accessor(bufferView=0, byteOffset=0, componentType=5126, count=len(vertices), type='VEC3', max=vertices.max(axis=0).tolist(), min=vertices.min(axis=0).tolist())
        gltf.accessors.append(accessor_vertices)
        accessor_indices = Accessor(bufferView=1, byteOffset=0, componentType=5123, count=len(indices), type='SCALAR', max=[int(indices.max())], min=[int(indices.min())])
        gltf.accessors.append(accessor_indices)

        primitive = Primitive(attributes=Accessor(POSITION=0), indices=1, mode=4)
        mesh = Mesh(primitives=[primitive])
        gltf.meshes.append(mesh)

        node = Node(mesh=0)
        gltf.nodes.append(node)
        scene = Scene(nodes=[0])
        gltf.scenes.append(scene)
        gltf.scene = 0
        gltf.asset = Asset(version="2.0", generator="pygltflib")
        # --- GLB バイナリデータを生成して返す ---
        glb_data = gltf.glb_bytes_representation(binchunk=buffer_data)
        return glb_data, 200, response_headers

    except Exception as e:
        error_message = f"3D Model generation or GCS access failed: {str(e)}"
        print(f"Error: {error_message}")
        return (json.dumps({'error': error_message}), 500, response_headers)