import os
from supabase import create_client, Client
from werkzeug.utils import secure_filename
import uuid

def get_supabase_client():
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        print(f"Error creating Supabase client: {e}")
        return None

def upload_to_supabase(file, folder='products'):
    client = get_supabase_client()
    
    filename = secure_filename(file.filename or "image.jpg")
    unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
    path_on_supabase = f"{folder}/{unique_filename}"
    
    if not client:
        print("Supabase client not initialized. Cloud storage required.")
        return None
    
    bucket_name = os.environ.get('SUPABASE_BUCKET_NAME', 'product-images')
    
    # Ensure folder structure in path
    try:
        # Read file content
        file.seek(0)
        content = file.read()
        
        # Upload to Supabase Storage
        res = client.storage.from_(bucket_name).upload(
            path=path_on_supabase,
            file=content,
            file_options={"content-type": file.content_type}
        )
        
        # Construct the public URL
        supabase_url = os.environ.get('SUPABASE_URL').rstrip('/')
        public_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{path_on_supabase}"
        return public_url
    except Exception as e:
        print(f"Supabase Upload Error: {e}")
        return None

def delete_from_supabase(url):
    """
    Deletes a file from Supabase storage given its public URL.
    """
    if not url or 'supabase.co' not in url:
        return False
        
    client = get_supabase_client()
    if not client:
        return False
    
    bucket_name = os.environ.get('SUPABASE_BUCKET_NAME', 'product-images')
    try:
        # Extract the path after /public/[bucket_name]/
        path_segments = url.split(f"/public/{bucket_name}/")
        if len(path_segments) < 2:
            return False
            
        file_path = path_segments[1]
        client.storage.from_(bucket_name).remove([file_path])
        return True
    except Exception as e:
        print(f"Supabase Delete Error: {e}")
        return False
