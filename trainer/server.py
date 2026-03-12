from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict
import datetime
import uvicorn
import html

app = FastAPI(title="KubeSchool Monitor")

# Base de données temporaire en mémoire
results_db: Dict[str, Dict[str, dict]] = {}

class LabReport(BaseModel):
    username: str
    lab_id: str
    status: bool
    score: int
    details: List[dict]

@app.post("/report")
async def receive_report(report: LabReport):
    if report.username not in results_db:
        results_db[report.username] = {}

    results_db[report.username][report.lab_id] = {
        "status": report.status,
        "score": report.score,
        "details": report.details,
        "last_updated": datetime.datetime.now().strftime("%H:%M:%S")
    }
    return {"message": "Rapport bien reçu !"}

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    rows = ""
    for user, labs in results_db.items():
        # Sanitize username for display
        safe_user = html.escape(user)
        for lab_id, data in labs.items():
            safe_lab_id = html.escape(lab_id)
            status_color = "text-green-600" if data['status'] else "text-red-600"
            status_icon = "✅" if data['status'] else "❌"

            details_list = ""
            for d in data['details']:
                rule = html.escape(d.get('rule', 'N/A'))
                msg = html.escape(d.get('message', ''))
                success_mark = "[OK]" if d.get('success') else "[FAIL]"
                details_list += f"<li>{rule}: {success_mark} {msg}</li>"

            rows += f"""
            <tr class="border-b hover:bg-gray-50">
                <td class="px-6 py-4 font-medium text-gray-900">{safe_user}</td>
                <td class="px-6 py-4">{safe_lab_id}</td>
                <td class="px-6 py-4 font-bold {status_color}">{status_icon} {data['score']}%</td>
                <td class="px-6 py-4 text-sm text-gray-500">{data['last_updated']}</td>
                <td class="px-6 py-4 text-xs">
                    <ul class="list-disc">
                        {details_list}
                    </ul>
                </td>
            </tr>
            """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>KubeSchool Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <meta http-equiv="refresh" content="5"> </head>
    <body class="bg-gray-100 p-8">
        <div class="max-w-6xl mx-auto bg-white shadow-md rounded-lg overflow-hidden">
            <div class="bg-blue-600 p-4 flex justify-between items-center">
                <h1 class="text-white text-2xl font-bold italic">KubeSchool // Monitor</h1>
                <span class="text-blue-100 text-sm">Rafraîchissement auto (5s)</span>
            </div>
            <table class="w-full text-left border-collapse">
                <thead class="bg-gray-200">
                    <tr>
                        <th class="px-6 py-3">Apprenant</th>
                        <th class="px-6 py-3">Lab</th>
                        <th class="px-6 py-3">Score</th>
                        <th class="px-6 py-3">Heure</th>
                        <th class="px-6 py-3">Détails des tests</th>
                    </tr>
                </thead>
                <tbody>
                    {rows if rows else '<tr><td colspan="5" class="p-10 text-center text-gray-400">En attente de rapports...</td></tr>'}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
