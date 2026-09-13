from flask import Flask, render_template, Response, request, jsonify, url_for, send_file
import cv2
import time
from ultralytics import YOLO
import datetime
import os
import threading
import math
import pyttsx3      # Library Suara
import requests     # Library Telegram
import csv          # Library CSV
import numpy as np
from werkzeug.utils import secure_filename

app = Flask(__name__)

# =====================================================
# ⚙️ KONFIGURASI (TELEGRAM & FOLDER)
# =====================================================
TELEGRAM_TOKEN = "8381873292:AAFcfGNrhUcy7oIz3JAJgJ4h81vS33ep4rU"
TELEGRAM_CHAT_ID = "1610793761"

UPLOAD_FOLDER = 'static/uploads'
SNAPSHOT_FOLDER = 'snapshots'
CSV_FILE = 'laporan_perjalanan.csv'

# Buat folder & file
for folder in [UPLOAD_FOLDER, SNAPSHOT_FOLDER, 'static']:
    os.makedirs(folder, exist_ok=True)

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as f:
        csv.writer(f).writerow(["Waktu", "Status", "Skor"])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# =====================================================
# 🤖 LOAD MODEL
# =====================================================
model = YOLO("best.pt")

# =====================================================
# GLOBAL VARIABLES
# =====================================================
camera = None
video_source = 0
lock = threading.Lock()
current_fps = 0
current_source_name = "LIVE WEBCAM"
driver_focus_score = 100

#ATUR

model_conf = 0.35        # Keyakinannya kalau 
logic_multiplier = 60    # Logic Radius 60% dari lebar kepala (Pas untuk deteksi nelfon)

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def log_incident(status, score):
    try:
        with open(CSV_FILE, 'a', newline='') as f:
            csv.writer(f).writerow([
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                status, int(score)
            ])
    except: pass

def speak_warning(text):
    def run():
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 140)
            engine.say(text)
            engine.runAndWait()
        except: pass
    threading.Thread(target=run).start()

def send_telegram_alert(msg, frame=None):
    def task():
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}
            )
            if frame is not None:
                cv2.imwrite("temp_alert.jpg", frame)
                with open("temp_alert.jpg", "rb") as f:
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                        data={"chat_id": TELEGRAM_CHAT_ID},
                        files={"photo": f}
                    )
            print("✅ Telegram Terkirim")
        except Exception as e:
            print(f"❌ Gagal Telegram: {e}")
    threading.Thread(target=task).start()

