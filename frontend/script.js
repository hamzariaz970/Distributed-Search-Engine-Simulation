// Three.js Background
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById("bg"), alpha: true });

renderer.setSize(window.innerWidth, window.innerHeight);
camera.position.z = 30;

const geometry = new THREE.SphereGeometry(50, 64, 64);
const material = new THREE.MeshBasicMaterial({ color: 0x0a0a23, wireframe: true });
const sphere = new THREE.Mesh(geometry, material);
scene.add(sphere);

function animate() {
  requestAnimationFrame(animate);
  sphere.rotation.y += 0.002;
  renderer.render(scene, camera);
}
animate();

// Search & Download Logic
document.getElementById("searchBtn").addEventListener("click", async () => {
  const query = document.getElementById("queryInput").value;
  const response = await fetch("http://localhost:8000/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query })
  });

  const data = await response.json();
  const resultsDiv = document.getElementById("results");
  resultsDiv.innerHTML = "";

  data.results.forEach(res => {
    const card = document.createElement("div");
    card.className = "result-card";
    card.innerHTML = `
      <h3>${res.title}</h3>
      <p><strong>Authors:</strong> ${res.author}</p>
      <p><strong>Path:</strong> ${res.path}</p>
      <button onclick="download('${res.basename}')">Download</button>
    `;
    resultsDiv.appendChild(card);
  });
});

function download(filename) {
  fetch("http://localhost:8000/api/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename })
  }).then(() => alert("Download triggered for " + filename));
}
