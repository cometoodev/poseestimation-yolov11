# 🚗 Real-Time Driver Distraction Detection System
> **Geometric Keypoint Body Analysis using YOLOv11s-pose & Flask**

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](#)
[![YOLOv11](https://img.shields.io/badge/Model-YOLOv11s--pose-ffd43b.svg)](#)
[![Flask](https://img.shields.io/badge/Framework-Flask-black.svg?logo=flask&logoColor=white)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#)

Sistem pendeteksi distraksi pengemudi secara *real-time* menggunakan estimasi pose tubuh berbasis **YOLOv11s-pose**. Aplikasi ini menganalisis orientasi geometris titik kunci tubuh (seperti kepala, mata, tangan, dan posisi kemudi) untuk mendeteksi perilaku berkendara berisiko—seperti penggunaan ponsel, mengantuk (*drowsiness*), atau menoleh ke luar jalur pandang—dilengkapi peringatan audio dan rekapitulasi riwayat perjalanan.

---

## 🎯 Fitur Utama

* **Real-Time Pose Estimation**: Pelacakan titik kunci tubuh pengemudi berkecepatan tinggi memanfaatkan model *lightweight* YOLOv11s-pose.
* **Geometric Keypoint Analysis**: Algoritma berbasis kalkulasi sudut dan jarak spasial untuk membedakan kondisi fokus vs. distraksi secara presisi.
* **Instant Audio & Visual Alerts**: Bunyi alarm otomatis (`alarm.mp3`) dan penanda visual pada antarmuka web saat terdeteksi distraksi.
* **Automated Incident Snapshot**: Pengambilan tangkapan layar otomatis saat indikasi bahaya terdeteksi untuk kebutuhan dokumentasi.
* **Trip Report & Export**: Pencatatan riwayat durasi distraksi dan status keselamatan ke dalam file log `laporan_perjalanan.csv`.
* **Interactive Web Dashboard**: Antarmuka berbasis Flask dengan grafik monitoring kebiasaan pengemudi secara visual.

---

## 🛠️ Tech Stack

* **Core Engine**: Python, OpenCV, Ultralytics YOLOv11
* **Web Framework**: Flask
* **Frontend UI**: HTML5, CSS3, JavaScript (Chart.js)
* **Audio Alerts**: HTML5 Audio API / Native Audio Player
* **Data Logging**: CSV-based Trip Logger

---

## 📂 Struktur Repositori

```text
PoseEstimation/
├── reports/              # Arsip rekapitulasi data perjalanan
├── snapshots/            # Tangkapan layar insiden distraksi
├── static/
│   ├── css/style.css     # Tata letak dan tema antarmuka
│   ├── js/               # Logika frontend dan grafik visual
│   └── sounds/           # Berkas efek suara (alarm.mp3, safe.mp3)
├── templates/
│   └── index.html        # Halaman dashboard monitoring
├── app.py                # Server Flask & alur inferensi utama
├── laporan_perjalanan.csv# Berkas log data perjalanan aktif
├── requirements.txt      # Daftar dependensi modul Python
└── README.md
