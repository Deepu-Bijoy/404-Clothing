# 404Clothing

A modern, feature-rich cloth retail shop built with Flask.

## Features
- **Premium UI**: Modern Glassmorphism design with responsive layout.
- **Secure**: CSRF protection, secure session management, and hashed passwords.
- **Robust**: Custom error pages (404, 500) and safe file uploads.
- **Feature-Rich**: Product management, Shopping Cart, Checkout flow, and Admin Dashboard.

## Quick Start (Local Development)

1.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Setup**
    Copy the example environment file and configure it:
    ```bash
    cp .env.example .env
    # or manually create .env with the keys from .env.example
    ```

3.  **Initialize Database**
    This script will create the database and a default Admin user.
    ```bash
    python init_db.py
    ```
    > **Default Admin Credentials**:
    > - Email: `admin@example.com`
    > - Password: `admin123`

4.  **Run the Application**
    ```bash
    # Enable debug mode for development
    set FLASK_DEBUG=1
    python app.py
    ```
    Visit `http://127.0.0.1:5000` in your browser.

## Deployment to Production

1.  **Security Checks**:
    - Ensure `FLASK_ENV=production` in your `.env` file.
    - Set `FLASK_DEBUG=0`.
    - Change `SECRET_KEY` to a random, long string.

2.  **WSGI Server**:
    Do **not** use `python app.py` in production. Use a production server like `waitress` (Windows) or `gunicorn` (Linux).
    
    **For Windows (Waitress)**:
    ```bash
    pip install waitress
    waitress-serve --port=8080 --call app:create_app
    ```

3.  **Database**:
    - The app uses SQLite by default (`database.db`). For high traffic, consider PostgreSQL.
    - Ensure the `instance` folder and `database.db` are writable by the server process.

4.  **Uploads**:
    - Images are stored in `static/uploads`. Ensure this directory persists across deployments.