def dist(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

# =====================================================
# POSE SMOOTHER
# =====================================================
class PoseSmoother:
    def __init__(self, alpha=0.6):
        self.prev = None
        self.alpha = alpha

    def update(self, kpts):
        if self.prev is None:
            self.prev = kpts
            return kpts
        out = self.alpha * kpts + (1 - self.alpha) * self.prev
        self.prev = out
        return out

# =====================================================
# 🔥 LOGIKA DETEKSI FINAL (DENGAN SLIDER AKTIF)
# =====================================================
def annotate_frame(frame, smoother):
    global model_conf, logic_multiplier

    # Resize agar ringan
    frame = cv2.resize(frame, (640, int(frame.shape[0] * 640 / frame.shape[1])))
    
    # [FIX 1] Gunakan variable model_conf dari Slider
    results = model(frame, conf=model_conf, verbose=False)
    status = "Aman"

    for r in results:
        if r.boxes is None or len(r.boxes) == 0: break

        i = int(r.boxes.conf.argmax())
        cls = int(r.boxes.cls[i])
        label = model.names[cls]
        x1, y1, x2, y2 = map(int, r.boxes.xyxy[i])

        # --- 1. GAMBAR SKELETON ---
        if r.keypoints is not None:
            raw_kpts = r.keypoints.xy.cpu().numpy()[i]
            kpts = smoother.update(raw_kpts)
            
            for kp in kpts:
                if kp[0] > 0:
                    cv2.circle(frame, (int(kp[0]), int(kp[1])), 3, (0, 255, 255), -1)

        # --- 2. CEK STATUS ---
        
        # A. Model Bilang AMAN
        if label.lower() == "aman":
            cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
            cv2.putText(frame, "AMAN", (x1,y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
            status = "Aman"
            break 

        # B. Model Bilang BAHAYA
        else:
            status = label
            
            # [FIX 2] Validasi Pakai Logic Radius dari Slider
            # Slider nilai 0-100 -> Kita ubah jadi rasio 0.0 - 1.0
            # Contoh: Slider 60 -> Rasio 0.6
            ratio_threshold = logic_multiplier / 100.0 

            if results[0].keypoints is not None:
                # Jika Kepala Terdeteksi
                if kpts[3][0] > 0 and kpts[4][0] > 0:
                    head = dist(kpts[3], kpts[4])
                    
                    # Cek Jarak Tangan ke Kuping
                    # Jika jarak > threshold (Rasio Slider), batalkan Menelfon
                    is_calling = False
                    
                    if kpts[4][0] > 0 and kpts[10][0] > 0:
                        if dist(kpts[4], kpts[10]) < head * ratio_threshold: is_calling = True
                    
                    if kpts[3][0] > 0 and kpts[9][0] > 0:
                        if dist(kpts[3], kpts[9]) < head * ratio_threshold: is_calling = True
                    
                    # Jika AI bilang Menelfon TAPI tangan jauh (menurut slider), ubah jadi Aman
                    if status == "Menelfon" and not is_calling:
                        # status = "Aman" # (Opsional: Uncomment jika ingin Logic Slider menimpa AI)
                        pass

            cv2.rectangle(frame, (x1,y1), (x2,y2), (0,0,255), 2)
            cv2.putText(frame, status.upper(), (x1,y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
        break

    return frame, status

# =====================================================
# VIDEO LOOP
# =====================================================
def generate_frames():
    global camera, current_fps, driver_focus_score

    smoother = PoseSmoother()
    prev = time.time()
    last_announced_status = "Aman"
    status_counter = 0      
    telegram_trigger_count = 0 
    has_sent_telegram = False  

    while True:
        with lock:
            if camera is None or not camera.isOpened():
                time.sleep(0.1); continue
            ret, frame = camera.read()
            if not ret: break
            
            frame = cv2.flip(frame, 1) # Mirroring

        frame, status = annotate_frame(frame, smoother)

        now = time.time()
        current_fps = int(1 / (now - prev)) if (now - prev) > 0 else 0
        prev = now

        # Scoring
        if status == "Aman":
            driver_focus_score = min(100, driver_focus_score + 0.5)
            telegram_trigger_count = 0 
            has_sent_telegram = False 
        else:
            driver_focus_score = max(0, driver_focus_score - 1.5)
            telegram_trigger_count += 1

        # Jarvis Suara
        if status != last_announced_status:
            status_counter += 1
            if status_counter > 5:
                if status == "Aman": speak_warning("Posisi Aman.")
                else: speak_warning(f"Peringatan! Terdeteksi {status}")
                log_incident(status, driver_focus_score)
                last_announced_status = status
                status_counter = 0
        else:
            status_counter = 0

        # Telegram
        if telegram_trigger_count > 15 and not has_sent_telegram:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            msg = f"🚨 ALERT RAFLY!\nStatus: {status.upper()}\nWaktu: {ts}"
            send_telegram_alert(msg, frame)
            has_sent_telegram = True

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# =====================================================
# ROUTES
# =====================================================
@app.route('/')
def index():
    # Kita kirim nilai model_conf dan logic_multiplier ke HTML
    return render_template('index.html', conf=model_conf, logic=logic_multiplier)

@app.route('/video_feed')
def video_feed(): return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status_feed')
def status_feed():
    return jsonify({
        "fps": f"{current_fps} FPS",
        "source": current_source_name,
        "score": int(driver_focus_score)
    })

@app.route('/download_report')
def download_report():
    try: return send_file(CSV_FILE, as_attachment=True)
    except Exception as e: return str(e)

@app.route('/test_telegram', methods=['POST'])
def test_telegram():
    send_telegram_alert("🧪 TES KONEKSI: Sistem Telegram Rafly Terhubung & Siap!")
    return jsonify({"status": "success"})

# [FIX] UPDATE NILAI SLIDER DARI WEB
@app.route('/api/set_conf', methods=['POST'])
def set_conf():
    global model_conf
    val = request.form.get('val')
    if val: model_conf = float(val)
    return jsonify({"status": "success", "new_conf": model_conf})

@app.route('/api/set_logic', methods=['POST'])
def set_logic():
    global logic_multiplier
    val = request.form.get('val')
    if val: logic_multiplier = int(val)
    return jsonify({"status": "success", "new_logic": logic_multiplier})

@app.route('/upload_image', methods=['POST'])
def upload_image():
    global driver_focus_score
    if 'file' not in request.files: return jsonify({"status":"error"})
    file = request.files['file']
    if file.filename == '': return jsonify({"status":"error"})

    filename = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)

    img = cv2.imread(path)
    res_img, status = annotate_frame(img, PoseSmoother())

    driver_focus_score = 95 if status == "Aman" else 20
    
    if status == "Aman": speak_warning("Gambar Aman.")
    else: 
        speak_warning(f"Bahaya: {status}")
        send_telegram_alert(f"🚨 UPLOAD IMAGE: {status}", res_img)
    
    log_incident(f"IMG: {status}", driver_focus_score)

    out = os.path.join(app.config['UPLOAD_FOLDER'], "res_" + filename)
    cv2.imwrite(out, res_img)

    return jsonify({
        "status": "success",
        "type": "image",
        "url": url_for('static', filename=f'uploads/res_{filename}'),
        "score": driver_focus_score
    })

@app.route('/upload_video', methods=['POST'])
def upload_video():
    global driver_focus_score
    if 'file' not in request.files: return jsonify({"status":"error"})
    
    file = request.files['file']
    if file.filename == '': return jsonify({"status":"error"})

    filename = secure_filename(file.filename)
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)

    cap = cv2.VideoCapture(input_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    target_w = 640
    target_h = int(orig_h * 640 / orig_w)

    out_name = "res_" + os.path.splitext(filename)[0] + ".mp4"
    out_path = os.path.join(app.config['UPLOAD_FOLDER'], out_name)
    fourcc = cv2.VideoWriter_fourcc(*'avc1') 
    
    out = cv2.VideoWriter(out_path, fourcc, fps, (target_w, target_h))
    smoother = PoseSmoother()
    final_status = "Aman"
    
    print("⏳ Processing Video...")
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        processed_frame, status = annotate_frame(frame, smoother)
        if status != "Aman": final_status = status
        out.write(processed_frame)

    cap.release()
    out.release()
    print("✅ Video Done!")

    driver_focus_score = 95 if final_status == "Aman" else 20
    if final_status != "Aman": speak_warning(f"Video selesai. Terdeteksi {final_status}")
    log_incident(f"VIDEO: {final_status}", driver_focus_score)

    return jsonify({
        "status": "success",
        "type": "video",
        "url": url_for('static', filename=f'uploads/{out_name}'),
        "score": driver_focus_score
    })

@app.route('/reset_camera', methods=['POST'])
def reset_camera():
    global video_source
    video_source = 0
    init_camera()
    return jsonify({"status": "success"})

@app.route('/take_snapshot', methods=['POST'])
def take_snapshot():
    success, frame = camera.read()
    if success:
        fname = f"SNAP_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(os.path.join(SNAPSHOT_FOLDER, fname), frame)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

def init_camera():
    global camera
    if camera: camera.release()
    camera = cv2.VideoCapture(video_source)

init_camera()

if __name__ == "__main__":
    app.run(debug=True, threaded=True, port=5000)