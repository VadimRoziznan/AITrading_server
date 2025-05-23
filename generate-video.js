const { createCanvas } = require("canvas");
const gl = require("gl"); // Импортируем headless-gl
const THREE = require("three");
const ffmpeg = require("fluent-ffmpeg");
const fs = require("fs");
const path = require("path");

// Путь к видеофайлу
const videoPath = path.join(__dirname, "MengerSponge.mp4");

// Функция для создания губки Менгера
function createMengerSponge(size, level, material) {
  const group = new THREE.Group();

  if (level === 0) {
    const geometry = new THREE.BoxGeometry(size, size, size);
    const cube = new THREE.Mesh(geometry, material);
    group.add(cube);
  } else {
    const newSize = size / 3;
    for (let x = -1; x <= 1; x++) {
      for (let y = -1; y <= 1; y++) {
        for (let z = -1; z <= 1; z++) {
          const sum = Math.abs(x) + Math.abs(y) + Math.abs(z);
          if (sum > 1) {
            const child = createMengerSponge(newSize, level - 1, material);
            child.position.set(x * newSize, y * newSize, z * newSize);
            group.add(child);
          }
        }
      }
    }
  }

  return group;
}

// Функция для рендеринга видео
async function renderVideo() {
  return new Promise((resolve, reject) => {
    const width = 1920;
    const height = 1080;
    const frames = 240; // Количество кадров (например, 240 кадров для 8 секунд при 30 FPS)
    const fps = 30;

    // Создаем WebGL-контекст с помощью headless-gl
    const glContext = gl(width, height);

    // Создаем canvas
    const canvas = createCanvas(width, height);
    const context = canvas.getContext("2d");

    // Создаем сцену, камеру и губку Менгера
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.z = 5;

    const material = new THREE.MeshNormalMaterial();
    const sponge = createMengerSponge(2, 2, material);
    scene.add(sponge);

    // Создаем WebGLRenderer и передаем ему контекст из headless-gl
    const renderer = new THREE.WebGLRenderer({
      context: glContext, // Передаем контекст WebGL
      antialias: true,
    });
    renderer.setSize(width, height);

    // Настраиваем вращение
    const rotationPerFrame = (Math.PI * 2) / frames;

    // Создаем поток для ffmpeg
    const ffmpegProcess = ffmpeg()
      .addInput("pipe:0")
      .inputFormat("image2pipe")
      .outputOptions(["-r " + fps, "-pix_fmt yuv420p"])
      .output(videoPath)
      .on("end", resolve)
      .on("error", reject)
      .run();

    // Рендерим кадры
    for (let i = 0; i < frames; i++) {
      sponge.rotation.x += rotationPerFrame;
      sponge.rotation.y += rotationPerFrame;

      renderer.render(scene, camera);

      // Передаем текущий кадр в ffmpeg
      const buffer = canvas.toBuffer("image/png");
      ffmpegProcess.stdin.write(buffer);
    }

    ffmpegProcess.stdin.end();
  });
}

// Генерация видео
console.log("Начинается генерация видео...");
renderVideo()
  .then(() => console.log("Видео успешно создано:", videoPath))
  .catch((err) => console.error("Ошибка генерации видео:", err));