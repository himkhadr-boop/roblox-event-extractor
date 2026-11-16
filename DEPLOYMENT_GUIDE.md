# Deployment & Permanent Link Guide

This guide covers two simple ways to get a permanent, publicly accessible link for the Winslow Accord Event Extractor.

---

## Option 1: 100% Free Cloud Deployment on Render.com (Recommended)

Render offers free web service hosting with automatic HTTPS, making your tool available 24/7 at a permanent `https://<service-name>.onrender.com` address.

### Step-by-Step Setup (2 Minutes)

1. **Push your code to GitHub**:
   - Initialize git in your project directory (if not already done):
     ```bash
     git init
     git add .
     git commit -m "Initial commit"
     ```
   - Create a new repository on [GitHub](https://github.com/new) and push your code:
     ```bash
     git remote add origin https://github.com/<your-username>/<your-repo-name>.git
     git branch -M main
     git push -u origin main
     ```

2. **Deploy on Render**:
   - Go to [dashboard.render.com](https://dashboard.render.com/) and sign in.
   - Click **New +** at the top right and select **Blueprint** (or **Web Service**).
   - Connect your GitHub repository.
   - Render will automatically read `render.yaml` and configure the service.
     *(If deploying manually without Blueprint: Runtime = `Python 3`, Build Command = `pip install -r requirements.txt`, Start Command = `uvicorn app:app --host 0.0.0.0 --port $PORT`)*.

3. **Configure Environment Variables**:
   - In the **Environment Variables** section on Render, add:
     - `GEMINI_API_KEYS`: Paste your Gemini API key (or multiple comma-separated keys for automatic rotation).
     - *(Optional)* Override clan settings if needed:
       - `DEFAULT_CLAN_NAME`: `Winslow Accord`
       - `DEFAULT_CLAN_GROUP_ID`: `825966682`
       - `WIN_XP`: `10`
       - `LOSS_XP`: `5`

4. **Launch**:
   - Click **Create Web Service** / **Apply**.
   - Render will build and deploy the app in ~1 minute.
   - Your permanent URL will be displayed at the top: `https://winslow-event-extractor.onrender.com`. Share this link with clan officers!

---

## Option 2: Local Host with Free ngrok Static Domain Tunnel

If you prefer to run the extractor on your own computer or laptop without pushing to GitHub, you can tunnel your local server using ngrok.

### Step-by-Step Setup

1. **Install and Authorize ngrok**:
   - Download ngrok from [ngrok.com](https://ngrok.com/download) or install via PowerShell:
     ```powershell
     winget install ngrok
     ```
   - Sign up for a free ngrok account and grab your auth token from the dashboard.
   - Run in terminal:
     ```powershell
     ngrok config add-authtoken <YOUR_AUTHTOKEN>
     ```

2. **Claim a Free Permanent Static Domain**:
   - In the ngrok dashboard, go to **Cloud Edge** > **Domains**.
   - Click **Create Domain** (every free account gets 1 free permanent static domain, e.g., `great-badger-promptly.ngrok-free.app`).

3. **Start the Local Extractor Server**:
   - In PowerShell within the project folder:
     ```powershell
     python app.py
     ```
   - The app will run locally on `http://localhost:8000`.

4. **Start the ngrok Tunnel**:
   - In a separate PowerShell window, run:
     ```powershell
     ngrok http --domain=<your-static-domain>.ngrok-free.app 8000
     ```
     *(Or if you just want a temporary tunnel: `ngrok http 8000`)*.
   - ngrok will provide your permanent public HTTPS link pointing directly to your local machine.
