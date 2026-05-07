from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import cv2
import numpy as np
import base64
from ultralytics import YOLO
import time
import os
import uuid
import requests
import json
from collections import deque
import tempfile

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thư mục lưu trữ video bằng chứng
os.makedirs("videos", exist_ok=True)
# Phục vụ file video tĩnh qua HTTP
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

print("Loading YOLOv8 models...")
det_model = YOLO('yolov8n.pt')       # Phát hiện người, điện thoại
pose_model = YOLO('yolov8n-pose.pt') # Trích xuất khung xương, hướng mặt
print("Models loaded successfully!")

def decode_base64_image(base64_string):
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    img_data = base64.b64decode(base64_string)
    nparr = np.frombuffer(img_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def check_head_pose(keypoints):
    try:
        pts = keypoints[0]
        nose = pts[0]
        l_eye = pts[1]
        r_eye = pts[2]
        
        nose_conf = nose[2]
        if nose_conf < 0.3:
            return "head_down_deep"
            
        dist_nose_le = np.linalg.norm(nose[:2] - l_eye[:2])
        dist_nose_re = np.linalg.norm(nose[:2] - r_eye[:2])
        
        if dist_nose_le > 0 and dist_nose_re > 0:
            ratio = dist_nose_le / dist_nose_re
            # Nới lỏng nhẹ: > 1.4 hoặc < 0.7 là quay mặt (để dễ test hơn)
            if ratio > 1.4:
                return "looking_right"
            elif ratio < 0.7:
                return "looking_left"
                
        avg_eye_y = (l_eye[1] + r_eye[1]) / 2.0
        nose_y = nose[1]
        vertical_dist = nose_y - avg_eye_y
        
        eye_dist = np.linalg.norm(l_eye[:2] - r_eye[:2])
        # Nới lỏng: Người dùng bình thường có thể có tỉ lệ ~ 0.4 - 0.6 tùy góc camera.
        # Chỉ khi cúi gập hẳn xuống (tỉ lệ < 0.25) mới tính là cúi nhìn tài liệu.
        if eye_dist > 0 and vertical_dist / eye_dist < 0.25:
            return "looking_down"
            
    except Exception as e:
        pass
    return "normal"

@app.websocket("/ws/detect/{exam_code}/{student_id}")
async def websocket_endpoint(websocket: WebSocket, exam_code: str, student_id: str, student_name: str = "Unknown", record: str = "false"):
    await websocket.accept()
    
    # Buffer lưu 15 khung hình gần nhất (ở tốc độ 3 FPS -> tương đương 5 giây video)
    fps = 3.0
    frame_buffer = deque(maxlen=15)
    
    # Bộ đếm vi phạm liên tục
    violation_counts = {
        "no_face": 0,
        "multiple_faces": 0,
        "cell_phone": 0,
        "looking_left": 0,
        "looking_right": 0,
        "looking_down": 0,
        "head_down_deep": 0
    }
    
    # Lưu thời gian gửi report cuối cùng để không spam
    last_reported_time = 0
    
    try:
        while True:
            # Nhận ảnh base64 từ frontend (3 khung hình / giây)
            data = await websocket.receive_text()
            img = decode_base64_image(data)
            
            # Lưu khung hình vào buffer (phục vụ việc tạo video lùi về 5s trước)
            frame_buffer.append(img)
            
            violations_in_frame = set()
            
            # --- CHẠY YOLO ---
            det_results = det_model(img, verbose=False)[0]
            person_count = 0
            phone_detected = False
            
            for box in det_results.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                if conf > 0.45:
                    if cls_id == 0: person_count += 1
                    elif cls_id == 67: phone_detected = True
                        
            if person_count == 0: violations_in_frame.add("no_face")
            elif person_count > 1: violations_in_frame.add("multiple_faces")
            if phone_detected: violations_in_frame.add("cell_phone")
                
            if person_count == 1:
                pose_results = pose_model(img, verbose=False)[0]
                if pose_results.keypoints is not None and len(pose_results.keypoints.data) > 0:
                    pose = check_head_pose(pose_results.keypoints.data.cpu().numpy())
                    if pose != "normal":
                        violations_in_frame.add(pose)
                        
            # --- CẬP NHẬT BỘ ĐẾM ---
            # Chỉ gửi cảnh báo nếu vi phạm liên tục trong 3 giây (9 khung hình)
            triggered_violation = None
            
            for v_type in violation_counts.keys():
                if v_type in violations_in_frame:
                    violation_counts[v_type] += 1
                    if violation_counts[v_type] >= 4: # ~1.3 giây liên tục (giảm từ 6→4)
                        triggered_violation = v_type
                else:
                    # Nếu có 1 khung hình bình thường xen ngang, giảm đếm thay vì reset về 0 ngay để chống nhiễu
                    violation_counts[v_type] = max(0, violation_counts[v_type] - 1)
            
            # Phản hồi realtime cho frontend biết để hiển thị nháy đỏ
            await websocket.send_text(json.dumps({
                "currentViolations": list(violations_in_frame)
            }))
            
            # --- GHI NHẬN & XUẤT VIDEO 5S ---
            current_time = time.time()
            if triggered_violation and (current_time - last_reported_time > 5):  # Giảm cooldown: 15s → 5s
                last_reported_time = current_time

                # Bắt buộc record="true" (Tức là đang TRONG BÀI THI) mới lưu video và gửi báo cáo về Backend
                if record.lower() == "true":
                    print(f"🔥 GIAN LẬN PHÁT HIỆN: {student_name} - {triggered_violation} - Tiến hành xuất video 5s...")

                    # Chỉ reset bộ đếm của loại vi phạm đã kích hoạt (không reset tất cả)
                    violation_counts[triggered_violation] = 0

                    # Mã hóa video buffer sang Base64 để tránh phụ thuộc localhost:8001
                    video_base64 = None
                    if len(frame_buffer) > 0:
                        try:
                            height, width, _ = frame_buffer[0].shape
                            
                            # Sử dụng NamedTemporaryFile để an toàn hơn
                            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                                tmp_path = tmp.name
                                
                            fourcc = cv2.VideoWriter_fourcc(*'vp80')
                            out = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))
                            for frame in frame_buffer:
                                out.write(frame)
                            out.release()

                            # Đọc file và mã hóa Base64
                            if os.path.exists(tmp_path):
                                with open(tmp_path, "rb") as f:
                                    video_bytes = f.read()
                                if video_bytes:
                                    video_base64 = base64.b64encode(video_bytes).decode("utf-8")
                                    print(f"✅ Đã mã hóa video {len(video_bytes)//1024}KB sang Base64")
                                
                                # Xóa file tạm
                                os.remove(tmp_path)
                        except Exception as e:
                            print(f"⚠️ Không thể mã hóa video: {e}")

                    # Gửi API về Backend Spring Boot (kèm video Base64)
                    payload = {
                        "studentId": student_id,
                        "studentName": student_name,
                        "type": triggered_violation,
                        "videoBase64": video_base64
                    }

                    try:
                        requests.post(
                            f"http://localhost:8088/api/exams/{exam_code}/violation",
                            json=payload,
                            headers={"Content-Type": "application/json"},
                            timeout=10
                        )
                        print(f"✅ Đã gửi report về Backend (video {'kèm' if video_base64 else 'không có'})")
                    except Exception as e:
                        print("Lỗi khi gửi về Spring Boot:", e)
                else:
                    # Nếu đang ở phòng chờ (Lobby), chỉ cảnh báo trên giao diện học sinh, KHÔNG báo cho giáo viên
                    print(f"⚠️ {student_name} có hành vi {triggered_violation} nhưng ĐANG Ở PHÒNG CHỜ. Bỏ qua.")

    except WebSocketDisconnect:
        print(f"Client {student_id} disconnected from WebSocket.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
