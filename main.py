# main.py
import functions_framework
import json
import numpy as np
from pygltflib import GLTF2, Buffer, BufferView, Accessor, Mesh, Primitive, Node, Scene, Asset
from google.cloud import storage 
import os 

storage_client = storage.Client()

GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "your-gcs-bucket-name-if-not-set")
if GCS_BUCKET_NAME == "your-gcs-bucket-name-if-not-set":
    print("WARNING: GCS_BUCKET_NAME environment variable is not set in Cloud Functions. Using placeholder. Please set it in Cloud Build or function configuration.")

@functions_framework.http
def model_generate_v2(request):
    """
    HTTP リクエストを受け取り、Next.jsから送信されたtaskIdとfileExtensionに基づいて
    Cloud Storageからファイルを読み込み（`uploads/UUID.EXT`形式）、
    固定の立方体GLBモデルを生成して返すCloud Function。
    """
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'model/gltf-binary' 
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
        response_headers['Content-Type'] = 'application/json'
        return (json.dumps({'error': error_message}), 400, response_headers)

    if not received_task_id:
        error_message = "Missing 'taskId' in request body."
        print(f"Error: {error_message}")
        response_headers['Content-Type'] = 'application/json'
        return (json.dumps({'error': error_message}), 400, response_headers)
    
    if not received_file_extension:
        error_message = "Missing 'fileExtension' in request body."
        print(f"Error: {error_message}")
        response_headers['Content-Type'] = 'application/json'
        return (json.dumps({'error': error_message}), 400, response_headers)

    try:
        # ★★★ Cloud Storage からファイルを読み込むロジック (uploads/UUID.EXT 形式に戻す) ★★★
        gcs_file_path = f"uploads/{received_task_id}.{received_file_extension}" 
        
        print(f"Cloud Functions: Attempting to download from GCS path: gs://{GCS_BUCKET_NAME}/{gcs_file_path}")

        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_file_path)

        if not blob.exists():
            error_message = f"File not found in GCS: gs://{GCS_BUCKET_NAME}/{gcs_file_path}. Please check filename or upload status. (Expected path: {gcs_file_path})"
            print(f"Error: {error_message}")
            response_headers['Content-Type'] = 'application/json'
            return (json.dumps({'error': error_message}), 404, response_headers)

        file_contents = blob.download_as_bytes()
        print(f"File '{gcs_file_path}' downloaded from GCS. Size: {len(file_contents)} bytes")

        # ... (固定立方体GLBモデル生成ロジックは変更なし) ...
        vertices = np.array([
            [-0.5, -0.5, -0.5], [ 0.5, -0.5, -0.5], [ 0.5,  0.5, -0.5], [-0.5,  0.5, -0.5],
            [-0.5, -0.5,  0.5], [ 0.5, -0.5,  0.5], [ 0.5,  0.5,  0.5], [-0.5,  0.5,  0.5],
        ], dtype=np.float32)
        indices = np.array([
            0, 1, 2,  0, 2, 3,  # Front face (-Z)
            1, 5, 6,  1, 6, 2,  # Right face (+X)
            5, 4, 7,  5, 7, 6,  # Back face (+Z)
            4, 0, 3,  4, 3, 7,  # Left face (-X)
            3, 2, 6,  3, 6, 7,  # Top face (+Y)
            4, 5, 1,  4, 1, 0
        ], dtype=np.uint16)
        gltf = GLTF2()
        vertex_buffer_byte_offset = 0
        vertex_buffer_bytes = vertices.tobytes()
        index_buffer_byte_offset = len(vertex_buffer_bytes)
        index_buffer_bytes = indices.tobytes()
        buffer_data = vertex_buffer_bytes + index_buffer_bytes
        buffer = Buffer(byteLength=len(buffer_data))
        gltf.buffers.append(buffer)
        buffer_view_vertices = BufferView(
            buffer=0, byteOffset=vertex_buffer_byte_offset, byteLength=len(vertex_buffer_bytes), target=34962)
        gltf.bufferViews.append(buffer_view_vertices)
        buffer_view_indices = BufferView(
            buffer=0, byteOffset=index_buffer_byte_offset, byteLength=len(index_buffer_bytes), target=34963)
        gltf.bufferViews.append(buffer_view_indices) # This should be gltf.bufferViews.append(buffer_view_indices)

        accessor_vertices = Accessor(
            bufferView=0, byteOffset=0, componentType=5126, count=len(vertices), type='VEC3',
            max=vertices.max(axis=0).tolist(), min=vertices.min(axis=0).tolist())
        gltf.accessors.append(accessor_vertices)
        accessor_indices = Accessor(
            bufferView=1, byteOffset=0, componentType=5123, count=len(indices), type='SCALAR',
            max=[int(indices.max())], min=[int(indices.min())])
        gltf.accessors.append(accessor_indices)
        primitive = Primitive(
            attributes=Accessor(POSITION=0), indices=1, mode=4)
        gltf.meshes.append(Mesh(primitives=[primitive])) # This should be Mesh(primitives=[primitive]) then gltf.meshes.append(mesh)
        node = Node(mesh=0)
        gltf.nodes.append(node)
        scene = Scene(nodes=[0])
        gltf.scenes.append(scene)
        gltf.scene = 0
        gltf.asset = Asset(version="2.0", generator="pygltflib")
        glb_data = gltf.glb_bytes_representation(binchunk=buffer_data)

        return glb_data, 200, response_headers

    except Exception as e:
        error_message = f"3D Model generation or GCS access failed: {str(e)}"
        print(f"Error: {error_message}")
        response_headers['Content-Type'] = 'application/json'
        if "File not found in GCS" in str(e):
            return (json.dumps({'error': error_message}), 404, response_headers)
        else:
            return (json.dumps({'error': error_message}), 500, response_headers)