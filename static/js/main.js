const statusText = document.getElementById('status-text');
const imgElement = document.getElementById('videoStream');
const videoWrapper = document.querySelector('.video-wrapper'); // Ambil wrapper pembungkus
const ctx = document.getElementById('focusChart').getContext('2d');

// --- CHART SETUP ---
let gradient = ctx.createLinearGradient(0, 0, 0, 300);
gradient.addColorStop(0, 'rgba(255, 255, 255, 0.3)'); 
gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

const initialData = {
    labels: Array(60).fill(''),
    datasets: [{
        label: 'Focus Score',
        data: Array(60).fill(100),
        borderColor: '#ffffff', 
        backgroundColor: gradient,
        borderWidth: 2,
        tension: 0.4,
        pointRadius: 0,
        fill: true
    }]
};

const focusChart = new Chart(ctx, {
    type: 'line',
    data: initialData,
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: {
            x: { display: false },
            y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.05)' } }
        },
        plugins: { legend: { display: false } }
    }
});

// --- MAIN LOOP ---
function updateDashboard() {
    fetch('/status_feed')
        .then(response => response.json())
        .then(data => {
            // Update Text
            document.getElementById('fps-val').innerText = data.fps;
            let sourceName = data.source.length > 15 ? data.source.substring(0, 15) + "..." : data.source;
            document.getElementById('source-val').innerText = sourceName;

            // Update Bar & Score
            let score = data.score;
            const barFill = document.getElementById('focus-bar');
            document.getElementById('focus-text').innerText = score + "%";
            barFill.style.width = score + "%";

            // Warna Bar
            let colorGradient = "";
            let shadowColor = "";

            if (score > 50) {
                // AMAN
                colorGradient = "linear-gradient(90deg, #00b09b, #96c93d)";
                shadowColor = "rgba(150, 201, 61, 0.5)";
            } else if (score > 20) {
                // WARNING
                colorGradient = "linear-gradient(90deg, #f83600, #f9d423)";
                shadowColor = "rgba(249, 212, 35, 0.5)";
            } else {
                // BAHAYA
                colorGradient = "linear-gradient(90deg, #ff416c, #ff4b2b)";
                shadowColor = "rgba(255, 75, 43, 0.5)";
            }

            barFill.style.background = colorGradient;
            barFill.style.boxShadow = `0 0 15px ${shadowColor}`;

            // Update Chart
            focusChart.data.datasets[0].data.shift();
            focusChart.data.datasets[0].data.push(score);
            focusChart.update();
        })
        .catch(err => console.log("Waiting connection..."));
}

setInterval(updateDashboard, 1000);

// --- CONTROLS ---
const sliderConf = document.getElementById('confSlider');
const labelConf = document.getElementById('confValue');
sliderConf.oninput = function() { labelConf.innerText = this.value; }
sliderConf.onchange = function() {
    const formData = new FormData();
    formData.append('val', this.value);
    fetch('/api/set_conf', { method: 'POST', body: formData })
    .then(() => showStatus("SENSITIVITY UPDATED"));
}

const sliderLogic = document.getElementById('logicSlider');
const labelLogic = document.getElementById('logicValue');
sliderLogic.oninput = function() { labelLogic.innerText = this.value; }
sliderLogic.onchange = function() {
    const formData = new FormData();
    formData.append('val', this.value);
    fetch('/api/set_logic', { method: 'POST', body: formData })
    .then(() => showStatus("LOGIC RADIUS UPDATED"));
}

// --- FUNGSI UPLOAD YANG SUDAH DIPERBAIKI ---
function uploadFile(type) {
    let inputId = type === 'video' ? 'videoInput' : 'imageInput';
    let route = type === 'video' ? '/upload_video' : '/upload_image';
    
    let input = document.getElementById(inputId);
    if (input.files.length === 0) return;

    let formData = new FormData();
    formData.append('file', input.files[0]);

    showStatus("UPLOADING & PROCESSING...");
    
    fetch(route, { method: 'POST', body: formData })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            showStatus("ANALYSIS COMPLETE");
            
            // LOGIKA GANTI TAMPILAN
            if (data.type === 'video') {
                // Jika Video: Hapus IMG, Ganti dengan Tag VIDEO HTML5
                videoWrapper.innerHTML = `
                    <video id="videoStream" src="${data.url}" controls autoplay loop 
                           style="width: 100%; height: 100%; object-fit: cover; border-radius: 12px;">
                    </video>`;
            } else {
                // Jika Gambar: Pastikan elemen IMG ada
                videoWrapper.innerHTML = `<img id="videoStream" src="${data.url}?t=${new Date().getTime()}" alt="Result">`;
            }
        } else {
            showStatus("UPLOAD FAILED");
        }
    })
    .catch(err => {
        showStatus("ERROR UPLOADING");
        console.error(err);
    });
}

function resetToWebcam() {
    showStatus("SWITCHING TO WEBCAM...");
    fetch('/reset_camera', { method: 'POST' }).then(() => {
        showStatus("SOURCE: LIVE WEBCAM");
        // Kembalikan ke elemen IMG untuk Webcam Stream
        videoWrapper.innerHTML = `<img id="videoStream" src="/video_feed" alt="Camera">`;
    });
}

function takeSnapshot() {
    fetch('/take_snapshot', { method: 'POST' }).then(res => res.json()).then(data => {
        if(data.status==='success') showStatus("SNAPSHOT SAVED!");
    });
}

function showStatus(msg) {
    statusText.innerText = msg;
    statusText.style.opacity = 1;
    setTimeout(() => { statusText.style.opacity = 0.7; }, 2000);
}

// --- FITUR TES TELEGRAM ---
function testTelegram() {
    showStatus("SENDING TELEGRAM TEST...");
    
    fetch('/test_telegram', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if(data.status === 'success') {
            showStatus("✅ TEST MESSAGE SENT!");
        } else {
            showStatus("❌ FAILED TO SEND");
        }
    })
    .catch(err => showStatus("ERROR CONNECTION"));
}