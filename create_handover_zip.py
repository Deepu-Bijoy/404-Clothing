import os
import zipfile

def zip_project(output_filename):
    # Get the directory of this script (project root)
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Files/Dirs to exclude
    EXCLUDE_DIRS = {'__pycache__', '.git', '.gemini', 'venv', 'env', '.venv', 'node_modules', 'instance'}
    EXCLUDE_FILES = {'.env', 'database.db', output_filename, os.path.basename(__file__)}
    
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(root_dir):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                if file in EXCLUDE_FILES or file.endswith('.pyc') or file.endswith('.zip'):
                    continue
                
                # Create relative path for the zip entry
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, root_dir)
                
                print(f"Adding {arcname}")
                zipf.write(file_path, arcname)

if __name__ == "__main__":
    output_zip = "ClothRetailShop_Handover.zip"
    try:
        zip_project(output_zip)
        print(f"\nSuccessfully created {output_zip}")
    except Exception as e:
        print(f"Error creating zip: {e}")
