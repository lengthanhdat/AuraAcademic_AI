# AuraAcademic AI Service 🤖

A professional AI-powered proctoring service built with **FastAPI** and **YOLOv8** to ensure integrity in online examinations. This service performs real-time behavioral analysis and violation detection via WebSockets.

## 🚀 Features

- **Real-time Monitoring**: Low-latency image processing at 3 FPS via WebSockets.
- **Smart Detection**:
  - 👤 **Identity**: Detection of missing or multiple faces.
  - 📱 **Objects**: Detection of unauthorized devices (cell phones).
  - 📐 **Behavioral Analysis**: Pose estimation to detect suspicious head movements (looking left, right, or down).
- **Evidence Management**:
  - Automatically records 5-second video clips of sustained violations.
  - Generates evidence in `.webm` format (VP8) for high browser compatibility.
  - Integrates seamlessly with the AuraAcademic Spring Boot backend for reporting.

## 🛠️ Tech Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Computer Vision**: [OpenCV](https://opencv.org/)
- **AI Models**: [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) (Detection & Pose)
- **Networking**: WebSockets for real-time bidirectional communication.

## 📋 Prerequisites

- Python 3.8+
- Pre-trained models: `yolov8n.pt` and `yolov8n-pose.pt` (included in root).

## 🔧 Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/lengthanhdat/AuraAcademic_AI.git
   cd AuraAcademic_AI
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the service**:
   ```bash
   python main.py
   ```
   The server will start at `http://0.0.0.0:8001`.

## 📡 API Endpoints

- **WebSocket**: `/ws/detect/{exam_code}/{student_id}`
  - Receives base64 image strings.
  - Returns real-time violation status.
- **Static Files**: `/videos/`
  - Access generated video evidence clips.

## ⚙️ Configuration

- The service communicates with the Spring Boot backend at `http://localhost:8088`.
- Ensure the `videos/` directory exists for evidence storage (auto-created on startup).

---
Developed as part of the **AuraAcademic** ecosystem.
